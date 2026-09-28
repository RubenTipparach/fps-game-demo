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

### 1. Water volumes from the layout

`city_plan.py` gives every layout water body an `ENT_water_<id>` entity. Its extras are
`surface_m`, `bed_m` and the polygon. The importer makes it a `Water` node: an Area3D on no
layer, which watches the player, NPC bodies, ragdoll bones and items. Its shape is the polygon
split into convex pieces, from the bed to 0.5 m above the surface.

Nothing reads the collider's top as the surface: the surface is data, `surface_m`. The water
prim keeps no collider, so things still pass through the surface and the volume decides what
happens to them.

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
| **Ladder** | A `ladder` entity (`scenes/undercity/ladder.tscn`, rails and rungs from Blender). Its climb volume runs from 0.6 m below the surface to 1.0 m above the quay. Facing it (look · into-wall > 0.3) with forward held climbs at 2.4 m/s, and back descends. Jump pushes off at 3.0 m/s. At the top, the player steps onto the quay 0.7 m in, over 0.3 s. At the top, Use climbs down. |
| **Mantle** | Swimming or standing, with a ledge top 0.2-1.0 m above the water surface within 0.6 m ahead and 1.8 m of headroom: jump pulls you up in 0.45 s. This covers boat decks (0.5 m) and the outfall ledge (0.22 m). |
| **Stairs** | Any stair or slipway that runs into the water (none in the hub today). |

**Placement** (`city_plan.py`, from the water polygons):
- A ladder every 30 m along each quay edge that meets paving. None within 3 m of a bridge deck,
  a boat or a pillar.
- The outfall's decorative rungs become a ladder entity.
- Each ladder opens a 1.2 m gap in the quay railing and has two grab hoops rising 1.0 m above
  the quay, the way real quay ladders do.

**The exit rule** is asserted by the plan: every point of every water surface, sampled on a
1 m grid, is within 25 m in a straight line (inside the water) of an exit. That is at most
8.3 s of swimming at 3.0 m/s, a fifth of the breath.

For the Cut, this puts 5 or 6 ladders on each bank. The dry dock gets one ladder on each long
side; the gate channel is covered by the dock's ladders.

### 5. Water physics for bodies and things

- **Ragdolls float face down.** Each ragdoll capsule in the water gets an upward force
  `1.15 x m x g x f`, where `f` is the submerged fraction of that capsule (from its centre
  height and radius). Linear damping is 2.5/s and angular damping 3.0/s.
  - The ragdoll's freeze rule is unchanged: it freezes `settle_s` after the fall, wherever it
    floats.
- **Dropped items sink** at 0.6 m/s to the bed and rest there. The use ray reaches them under
  water.
- **Splashes and ripples** mark where anything enters: player, body, item, bullet.

### 6. Seeing and hearing water

**The surface:** `game/shaders/water.gdshader` replaces the opaque material.
- A depth colour from shallow `#1f4a4a` to deep `#0b2327`, over the water's thickness.
- Two scrolling normal maps, plus a rain-ripple flipbook (the hub always rains). The textures
  come from Material Maker.
- Roughness 0.05, a screen-space refraction offset, reflections from the existing probes, and
  both faces drawn so the surface shows from below.

**Under the surface:** when the camera is below it, a tint and a dense fog (colour `#0a2226`,
about 8 m of visibility) cover the view. The world audio bus goes through a low-pass filter
(800 Hz); the UI bus doesn't.

**The breath meter** (mockup D8, approved by the owner, survey I6): a thin cyan AIR bar under the health bar, shown only
while breath isn't full. It turns red below 25 %, and fades 1 s after it refills.

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
  "mantle_reach_m": 0.6, "mantle_min_rise_m": 0.2, "mantle_max_rise_m": 1.0, "mantle_time_s": 0.45,
  "ladder_speed_mps": 2.4, "ladder_facing_dot": 0.3, "ladder_push_off_mps": 3.0, "ladder_top_step_m": 0.7,
  "body_buoyancy_ratio": 1.15, "body_linear_damp_per_s": 2.5, "body_angular_damp_per_s": 3.0,
  "item_sink_mps": 0.6
}
```

The placement numbers are level construction, so they live in `city_plan.py` with the other
kit constants: `LADDER_EVERY_M` 30, `EXIT_REACH_M` 25, `LADDER_CLEAR_M` 3, `RAIL_GAP_M` 1.2,
`LADDER_HOOP_M` 1.0.

### 8. Walkthrough: the owner's fall, again

1. The runner walks off the open quay beside the Tin Bridge at (192, 66). Splash. They sink
   about 0.7 m, and the water catches them.
2. They bob up with their eyes 0.15 m above the surface.
3. The nearest ladder is 11 m up the bank. Swimming there takes about 4 s. Forward climbs the
   2.8 m in 1.2 s, and the runner steps onto the quay.
4. Or they dive: crouch takes them to the bed in about 1 s. The AIR bar appears and drains.
   Surfacing refills it in 3 s.

## Risks / Trade-offs

- **Transparent water loses screen-space reflections** in Godot. The probes and a fresnel mix
  stand in. A still will show whether that reads well enough.
- **Area3D shapes from concave polygons** are split into convex pieces. The Cut's bends take a
  few more pieces, which cost nothing that matters.
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
