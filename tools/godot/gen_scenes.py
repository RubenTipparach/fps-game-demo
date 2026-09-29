#!/usr/bin/env python3
"""Generate the game's prop/actor scenes and their materials.

Weapons, enemies, pickups and props are assembled from primitive meshes (old-school rigid
"segment" models, animated procedurally in C#). Defining them here keeps transforms readable.

    python3 tools/godot/gen_scenes.py

Outputs .tscn/.tres files under game/. They are ordinary Godot scenes: tweak them in the editor
afterwards if you like (re-running this script overwrites them).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tscn import Raw, Resource, Scene, color, hexcolor, path, v2, v3  # noqa: E402

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "game")


def out(rel):
    return os.path.join(GAME, rel)


# ============================================================================ materials

def std_mat(file, **props):
    r = Resource("StandardMaterial3D", **props)
    r.save(out(file))
    return "res://" + file


def orm_mat(file, tex, tint="#ffffff", triplanar=True, scale=1.0, world=False, normal_scale=1.0, **extra):
    r = Resource("ORMMaterial3D")
    r.props = dict(
        resource_name=os.path.basename(file).split(".")[0],
        albedo_color=hexcolor(tint),
        albedo_texture=r.ext_res("Texture2D", f"res://textures/{tex}.png"),
        metallic=1.0,
        roughness=1.0,
        orm_texture=r.ext_res("Texture2D", f"res://textures/{tex}_orm.png"),
        normal_enabled=True,
        normal_scale=normal_scale,
        normal_texture=r.ext_res("Texture2D", f"res://textures/{tex}_normal.png"),
        texture_filter=5,
    )
    if triplanar:
        r.props.update(uv1_scale=v3(scale, scale, scale), uv1_triplanar=True, uv1_world_triplanar=world,
                       uv1_triplanar_sharpness=4.0)
    r.props.update(extra)
    r.save(out(file))
    return "res://" + file


def glow_mat(file, hex_, energy=4.0, unshaded=False):
    props = dict(albedo_color=hexcolor(hex_), emission_enabled=True, emission=hexcolor(hex_),
                 emission_energy_multiplier=energy, roughness=0.4)
    if unshaded:
        props["shading_mode"] = 0
    return std_mat(file, **props)


MAT = {}


def make_materials():
    MAT["gunmetal"] = std_mat("materials/props/gunmetal.tres", albedo_color=hexcolor("#2b2d31"), metallic=1.0, roughness=0.36)
    MAT["gunmetal_light"] = std_mat("materials/props/gunmetal_light.tres", albedo_color=hexcolor("#5a5d63"), metallic=1.0, roughness=0.45)
    MAT["wood"] = std_mat("materials/props/gun_wood.tres", albedo_color=hexcolor("#5c3a1d"), metallic=0.0, roughness=0.55)
    MAT["rubber"] = std_mat("materials/props/rubber.tres", albedo_color=hexcolor("#141414"), metallic=0.0, roughness=0.85)
    MAT["white"] = std_mat("materials/props/white_plastic.tres", albedo_color=hexcolor("#d9d8d0"), metallic=0.0, roughness=0.45)
    MAT["olive"] = std_mat("materials/props/ammo_olive.tres", albedo_color=hexcolor("#4b5230"), metallic=0.4, roughness=0.55)
    MAT["shell"] = std_mat("materials/props/shell_red.tres", albedo_color=hexcolor("#9c1c16"), metallic=0.0, roughness=0.4)
    MAT["brass"] = std_mat("materials/props/brass.tres", albedo_color=hexcolor("#b58a3c"), metallic=1.0, roughness=0.28)
    MAT["hazard"] = orm_mat("materials/props/hazard_triplanar.tres", "hazard_stripes", scale=2.0)
    MAT["barrel"] = orm_mat("materials/props/barrel.tres", "rust_metal", tint="#b8392a", scale=1.2)
    MAT["door"] = orm_mat("materials/props/door_metal.tres", "tech_panel", tint="#c8ccd0", scale=0.5)
    # Light fixture panel: object-space triplanar so one texture tile spans the 1.2 x 0.4 m panel.
    r = Resource("ORMMaterial3D")
    r.props = dict(
        resource_name="light_fixture",
        albedo_texture=r.ext_res("Texture2D", "res://textures/light_panel.png"),
        metallic=1.0, roughness=1.0,
        orm_texture=r.ext_res("Texture2D", "res://textures/light_panel_orm.png"),
        normal_enabled=True,
        normal_texture=r.ext_res("Texture2D", "res://textures/light_panel_normal.png"),
        # Multiply operator: only the lit cells glow, the grille stays dark (see postprocess.py)
        emission_enabled=True, emission=color(1, 0.96, 0.88), emission_operator=1, emission_energy_multiplier=9.0,
        emission_texture=r.ext_res("Texture2D", "res://textures/light_panel_emission.png"),
        uv1_scale=v3(0.833, 1.0, 2.5), uv1_offset=v3(0.5, 0.0, 0.5), uv1_triplanar=True, uv1_triplanar_sharpness=8.0,
        texture_filter=5,
    )
    r.save(out("materials/props/light_fixture.tres"))
    MAT["fixture_panel"] = "res://materials/props/light_fixture.tres"
    MAT["cage"] = std_mat("materials/props/lamp_cage.tres", albedo_color=hexcolor("#303235"), metallic=1.0, roughness=0.5)
    MAT["lamp_glow"] = glow_mat("materials/props/lamp_glow.tres", "#ffc27a", 7.0)
    MAT["exit_glow"] = glow_mat("materials/props/exit_glow.tres", "#39ff7a", 3.0)
    MAT["red_cross"] = glow_mat("materials/props/red_cross.tres", "#d01212", 1.2)
    MAT["mega"] = glow_mat("materials/props/megahealth.tres", "#3d7dff", 3.0)
    MAT["armor_green"] = orm_mat("materials/props/armor_green.tres", "tech_panel", tint="#6fbf5a", scale=2.5)
    MAT["armor_red"] = orm_mat("materials/props/armor_red.tres", "tech_panel", tint="#e05030", scale=2.5)
    MAT["stripe_yellow"] = glow_mat("materials/props/stripe_yellow.tres", "#ffc21a", 1.5)
    MAT["status_light"] = glow_mat("materials/props/status_light.tres", "#ff2010", 5.0)
    # UT99-style corona: additive soft glow billboard that fades out when you get close.
    # pink and cyan: Undercity's neon accent pair (openspec/changes/sump-market-hub/design.md)
    for name, hexc in (("corona_warm", "#ffb070"), ("corona_cool", "#7ac8ff"), ("corona_green", "#60ff90"),
                       ("corona_pink", "#ff4fa3"), ("corona_cyan", "#35e0ff")):
        r = Resource("StandardMaterial3D")
        r.props = dict(transparency=1, blend_mode=1, shading_mode=0, billboard_mode=1, billboard_keep_scale=True,
                       albedo_color=hexcolor(hexc, 0.55),
                       albedo_texture=r.ext_res("Texture2D", "res://textures/fx/soft_particle.png"),
                       disable_receive_shadows=True, no_depth_test=False,
                       distance_fade_mode=1, distance_fade_min_distance=0.6, distance_fade_max_distance=2.5)
        r.save(out(f"materials/fx/{name}.tres"))
        MAT[name] = f"res://materials/fx/{name}.tres"

    MAT["grunt"] = orm_mat("materials/enemies/grunt_armor.tres", "tech_panel", tint="#9aa77a", scale=1.4)
    MAT["brute"] = orm_mat("materials/enemies/brute_armor.tres", "rust_metal", tint="#c08870", scale=1.0)
    MAT["drone"] = orm_mat("materials/enemies/drone_shell.tres", "tech_panel", tint="#8aa0c0", scale=1.6)
    MAT["joint"] = std_mat("materials/enemies/joint.tres", albedo_color=hexcolor("#1b1c1f"), metallic=0.6, roughness=0.55)
    MAT["eye_red"] = glow_mat("materials/enemies/eye_red.tres", "#ff2a1a", 6.0)
    MAT["eye_orange"] = glow_mat("materials/enemies/eye_orange.tres", "#ff8a1a", 6.0)
    MAT["eye_cyan"] = glow_mat("materials/enemies/eye_cyan.tres", "#2ae8ff", 6.0)

    r = Resource("StandardMaterial3D")
    r.props = dict(transparency=1, blend_mode=1, cull_mode=2, shading_mode=0,
                   albedo_color=color(1.0, 0.85, 0.6), albedo_texture=r.ext_res("Texture2D", "res://textures/fx/muzzle_flash.png"),
                   disable_receive_shadows=True)
    r.save(out("materials/fx/muzzle_flash.tres"))
    MAT["flash"] = "res://materials/fx/muzzle_flash.tres"
    MAT["plasma"] = glow_mat("materials/fx/plasma.tres", "#6af0ff", 8.0, unshaded=True)
    MAT["exhaust"] = glow_mat("materials/fx/rocket_exhaust.tres", "#ffae4a", 10.0, unshaded=True)


# ============================================================================ helpers

class Builder:
    """Adds primitive mesh parts to a Scene with minimal ceremony."""

    def __init__(self, scene, shadows=True):
        self.s = scene
        self.shadows = shadows
        self._mesh_cache = {}

    def mat(self, key):
        return self.s.ext_res("Material", MAT[key])

    def mesh(self, kind, **props):
        key = (kind, tuple(sorted((k, str(v)) for k, v in props.items())))
        if key not in self._mesh_cache:
            self._mesh_cache[key] = self.s.sub_res(kind, **props)
        return self._mesh_cache[key]

    def part(self, name, parent, kind, mat, pos=(0, 0, 0), rot=(0, 0, 0), scale=None, gi=2, **mesh_props):
        # gi=2 (dynamic): actors, pickups and small props are lit by the lightmap probes rather
        # than being baked into lightmaps (they move, or are too small to be worth UV2 space).
        props = dict(mesh=self.mesh(kind, **mesh_props), material_override=self.mat(mat),
                     position=v3(*pos))
        if any(rot):
            props["rotation_degrees"] = v3(*rot)
        if scale:
            props["scale"] = v3(*scale)
        if not self.shadows:
            props["cast_shadow"] = 0
        if gi is not None:
            props["gi_mode"] = gi
        return self.s.node(name, "MeshInstance3D", parent, **props)

    def box(self, name, parent, mat, size, pos=(0, 0, 0), rot=(0, 0, 0), **kw):
        return self.part(name, parent, "BoxMesh", mat, pos, rot, size=v3(*size), **kw)

    def cyl(self, name, parent, mat, r, h, pos=(0, 0, 0), rot=(0, 0, 0), r2=None, seg=16, **kw):
        return self.part(name, parent, "CylinderMesh", mat, pos, rot, top_radius=float(r),
                         bottom_radius=float(r if r2 is None else r2), height=float(h), radial_segments=seg, rings=1, **kw)

    def sphere(self, name, parent, mat, r, pos=(0, 0, 0), **kw):
        return self.part(name, parent, "SphereMesh", mat, pos, radius=float(r), height=float(2 * r),
                         radial_segments=16, rings=8, **kw)

    def corona(self, name, parent, pos, size=0.9, mat="corona_warm"):
        return self.s.node(name, "MeshInstance3D", parent, position=v3(*pos), cast_shadow=0, gi_mode=0,
                           mesh=self.mesh("QuadMesh", size=v2(size, size)), material_override=self.mat(mat))

    def pivot(self, name, parent, pos=(0, 0, 0), rot=(0, 0, 0)):
        props = dict(position=v3(*pos))
        if any(rot):
            props["rotation_degrees"] = v3(*rot)
        return self.s.node(name, "Node3D", parent, **props)


def script(scene, cs_path):
    return scene.ext_res("Script", cs_path)


# ============================================================================ weapon models

def weapon_models():
    # Shotgun: pump action, wooden furniture. Forward is -Z; units are "full size" metres.
    s = Scene("ShotgunModel", "Node3D")
    b = Builder(s, shadows=False)
    X = 90  # rotate cylinders from Y-up to Z-forward
    b.box("Receiver", ".", "gunmetal", (0.07, 0.09, 0.28))
    b.cyl("Barrel", ".", "gunmetal", 0.019, 0.62, (0, 0.026, -0.44), (X, 0, 0))
    b.cyl("Magazine", ".", "gunmetal_light", 0.015, 0.52, (0, -0.02, -0.39), (X, 0, 0))
    b.box("Rib", ".", "gunmetal", (0.012, 0.01, 0.6), (0, 0.05, -0.43))
    b.box("Sight", ".", "brass", (0.008, 0.014, 0.01), (0, 0.058, -0.72))
    pump = b.pivot("Pump", ".", (0, -0.02, -0.34))
    b.cyl("Forend", pump, "wood", 0.03, 0.18, (0, 0, 0), (X, 0, 0))
    for i, z in enumerate((-0.05, 0.0, 0.05)):
        b.cyl(f"Groove{i}", pump, "gunmetal", 0.031, 0.008, (0, 0, z), (X, 0, 0))
    b.box("Stock", ".", "wood", (0.055, 0.1, 0.32), (0, -0.04, 0.28), (-8, 0, 0))
    b.box("Grip", ".", "wood", (0.048, 0.11, 0.07), (0, -0.085, 0.1), (22, 0, 0))
    b.box("Trigger", ".", "gunmetal", (0.01, 0.04, 0.03), (0, -0.065, 0.02))
    muzzle = s.node("Muzzle", "Marker3D", ".", position=v3(0, 0.026, -0.77))
    b.part("Flash", muzzle, "QuadMesh", "flash", size=v2(0.42, 0.42))
    s.save(out("scenes/weapons/models/shotgun_model.tscn"))

    # Chaingun: six rotating barrels in a housing.
    s = Scene("ChaingunModel", "Node3D")
    b = Builder(s, shadows=False)
    b.box("Housing", ".", "gunmetal", (0.13, 0.14, 0.34))
    b.box("Top", ".", "gunmetal_light", (0.09, 0.03, 0.26), (0, 0.085, 0))
    b.box("Handle", ".", "rubber", (0.05, 0.12, 0.07), (0, -0.11, 0.08), (18, 0, 0))
    b.box("Drum", ".", "olive", (0.11, 0.13, 0.13), (-0.11, -0.03, 0.02))
    b.cyl("Motor", ".", "gunmetal_light", 0.05, 0.08, (0, 0, -0.2), (90, 0, 0))
    barrels = b.pivot("Barrels", ".", (0, 0, -0.42))
    import math
    for i in range(6):
        a = i / 6 * 2 * math.pi
        b.cyl(f"Barrel{i}", barrels, "gunmetal", 0.012, 0.46, (math.cos(a) * 0.034, math.sin(a) * 0.034, 0), (90, 0, 0), seg=8)
    b.cyl("Clamp1", barrels, "gunmetal_light", 0.05, 0.02, (0, 0, -0.1), (90, 0, 0))
    b.cyl("Clamp2", barrels, "gunmetal_light", 0.05, 0.02, (0, 0, 0.14), (90, 0, 0))
    muzzle = s.node("Muzzle", "Marker3D", ".", position=v3(0, 0, -0.68))
    b.part("Flash", muzzle, "QuadMesh", "flash", size=v2(0.36, 0.36))
    s.save(out("scenes/weapons/models/chaingun_model.tscn"))

    # Rocket launcher: fat tube, hazard band, sight.
    s = Scene("RocketLauncherModel", "Node3D")
    b = Builder(s, shadows=False)
    b.cyl("Tube", ".", "gunmetal", 0.065, 0.82, (0, 0.01, -0.18), (90, 0, 0), seg=20)
    b.cyl("Band", ".", "hazard", 0.068, 0.12, (0, 0.01, -0.38), (90, 0, 0), seg=20)
    b.cyl("MuzzleRing", ".", "gunmetal_light", 0.075, 0.06, (0, 0.01, -0.58), (90, 0, 0), seg=20)
    b.cyl("RearRing", ".", "gunmetal_light", 0.072, 0.05, (0, 0.01, 0.22), (90, 0, 0), seg=20)
    b.box("Grip", ".", "rubber", (0.045, 0.12, 0.06), (0, -0.1, 0.02), (18, 0, 0))
    b.box("Sight", ".", "gunmetal_light", (0.03, 0.05, 0.1), (-0.07, 0.08, -0.1))
    b.box("SightGlass", ".", "eye_red", (0.02, 0.02, 0.005), (-0.07, 0.09, -0.152))
    muzzle = s.node("Muzzle", "Marker3D", ".", position=v3(0, 0.01, -0.62))
    b.part("Flash", muzzle, "QuadMesh", "flash", size=v2(0.5, 0.5))
    s.save(out("scenes/weapons/models/rocket_launcher_model.tscn"))


def weapons():
    common = dict()
    s = Scene("Shotgun", "Node3D")
    s.nodes[0][3].update(
        script=script(s, "res://scripts/Player/ShotgunWeapon.cs"), DisplayName="Shotgun", Slot=1, Owned=True,
        Ammo=0, AmmoPerShot=1, FireInterval=0.9, Damage=7.0, Pellets=11, SpreadDegrees=5.0, Range=120.0,
        ViewKick=3.2, KickPush=v3(0, 0.02, 0.16), KickPitch=11.0, FireSound="shotgun_fire", FireVolumeDb=0.0,
        NoiseRadius=40.0, **common)
    s.instance("Model", "res://scenes/weapons/models/shotgun_model.tscn", ".", position=v3(0.24, -0.25, -0.42))
    s.save(out("scenes/weapons/shotgun.tscn"))

    s = Scene("Chaingun", "Node3D")
    s.nodes[0][3].update(
        script=script(s, "res://scripts/Player/ChaingunWeapon.cs"), DisplayName="Chaingun", Slot=2, Owned=False,
        Ammo=1, AmmoPerShot=1, FireInterval=0.075, Damage=9.0, Pellets=1, SpreadDegrees=1.0, Range=250.0,
        ViewKick=0.45, KickPush=v3(0, 0.005, 0.045), KickPitch=1.8, FireSound="chaingun_fire", FireVolumeDb=-4.0,
        NoiseRadius=40.0, Tracers=True)
    s.instance("Model", "res://scenes/weapons/models/chaingun_model.tscn", ".", position=v3(0.22, -0.27, -0.4))
    s.save(out("scenes/weapons/chaingun.tscn"))

    s = Scene("RocketLauncher", "Node3D")
    s.nodes[0][3].update(
        script=script(s, "res://scripts/Player/RocketLauncherWeapon.cs"), DisplayName="Rocket Launcher", Slot=3,
        Owned=False, Ammo=2, AmmoPerShot=1, FireInterval=0.8, Damage=0.0, ViewKick=2.4,
        KickPush=v3(0, 0.03, 0.2), KickPitch=7.0, FireSound="rocket_fire", NoiseRadius=45.0,
        ProjectileScene=s.ext_res("PackedScene", "res://scenes/weapons/rocket.tscn"))
    s.instance("Model", "res://scenes/weapons/models/rocket_launcher_model.tscn", ".", position=v3(0.22, -0.2, -0.3))
    s.save(out("scenes/weapons/rocket_launcher.tscn"))


def particle_trail(s, parent, name, mat_props, amount, lifetime, size, ramp_colors, gravity=(0, 0.6, 0), speed=0.2):
    m = s.sub_res("StandardMaterial3D", **mat_props)
    q = s.sub_res("QuadMesh", size=v2(size, size), material=m)
    g = s.sub_res("Gradient", offsets=Raw("PackedFloat32Array(" + ", ".join(str(o) for o, _ in ramp_colors) + ")"),
                  colors=Raw("PackedColorArray(" + ", ".join(
                      ", ".join(str(x) for x in c) for _, c in ramp_colors) + ")"))
    curve = s.sub_res("Curve", _data=[v2(0, 0.5), 0.0, 0.0, 0, 0, v2(1, 1.6), 0.0, 0.0, 0, 0], point_count=2)
    return s.node(name, "CPUParticles3D", parent, amount=amount, lifetime=lifetime, local_coords=False, mesh=q,
                  direction=v3(0, 0, 1), spread=12.0, initial_velocity_min=speed * 0.5, initial_velocity_max=speed,
                  gravity=v3(*gravity), scale_amount_curve=curve, color_ramp=g, cast_shadow=0)


def projectiles():
    s = Scene("Rocket", "Node3D")
    s.nodes[0][3].update(script=script(s, "res://scripts/Core/Projectile.cs"), Speed=26.0, DirectDamage=100.0,
                         SplashDamage=90.0, SplashRadius=4.2, Knockback=13.0, Kind=1, Explodes=True)
    b = Builder(s, shadows=False)
    b.cyl("Body", ".", "gunmetal_light", 0.045, 0.38, (0, 0, 0), (90, 0, 0), seg=10)
    b.cyl("Nose", ".", "hazard", 0.0, 0.1, (0, 0, -0.24), (-90, 0, 0), r2=0.045, seg=10)
    b.sphere("Flame", ".", "exhaust", 0.06, (0, 0, 0.22))
    s.node("Light", "OmniLight3D", ".", position=v3(0, 0, 0.35), light_color=hexcolor("#ffb060"), light_energy=2.5,
           omni_range=5.0, light_bake_mode=0)
    particle_trail(s, ".", "Trail",
                   dict(transparency=1, shading_mode=2, billboard_mode=3, vertex_color_use_as_albedo=True,
                        albedo_texture=s.ext_res("Texture2D", "res://textures/fx/smoke_puff.png"), roughness=1.0),
                   60, 1.2, 0.5, [(0.0, (0.9, 0.8, 0.7, 0.0)), (0.08, (0.8, 0.75, 0.7, 0.7)), (1.0, (0.4, 0.4, 0.4, 0.0))])
    s.node("Sound", "AudioStreamPlayer3D", ".", stream=s.ext_res("AudioStream", "res://audio/sfx/rocket_fly.wav"),
           autoplay=True, unit_size=6.0, max_distance=60.0, bus="World", volume_db=-4.0)
    s.save(out("scenes/weapons/rocket.tscn"))

    s = Scene("PlasmaBall", "Node3D")
    s.nodes[0][3].update(script=script(s, "res://scripts/Core/Projectile.cs"), Speed=17.0, DirectDamage=14.0,
                         SplashDamage=0.0, SplashRadius=0.0, Knockback=4.0, Kind=3, Explodes=False, Radius=0.2,
                         ImpactColor=color(0.4, 0.9, 1.0))
    b = Builder(s, shadows=False)
    b.sphere("Core", ".", "plasma", 0.14)
    s.node("Light", "OmniLight3D", ".", light_color=hexcolor("#5ae6ff"), light_energy=2.0, omni_range=4.0, light_bake_mode=0)
    particle_trail(s, ".", "Trail",
                   dict(transparency=1, blend_mode=1, shading_mode=0, billboard_mode=3, vertex_color_use_as_albedo=True,
                        albedo_texture=s.ext_res("Texture2D", "res://textures/fx/soft_particle.png")),
                   30, 0.35, 0.3, [(0.0, (0.6, 1.0, 1.0, 0.9)), (1.0, (0.1, 0.4, 1.0, 0.0))], gravity=(0, 0, 0), speed=0.1)
    s.save(out("scenes/enemies/plasma_ball.tscn"))


# ============================================================================ player

def player():
    s = Scene("Player", "CharacterBody3D")
    s.nodes[0][3].update(collision_layer=2, collision_mask=1 | 4,
                         script=script(s, "res://scripts/Player/PlayerController.cs"))
    s.node("CollisionShape3D", "CollisionShape3D", ".", position=v3(0, 0.9, 0),
           shape=s.sub_res("CylinderShape3D", height=1.8, radius=0.4))
    s.node("CameraRig", "Node3D", ".")
    s.node("Camera3D", "Camera3D", "CameraRig", current=True, fov=67.0, near=0.02, far=400.0)
    wm = s.node("WeaponManager", "Node3D", "CameraRig/Camera3D", script=script(s, "res://scripts/Player/WeaponManager.cs"))
    root = s.node("ViewmodelRoot", "Node3D", wm)
    s.instance("Shotgun", "res://scenes/weapons/shotgun.tscn", root)
    s.instance("Chaingun", "res://scenes/weapons/chaingun.tscn", root)
    s.instance("RocketLauncher", "res://scenes/weapons/rocket_launcher.tscn", root)
    s.node("Flashlight", "SpotLight3D", "CameraRig/Camera3D", visible=False, position=v3(0.15, -0.1, 0),
           light_color=hexcolor("#fff1d6"), light_energy=4.0, light_bake_mode=0, shadow_enabled=True,
           spot_range=32.0, spot_angle=26.0, spot_angle_attenuation=0.6)
    s.node("Hud", "CanvasLayer", ".", script=script(s, "res://scripts/UI/Hud.cs"))
    s.save(out("scenes/player/player.tscn"))


# ============================================================================ enemies

def enemy_base(name, kind, hp, speed, extra, radius, height, floating=False):
    s = Scene(name, "CharacterBody3D")
    s.set_root_groups(["enemies"])
    props = dict(collision_layer=4, collision_mask=1 | 2 | 4, script=script(s, "res://scripts/Enemies/Enemy.cs"),
                 Kind=kind, MaxHealth=float(hp), MoveSpeed=float(speed))
    props.update(extra)
    s.nodes[0][3].update(props)
    if floating:
        s.node("CollisionShape3D", "CollisionShape3D", ".", shape=s.sub_res("SphereShape3D", radius=radius))
    else:
        s.node("CollisionShape3D", "CollisionShape3D", ".", position=v3(0, height / 2, 0),
               shape=s.sub_res("CapsuleShape3D", radius=radius, height=height))
        s.node("NavigationAgent3D", "NavigationAgent3D", ".", path_desired_distance=0.7, target_desired_distance=1.2,
               radius=radius, height=height, path_max_distance=4.0)
    s.node("Rig", "Node3D", ".")
    s.node("Voice", "AudioStreamPlayer3D", ".", position=v3(0, height * 0.8 if not floating else 0, 0),
           unit_size=9.0, max_distance=70.0, bus="World")
    return s, Builder(s)


def grunt():
    s, b = enemy_base("Grunt", 0, 60, 4.2, dict(
        EyeHeight=1.7, SightRange=45.0, AttackRange=24.0, AttackCooldown=1.7, WindupTime=0.5, Damage=6.0,
        BurstCount=3, BurstInterval=0.12, Inaccuracy=2.5, PainChance=0.6, DropChance=0.45), 0.42, 1.85)
    s.nodes[0][3]["DropScene"] = s.ext_res("PackedScene", "res://scenes/pickups/bullets_small.tscn")
    for side, x in (("L", -0.16), ("R", 0.16)):
        leg = b.pivot(f"Leg{side}", "Rig", (x, 0.95, 0))
        b.box("Thigh", leg, "joint", (0.16, 0.5, 0.18), (0, -0.25, 0))
        b.box("Shin", leg, "grunt", (0.19, 0.46, 0.21), (0, -0.66, 0.0))
        b.box("Foot", leg, "joint", (0.2, 0.08, 0.32), (0, -0.91, -0.06))
    torso = b.pivot("Torso", "Rig", (0, 1.0, 0))
    b.box("Pelvis", torso, "joint", (0.42, 0.18, 0.26), (0, 0.02, 0))
    b.box("Chest", torso, "grunt", (0.56, 0.5, 0.34), (0, 0.42, 0))
    b.box("Pack", torso, "grunt", (0.42, 0.36, 0.18), (0, 0.45, 0.24))
    b.box("Vent", torso, "eye_red", (0.28, 0.035, 0.02), (0, 0.5, -0.176))
    head = b.pivot("Head", "Rig", (0, 1.7, 0))
    b.box("Helmet", head, "grunt", (0.3, 0.27, 0.32), (0, 0.1, 0))
    b.box("Visor", head, "eye_red", (0.24, 0.06, 0.02), (0, 0.11, -0.165))
    s.node("EyeLight", "OmniLight3D", head, position=v3(0, 0.1, -0.35), light_color=hexcolor("#ff3020"),
           light_energy=0.5, omni_range=2.5, light_bake_mode=0)
    for side, x in (("L", -0.37), ("R", 0.37)):
        arm = b.pivot(f"Arm{side}", "Rig", (x, 1.56, 0))
        b.box("Upper", arm, "joint", (0.14, 0.32, 0.14), (0, -0.16, 0))
        b.box("Fore", arm, "grunt", (0.17, 0.34, 0.17), (0, -0.46, 0))
        if side == "R":
            gun = b.pivot("Gun", arm, (-0.02, -0.6, -0.12), (-90, 0, 0))
            b.box("GunBody", gun, "gunmetal", (0.1, 0.13, 0.55), (0, 0, -0.18))
            b.cyl("GunBarrel", gun, "gunmetal_light", 0.025, 0.3, (0, 0.02, -0.58), (90, 0, 0), seg=10)
            s.node("Muzzle", "Marker3D", gun, position=v3(0, 0.02, -0.76))
    s.save(out("scenes/enemies/grunt.tscn"))


def brute():
    s, b = enemy_base("Brute", 1, 240, 3.4, dict(
        ChargeSpeed=9.0, EyeHeight=2.2, SightRange=40.0, AttackRange=2.9, AttackCooldown=1.1, WindupTime=0.42,
        Damage=26.0, BurstCount=1, PainChance=0.25, TurnSpeed=6.0, DropChance=0.6), 0.7, 2.5)
    s.nodes[0][3]["DropScene"] = s.ext_res("PackedScene", "res://scenes/pickups/health.tscn")
    for side, x in (("L", -0.3), ("R", 0.3)):
        leg = b.pivot(f"Leg{side}", "Rig", (x, 1.15, 0))
        b.box("Thigh", leg, "joint", (0.3, 0.6, 0.32), (0, -0.3, 0))
        b.box("Shin", leg, "brute", (0.36, 0.55, 0.38), (0, -0.8, 0))
        b.box("Foot", leg, "joint", (0.4, 0.14, 0.52), (0, -1.08, -0.08))
    torso = b.pivot("Torso", "Rig", (0, 1.2, 0))
    b.box("Pelvis", torso, "joint", (0.7, 0.26, 0.42), (0, 0.05, 0))
    b.box("Chest", torso, "brute", (1.1, 0.85, 0.7), (0, 0.62, 0))
    b.box("Hump", torso, "brute", (0.8, 0.4, 0.4), (0, 0.95, 0.25), (20, 0, 0))
    b.box("Grille", torso, "eye_orange", (0.5, 0.06, 0.02), (0, 0.55, -0.356))
    head = b.pivot("Head", "Rig", (0, 2.2, -0.15))
    b.box("Skull", head, "brute", (0.42, 0.34, 0.4), (0, 0.05, 0))
    b.box("EyeL", head, "eye_orange", (0.09, 0.05, 0.02), (-0.1, 0.07, -0.205))
    b.box("EyeR", head, "eye_orange", (0.09, 0.05, 0.02), (0.1, 0.07, -0.205))
    s.node("EyeLight", "OmniLight3D", head, position=v3(0, 0.05, -0.45), light_color=hexcolor("#ff8a20"),
           light_energy=0.7, omni_range=3.0, light_bake_mode=0)
    for side, x in (("L", -0.75), ("R", 0.75)):
        arm = b.pivot(f"Arm{side}", "Rig", (x, 2.0, 0))
        b.box("Shoulder", arm, "brute", (0.42, 0.34, 0.46), (0, 0.02, 0))
        b.box("Upper", arm, "joint", (0.24, 0.5, 0.24), (0, -0.4, 0))
        b.box("Fore", arm, "brute", (0.32, 0.55, 0.32), (0, -0.88, 0))
        b.box("Fist", arm, "joint", (0.38, 0.32, 0.38), (0, -1.28, 0))
    s.save(out("scenes/enemies/brute.tscn"))


def drone():
    s, b = enemy_base("Drone", 2, 45, 5.0, dict(
        EyeHeight=0.0, SightRange=45.0, AttackRange=24.0, PreferredRange=9.0, AttackCooldown=2.0, WindupTime=0.6,
        Damage=14.0, BurstCount=1, Inaccuracy=1.5, PainChance=0.5, HoverHeight=2.8, DropChance=0.35,
        FieldOfView=200.0), 0.55, 1.0, floating=True)
    s.nodes[0][3]["ProjectileScene"] = s.ext_res("PackedScene", "res://scenes/enemies/plasma_ball.tscn")
    s.nodes[0][3]["DropScene"] = s.ext_res("PackedScene", "res://scenes/pickups/shells_small.tscn")
    b.sphere("Body", "Rig", "drone", 0.42)
    b.part("Ring", "Rig", "TorusMesh", "joint", (0, 0, 0), (90, 0, 0), inner_radius=0.4, outer_radius=0.52,
           rings=24, ring_segments=8)
    b.sphere("Eye", "Rig", "eye_cyan", 0.14, (0, 0, -0.36))
    b.box("FinL", "Rig", "drone", (0.4, 0.05, 0.3), (-0.55, 0, 0.05))
    b.box("FinR", "Rig", "drone", (0.4, 0.05, 0.3), (0.55, 0, 0.05))
    b.cyl("Emitter", "Rig", "gunmetal", 0.05, 0.16, (0, -0.28, -0.25), (90, 0, 0), seg=10)
    s.node("Muzzle", "Marker3D", "Rig", position=v3(0, -0.28, -0.4))
    s.node("EyeLight", "OmniLight3D", "Rig", position=v3(0, 0, -0.6), light_color=hexcolor("#40e8ff"),
           light_energy=0.9, omni_range=3.5, light_bake_mode=0)
    s.node("Hum", "AudioStreamPlayer3D", ".", stream=s.ext_res("AudioStream", "res://audio/sfx/drone_hum.wav"),
           autoplay=True, unit_size=5.0, max_distance=40.0, bus="World", volume_db=-6.0)
    s.save(out("scenes/enemies/drone.tscn"))


# ============================================================================ pickups

def pickup(file, kind, amount, build):
    s = Scene(os.path.basename(file).split(".")[0].title().replace("_", ""), "Area3D")
    s.nodes[0][3].update(collision_layer=8, collision_mask=2, monitorable=False,
                         script=script(s, "res://scripts/World/Pickup.cs"), Kind=kind, Amount=amount)
    s.node("CollisionShape3D", "CollisionShape3D", ".", position=v3(0, 0.5, 0),
           shape=s.sub_res("SphereShape3D", radius=0.7))
    vis = s.node("Visual", "Node3D", ".", position=v3(0, 0.4, 0))
    b = Builder(s, shadows=False)
    build(s, b, vis)
    s.save(out(f"scenes/pickups/{file}"))


def pickups():
    def medkit(s, b, v):
        b.box("Case", v, "white", (0.46, 0.24, 0.34))
        b.box("CrossA", v, "red_cross", (0.26, 0.02, 0.08), (0, 0.125, 0))
        b.box("CrossB", v, "red_cross", (0.08, 0.02, 0.26), (0, 0.125, 0))
        b.box("Handle", v, "rubber", (0.2, 0.04, 0.04), (0, 0.15, 0.12))
    pickup("health.tscn", 0, 25, medkit)

    def mega(s, b, v):
        b.sphere("Orb", v, "mega", 0.24, (0, 0.1, 0))
        b.part("Ring", v, "TorusMesh", "gunmetal_light", (0, 0.1, 0), (90, 0, 0), inner_radius=0.27, outer_radius=0.31,
               rings=24, ring_segments=6)
    pickup("megahealth.tscn", 1, 100, mega)

    def vest(mat):
        def f(s, b, v):
            b.box("Plate", v, mat, (0.5, 0.56, 0.16), (0, 0.15, 0))
            b.box("ShoulderL", v, mat, (0.16, 0.1, 0.22), (-0.2, 0.45, 0))
            b.box("ShoulderR", v, mat, (0.16, 0.1, 0.22), (0.2, 0.45, 0))
            b.box("Stripe", v, "stripe_yellow", (0.4, 0.04, 0.02), (0, 0.2, -0.085))
        return f
    pickup("armor.tscn", 2, 50, vest("armor_green"))
    pickup("armor_heavy.tscn", 3, 100, vest("armor_red"))

    def shells(s, b, v):
        b.box("Box", v, "gunmetal_light", (0.34, 0.12, 0.24))
        for i in range(4):
            b.cyl(f"Shell{i}", v, "shell", 0.03, 0.14, (-0.11 + i * 0.075, 0.12, 0), seg=10)
            b.cyl(f"Cap{i}", v, "brass", 0.031, 0.03, (-0.11 + i * 0.075, 0.07, 0), seg=10)
    pickup("shells.tscn", 4, 12, shells)
    pickup("shells_small.tscn", 4, 6, shells)

    def bullets(s, b, v):
        b.box("Can", v, "olive", (0.4, 0.26, 0.2))
        b.box("Lid", v, "gunmetal", (0.42, 0.04, 0.22), (0, 0.15, 0))
        b.box("Stripe", v, "stripe_yellow", (0.3, 0.05, 0.01), (0, 0.02, -0.105))
    pickup("bullets.tscn", 5, 60, bullets)
    pickup("bullets_small.tscn", 5, 25, bullets)

    def rockets(s, b, v):
        for i, x in enumerate((-0.09, 0.09)):
            b.cyl(f"Body{i}", v, "gunmetal_light", 0.05, 0.4, (x, 0.05, 0), (90, 0, 0), seg=10)
            b.cyl(f"Nose{i}", v, "hazard", 0.0, 0.12, (x, 0.05, -0.26), (-90, 0, 0), r2=0.05, seg=10)
    pickup("rockets.tscn", 6, 5, rockets)

    def weapon_model(path):
        def f(s, b, v):
            s.instance("Model", path, v, scale=v3(1.4, 1.4, 1.4), rotation_degrees=v3(0, 90, 0))
        return f
    pickup("weapon_chaingun.tscn", 7, 80, weapon_model("res://scenes/weapons/models/chaingun_model.tscn"))
    pickup("weapon_rocket_launcher.tscn", 8, 8, weapon_model("res://scenes/weapons/models/rocket_launcher_model.tscn"))


# ============================================================================ props

def props():
    # Explosive barrel.
    s = Scene("ExplosiveBarrel", "StaticBody3D")
    s.nodes[0][3].update(script=script(s, "res://scripts/World/ExplosiveBarrel.cs"))
    s.node("CollisionShape3D", "CollisionShape3D", ".", position=v3(0, 0.6, 0),
           shape=s.sub_res("CylinderShape3D", height=1.2, radius=0.38))
    b = Builder(s)
    b.cyl("Body", ".", "barrel", 0.36, 1.16, (0, 0.58, 0), seg=20, gi=2)
    b.cyl("RimTop", ".", "gunmetal_light", 0.375, 0.05, (0, 0.95, 0), seg=20, gi=2)
    b.cyl("RimBottom", ".", "gunmetal_light", 0.375, 0.05, (0, 0.22, 0), seg=20, gi=2)
    b.cyl("Label", ".", "hazard", 0.365, 0.22, (0, 0.6, 0), seg=20, gi=2)
    s.save(out("scenes/props/explosive_barrel.tscn"))

    # Player start marker.
    s = Scene("PlayerStart", "Marker3D", gizmo_extents=0.6)
    s.set_root_groups(["player_start"])
    s.save(out("scenes/props/player_start.tscn"))

    # Exit pad.
    s = Scene("Exit", "Area3D")
    s.nodes[0][3].update(script=script(s, "res://scripts/World/Trigger.cs"), Kind=0)
    s.node("CollisionShape3D", "CollisionShape3D", ".", position=v3(0, 1.2, 0),
           shape=s.sub_res("CylinderShape3D", height=2.4, radius=1.0))
    b = Builder(s)
    vis = s.node("Pad", "Node3D", ".")
    b.cyl("Base", vis, "gunmetal", 1.3, 0.14, (0, 0.07, 0), seg=24)
    b.cyl("Glow", vis, "exit_glow", 1.05, 0.02, (0, 0.15, 0), seg=24)
    b.corona("Corona", ".", (0, 2.6, 0), 2.2, "corona_green")
    s.node("Light", "OmniLight3D", ".", position=v3(0, 0.8, 0), light_color=hexcolor("#4aff8a"), light_energy=1.2,
           omni_range=5.0, light_bake_mode=1, shadow_enabled=False)
    s.node("Sign", "Label3D", ".", position=v3(0, 2.6, 0), text="EXIT", font_size=96, pixel_size=0.01,
           modulate=hexcolor("#5aff8a"), outline_size=0, billboard=1, shaded=False)
    s.save(out("scenes/props/exit.tscn"))

    # Sliding door (for hand-built levels).
    s = Scene("Door", "AnimatableBody3D")
    # Layer 7 ("movers") while baking so navmeshes pass through doorways; Door.cs switches it
    # to the world layer at runtime.
    s.nodes[0][3].update(script=script(s, "res://scripts/World/Door.cs"), OpenOffset=v3(0, 3.1, 0), collision_layer=64)
    s.node("CollisionShape3D", "CollisionShape3D", ".", position=v3(0, 1.6, 0),
           shape=s.sub_res("BoxShape3D", size=v3(3.0, 3.2, 0.3)))
    b = Builder(s)
    b.box("Slab", ".", "door", (3.0, 3.2, 0.3), (0, 1.6, 0), gi=2)
    b.box("StripeL", ".", "hazard", (0.3, 3.2, 0.32), (-1.35, 1.6, 0), gi=2)
    b.box("StripeR", ".", "hazard", (0.3, 3.2, 0.32), (1.35, 1.6, 0), gi=2)
    s.save(out("scenes/props/door.tscn"))

    # Ceiling light fixture: emissive panel + static (baked) omni light.
    s = Scene("CeilingLight", "Node3D")
    b = Builder(s)
    b.box("Housing", ".", "cage", (1.3, 0.1, 0.5), (0, 0.02, 0))
    b.box("Panel", ".", "fixture_panel", (1.2, 0.04, 0.4), (0, -0.04, 0))
    b.corona("CoronaA", ".", (-0.35, -0.12, 0), 1.1)
    b.corona("CoronaB", ".", (0.35, -0.12, 0), 1.1)
    s.node("Light", "OmniLight3D", ".", position=v3(0, -0.35, 0), light_color=hexcolor("#ffe2b8"), light_energy=2.6,
           light_indirect_energy=1.0, light_size=0.4, omni_range=11.0, omni_attenuation=1.2, light_bake_mode=1,
           shadow_enabled=True)
    s.save(out("scenes/props/ceiling_light.tscn"))

    # Caged wall lamp.
    s = Scene("WallLamp", "Node3D")
    b = Builder(s)
    b.box("Plate", ".", "cage", (0.3, 0.4, 0.06), (0, 0, 0.03))
    b.cyl("Bulb", ".", "lamp_glow", 0.07, 0.18, (0, 0, -0.1), (90, 0, 0), seg=12)
    for i, (x, y) in enumerate(((-0.1, 0.1), (0.1, 0.1), (-0.1, -0.1), (0.1, -0.1))):
        b.box(f"Bar{i}", ".", "cage", (0.015, 0.015, 0.2), (x, y, -0.1))
    b.corona("Corona", ".", (0, 0, -0.14), 0.8)
    s.node("Light", "OmniLight3D", ".", position=v3(0, 0, -0.35), light_color=hexcolor("#ffb46a"), light_energy=1.6,
           light_size=0.15, omni_range=8.0, omni_attenuation=1.4, light_bake_mode=1, shadow_enabled=True)
    s.save(out("scenes/props/wall_lamp.tscn"))


def doorways():
    """Split sliding door in a Blender-modelled frame (see tools/blender/build_props.py)."""
    s = Scene("Doorway", "Node3D")
    s.nodes[0][3].update(script=script(s, "res://scripts/World/Doorway.cs"))
    s.instance("Frame", "res://models/doorway/door_frame.glb", ".")
    b = Builder(s)
    for name, sign, mesh in (("LeafL", -1, "res://models/doorway/leaf_l.res"), ("LeafR", 1, "res://models/doorway/leaf_r.res")):
        leaf = s.node(name, "AnimatableBody3D", ".", collision_layer=64,
                      script=script(s, "res://scripts/World/Door.cs"), Controlled=True,
                      OpenOffset=v3(sign * 1.45, 0, 0), Speed=2.6)
        s.node("Mesh", "MeshInstance3D", leaf, mesh=s.ext_res("ArrayMesh", mesh), gi_mode=2)
        s.node("CollisionShape3D", "CollisionShape3D", leaf, position=v3(sign * 0.75, 1.61, 0),
               shape=s.sub_res("BoxShape3D", size=v3(1.5, 3.18, 0.2)))
    for i, z in enumerate((1.05, -1.05)):
        s.node(f"Light{i}", "OmniLight3D", ".", position=v3(0, 3.0, z), light_color=hexcolor("#ffc890"),
               light_energy=1.1, omni_range=4.5, omni_attenuation=1.3, light_size=0.3, light_bake_mode=1,
               shadow_enabled=True)
        b.corona(f"CoronaL{i}", ".", (-0.9, 3.25, z * 0.72), 0.7)
        b.corona(f"CoronaR{i}", ".", (0.9, 3.25, z * 0.72), 0.7)
        b.corona(f"CoronaStatus{i}", ".", (0, 3.7, z * 0.7), 0.9, "corona_warm")
    s.save(out("scenes/props/doorway.tscn"))

    for tag, h in (("400x350", 3.5), ("400x400", 4.0)):
        s = Scene("Archway", "Node3D")
        s.instance("Frame", f"res://models/doorway/arch_{tag}.glb", ".")
        b = Builder(s)
        for i, z in enumerate((0.95, -0.95)):
            s.node(f"Light{i}", "OmniLight3D", ".", position=v3(0, h - 0.25, z), light_color=hexcolor("#ffc890"),
                   light_energy=0.9, omni_range=4.5, omni_attenuation=1.3, light_size=0.5, light_bake_mode=1,
                   shadow_enabled=True)
            b.corona(f"Corona{i}", ".", (0, h + 0.02, z * 0.72), 1.2)
        s.save(out(f"scenes/props/archway_{tag}.tscn"))


def main():
    make_materials()
    weapon_models()
    weapons()
    projectiles()
    player()
    grunt()
    brute()
    drone()
    pickups()
    props()
    doorways()
    print("scenes generated")


if __name__ == "__main__":
    main()
