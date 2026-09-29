"""Write a level's gameplay data (game/data/levels/<id>.json) from its entity layout.

Usage: python3 tools/levels/export_level_data.py [level_id ...]   (default: every layout with entities)

The entity layout (tools/levels/layouts/<id>_entities.py) is the single source for where things are
and what they are (CLAUDE.md 7.1). The Blender build places them; this writes what they are, keyed
by stable id "<level>:<id>", for Undercity.Core (core/Undercity.Core/World/Tables.cs, LevelDef).
The output is generated: regenerate it, don't hand-edit it (CLAUDE.md 11).
"""

import contextlib
import importlib
import io
import json
import pathlib
import sys

from shapely.geometry import Point, Polygon

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "levels"))

import city_plan  # noqa: E402  (the plan knows the awnings a civilian stands under)
import puddle_mask  # noqa: E402

# How far an open umbrella reaches from its holder, metres: the canopy's 0.5 m radius, held 0.45 m
# forward and 0.18 m to the side (tools/blender/build_undercity_props.py, umbrella; the torch_l
# mount). A civilian this close to an awning would push it into the awning, and is sheltered.
UMBRELLA_REACH_M = 1.0

KINDS = {"loot": "containers", "terminal": "terminals", "door": "doors", "trigger": "triggers",
         "exit": "exits", "zone": "zones", "item": "items"}
NO_DATA = {"spawn", "npc", "civ", "bed", "stash"}


def crowd_place(e, layout, covers):
    """Where a civilian stands, for the crowd rule (openspec/changes/archive/2026-09-29-crowd-variety): the place in
    layout metres, the district it stands in (none between districts) and whether it is sheltered,
    inside a named building, or under or within an umbrella's reach of an awning the plan registered
    (umbrellas are for the open)."""
    x, y = (float(v) for v in e["at"])
    pt = Point(x, y)
    district = next((d["name"].lower().replace(" ", "_") for d in layout.get("districts", [])
                     if Polygon(d["poly"]).covers(pt)), None)
    sheltered = (any(Polygon(b["poly"]).covers(pt) for b in layout.get("buildings", []))
                 or any(fp.distance(pt) <= UMBRELLA_REACH_M for _, fp, _ in covers))
    return {"at": [x, y], "district": district, "sheltered": sheltered}


def shelters(level_id, plan):
    """Every roof the plan registered (Plan.shelter), for the core's wetness rule
    (openspec/changes/archive/2026-09-29-character-lighting, design section 9): its label, its footprint in layout
    metres and the height of its underside. The core's polygon rule has no holes, so a footprint
    with one is refused rather than written as if it were solid."""
    out = []
    for label, pg, z0 in plan.shelters:
        if pg.interiors:
            raise SystemExit(f"{level_id}: shelter '{label}' has a hole the core can't represent")
        out.append({"label": label, "poly": [[round(x, 3), round(y, 3)] for x, y in list(pg.exterior.coords)[:-1]],
                     "under_m": round(z0, 3)})
    return out


# Where the placement test starts its walk to the runner's spawn: this far outside each exterior
# door, on its approach (openspec/changes/hub-doorways, "Every door opens onto ground a person can
# reach").
APPROACH_START_M = 1.0


def approaches(layout):
    """Every exterior door of an enterable building, from render_map.door_approaches, the one
    approach the plan's check and the lot cut use: its building and door, whether it is an entrance
    or a service door, and the point APPROACH_START_M outside it, in layout metres."""
    geo = city_plan.RM.base_geometry(layout)
    out = []
    for b, d, ap in city_plan.RM.door_approaches(layout, geo):
        nx, ny = d["n"]
        out.append({"door": f"{b['id']}:{d['i']}", "kind": ap["kind"],
                    "at": [round(d["x"] + nx * APPROACH_START_M, 3), round(d["y"] + ny * APPROACH_START_M, 3)]})
    return out


def puddles(level_id, city):
    """The level's puddles (city_plan.py City.puddles(), openspec/changes/street-puddles), for the
    core's check that each lies in the rain, and the numbers the level hands the ground's shader to
    read the mask. The mask itself (puddle_mask.py) is written here too, from the same plan, so the
    list and the mask can't disagree."""
    puddle_mask.write(level_id, city)
    out = []
    for p in city.puddle_list:
        pg = p["g"].simplify(0.02)
        if pg.interiors or not pg.contains(Point(*p["at"])):
            raise SystemExit(f"{level_id}: puddle {p['id']} has a hole, or its point lies outside it")
        out.append({"id": p["id"], "kind": p["kind"], "at": [round(v, 3) for v in p["at"]], "ground_m": p["ground_m"],
                    "poly": [[round(x, 3), round(y, 3)] for x, y in list(pg.exterior.coords)[:-1]]})
    return {"mask": puddle_mask.res_path(level_id), "rect_m": [0.0, 0.0, float(city.P.W), float(city.P.H)],
            "range_m": puddle_mask.RANGE_M, "height_m": list(puddle_mask.HEIGHT_M), "list": out}


def export(level_id):
    ents = importlib.import_module(f"layouts.{level_id}_entities").ENTITIES
    layout = importlib.import_module(f"layouts.{level_id}").MAP
    title = layout["title"].title()
    out = {"id": level_id, "title": title, "spawns": [],
           **{v: {} for v in KINDS.values()}, "npcs": {}, "crowd": {}, "water": [], "districts": []}
    # The layout's districts, for the conversation rig's gels (openspec/changes/archive/2026-09-29-character-lighting).
    for d in layout.get("districts", []):
        out["districts"].append({"id": d["name"].lower().replace(" ", "_"),
                                 "poly": [[float(x), float(y)] for x, y in d["poly"]]})
    # The layout's water bodies, for the core's water rule (openspec/changes/archive/2026-09-29-water-and-swimming).
    for w in layout.get("water", []):
        if "id" not in w:
            raise SystemExit(f"{level_id}: a water body has no id")
        out["water"].append({"id": w["id"], "surface_m": w["surface_m"], "bed_m": w["bed_m"],
                             "poly": [[float(x), float(y)] for x, y in w["poly"]]})
    # The awnings civilians shelter under, and every roof the rain can't pass, from the level's
    # plan (a city layout has one); its checks report on stderr.
    covers = []
    if layout.get("base", "city") == "city":
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            city = city_plan.City(*city_plan.load(level_id))
            plan = city.build()
        covers = plan.covers
        out["shelters"] = shelters(level_id, plan)
        out["approaches"] = approaches(layout)
        out["puddles"] = puddles(level_id, city)
    # Stable ids share one namespace across kinds; spawns, beds and stashes are placements only.
    seen = set()
    for e in ents:
        kind, local = e["kind"], e["id"]
        key = (kind, local) if kind in NO_DATA - {"npc", "civ"} else local
        if key in seen:
            raise SystemExit(f"{level_id}: id '{local}' ({kind}) is used twice")
        seen.add(key)
        sid = f"{level_id}:{local}"
        if kind == "spawn":
            out["spawns"].append(local)
        elif kind == "npc":
            out["npcs"][sid] = e["props"]["npc"]
        elif kind == "civ":
            out["npcs"][sid] = "civ"
            out["crowd"][sid] = crowd_place(e, layout, covers)
        elif kind in KINDS:
            if "data" not in e:
                raise SystemExit(f"{level_id}: {kind} '{local}' has no data")
            out[KINDS[kind]][sid] = e["data"]
        elif kind not in NO_DATA:
            raise SystemExit(f"{level_id}: unknown entity kind '{kind}'")
    path = ROOT / "game" / "data" / "levels" / f"{level_id}.json"
    header = f"// Generated by tools/levels/export_level_data.py from tools/levels/layouts/{level_id}_entities.py. Don't edit.\n"
    path.write_text(header + json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}: {sum(len(v) for v in out.values() if isinstance(v, dict))} records")


if __name__ == "__main__":
    ids = sys.argv[1:] or sorted(p.stem[:-len("_entities")] for p in (ROOT / "tools/levels/layouts").glob("*_entities.py"))
    for i in ids:
        export(i)
