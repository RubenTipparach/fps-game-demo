# Design: Meridian's towers around Low Harbor

## Context

Measured on the committed hub (2026-09-28):

| Fact | Value |
|---|---|
| Hub | 240 x 170 m. Its centre is (120, 85). |
| Edges | Invisible 1 m colliders from -8 to 45 m. Blank 10 m backdrop walls where open ground or water meets an edge. Lot buildings of 5-22 m elsewhere. |
| North edge | The Spire Foundations: a 40 m wall with buttresses to 31 m and a holo-billboard, labelled "Halcyon Spire foundation wall, 400 m of tower above". |
| Tallest building | 21 m (Lantern Row); the Sump Market reaches 15.5 m. |
| Skyway | Deck 13-14 m, entering the west edge at y 64 and leaving the east edge at y 146; it ends 4 m past each edge. |
| View | Camera far plane 400 m, fov 67°. Fog colour #2a2d55, density 0.011, no height fog. Sky top #04050b, horizon #2a1f40. Glow threshold 1.0. |
| Fog left at distance d | e^(-0.011 d): 33 % at 100 m, 11 % at 200 m, 1 % at 400 m |
| Sectors | Eight glbs, 121,923 triangles, one LightmapGI each. |

The baseline stills from the market and the Cut show rooftops, then empty, fogged sky.

## Goals / Non-Goals

**Goals**
- The slum reads as the bottom of a megacity from every street.
- The towers are dark masses with lit windows, not fog ghosts.
- The skyline is cheap: unshaded, no shadows, no collision, a few draw calls.
- One source: the layout's `skyline` list drives the level and the map.

**Non-Goals**
- Towers you can enter. The Upper City is a later level.
- Flying traffic, an ad blimp, and animated crowds in windows.

## Decisions

### 1. The skyline in the layout

`hub.py` gains:

```python
"skyline": [
    {"id": "halcyon_spire", "name": "HALCYON SPIRE", "at": (170, -70), "size": (100, 80),
     "height_m": 440, "style": "spire", "crown": "halo", "lit": 0.35,
     "setbacks_m": [120, 260, 380]},
    ...
],
```

Coordinates are layout metres, like everything else, so towers sit at negative or beyond-edge
coordinates. `style` picks the massing (setbacks, a slab, a cluster), `crown` the top (halo,
neon band, billboard, beacons), and `lit` the share of windows lit.

**Named towers,** the near ring:

| Tower | Centre | Footprint | Height | Style and crown |
|---|---|---|---|---|
| Halcyon Spire | (170, -70), north | 100 x 80 m | 440 m | spire; halo ring, beacons |
| Castellan Arcology | (40, -60), north-west | 90 x 70 m | 260 m | stepped arcology; magenta neon band |
| Kosei Stacks | (-60, 60), west | 40 x 120 m | 150 m | residential slab; dense lit windows |
| Harrow Tower | (-70, 150), south-west | 50 x 50 m | 230 m | corporate; a holo-billboard |
| The Pylons | (20, 250), south-west | three of 20 x 20 m | 190-260 m | a cluster; beacons |
| Sable Mutual | (120, 240), south | 60 x 40 m | 320 m | corporate glass; cyan band |
| Pier Nine Arcology | (300, 170), south-east | 80 x 80 m | 210 m | stepped arcology; amber band |
| Meridian Water Authority | (300, 40), east | 60 x 60 m | 180 m | civic; blue band, over the Cut's outflow |

About four unnamed stacks of 120-200 m fill the near ring's gaps. The far ring is about 20
unnamed silhouettes, 200-650 m tall, 400-900 m from the centre. Their exact places are authored
in the layout during the build, within the rules below.

**The Skyway** continues as scenery: deck, parapets and piers 200 m past each edge, with no
collision, in the skyline sector.

### 2. The rules the plan asserts

`city_plan.py` refuses a skyline that breaks these:
- **Bounds:** every tower's footprint stands at least 25 m outside the hub's rectangle.
- **Coverage:** from the hub's centre, at eye height 1.6 m, every 30° sector of the horizon
  holds at least one tower whose top rises 25° or more above the horizon. The slum's rooftops
  reach about 20° from its streets, so every direction shows tower above roof.
- **No overlaps:** no two tower footprints overlap.
- **Budget:** at most 30,000 triangles in all.

### 3. How it renders

`game/shaders/skyline_tower.gdshader`:
- **Unshaded**, with `fog_disabled`: the scene fog would wash the towers out.
- **The facade** is near-black #07080d.
- **Windows** are procedural, from world-space position.
  - Floors are 3.2 m and bays 2.4 m, the window 60 % x 55 % of its cell.
  - A cell is lit if `hash(cell, tower seed) < lit`.
  - Lit colours: warm #ffd9a0 60 %, cool #bfe3ff 30 %, and the tower's neon 10 %.
  - Emission 1.8, above the glow threshold, so lit windows bloom slightly.
- **Crowns:** emissive neon bands; red aircraft beacons blinking every 1.6 s for 20 % of it.
  Billboards reuse the foundation wall's holo material.
- **Its own haze:** `colour = mix(colour, #151733, 1 - e^(-0.0018 d))`, with emission hazed at
  half that rate, since light carries further than surfaces.
  - At 500 m that is 59 % haze on the facade and 36 % on the windows.
  - #151733 is darker than the sky's horizon (#2a1f40), so towers stand out as silhouettes.

**Scene settings:**
- The skyline sector has no LightmapGI and casts no shadows. Its material is unshaded, so the
  bake ignores it.
- The player camera's far plane goes to 1,500 m. Godot 4's reversed depth keeps precision at
  near 0.02 m.
- The rain stays over the hub; the haze stands in for distant rain.
- Meshes merge per material and per ring, 6 draw calls at most.

### 3a. Searchlights (owner, survey I8)

Two beams rise from the Halcyon Spire's crown at 420 m. Each is a long open cone, 3° wide and
900 m long, with an additive unshaded shader. The shader fades along the beam and with the
viewing angle, so a beam seen end-on doesn't blow out. They sweep in slow, opposite circles
(periods of 47 s and 61 s, so they rarely line up), tilted 20-35° from vertical. They cost two
draw calls, and cast no light: they are sky decoration.

### 4. The map

`render_map.py` draws a locator inset in the legend panel, "Low Harbor in Meridian". It shows
the hub's rectangle, the tower footprints from the same `skyline` list, and the named towers'
labels. The main map's frame is unchanged: its 6 m margin can't hold towers 25 m or more
outside it.

### 5. What the runner sees

- **From the Sump Market, looking north:** the foundation wall, and above it the Halcyon Spire
  filling the upper half of the view, its halo ring 440 m up. The Castellan Arcology's magenta
  band sits to its left.
- **From the Cut, looking east:** the Meridian Water Authority's blue band over the Drydock's
  roofs, and Pier Nine to its right. The Skyway runs off into the haze.
- **From Tin Stacks, looking west:** the Kosei Stacks' wall of lit windows, 150 m high and
  120 m wide, over the shanties.

## Risks / Trade-offs

- **A 1,500 m far plane draws more.** Only the skyline sits past 400 m, and it is a handful of
  unshaded draw calls.
- **Procedural windows can look tiled.** Per-tower seeds, the lit share and colour mixes break
  it up; a still per view shows it.
- **The label says the foundation wall carries "400 m of tower above".** The Spire at 440 m
  total, 400 m above the wall, keeps that true.

## Found in building (2026-09-28)

- **One material, not one per part.** Built as first written (a facade material, a beacon
  material, one neon material per colour and the foundation wall's holo material for
  billboards), the sector came to 11 surfaces against the 6 draw calls above. Every tower part
  is now drawn by one `skyline` material. What a face is rides in its vertex colour
  (`tools/levels/skyline.py`, `vertex_color`):
  - red: the tower's lit share;
  - green: its window seed;
  - blue: (part x 8 + neon role) / 32. The parts are facade 0, neon band 1, beacon 2 and
    billboard 3. The role indexes `NEON_ROLES`, the shader's palette, filled from
    `data/character_lighting.json`'s colours by `gen_skyline_materials.py`.

  The built sector is 5 surfaces: the near ring, the far ring, and the Skyway scenery's
  asphalt, concrete and rust. A test decodes every part and role through 8-bit colour, and
  another reads the shader and checks it decodes with the same numbers.
- **A lit window's 10 % neon is now the tower's own.** With a material per part, the facade
  couldn't know its tower's neon, so every tower's neon windows were cyan.
- **Billboards are drawn by the skyline shader.** The foundation wall's holo material takes the
  scene fog. Harrow Tower's billboard is 174 m from the middle of the west edge and 238 m from
  the centre, where the fog leaves 15 % and 7 % of it. The skyline shader draws it as a panel in
  the tower's neon with scrolling scan lines, hazed like the windows (15-19 % there).
- **Triangles.** The budget rule counts the towers at 12 triangles a box: 1,332. The built
  sector, with the Skyway's scenery, is 2,556. Both are far inside 30,000.
- **The far plane.** The farthest tower corner is 1,078 m from the centre and 1,178 m from a
  hub corner, so 1,500 m holds all of it.
- **The rest of the hub is untouched.** The plan's eight existing sectors come out identical
  to the committed ones (compared as JSON). So their glbs, lightmaps and navmesh stand, and
  only the skyline glb is new. The skyline sector is left out of the navmesh group as well as
  the bake.
- **The searchlights sweep in the vertex shader** (`shaders/searchlight.gdshader`). There is no
  script and no per-frame CPU. Each beam is a 900 m open cone, 3° wide, off a lamp 0.8 m across
  (`scenes/undercity/searchlight.tscn`), with a custom AABB covering its whole sweep so it is
  never culled. The layout carries each beam's face, period, phase and tilt range, and
  `skyline.searchlights` places the lamps 1.5 m off the Spire's needle at 420 m. The level sets
  them as instance shader parameters.

## Owner decisions (survey, 2026-09-28)

- I7: all towers as meshes with their own haze (recommendation accepted).
- I8: the scale as designed, plus searchlights (recommendation accepted): section 3a.
- I1 builds this fourth.
