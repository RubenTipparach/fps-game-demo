"""Tests of the city plan's level rules that a layout alone can't show: ways out of the water
(openspec/changes/archive/2026-09-29-water-and-swimming, "Every water body has a way out") and people kept out of
it ("People stand clear of the level"). Each test builds on the committed hub.

    python3 -m unittest discover -s tools/levels -p 'test_*.py'
"""
import contextlib
import io
import json
import math
import os
import shutil
import struct
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import city_plan as CP  # noqa: E402
import render_map as RM  # noqa: E402


def built_hub():
    m, ents = CP.load("hub")
    city = CP.City(m, ents)
    with contextlib.redirect_stdout(io.StringIO()):
        city.build()
    return city


class WaysOutOfTheWater(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = built_hub()

    def test_every_point_of_the_hubs_water_is_a_short_swim_from_a_way_out(self):
        self.assertEqual(self.city.exit_problems(), [])

    def test_a_canal_with_its_ladders_removed_fails_naming_the_canal_and_a_point(self):
        problems = self.city.exit_problems(ladders=[])
        cut = [p for p in problems if p.startswith("the_cut:")]
        self.assertEqual(len(cut), 1, f"the Cut must fail with no ladders: {problems}")
        self.assertRegex(cut[0], r"the farthest is \(\d+(\.\d+)?, \d+(\.\d+)?\), with no way out at all")

    def test_a_canal_with_one_ladder_fails_at_its_far_end(self):
        one = [ld for ld in self.city.ladders if ld["id"] == "the_cut_1"]
        problems = [p for p in self.city.exit_problems(ladders=one) if p.startswith("the_cut:")]
        self.assertEqual(len(problems), 1)
        # the_cut_1 is at the north end: the farthest water is at the south end, 140 m and more away
        far = float(problems[0].split("), ")[1].split(" m")[0])
        self.assertGreater(far, 140, "the swim is measured the length of the canal, not across it")

    def test_a_quay_low_enough_to_climb_onto_needs_no_ladder(self):
        # were the game to let a swimmer climb 3 m, every quay of the Cut would be a way out
        with mock.patch.object(CP, "mantle_rise", return_value=(0.2, 3.0)):
            problems = self.city.exit_problems(ladders=[])
        self.assertFalse([p for p in problems if p.startswith("the_cut:")], problems)

    def test_quay_ladders_keep_clear_of_bridges_boats_and_pillars(self):
        boats = [RM.shape_geom(fx) for fx in self.city.m["props"] if fx[0] == "poly" and fx[-1] == "fix"
                 and RM.shape_geom(fx).intersects(self.city.W)]
        for ld in self.city.ladders:
            if ld["id"].endswith("_outfall"):
                continue
            pt = CP.Point(ld["at"])
            for what, g in [("a bridge", self.city.bridge_u)] + [("a boat", b) for b in boats] + \
                    [("a pillar", p) for p in self.city.water_pillars()]:
                self.assertGreaterEqual(g.distance(pt), CP.LADDER_CLEAR_M - 1e-6, f"{ld['id']} is too close to {what}")

    def test_every_ladder_reaches_under_the_surface_and_tops_out_on_a_floor(self):
        for ld in self.city.ladders:
            water = next(w for w in self.city.waters if w["id"] == ld["water"])
            self.assertAlmostEqual(ld["bottom"], water["surface"] - CP.LADDER_UNDER_M, 6)
            self.assertGreater(ld["top"], water["surface"], f"{ld['id']} must top out above the water")
            self.assertGreaterEqual(ld["top"], ld["floor"], f"{ld['id']} climbs over anything between the edge and its landing")

    def test_a_ladder_steps_off_past_a_kerb_onto_level_ground(self):
        # the Cut's east quay has a raised strip under a metre wide between the water and Quay Road
        kerbed = [ld for ld in self.city.ladders if ld["top"] > ld["floor"]]
        self.assertTrue(kerbed, "some ladders land past the quay's kerb")
        for ld in kerbed:
            x, y = ld["at"]
            n = ld["n"]
            lx, ly = x + n[0] * ld["step_in"], y + n[1] * ld["step_in"]
            self.assertAlmostEqual(self.city.ground_level(lx, ly), ld["floor"], 6, f"{ld['id']} lands on its floor")

    def test_the_outfalls_rungs_are_a_ladder(self):
        self.assertIn("the_cut_outfall", [ld["id"] for ld in self.city.ladders])

    def test_a_ladder_opens_the_quay_railing(self):
        # railing posts are 0.07 m boxes inset 0.12 m from the quay edge
        for ld in self.city.ladders:
            if ld["id"].endswith("_outfall") or "_hull_" in ld["id"]:
                continue
            x, y = ld["at"]
            n = ld["n"]
            px, py = x + n[0] * 0.12, y + n[1] * 0.12
            posts = [pr for sec in self.city.P.sectors.values() for obj in sec["objects"].values()
                     if obj["name"].startswith("streets_walk") for pr in obj["prims"]
                     if pr.get("t") == "hexa" and self.is_post(pr, px, py)]
            self.assertEqual(posts, [], f"{ld['id']}: a railing post stands in its opening")

    @staticmethod
    def is_post(pr, px, py):
        xs, ys = [q[0] for q in pr["p"]], [q[1] for q in pr["p"]]
        small = max(xs) - min(xs) < 0.1 and max(ys) - min(ys) < 0.1
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        return small and math.dist((cx, cy), (px, py)) < CP.RAIL_GAP_M / 2 - 0.05


class PeopleStayOutOfTheWater(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = built_hub()

    def test_a_civilian_standing_in_the_cut_is_refused(self):
        problems = self.city.standing_problems("civ:test", 203, 100, -4.5, "outdoors", "npc")
        self.assertTrue(any("stands in the water of the_cut" in p for p in problems), problems)

    def test_a_civilian_on_the_tin_bridge_is_not_in_the_water(self):
        problems = self.city.standing_problems("civ:test", 203, 62.2, 0.0, "outdoors", "npc")
        self.assertFalse(any("water" in p for p in problems), problems)

    def test_a_patrol_across_the_cut_is_refused_naming_the_water(self):
        saved = self.city.entities_in
        self.city.entities_in = [{"kind": "npc", "id": "swimmer", "at": (185, 100),
                                  "props": {"patrol": "185,100;220,100"}}]
        try:
            problems = self.city.patrol_leg_problems()
        finally:
            self.city.entities_in = saved
        self.assertTrue(problems and "water" in problems[0], problems)

    def test_a_patrol_over_the_tin_bridge_is_allowed(self):
        saved = self.city.entities_in
        self.city.entities_in = [{"kind": "npc", "id": "walker", "at": (188, 62.2),
                                  "props": {"patrol": "188,62.2;218,62.2"}}]
        try:
            problems = self.city.patrol_leg_problems()
        finally:
            self.city.entities_in = saved
        self.assertFalse([p for p in problems if "water" in p], problems)


def built_hub_with(patch):
    """The hub built with one part of the plan changed for the test: `patch` is a context manager."""
    m, ents = CP.load("hub")
    city = CP.City(m, ents)
    with patch, contextlib.redirect_stdout(io.StringIO()), mock.patch.object(CP.City, "check_doors", lambda self: None):
        city.build()
    return city


class DoorsAreFramedShownAndReachable(unittest.TestCase):
    """openspec/changes/hub-doorways: "Every doorway is framed", "Every building on the street
    shows a door" and "Every door opens onto ground a person can reach". Each check passes on
    the committed hub and names the fault on a hub broken on purpose."""

    @classmethod
    def setUpClass(cls):
        cls.city = built_hub()

    def test_the_hub_passes_all_three_door_checks(self):
        self.assertEqual([], self.city.door_problems())
        self.assertEqual([], self.city.building_door_problems())
        self.assertEqual([], self.city.door_approach_problems())

    def test_every_declared_door_has_a_frame_the_carve_of_its_fits(self):
        self.assertEqual(46, len(self.city.frames), "43 doors and the three shells' entrances")
        for (bid, i), f in self.city.frames.items():
            for want, got in zip(CP.detailing.door_fits(*f["clear"]), f["carved"]):
                self.assertAlmostEqual(want, got, 6, f"{bid} door {i}")

    def test_a_door_left_unframed_is_named(self):
        real = CP.City.frame_door

        def skip_the_anchors_entrance(self, b, sector, dd, airs, cx, cy):
            if not (b["id"] == "rusty_anchor" and dd[7]["i"] == 0):
                real(self, b, sector, dd, airs, cx, cy)
        city = built_hub_with(mock.patch.object(CP.City, "frame_door", skip_the_anchors_entrance))
        self.assertEqual(["rusty_anchor door 0 at (90, 44), 3 m: no frame"], city.door_problems())

    def test_a_lot_back_in_front_of_the_fish_halls_entrance_is_named(self):
        real = CP.RM.approach_cut

        def without_the_fish_halls_north_entrance(m, geo):
            keep = [ap["poly"] for b, d, ap in CP.RM.door_approaches(m, geo) if not (b["id"] == "fish_hall" and d["i"] == 0)]
            return CP.unary_union(keep)
        city = built_hub_with(mock.patch.object(CP.RM, "approach_cut", without_the_fish_halls_north_entrance))
        problems = city.door_approach_problems()
        self.assertEqual(1, len(problems), problems)
        self.assertRegex(problems[0], r"^fish_hall door 0 at \(174, 76\), a 4 m entrance: its approach is blocked by lot 242 \(1\.35 m out\)")
        self.assertIs(CP.RM.approach_cut, real)

    def test_a_lot_with_its_door_taken_away_is_named(self):
        real = CP.City.dressing_doors

        def none_for_lot_0(self, lot, *args):
            if lot["id"] != "0":
                real(self, lot, *args)
        city = built_hub_with(mock.patch.object(CP.City, "dressing_doors", none_for_lot_0))
        problems = city.building_door_problems()
        self.assertEqual(1, len(problems), problems)
        self.assertTrue(problems[0].startswith("lot 0: no door on its 1 walkable edge"), problems)

    def test_no_dressing_door_z_fights_in_its_own_frame(self):
        self.assertEqual([], self.city.door_zfights)

    def test_the_doors_stay_in_their_triangle_budget(self):
        frames = sum(f["tris"] for f in self.city.frames.values())
        dressing = sum(self.city.door_tris.values())
        self.assertLessEqual(frames + dressing, 30000, f"frames {frames}, dressing doors and fittings {dressing}")
        for (bid, i), f in self.city.frames.items():
            self.assertLessEqual(f["tris"], 180 if f["kind"] == "portal" else 72, f"{bid} door {i}")


class PuddlesLieWhereWaterGathers(unittest.TestCase):
    """openspec/changes/archive/2026-09-30-street-puddles: "Puddles lie where water gathers". The hub's puddles pass
    the check, a puddle forced into the wrong place is refused by name, and placing them moves
    nothing else in the level."""

    @classmethod
    def setUpClass(cls):
        cls.city = built_hub()

    def forced(self, g, z=CP.STREET_Z):
        return {"id": "forced_001", "kind": "gutter", "at": (g.centroid.x, g.centroid.y), "ground_m": z, "g": g}

    def refusal(self, puddle):
        with self.assertRaises(SystemExit) as caught:
            self.city.check_puddles(self.city.puddle_list + [puddle])
        return str(caught.exception)

    def test_the_hub_passes_and_holds_the_amount_the_owner_chose(self):
        self.city.check_puddles()
        ground = sum(g.area for _, g, _, _ in self.city.puddle_ground()["ground"].values())
        share = sum(p["g"].area for p in self.city.puddle_list) / ground
        self.assertTrue(0.02 <= share <= 0.03, f"survey L2 chose about 2.6 % of the ground; the plan puts {share:.2%}")
        self.assertEqual({p["kind"] for p in self.city.puddle_list}, {"gully", "gutter", "drip"})

    def test_a_puddle_under_the_skyway_is_refused_naming_it_and_the_deck(self):
        deck = next(g for label, g, _ in self.city.P.shelters if label == "Skyway deck")
        road = self.city.puddle_ground()["ground"][CP.STREET_Z][2]
        spot = deck.intersection(road).buffer(-1.0).representative_point()
        message = self.refusal(self.forced(CP.ellipse(spot.x, spot.y, 2.0, 0.6, 0.0)))
        self.assertIn("forced_001 lies under a roof, the Skyway deck", message)

    def test_a_puddle_over_a_kerb_is_refused_naming_it(self):
        key, line = max(self.city.kerbs(), key=lambda kl: kl[1].length)
        (x, y), t, _ = self.city.kerb_frame(line, line.length / 2)
        message = self.refusal(self.forced(CP.ellipse(x, y, 2.0, 0.6, math.atan2(t[1], t[0]))))
        self.assertIn("forced_001 runs off its road", message, "half of it lies on the kerb's top")

    def test_puddles_keep_apart(self):
        first = self.city.puddle_list[0]
        twin = dict(first, id="forced_001")
        self.assertIn(f"forced_001 is 0.00 m from {first['id']}", self.refusal(twin))

    def test_every_long_kerb_has_a_gully_and_gutter_puddles(self):
        for key, line in self.city.kerbs():
            if line.length < 40.0:
                continue
            kinds = [p["kind"] for p in self.city.puddle_list if p["g"].distance(line) < 0.2]
            self.assertGreaterEqual(kinds.count("gully"), 1, f"the kerb from {key}, {line.length:.0f} m")
            self.assertGreaterEqual(kinds.count("gutter"), 3, f"the kerb from {key}, {line.length:.0f} m")

    def test_placing_puddles_moves_nothing_else(self):
        m, ents = CP.load("hub")
        dry = CP.City(m, ents)
        with mock.patch.object(CP.City, "place_puddles", lambda self: None), \
                contextlib.redirect_stdout(io.StringIO()):
            dry.build()
        wet, dry = self.city.P.to_json(), dry.P.to_json()
        for s in wet["sectors"]:
            s["entities"] = [e for e in s["entities"] if not e["name"].startswith("ENT_gully_")]
        del wet["stats"], dry["stats"]    # counts of what's compared, gullies included
        self.assertTrue(wet == dry, "puddles draw from their own seeded streams, so nothing else in the plan moves")


def car_spots(node):
    """Every car spot in a layout: its ("orect", cx, cy, w, h, angle, "car") shapes, wherever they are."""
    if isinstance(node, dict):
        return [fx for v in node.values() for fx in car_spots(v)]
    if isinstance(node, (list, tuple)):
        if node and node[-1] == "car" and node[0] == "orect":
            return [tuple(node)]
        return [fx for v in node for fx in car_spots(v)]
    return []


class ParkedVehiclesAreModelsThatFitTheirSpots(unittest.TestCase):
    """openspec/changes/archive/2026-09-30-vehicle-fixes: "Parked vehicles are generated models placed by the plan",
    and openspec/changes/archive/2026-09-30-cc0-vehicles. Every car spot holds one model that fits it and stands on one
    ground, read from the committed glb; each is a static model of the sector that owns its ground;
    a model that doesn't fit, or a spot across a kerb, is refused by name; dealing the models moves
    nothing else in the plan."""

    @classmethod
    def setUpClass(cls):
        cls.city = built_hub()

    def test_every_car_spot_holds_one_vehicle(self):
        m, _ = CP.load("hub")
        self.assertEqual(sorted(car_spots(m)), sorted(tuple(v["spot"]) for v in self.city.vehicles))
        names = [e["name"] for s in self.city.P.to_json()["sectors"] for e in s["entities"]
                 if e["name"].startswith("ENT_car_")]
        self.assertEqual(sorted(names), sorted(v["name"] for v in self.city.vehicles))

    def test_every_car_spot_is_a_car_spot_the_depot_s_too(self):
        m, _ = CP.load("hub")
        self.assertEqual({(5.6, 2.6)}, {(max(fx[3:5]), min(fx[3:5])) for fx in car_spots(m)},
                         "survey O7: no trucks, so the depot's spots take what every car spot deals")

    def test_no_model_parks_twice_before_every_model_has(self):
        models = [v["model"] for v in self.city.vehicles]
        self.assertEqual(len(models), len(set(models)), "15 spots deal 15 of the 22 variants, none twice")
        self.assertTrue(set(models) <= {v["id"] for v in CP.VEHICLES["variants"]})

    def test_every_vehicle_fits_its_spot_on_one_ground(self):
        self.city.check_vehicles()

    def test_each_car_is_a_model_of_the_sector_that_owns_its_ground(self):
        plan = self.city.P.to_json()
        models = {m["name"]: (s["name"], m) for s in plan["sectors"] for m in s["models"]}
        for v in self.city.vehicles:
            n = v["name"][len("ENT_car_"):]
            sector, m = models[f"car_{n}"]
            self.assertEqual("kiln" if v["inside"] else "streets", sector,
                             f"{v['name']}: the streets own every road and yard; the garage's bay is the kiln's floor")
            self.assertEqual(f"models/undercity/props/vehicle_{v['model']}.glb", m["path"])
            self.assertEqual(CP.CAR_EXTRAS, m["extras"], "bakes at 0.1 m, a quarter of the level's texel")
            ent = next(e for s in plan["sectors"] for e in s["entities"] if e["name"] == v["name"])
            self.assertEqual((m["pos"], m["heading"]), (ent["pos"], ent["heading"]), "the contact shadow lies under its car")
            (x0, y0, _), (x1, y1, _) = CP.vehicle_data.model_bounds(v["model"])
            self.assertEqual(f"{x1 - x0 + 0.3:.2f},{y1 - y0 + 0.3:.2f}", ent["extras"]["size"],
                             f"{v['name']}: the shadow is the committed model's footprint, 0.3 m longer and wider")
        self.assertEqual(sorted(models), sorted(f"car_{v['name'][len('ENT_car_'):]}" for v in self.city.vehicles),
                         "no model in the plan but the cars")

    def test_a_van_too_long_for_its_spot_is_refused_naming_the_spot_and_the_model(self):
        car = next(v for v in self.city.vehicles if not v["inside"])
        small = ("orect", *car["spot"][1:3], 4.6, 2.0, *car["spot"][5:])
        problems = self.city.vehicle_problems(dict(car, model="fullsize_red", spot=small))
        self.assertEqual(1, len(problems), problems)
        self.assertIn(f"{car['name']} (fullsize_red, 5.22 x 1.97 m) doesn't fit its 4.6 x 2 m spot", problems[0])

    def test_a_car_turned_across_its_spot_is_refused(self):
        car = next(v for v in self.city.vehicles if v["spot"][1] == 228)       # the depot's flat yard
        self.assertEqual([], self.city.vehicle_problems(dict(car, heading=car["heading"] + 180.0)),
                         "the spot fits either way round")
        problems = self.city.vehicle_problems(dict(car, heading=car["heading"] + 90.0))
        self.assertEqual(1, len(problems), problems)
        self.assertIn("doesn't fit its 5.6 x 2.6 m spot", problems[0], "across the spot the car sticks out of its sides")

    def test_a_spot_across_a_kerb_is_refused_naming_the_car_and_the_heights(self):
        # the street-vehicles layout's spot on Lantern Row's south pavement, which hung a van's
        # wheels over the road (openspec/changes/archive/2026-09-30-vehicle-fixes, design section 1.1)
        car = next(v for v in self.city.vehicles if v["spot"][1] == 12)
        old = ("orect", 12, 43.3, 5.6, 2.6, 0, "car")
        problems = self.city.vehicle_problems(dict(car, at=(12, 43.3, car["at"][2]), spot=old))
        self.assertEqual([f"{car['name']} at (12.0, 43.3) straddles a kerb: ground at 0.00 and 0.15 m under it"], problems)

    def test_a_car_indoors_stands_on_its_room_s_one_floor(self):
        garage = next(v for v in self.city.vehicles if v["inside"])
        self.assertEqual("kiln", garage["sector"])
        self.assertEqual(CP.FLOOR_Z, garage["at"][2])
        self.assertEqual([], self.city.vehicle_problems(garage))

    def test_every_model_stays_in_its_triangle_budget(self):
        for v in CP.VEHICLES["variants"]:
            tris = glb_triangles(CP.vehicle_data.model_path(v["id"]))
            self.assertLessEqual(tris, CP.VEHICLES["budget_tris"], v["id"])

    def test_an_entity_named_with_a_godot_type_suffix_is_refused(self):
        # Godot 4.7.2 imported "ENT_vehicle_008" as a VehicleBody3D named "ENT_008", and the level
        # importer freed it with the empty under it: every parked vehicle went missing
        with self.assertRaisesRegex(SystemExit, "ENT_vehicle_008: Godot's importer reads '_vehicle'"):
            self.city.P.entity("streets", "ENT_vehicle_008", 0.0, 0.0, 0.0)
        with self.assertRaisesRegex(SystemExit, "car_wheel: Godot's importer reads '_wheel'"):
            self.city.P.model("streets", "car_wheel", "models/x.glb", 0.0, 0.0, 0.0)
        for name in ("ENT_door_col", "ENT_crate-rigid", "ENT_x_navmesh_2"):
            self.assertIsNotNone(CP.godot_type_suffix(name), name)
        for name in ("ENT_car_008", "ENT_civ_12", "ENT_collector_1", "ENT_occupant_3", "ENT_wheelhouse", "car_008"):
            self.assertIsNone(CP.godot_type_suffix(name), f"{name} carries no suffix")

    def test_dealing_the_vehicles_moves_nothing_else(self):
        m, ents = CP.load("hub")
        empty = CP.City(m, ents)
        with mock.patch.object(CP.City, "vehicle", lambda self, sector, fx, z: None), \
                contextlib.redirect_stdout(io.StringIO()):
            empty.build()
        parked, empty = self.city.P.to_json(), empty.P.to_json()
        for s in parked["sectors"]:
            s["entities"] = [e for e in s["entities"] if not e["name"].startswith("ENT_car_")]
            s["models"] = []
        del parked["stats"], empty["stats"]     # counts of what's compared, the vehicles included
        self.assertTrue(parked == empty, "the vehicles draw from their own seeded stream, so nothing else in the plan moves")


class TheVehicleTableIsThePinnedPack(unittest.TestCase):
    """openspec/changes/archive/2026-09-30-cc0-vehicles, "A vehicle taken from a CC0 pack is pinned and recorded": the
    table names a pinned pack, its variants name bodies it has and textures beside them, and the
    committed models and textures are all there with their albedo in range."""

    def raw(self):
        with open(CP.vehicle_data.TABLE) as f:
            return json.load(f)

    def test_the_committed_table_models_and_textures_pass(self):
        self.assertEqual([], CP.vehicle_data.committed_problems(CP.VEHICLES))

    def test_every_vehicle_is_the_psx_pack_s(self):
        self.assertEqual("psx_style_cars", CP.VEHICLES["pack"], "one style: every vehicle from GGBotNet's PSX Style Cars")

    def test_an_unpinned_pack_is_refused(self):
        raw = dict(self.raw(), pack="kenney_car_kit")
        with self.assertRaisesRegex(CP.vehicle_data.DataError, r"vehicles.json.pack: pack 'kenney_car_kit' is in none of"):
            CP.vehicle_data.validate(raw)

    def test_a_variant_of_a_body_the_table_lacks_is_refused(self):
        raw = self.raw()
        raw["variants"] = raw["variants"] + [{"id": "truck_red", "body": "truck", "texture": "Car 08/Car8.png"}]
        with self.assertRaisesRegex(CP.vehicle_data.DataError, r"variants\[22\].body: no body 'truck'"):
            CP.vehicle_data.validate(raw)

    def test_a_texture_from_another_body_s_folder_is_refused(self):
        raw = self.raw()
        raw["variants"][0] = dict(raw["variants"][0], texture="Car 02/car2.png")
        with self.assertRaisesRegex(CP.vehicle_data.DataError, r"is not a .png beside its body's blend in 'Car 01'"):
            CP.vehicle_data.validate(raw)

    def test_a_misspelt_key_is_refused(self):
        raw = dict(self.raw(), budget_tri=2500)
        with self.assertRaisesRegex(CP.vehicle_data.DataError, "vehicles.json.budget_tri: unknown key"):
            CP.vehicle_data.validate(raw)

    def test_a_missing_model_and_a_texture_out_of_range_are_named(self):
        with tempfile.TemporaryDirectory() as d:
            models, textures = os.path.join(d, "models"), os.path.join(d, "textures")
            os.makedirs(models)
            os.makedirs(textures)
            one = CP.VEHICLES["variants"][0]["id"]
            shutil.copy(CP.vehicle_data.texture_path(one), textures)
            black = os.path.join(textures, CP.VEHICLES["variants"][1]["id"] + ".png")
            Image.new("RGB", (8, 8), (10, 10, 10)).save(black)
            table = dict(CP.VEHICLES, variants=CP.VEHICLES["variants"][:2])
            problems = CP.vehicle_data.committed_problems(table, models, textures)
        self.assertEqual(3, len(problems), problems)
        self.assertIn(f"{one}: its model", problems[0])
        self.assertIn("its texture's mean albedo 0.003 is outside 0.03-0.8", problems[2],
                      "a car that reads black in the baked light (vehicle-fixes, design section 3.2)")

    def test_the_png_reader_agrees_with_the_imaging_library(self):
        for v in CP.VEHICLES["variants"][:4]:
            path = CP.vehicle_data.texture_path(v["id"])
            a = np.asarray(Image.open(path).convert("RGB"), np.float64) / 255.0
            want = float(np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).mean())
            self.assertAlmostEqual(want, CP.vehicle_data.mean_albedo(path), places=9, msg=v["id"])


def glb_triangles(path):
    """The visible triangles in a glb: its meshes' index counts over three, collision aside."""
    with open(path, "rb") as f:
        data = f.read()
    j = json.loads(data[20:20 + struct.unpack("<I", data[12:16])[0]])
    return sum(j["accessors"][prim["indices"]]["count"] // 3 for node in j["nodes"] if "mesh" in node
               and "colonly" not in node.get("name", "") for prim in j["meshes"][node["mesh"]]["primitives"])


if __name__ == "__main__":
    unittest.main()
