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
- Flying traffic and animated crowds in windows. The survey offers searchlights and an ad blimp
  (I8).

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

## Open Questions

For the owner, in the survey:
- I7: how to render (all meshes with their own haze, recommended; or a painted panorama for
  the far ring);
- I8: the scale and extras (searchlights, an ad blimp).
