"""E1M3 "The Cistern" - a level modelled in Blender with non-destructive boolean (CSG) brushes.

Run:  blender -b --factory-startup -P tools/blender/build_cistern.py
Writes:
  tools/blender/cistern.blend       editable source (open it in Blender 4.2+/5.x)
  game/levels/blender/cistern.glb   what Godot imports

How the .blend is organised (the "CSG in Blender" workflow):
  * "Shell"      one big solid block with a Boolean modifier (Difference, operand = the
                 "Carve" collection, Exact solver, material mode = Transfer).
  * "Carve"      cutter brushes: boxes for rooms, cylinders for barrel/groin vaults and arches.
                 Each cutter carries its own materials - bottom face = floor, top/curved faces =
                 ceiling, sides = walls - which the boolean transfers onto the carved surfaces.
                 Move/scale a cutter and the level updates live.
  * "Detail"     additive geometry: columns, stairs, railings, crates, pipes.
  * "Entities"   empties named ENT_<kind>_<n> (grunt, health, wall_lamp, ...). Godot's import
                 script (addons/brushfire_tools/blender_level_import.gd) swaps them for the game's
                 scenes. ENT_light empties carry custom properties energy/range/color.
  * "Preview"    Blender lights for viewport preview only (not exported).

Exporting (the bottom of this script, or File > Export > glTF with the same options) applies the
booleans on a copy, projects world-aligned UVs at the texel density from materials.json
(same as the CSG and TrenchBroom levels), culls the unseen outside of the shell and writes one
"Level-col" mesh (Godot makes a trimesh collider from the -col suffix) plus the entity empties.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blendkit import (GAME, HERE, ROOT, B, add_world_uv, box_bm, collection, cylinder_bm,  # noqa: E402
                      export_level, material, mesh_object)

sys.path.insert(0, os.path.join(ROOT, "tools", "godot"))
import detailing  # noqa: E402

STYLE = {"tech_panel": "tech", "concrete": "tech", "rust_metal": "tech", "brick_wall": "brick", "stone_blocks": "stone"}

BLEND = os.path.join(HERE, "cistern.blend")
GLB = os.path.join(GAME, "levels", "blender", "cistern.glb")


# ----------------------------------------------------------------------------- scene setup

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Cistern"
    scene.unit_settings.system = "METRIC"
    return scene


class Level:
    def __init__(self):
        self.carve = collection("Carve")
        self.detail = collection("Detail")
        self.entities = collection("Entities")
        self.preview = collection("Preview")
        self.n = {}
        self.rooms = []

    def _name(self, prefix):
        self.n[prefix] = self.n.get(prefix, 0) + 1
        return f"{prefix}_{self.n[prefix]:02d}"

    # carved spaces --------------------------------------------------------
    def room(self, name, lo, hi, wall, floor, ceiling, trims=True):
        self.rooms.append(detailing.Room(name, (lo[0], hi[0]), (lo[1], hi[1]), (lo[2], hi[2]), STYLE.get(wall, "tech"),
                                         trims))
        bm = box_bm(lo, hi, {"side": 0, "bottom": 1, "top": 2})
        ob = mesh_object(name, bm, self.carve, [wall, floor, ceiling])
        ob.display_type = "WIRE"
        ob.hide_render = True
        return ob

    def vault(self, name, center, radius, length, axis, surface, ends):
        bm = cylinder_bm(center, radius, length, axis, 0, 1, segments=32)
        ob = mesh_object(name, bm, self.carve, [surface, ends])
        ob.display_type = "WIRE"
        ob.hide_render = True
        return ob

    # additive detail -------------------------------------------------------
    def block(self, lo, hi, mat, skip=("bottom",), name=None):
        bm = box_bm(lo, hi, {"side": 0, "bottom": 0, "top": 0}, skip)
        return mesh_object(name or self._name("Block"), bm, self.detail, [mat])

    def column(self, x, z, y0, y1, radius, mat, cap_mat=None, name=None):
        bm = cylinder_bm((x, (y0 + y1) / 2, z), radius, y1 - y0, "y", 0, 0, segments=16, caps=False)
        ob = mesh_object(name or self._name("Column"), bm, self.detail, [mat])
        if cap_mat:  # square plinth and capital
            self.block((x - radius * 1.3, y0, z - radius * 1.3), (x + radius * 1.3, y0 + 0.5, z + radius * 1.3), cap_mat)
            self.block((x - radius * 1.3, y1 - 0.4, z - radius * 1.3), (x + radius * 1.3, y1, z + radius * 1.3), cap_mat,
                       skip=("top",))
        return ob

    def pipe(self, center, radius, length, axis, mat):
        bm = cylinder_bm(center, radius, length, axis, 0, 0, segments=12, caps=False)
        return mesh_object(self._name("Pipe"), bm, self.detail, [mat])

    def arch_ring(self, center, y_spring, radius, span, face, out, y_floor=0.0, depth=0.32, width=0.5, blocks=9):
        """Romanesque arch around a round opening: bevelled voussoirs + jambs + plinths.
        span = axis the opening spans ('x' or 'z'); face = wall plane coordinate on the other
        horizontal axis; out = +1/-1 direction the ring stands proud of the wall."""
        def P(u, v, w):
            return (center + u, v, w) if span == "x" else (w, v, center + u)
        w0, w1 = face, face + out * depth
        for i in range(blocks):
            t0, t1 = math.pi * i / blocks, math.pi * (i + 1) / blocks
            pts = []
            for t in (t0, t1):
                for r in (radius, radius + width + (0.12 if i == blocks // 2 else 0.0)):
                    for w in (w0, w1 + (out * 0.06 if i == blocks // 2 else 0.0)):
                        pts.append(P(math.cos(t) * r, y_spring + math.sin(t) * r, w))
            bm = bmesh.new()
            for p in pts:
                bm.verts.new(B(*p))
            bmesh.ops.convex_hull(bm, input=bm.verts)
            ob = mesh_object(self._name("Voussoir"), bm, self.detail,
                             ["tech_panel" if i == blocks // 2 else "stone_blocks"])
            bev = ob.modifiers.new("Bevel", "BEVEL")
            bev.width, bev.segments, bev.limit_method = 0.035, 1, "ANGLE"
        for sgn in (-1, 1):
            u0, u1 = sorted((sgn * radius, sgn * (radius + width)))
            lo, hi = P(u0, y_floor, min(w0, w1)), P(u1, y_spring, max(w0, w1))
            ob = self.block(tuple(min(a, b) for a, b in zip(lo, hi)), tuple(max(a, b) for a, b in zip(lo, hi)), "stone_blocks")
            ob.modifiers.new("Bevel", "BEVEL").width = 0.035
            lo, hi = P(u0 - 0.06, y_floor, min(w0, w1) - 0.06), P(u1 + 0.06, y_floor + 0.45, max(w0, w1) + 0.06)
            ob = self.block(tuple(min(a, b) for a, b in zip(lo, hi)), tuple(max(a, b) for a, b in zip(lo, hi)), "tech_panel")
            ob.modifiers.new("Bevel", "BEVEL").width = 0.03

    # entities --------------------------------------------------------------
    def ent(self, kind, pos, yaw=0.0, **props):
        e = bpy.data.objects.new(self._name(f"ENT_{kind}"), None)
        e.empty_display_type = "ARROWS" if kind not in ("wall_lamp", "ceiling_light", "light") else "SPHERE"
        e.empty_display_size = 0.5
        e.location = B(*pos)
        e.rotation_euler = (0, 0, math.radians(yaw))
        for k, v in props.items():
            e[k] = v
        self.entities.objects.link(e)
        if kind in ("wall_lamp", "ceiling_light", "light"):
            ld = bpy.data.lights.new(e.name + "_preview", "POINT")
            ld.energy = props.get("energy", 1.5) * 150
            col = props.get("color", (1.0, 0.85, 0.65))
            ld.color = col[:3]
            lo = bpy.data.objects.new(e.name + "_preview", ld)
            lo.location = e.location + (Vector((0, 0, -0.4)) if kind == "ceiling_light" else Vector((0, 0, 0)))
            self.preview.objects.link(lo)
        return e


# ----------------------------------------------------------------------------- the level

def build():
    L = Level()
    # Solid block the rooms are carved from.
    shell_bm = box_bm((-36, -5, -40), (36, 13, 54), {"side": 0, "bottom": 0, "top": 0})
    shell = mesh_object("Shell", shell_bm, bpy.context.scene.collection, ["stone_blocks"])

    # --- entry chamber with a barrel vault
    L.room("Entry", (-5, 0, 40), (5, 5.2, 50), "stone_blocks", "floor_tiles", "brick_wall")
    L.vault("EntryVault", (0, 5.2, 45), 4.99, 9.98, "z", "brick_wall", "stone_blocks")
    # --- tunnel to the cistern (arched)
    L.room("TunnelS", (-2, 0, 28.4), (2, 3, 40.1), "brick_wall", "diamond_plate", "brick_wall")
    L.vault("TunnelSVault", (0, 3, 34.26), 2.0, 11.66, "z", "brick_wall", "brick_wall")
    L.room("DoorS", (-1.5, 0, 27.9), (1.5, 3.2, 28.5), "tech_panel", "diamond_plate", "tech_panel", trims=False)

    # --- the great cistern: walkway level + sunken pit, groin-vaulted ceiling
    L.room("Cistern", (-18, 0, -10), (18, 7, 28), "stone_blocks", "concrete", "brick_wall")
    L.room("Pit", (-11, -3, -2), (11, 0.01, 20), "stone_blocks", "concrete", "concrete", trims=False)
    for i, x in enumerate((-8, 0, 8)):
        L.vault(f"VaultNS{i}", (x, 7, 9), 4.0, 37.98, "z", "brick_wall", "brick_wall")
    for i, z in enumerate((1, 9, 17)):
        L.vault(f"VaultEW{i}", (0, 7, z), 4.0, 35.98, "x", "brick_wall", "brick_wall")
    # secret crawlspace (crouch!) off the pit's east wall, and the room behind it
    L.room("Crawl", (10.9, -3, 8), (15.1, -1.8, 10), "stone_blocks", "stone_blocks", "stone_blocks", trims=False)
    L.room("SecretRoom", (15, -3, 7), (17.5, -0.9, 11), "stone_blocks", "stone_blocks", "stone_blocks", trims=False)

    # --- west pump room through an arched doorway
    L.room("PumpRoom", (-32, 0, 0), (-18.4, 6, 14), "brick_wall", "floor_tiles", "ceiling_tiles")
    L.room("ArchW", (-18.6, 0, 5), (-17.8, 3.2, 9), "stone_blocks", "concrete", "stone_blocks", trims=False)
    L.vault("ArchWTop", (-18.2, 3.2, 7), 2.0, 0.8, "x", "stone_blocks", "stone_blocks")

    # --- east overflow gallery, raised 2 m, reached by stairs + landing
    L.room("Overflow", (18.4, 2, -8), (30, 8, 20), "tech_panel", "diamond_plate", "ceiling_tiles")
    L.room("ArchE", (17.8, 2, 8), (18.6, 5.2, 12), "stone_blocks", "diamond_plate", "stone_blocks", trims=False)
    L.vault("ArchETop", (18.2, 5.2, 10), 2.0, 0.8, "x", "stone_blocks", "stone_blocks")

    # --- north tunnel and exit chamber
    L.room("DoorN", (-1.5, 0, -10.5), (1.5, 3.2, -9.9), "tech_panel", "diamond_plate", "tech_panel", trims=False)
    L.room("TunnelN", (-2, 0, -22.1), (2, 3, -10.4), "brick_wall", "diamond_plate", "brick_wall")
    L.vault("TunnelNVault", (0, 3, -16.25), 2.0, 11.66, "z", "brick_wall", "brick_wall")
    L.room("ExitChamber", (-6, 0, -34), (6, 6.2, -22), "stone_blocks", "floor_tiles", "brick_wall")
    L.vault("ExitVault", (0, 6.2, -28), 5.99, 11.98, "z", "brick_wall", "stone_blocks")

    mod = shell.modifiers.new("Carve", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.operand_type = "COLLECTION"
    mod.collection = L.carve
    mod.solver = "EXACT"
    mod.material_mode = "TRANSFER"
    mod.use_hole_tolerant = True

    # --- detail brushes
    for x in (-12, -4, 4, 12):
        for z in (-3, 5, 13, 21):
            y0 = -3 if (-11 < x < 11 and -2 < z < 20) else 0
            L.column(x, z, y0, 7.2, 0.55, "stone_blocks", "tech_panel")
    # pit stairs (south), 8 x 0.375 m
    for k in range(8):
        top = -0.375 * (k + 1)
        z1 = 20 - 0.5 * k
        L.block((-2, -3, z1 - 0.5), (2, top, z1), "diamond_plate")
    # railings along the pit edge (gap at the stairs)
    rail = "rust_metal"
    L.block((-11, 0, -2.25), (11, 1.0, -2.0), rail, skip=("bottom",))
    L.block((-11.25, 0, -2.25), (-11, 1.0, 20.25), rail, skip=("bottom",))
    L.block((11, 0, -2.25), (11.25, 1.0, 20.25), rail, skip=("bottom",))
    L.block((-11, 0, 20), (-2, 1.0, 20.25), rail, skip=("bottom",))
    L.block((2, 0, 20), (11, 1.0, 20.25), rail, skip=("bottom",))
    # stairs up to the east gallery + landing
    for k in range(5):
        top = 0.4 * (k + 1)
        z1 = 16 - 0.8 * k
        L.block((14.5, 0, z1 - 0.8), (18, top, z1), "diamond_plate")
    L.block((14.5, 0, 8), (18, 2, 12), "diamond_plate")
    L.block((14.5, 2, 7.75), (18, 3.0, 8), "hazard_stripes", skip=())
    # pipes along the cistern walls
    L.pipe((-17.6, 5.5, 9), 0.35, 38, "z", "rust_metal")
    L.pipe((17.6, 5.5, 9), 0.35, 38, "z", "rust_metal")
    L.pipe((0, 6.2, -9.6), 0.3, 36, "x", "rust_metal")
    # pump room machinery and crates
    for i, z in enumerate((3.5, 10.5)):
        L.column(-28, z, 0, 3.2, 1.2, "rust_metal", "tech_panel", name=f"Pump_{i}")
    L.block((-31, 0, 12), (-29, 2, 14), "crate_large")
    L.block((-29, 0, 13), (-28, 1, 14), "crate")
    L.block((-22, 0, 0.5), (-20, 2, 2.5), "crate_large")
    L.block((-20, 0, 0.5), (-19, 1, 1.5), "crate")
    # overflow gallery cover
    L.block((22, 2, 2), (24, 4, 4), "crate_large")
    L.block((25, 2, 12), (27, 3.2, 13), "hazard_stripes")
    L.block((21, 2, -5), (23, 4, -3), "crate_large")
    # exit chamber dais
    L.block((-2.5, 0, -31), (2.5, 0.3, -26), "hazard_stripes")
    # UT99-style trims generated from the room list (openings, arches and tunnels are skipped)
    for lo, hi, mat in detailing.all_trims(L.rooms):
        ob = L.block(lo, hi, mat, skip=())
        ob.modifiers.new("Bevel", "BEVEL").width = 0.02
    # stone arch rings around the round tunnel mouths and side arches (Unreal 1 style)
    L.arch_ring(0, 3.0, 2.0, "x", 40.0, +1)            # entry -> south tunnel
    L.arch_ring(0, 3.0, 2.0, "x", -22.0, -1)           # north tunnel -> exit chamber
    L.arch_ring(7, 3.2, 2.0, "z", -18.0, +1)           # cistern side of the west arch
    L.arch_ring(7, 3.2, 2.0, "z", -18.4, -1)           # pump room side
    L.arch_ring(10, 5.2, 2.0, "z", 18.0, -1, y_floor=2.0)   # cistern side of the east arch
    L.arch_ring(10, 5.2, 2.0, "z", 18.4, +1, y_floor=2.0)   # overflow gallery side

    # --- entities
    E = L.ent
    E("player_start", (0, 0.05, 47), 0)
    E("doorway", (0, 0, 28.2), 0)
    E("doorway", (0, 0, -10.2), 0)
    # lights (static, baked)
    E("ceiling_light", (0, 10.1, 45))
    for z in (32, 37):
        E("wall_lamp", (-1.95, 2.4, z), -90)
        E("wall_lamp", (1.95, 2.4, z), 90)
    for z in (-6, 4, 14, 24):
        E("wall_lamp", (-17.95, 3.0, z), -90)
        E("wall_lamp", (17.95, 3.0, z), 90)
    for x in (-10, 10):
        E("wall_lamp", (x, 3.0, -9.95), 180)
        E("wall_lamp", (x, 3.0, 27.95), 0)
    for x in (-8, 0, 8):
        for z in (1, 17):
            E("ceiling_light", (x, 10.9, z))
    for p in ((-6, -1.5, 9), (6, -1.5, 9), (0, -1.5, 1), (0, -1.5, 17)):
        E("light", p, energy=1.4, range=9.0, color=(0.45, 0.8, 1.0))
    E("light", (13.5, -2.4, 9), energy=0.8, range=4.0, color=(1.0, 0.7, 0.4))
    E("wall_lamp", (16.25, -1.6, 10.95), 0)
    for z in (4, 10):
        E("ceiling_light", (-24, 5.9, z))
    E("light", (-28, 4.0, 7), energy=1.2, range=7.0, color=(1.0, 0.55, 0.25))
    for z in (-2, 8, 16):
        E("ceiling_light", (24, 7.9, z))
    for z in (-14, -19):
        E("wall_lamp", (-1.95, 2.4, z), -90)
        E("wall_lamp", (1.95, 2.4, z), 90)
    E("ceiling_light", (0, 12.1, -28))
    E("wall_lamp", (-5.95, 2.5, -28), -90)
    E("wall_lamp", (5.95, 2.5, -28), 90)

    # monsters
    for kind, p, yaw in (
            ("grunt", (0, 0, 33), 180),
            ("grunt", (-14, 0, 24), 180), ("grunt", (14, 0, 0), 150), ("grunt", (-14, 0, -6), 200),
            ("brute", (-6, -3, 12), 180), ("brute", (6, -3, 2), 180), ("grunt", (0, -3, 6), 180),
            ("drone", (-6, 4, 5), 180), ("drone", (7, 5, 13), 180),
            ("grunt", (-24, 0, 7), -90), ("grunt", (-30, 0, 2), -60), ("drone", (-26, 3.5, 11), -90),
            ("grunt", (26, 2, 6), 90), ("brute", (26, 2, -4), 90),
            ("grunt", (0, 0, -16), 180), ("brute", (-3, 0, -30), 180), ("drone", (3, 4, -27), 180)):
        E(kind, p, yaw)
    # pickups & hazards
    for kind, p in (
            ("shells", (3, 0, 44)), ("armor", (-3, 0, 44)), ("health", (0, 0, 38)),
            ("chaingun", (0, -3, 10)), ("bullets", (-9, -3, 0)), ("health", (9, -3, 18)), ("shells", (-9, -3, 18)),
            ("health", (-16, 0, 26)), ("health", (16, 0, -8)), ("bullets", (16, 0, 26)),
            ("megahealth", (16.5, -3, 9)),
            ("shells", (-30, 0, 8)), ("health", (-20, 0, 12)), ("rockets", (-25, 0, 1)),
            ("rocket_launcher", (28, 2, 16)), ("rockets", (28, 2, 14)), ("armor_heavy", (28, 2, -6)),
            ("health", (0, 0, -20)), ("bullets", (4.5, 0, -24)), ("health", (-4.5, 0, -24))):
        E(kind, p)
    for p in ((-15, 0, 18), (-15.8, 0, 17.2), (15.5, 0, -4), (-25, 0, 13), (-24.2, 0, 12.4), (20, 2, 0)):
        E("barrel", p)
    E("exit", (0, 0.3, -28.5))
    E("secret", (16.25, -3, 9), size=(2.5, 2.1, 4.0))
    E("message", (0, 0, 30), size=(4.0, 3.0, 1.0), text="Something is hidden low in the pit. Crouch (Ctrl) to crawl.")
    return shell


# ----------------------------------------------------------------------------- export

def main():
    reset()
    shell = build()
    # Live world-aligned UVs so the level previews with the right texture scale in Blender.
    for ob in [shell] + list(bpy.data.collections["Detail"].objects):
        add_world_uv(ob)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True, compress=True)
    print("[cistern] saved", BLEND)
    export_level(GLB)


if __name__ == "__main__":
    main()
