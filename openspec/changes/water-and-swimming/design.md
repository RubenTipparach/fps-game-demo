# Design: water you can fall into, swim in and climb out of

## Context

Measured on the committed hub (2026-09-28, `docs/playtest/scripts/baseline_edges.json`):

| Water body | Extent | Surface | Bed | Depth | Quay top above surface |
|---|---|---|---|---|---|
| The Cut | x 192-214, the full 170 m | -2.2 m | -4.5 m | 2.3 m | 2.2 m |
| Dry dock basin | 16 x 40 m, (223, 20)-(239, 60) | -2.2 m | -6.0 m | 3.8 m | 2.2 m |
| Dock gate channel | 11 x 8 m | -2.2 m | -4.5 m | 2.3 m | 2.2 m |

- **The surface** is a zero-thickness prism in `streets_water_*`, which has no `-col` suffix, so
  it has no collider. Its material, `materials/water.tres`, is an opaque ORMMaterial3D.
- **The bed and quay walls** are collidable (`streets_walk_*-col`).
- **The player** (`PlayerController`, Brushfire's Quake-style controller) has gravity 22 and
  jump 7.4, a 1.24 m apex (1.99 m with the crouch tuck), and a 0.45 m step. It has no water,
  ladder or swim code. Neither has anything else in `game/`.
- **The outfall** has a ledge 0.22 m above the surface and a ladder of 4 cm rungs, which the
  step rule (0.2 m ledge depth) can't stand on. It is collision only.
- **Boats** moored in the Cut have decks 0.5 m above the surface.
- **Skyway pillar bases** stand in the Cut at about (206.7, 129.5) and (203.6, 138.6).
- **Railings** leave the west quay open beside both bridges and at the outfall.
- **Brushfire's lava** is a `trigger_hurt` Area3D brush; it is the only liquid-like volume.

## Goals / Non-Goals

**Goals**
- Falling in is never a soft lock.
- Swimming feels like a Quake-era game's, not a physics toy.
- One set of rules for every water body, the Drains' bypass included.
- Water reads as water, from above and below.

**Non-Goals**
- Currents, waves and boats you can drive.
- Swimming NPCs: NPCs stay out of the water, and the placement check enforces it.
- Underwater combat. Weapons holster while swimming.

## Decisions

### 1. Water from the level's data

`tools/levels/export_level_data.py` writes every layout water body into the level's data
(`data/levels/<id>.json` "water": id, `surface_m`, `bed_m` and the polygon). `Undercity.Core`
holds the one rule for how deep a body is in it (`WaterRules.At`, `WaterRules.Contact`), and the
Godot layer asks it through `LevelWater` in engine coordinates (layout x, y is Godot x, z). The
player, ragdoll bones and dropped items all ask the same rule.

Changed in building: the plan was an `ENT_water_<id>` entity per body and an Area3D split into
convex pieces. Data and a point-in-polygon test do the same with nothing to keep in step: no
physics volume, no importer case, and a core test pins the Cut's numbers.

The water prim keeps no collider, and nothing reads a collider's top as the surface: the
surface is data.

### 2. Wading and swimming (the player)

Depth is measured at the feet: `d = surface_y - feet_y`.

| State | When | Movement |
|---|---|---|
| Dry | d <= 0.1 m | Brushfire's ground and air movement, unchanged |
| Wading | 0.1 < d <= 1.2 m | ground movement at 0.6 x speed; no sprint; wading noise (8 m, already in `perception.json`) |
| Swimming | d > 1.2 m | the swim motor below; no gravity; swimming noise (6 m, new) |

The swim motor (`game/scripts/Player/SwimMotor.cs`) is its own class, with a single job.
`PlayerController` hands it the body while swimming.

- **Where you swim.** You move along the look direction (Quake's rule). At the surface a ±20°
  pitch dead zone keeps you from diving when you look slightly down.
- **Horizontal speed.** `v += (wish x speed - v) x (1 - e^(-accel x dt))`. With no input,
  `v *= e^(-drag x dt)`.
- **Floating.** At the surface the eyes settle `float_eye_above_m` above the water:
  `a_y = k x (target - y) - c x v_y`, with k 18/s² and c 7/s (close to critically damped).
- **Up and down.** Jump rises at 2.0 m/s and crouch dives at 2.4 m/s.
- **Entering.** On crossing the surface downwards, vertical speed keeps 30 %, and a splash
  plays, scaled by the impact speed.

Weapons holster on entering the swimming state, and the belt refuses to draw ("Not while
swimming.") until you are wading or dry.

Found in building:
- **The fall is caught at the surface.** The swim motor also takes over the moment the feet
  cross the surface where the water is too deep to stand in (no floor within `swim_depth_m` of
  the surface below). Waiting for swimming depth let a runner falling off the quay accelerate
  through the first 1.2 m of water under gravity.
- **Under the surface with no vertical input, a swimmer hovers** (drag only); the float spring
  acts only while the eyes are above the surface. Jump rises until the eyes break the surface,
  and the spring settles them from there.
- **The hand-off** is `Brushfire.IMovementOverride`: the controller asks `PlayerWater` first on
  every physics tick, and wading slows its ground speed and stops the sprint. `PlayerWater`
  chooses the rule: a mantle under way, a ladder held, the swim motor, or the ground and air.

### 3. Breath (the core)

`Undercity.Core/Vitals/Breath.cs`: breath is a pool of `breath_s` (45 s). It drains 1 per
second while the eyes are under the surface. At the surface it refills to full in
`breath_refill_s` (3 s). At 0 it returns `drown_damage_per_s` (8) damage per second to the
player's health rule. From full health (100) that is 12.5 s more, or 57.5 s in all.

It is the Drains' bypass number: the Drains design gave that bypass a 45 s breath bar for a
35 s swim, and it now reads the same data. A save keeps the current breath.

### 3a. Stamina (owner, survey I3: "swimming consumes stamina but slowly")

`Undercity.Core/Vitals/Stamina.cs` is a pool of `stamina_max` (100). It is used only by
swimming; sprinting on land is unchanged.

| When | Stamina |
|---|---|
| Swimming, at the surface or under it | drains `swim_stamina_per_s` (0.8): 125 s from full, about 375 m at 3 m/s, twice the Cut's length |
| Wading or dry | refills `stamina_regen_per_s` (12): full in about 8 s |
| Empty | swim, dive and rise speeds x `tired_speed_factor` (0.5); no damage, since drowning is the danger |

Below 25 %, the runner's breathing gets heavier and the strokes slower. That is the warning;
there is no meter, and the approved D8 shows air only. A save keeps the current stamina.

### 4. Ways out

| Exit | Rule |
|---|---|
| **Ladder** | A `ladder` entity (`scenes/undercity/ladder.tscn`); its stiles, rungs and hoops are built by the level plan with the quay. It reaches 0.6 m below the surface. Within reach of it (0.5 m out, 0.3 m past a stile, eyes above its foot), facing it (look · into-wall > 0.3) with forward held climbs at 3.0 m/s, and back descends. Jump pushes off at 3.0 m/s. At the top, the player steps in to the ladder's landing over 0.3 s. From the floor there, Use ("Climb down") takes hold at the top. |
| **Mantle** | Swimming or standing, with a ledge top 0.2-1.0 m above the water surface within 0.6 m ahead and 1.8 m of headroom: jump pulls you up in 0.45 s. This covers boat decks (0.5 m) and the outfall ledge (0.22 m). |
| **Stairs** | Any stair or slipway that runs into the water (none in the hub today). |

**Placement** (`city_plan.py`, from the water polygons):
- A ladder every 30 m along each quay edge that meets paving. None within 3 m of a bridge deck,
  a boat or a pillar.
- The outfall's decorative rungs become a ladder entity.
- Each ladder opens a 1.2 m gap in the quay railing and has two grab hoops rising 1.0 m above
  the quay, the way real quay ladders do.

**The exit rule** is asserted by the plan: every point of every water surface, sampled on a
1 m grid, is within 25 m of swimming (the shortest path through the water, round hulls,
buildings and pillars) of a ladder's foot or of a quay low enough to climb onto. That is at most
8.3 s of swimming at 3.0 m/s, a fifth of the breath.

Found in building (the plan's checks and the placement test found each):
- **A straight line was the wrong measure.** A Skyway pillar in the Cut blocked the straight
  line from the water under the Freight Bridge to the nearest ladder, which is 20 m away round
  it. The rule measures the swim.
- **The dry dock is a moat.** The MV Anselm fills the basin, leaving 2-4 m of water round it,
  and buildings stand on the basin's north and east walls, so quay ladders alone left its far
  corner 42 m of swimming from one. The ship hangs four boarding ladders over its side instead:
  its deck is 3.4 m above the water and 2 m from the quay, a jump ashore.
- **A ladder needs somewhere to step off.** Most of the Cut's east quay has a raised strip under
  a metre wide between the water and Quay Road, so a climber stepping 0.7 m in would stand
  astride its kerb. Each ladder's landing is the first spot 0.7-2.0 m in from the edge where a
  standing player (their collider, from `player.tscn`) is on level ground; the climb clears any
  kerb on the way, no more than the player's step (0.45 m) above the landing.
- **Ladder speed is 3.0 m/s, not 2.4.** A floating swimmer's feet are 1.47 m under the surface,
  so the climb to a quay is 3.8 m; at 2.4 m/s plus the 0.3 s step it took 1.97 s, too close to
  the requirement's 2 s. It now takes 1.7 s.
- **Ledges count only as low quays.** A boat deck or the outfall's ledge can be climbed onto,
  and a tired swimmer can rest there, but it leads nowhere, so it isn't a way out.
- **Street lamps step aside.** A lamp that would stand on a ladder's landing moves 2.5 m along
  its street.

The hub has 12 ladders on the Cut (the outfall's among them), one on the dry dock's quay and
four on the ship.

### 5. Water physics for bodies and things

- **Ragdolls float.** Each ragdoll bone in the water gets an upward force
  `1.3 x m x g x f`, where `f` is the submerged fraction of that bone's collider (from its
  centre height and how upright it lies). Linear damping is 2.5/s and angular damping 3.0/s.
  - Changed in building: the ratio was 1.15, and a body that fell in from the quay had risen
    only halfway back to the surface after 6 s. At 1.3 it floats at the surface from 4 s.
  - Changed in building: a body in water isn't frozen at `settle_s`; the freeze stopped a
    rising body under water. It floats on, damped. A body on land freezes as before.
- **Dropped items fall to the floor under them**, through air and, in water, sinking at
  0.6 m/s to the bed, and rest there. The use ray reaches them under water. (Before this, a
  dropped item hung where it was dropped; at a quay's edge it would have hung over the water.)
- **Splashes and ripples** mark where anything enters: player, body, item, bullet.

### 6. Seeing and hearing water

**The surface:** `game/shaders/water.gdshader` replaces the opaque material.
- A depth colour from shallow `#1f4a4a` to deep `#0b2327`, over the water's thickness.
- Two scrolling normal maps (the existing procedural water normal), plus rain ripples, one ring
  at a time in each 0.9 m cell (the hub always rains). The ripples are computed in the shader
  rather than a flipbook texture.
- Roughness 0.05, a screen-space refraction offset, reflections from the existing probes, and
  both faces drawn so the surface shows from below.
- Its numbers are `materials.json` "water" "shader_params": the material pipeline
  (`postprocess.py`) now writes a ShaderMaterial for a material that names a shader. The surface
  takes no baked light and casts no shadow.

**Under the surface:** when the camera is below it, a tint and a dense fog (colour `#0a2226`,
about 8 m of visibility) cover the view: a full-screen quad in front of the player's camera
(`shaders/underwater.gdshader`, `materials/underwater.tres`, `UnderwaterView.cs`). The SFX bus,
which the world bus sends into, goes through a low-pass filter (800 Hz); music doesn't. There is
no separate UI bus, so a menu's clicks are muffled too, and only while the head is under.

**Sound:** splashes (by impact speed), strokes, tired strokes with heavy breathing below 25 %
stamina, and a gasp on surfacing short of air, synthesised by `tools/sfx/generate_sfx.py`. A
splash of droplets (`scenes/undercity/splash.tscn`) marks where the runner, a body or a dropped
item enters.

**The breath meter** (mockup D8, approved by the owner, survey I6): a thin cyan AIR bar under the health bar, shown only
while breath isn't full. It turns red below 25 %, and fades 1 s after it refills. The colours
are the theme's `cyan` and `danger` roles.

### 7. Data

`game/data/water.json`, loaded and validated like every data file (unknown keys refused):

```json
{
  "wade_depth_m": 0.1, "swim_depth_m": 1.2, "wade_speed_factor": 0.6,
  "swim_speed_mps": 3.0, "dive_speed_mps": 2.4, "rise_speed_mps": 2.0,
  "accel_per_s": 4.0, "drag_per_s": 3.0, "surface_pitch_dead_zone_deg": 20.0,
  "float_eye_above_m": 0.15, "float_stiffness_per_s2": 18.0, "float_damping_per_s": 7.0,
  "entry_keep_fraction": 0.3,
  "breath_s": 45.0, "breath_refill_s": 3.0, "drown_damage_per_s": 8.0,
  "stamina_max": 100.0, "swim_stamina_per_s": 0.8, "stamina_regen_per_s": 12.0, "tired_speed_factor": 0.5,
  "stamina_low_fraction": 0.25, "stroke_s": 0.9, "tired_stroke_s": 1.3,
  "breath_low_fraction": 0.25, "air_bar_fade_s": 1.0, "gasp_below_breath_fraction": 0.5,
  "mantle_reach_m": 0.6, "mantle_min_rise_m": 0.2, "mantle_max_rise_m": 1.0, "mantle_time_s": 0.45,
  "ladder_speed_mps": 3.0, "ladder_facing_dot": 0.3, "ladder_reach_m": 0.5, "ladder_side_reach_m": 0.3,
  "ladder_push_off_mps": 3.0, "ladder_top_step_m": 0.7, "ladder_top_step_s": 0.3,
  "body_buoyancy_ratio": 1.3, "body_linear_damp_per_s": 2.5, "body_angular_damp_per_s": 3.0,
  "item_sink_mps": 0.6
}
```

The keys from `stamina_low_fraction` to `gasp_below_breath_fraction`, `ladder_reach_m`,
`ladder_side_reach_m` and `ladder_top_step_s` were added in building: they were numbers in the
design's prose, and CLAUDE.md 5.5 keeps them out of code. The level plan reads
`ladder_top_step_m` and the mantle rise from this file too.

The placement numbers are level construction, so they live in `city_plan.py` with the other
kit constants: `LADDER_EVERY_M` 30, `EXIT_REACH_M` 25, `EXIT_GRID_M` 1, `LADDER_CLEAR_M` 3,
`LADDER_SPACING_M` 10, `RAIL_GAP_M` 1.2, `LADDER_HOOP_M` 1.0, `LADDER_LAND_MAX_M` 2.0.

### 8. Walkthrough: the owner's fall, again

1. The runner walks off the open quay beside the Tin Bridge at (192, 66). Splash. They sink
   about 0.7 m, and the water catches them.
2. They bob up with their eyes 0.15 m above the surface.
3. The nearest ladder is 9 m up the bank. Swimming there takes about 3 s. Forward climbs the
   3.8 m in 1.3 s, and the runner steps over the kerb onto the street behind it.
4. Or they dive: crouch takes them to the bed in about 1 s. The AIR bar appears and drains.
   Surfacing refills it in 3 s.

## Risks / Trade-offs

- **Transparent water loses screen-space reflections** in Godot. The probes and a fresnel mix
  stand in. A still will show whether that reads well enough.
  - Found in building: it didn't. No probe covered any water body, so at swimming height the
    surface reflected the black sky, and the first video showed the lower half of the view
    black, with the floating body lost in it.
  - Now every water body carries outdoor, box-projected probes (`gen_level_hub.py`
    `water_probes`): one per 40 m of its length, 4 m past each side and 20 m tall, capturing
    0.7 m above the surface, where a swimmer's eyes are.
  - The body is filmed from the quay.
- **A point-in-polygon test per body per tick** replaces the Area3D. The hub has three water
  bodies of 4 to 8 points, so it costs nothing that matters; a level with many would want a
  grid.
- **Floating bodies keep simulating.** Each costs a ragdoll's physics while it floats; the hub
  has few, and a level that drowns many would want a cap.
- **Mantling could climb onto things it shouldn't**, such as the top of a moored boat's cabin.
  The 1.0 m limit and the headroom check keep it to decks and ledges.
- **Brushfire's controller predates the rules** (CLAUDE.md 13). The swim motor is new code
  beside it, so the controller only gains the hand-off.

## Owner decisions (survey, 2026-09-28)

- I1: this change is built first.
- I3: drowning on (recommendation accepted), and "swimming consumes stamina but slowly":
  section 3a.
- I4: the exits as designed (recommendation accepted).
- I5: the drowned locker moves to the bed under the Tin Bridge (recommendation accepted). Its
  lock (tier 1) and loot (the Whisper and 10 rounds) are unchanged.
- I6: mockup D8 approved (recommendation accepted).
