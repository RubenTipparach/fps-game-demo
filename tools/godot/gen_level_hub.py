#!/usr/bin/env python3
"""Writes game/levels/undercity/hub/hub.tscn: Low Harbor's sectors, environment and lighting.

    python3 tools/godot/gen_level_hub.py

The geometry comes from tools/blender/build_undercity.py (one glb per sector, built from the
layout). This scene composes them and adds what the glbs don't carry:

  * the root: UndercityLevel with LevelId "hub";
  * one node per sector, holding its glb, its own LightmapGI (each bakes its own .lmbake), its
    cool fill lights and the zone ambient of its interiors;
  * a NavigationRegion3D that bakes from every sector's static colliders (group "hub_nav");
  * a night environment: a dark sky with the city's glow, blue-violet fog, glow for the neon,
    screen-space reflections for the wet streets;
  * box-projected reflection probes for the market, Lantern Row and every interior;
  * rain: GPU particles over the whole hub, stopped by a heightfield so it never falls indoors.

Baking by sector. A LightmapGI bakes only the lights under its own parent, and a static light
still lights dynamic objects at runtime (Godot's forward shader skips it only for lightmapped
meshes). So a light that reaches another sector's geometry is copied into that sector as a
bake-only light with light_cull_mask = 0: the lightmapper ignores cull masks, the renderer
does not, so the copy bakes and never renders twice. The city glow is each LightmapGI's
environment colour, which needs no light at all.
"""
import contextlib
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "levels"))
import level_common as lc  # noqa: E402
from tscn import Raw, Scene, color, hexcolor, v3  # noqa: E402

import city_plan  # noqa: E402
from shapely.geometry import box  # noqa: E402

LEVEL = "hub"
NAV_GROUP = "hub_nav"
CITY_GLOW = "#2c2a52"          # the sky's glow over the Sump: blue-violet, light-polluted
CITY_GLOW_ENERGY = 0.55
FILL = ("#4f7dff", 0.6, 26.0)  # cool blue fill: colour, energy, range (m)
FILL_Z = 9.0


def scene_light(path):
    """The Light child of a fixture scene (wall_lamp): offset and settings, read
    from the .tscn so the bake-only copies match what the game places."""
    text = open(os.path.join(ROOT, "game", path)).read()
    block = text.split('[node name="Light" type="OmniLight3D"', 1)[1].split("\n\n", 1)[0]
    props = dict(re.findall(r"^(\w+) = (.+)$", block, re.M))
    pos = [float(v) for v in re.findall(r"[-\d.]+", props.get("position", "Vector3(0, 0, 0)"))]
    col = [float(v) for v in re.findall(r"[-\d.]+", props["light_color"])][:3]
    return {"offset": pos, "color": col, "energy": float(props["light_energy"]),
            "range": float(props["omni_range"]), "attenuation": float(props.get("omni_attenuation", 1.0)),
            "size": float(props.get("light_size", 0.2)), "indirect": float(props.get("light_indirect_energy", 1.0))}


def prim_points(p):
    t = p["t"]
    if t in ("hexa", "quad"):
        return [tuple(q) for q in p["p"]]
    if t == "prism":
        return [(x, y, z) for r in p["rings"] for x, y in r for z in (p["z0"], p["z1"])]
    if t == "loft":
        return [(x, y, z) for r, z in zip(p["rings"], p["z"]) for x, y in r]
    if t == "cyl":
        x, y, z = p["c"]
        r = p["r"] + abs(p["h"])
        return [(x - r, y - r, z - r), (x + r, y + r, z + r)]
    if t == "text":
        x, y, z = p["p"]
        return [(x - 3, y - 3, z), (x + 3, y + 3, z + 3)]
    if t == "bool":
        return prim_points(p["solid"])
    return []


def aabbs(sector):
    out = []
    for o in sector["objects"]:
        if o["name"].startswith("corona_") or o.get("col") == "colonly":
            continue
        pts = [q for p in o["prims"] for q in prim_points(p)]
        if pts:
            out.append((tuple(min(q[i] for q in pts) for i in range(3)), tuple(max(q[i] for q in pts) for i in range(3))))
    return out


def near(pos, boxes, rng):
    for lo, hi in boxes:
        d2 = sum(max(lo[i] - pos[i], 0, pos[i] - hi[i]) ** 2 for i in range(3))
        if d2 < rng * rng:
            return True
    return False


def G(p):
    """Layout (x east, y south, z up) to Godot (x, y up, z south)."""
    return v3(p[0], p[2], p[1])


def main():
    with contextlib.redirect_stdout(sys.stderr):
        city = city_plan.City(*city_plan.load(LEVEL))
        plan = city.build().to_json()
    sectors = [s["name"] for s in plan["sectors"]]
    boxes = {s["name"]: aabbs(s) for s in plan["sectors"]}
    wall = scene_light("scenes/props/wall_lamp.tscn")

    s = Scene("LowHarbor", "Node3D")
    lc.setup_root(s, script="res://scripts/Undercity/Level/UndercityLevel.cs", LevelId=LEVEL)
    lc.add_navigation(s, geometry_source_geometry_mode=1, geometry_source_group_name=NAV_GROUP,
                      agent_max_climb=0.3)
    lc.add_environment(
        s, fog_color="#2a2d55", fog_density=0.011, exposure=1.2,
        sky=dict(sky_top_color=hexcolor("#04050b"), sky_horizon_color=hexcolor("#2a1f40"),
                 ground_bottom_color=hexcolor("#030407"), ground_horizon_color=hexcolor("#2a1f40"),
                 sun_angle_max=0.0, sky_energy_multiplier=1.0),
        fog_sky_affect=0.6, glow_intensity=0.8, glow_bloom=0.08, glow_hdr_threshold=1.0,
        ssr_enabled=True, ssr_max_steps=48, ssr_fade_in=0.15, ssr_fade_out=2.0, ssr_depth_tolerance=0.3)

    s.node("Sectors", "Node3D", ".")
    # every light that the plan places, with the sector that owns it
    lights = []
    for sec in plan["sectors"]:
        for e in sec["entities"]:
            kind = e["extras"].get("kind")
            if kind == "light":
                ex = e["extras"]
                lights.append({"name": e["name"][4:], "sector": sec["name"], "pos": e["pos"], "color": ex["color"],
                               "energy": ex["energy"], "range": ex["range"], "attenuation": 1.0, "size": 0.2,
                               "indirect": 1.0})
            elif kind == "wall_lamp":
                h = math.radians(e["heading"])
                fx, fy = math.sin(h), -math.cos(h)
                off = -wall["offset"][2]
                p = [e["pos"][0] + fx * off, e["pos"][1] + fy * off, e["pos"][2] + wall["offset"][1]]
                lights.append({**wall, "name": e["name"][4:], "sector": sec["name"], "pos": p})
    # cool fills over open ground, one per chunk cell, owned by the streets sector
    fills = []
    nx, ny = int(math.ceil(city.P.W / city_plan.CHUNK_M)), int(math.ceil(city.P.H / city_plan.CHUNK_M))
    for i in range(nx):
        for j in range(ny):
            cell = box(i * 40, j * 40, (i + 1) * 40, (j + 1) * 40)
            ground = cell.intersection(city.O.union(city.W))
            if ground.is_empty or ground.area < 30:
                continue
            c = ground.representative_point()
            fills.append({"name": f"Fill_{i}_{j}", "sector": "streets", "pos": [c.x, c.y, FILL_Z],
                          "color": list(int(FILL[0][k:k + 2], 16) / 255 for k in (1, 3, 5)), "energy": FILL[1],
                          "range": FILL[2], "attenuation": 0.8, "size": 1.5, "indirect": 1.2})

    def omni(name, parent, L, bake_only):
        props = dict(position=G(L["pos"]), light_color=color(*L["color"]), light_energy=float(L["energy"]),
                     light_indirect_energy=float(L["indirect"]), light_size=float(L["size"]),
                     omni_range=float(L["range"]), omni_attenuation=float(L["attenuation"]),
                     light_bake_mode=1, shadow_enabled=True)
        if bake_only:
            props["light_cull_mask"] = 0
        s.node(name, "OmniLight3D", parent, **props)

    rooms_by_sector = {}
    for r in plan["rooms"]:
        rooms_by_sector.setdefault(r["sector"], []).extend(r["rooms"])
    copies = 0
    for name in sectors:
        sp = s.node(name, "Node3D", "Sectors", groups=[NAV_GROUP])
        s.instance("Geometry", f"res://levels/undercity/{LEVEL}/{LEVEL}_{name}.glb", sp)
        lc.add_lightmap(s, parent=sp, interior=False, probes_subdiv=2, environment_mode=3,
                        environment_custom_color=hexcolor(CITY_GLOW), environment_custom_energy=CITY_GLOW_ENERGY)
        own_fills = [f for f in fills if f["sector"] == name]
        if own_fills:
            fp = s.node("FillLights", "Node3D", sp)
            for f in own_fills:
                omni(f["name"], fp, f, False)
        if rooms_by_sector.get(name):
            # plan rooms are detailing boxes: [x0, x1, floor, ceiling, z0, z1] in Godot axes
            lc.add_zone_ambient(s, [((r[0], r[1]), (r[2], r[3]), (r[4], r[5])) for r in rooms_by_sector[name]], at=sp)
        # bake-only copies of other sectors' lights that reach this sector's geometry
        foreign = [L for L in lights + fills if L["sector"] != name and near(L["pos"], boxes[name], L["range"])]
        if foreign:
            bp = s.node("BakeOnlyLights", "Node3D", sp)
            for L in foreign:
                omni(f"{L['sector']}_{L['name']}", bp, L, True)
                copies += 1

    # reflection probes: the market and Lantern Row outside, every interior inside
    ma = next(o for o in city.m["open"] if o["name"] == "SUMP MARKET")["_g"].bounds
    lc.add_reflection_probes(s, [("RefMarket", (ma[0], ma[2]), (0.0, 12.0), (ma[1], ma[3]))], parent="ReflectionProbes",
                             interior=False)
    lr = next(o for o in city.m["open"] if o["name"] == "LANTERN ROW")["_g"].bounds
    lc.add_reflection_probes(s, [("RefLanternRow", (lr[0], lr[2]), (0.0, 14.0), (lr[1] - 2, lr[3] + 2))],
                             parent="ReflectionProbesStreet", interior=False)
    lc.add_reflection_probes(s, [(p["name"], (p["box"][0], p["box"][1]), (p["box"][2], p["box"][3]),
                                  (p["box"][4], p["box"][5])) for p in plan["probes"]], parent="ReflectionProbesInterior")

    # rain over the hub; the heightfield stops it on roofs, decks and the Skyway
    W, H = city.P.W, city.P.H
    drop = s.sub_res("StandardMaterial3D", transparency=1, blend_mode=1, shading_mode=0, billboard_mode=2,
                     albedo_color=hexcolor("#9fb4d8", 0.3), disable_receive_shadows=True)
    mesh = s.sub_res("QuadMesh", size=Raw("Vector2(0.015, 0.7)"), material=drop)
    proc = s.sub_res("ParticleProcessMaterial", emission_shape=3, emission_box_extents=v3(W / 2, 1, H / 2),
                     direction=v3(0.06, -1, 0.03), spread=2.0, initial_velocity_min=20.0, initial_velocity_max=24.0,
                     gravity=v3(0, -9.8, 0), collision_mode=2)
    s.node("Rain", "GPUParticles3D", ".", position=v3(W / 2, 34, H / 2), amount=40000, lifetime=1.6, preprocess=1.6,
           visibility_aabb=Raw(f"AABB({-W / 2 - 5}, -40, {-H / 2 - 5}, {W + 10}, 80, {H + 10})"),
           process_material=proc, draw_pass_1=mesh, cast_shadow=0)
    s.node("RainStop", "GPUParticlesCollisionHeightField3D", ".", position=v3(W / 2, 16, H / 2),
           size=v3(W + 10, 60, H + 10), resolution=2, update_mode=0)

    out = os.path.join(ROOT, "game", "levels", "undercity", LEVEL, f"{LEVEL}.tscn")
    s.save(out)
    print(f"wrote {out}: {len(sectors)} sectors, {len(lights)} glb lights, {len(fills)} fills, "
          f"{copies} bake-only copies")


if __name__ == "__main__":
    main()
