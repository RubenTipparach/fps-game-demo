# Design: faces you can read, lit like a portrait

## Context

**What lights an NPC today** (measured in the code):
- The level's real-time lights: the baked lamps render live for dynamic objects, blue fills at
  0.6 energy, and interior zone ambients at 0.45 energy with no specular.
- The LightmapGI probes, for indirect light.
- Nothing else. Environment ambient is off, since lightmaps and probes carry it.
- The player's flashlight is a 26° spotlight at 4 energy, off by default, lighting everything.
- No light cull masks or visual layers separate characters from the world.

**The dialog screen** freezes the view, and the NPC turns to face the runner. A near-black band
(94 % opaque) covers the bottom 36 % of the screen, so the face sits just above it, where the
level's lighting leaves it.

**Skin:** a 1024 px albedo atlas with roughness 0.7, no normal map, and nothing else.
- The CC0 MakeHuman skins (18 age x ethnicity x sex skins, plus variants) are 2048 px colour
  maps only.
- Their `.mhmat` files declare subsurface scattering (red, green and blue scales 5, 2.5 and 1)
  and a specular colour of 0.027.
- Outfits do have normal maps (11 CC0 garments ship 2048 px normals).

**Face luma** (mean Rec. 709 luma 0-255 over the face box, 1280 x 720):

| Face | Mean | Brightest tenth | Darkest tenth |
|---|---|---|---|
| Tank in conversation, the Anchor | 23 | 46 | 10 |
| Silk, Lantern Row at night | 60 | 77 | 26 |
| Petra, the depot at night | 112 | 170 | 48 |
| Lin, the shrine hall | 161 | 194 | 129 |

The boxes were placed by hand for this measurement. The check below finds them from the head
bone instead.

**The owner's reference:** Digital Camera magazine, "Lighting Guide: master pro portrait
lighting with these 24 essential studio set-ups" (digitalcameraworld.com), sent 2026-09-28.
The set-ups this design takes the shape of:
- **LOOP:** one softbox high and to the side, so the nose's shadow loops towards the corner of
  the mouth.
- **KEY WITH A CLOSE SOFTBOX:** the key a couple of feet away for soft shadows.
- **LOOP WITH A RIM LIGHT:** a hard light behind, catching the edge of the hair.
- **COLOURED GELS:** "A softbox with a red gel creates a glow from the right. A strobe with a
  blue gel lights the background. A strobe with a purple gel adds an accent."

## Goals / Non-Goals

**Goals**
- Every face the runner talks to reads, everywhere in the hub, measured.
- Skin looks like skin under a key light: pores, oily highlights, light through the ears.
- The world's lighting and mood don't change: the new lights touch only characters.

**Non-Goals**
- Cinematic cameras or cut shots. The first-person view stays, with at most a narrower field
  of view (D9).
- Changing how perception treats light. The new lights don't count for stealth.

## Decisions

### 1. Skin that takes light

**The normal map comes from the skin's own detail**, at build time in `build_npcs.py`:
1. Take the luminance `L` of the CC0 skin's 2048 px colour map.
2. High-pass it: `H = L - blur(L, σ = 6 px)`, normalised by the local standard deviation and
   clamped to ±2.5. Pores and fine creases are darker, so `h = -H` serves as height.
3. Compute the tangent-space normal `n = normalize(-s · ∂h/∂x, -s · ∂h/∂y, 1)`, with s = 2.0.
4. Resample it into the body's 1024 px skin atlas, the way the albedo already is.

The MakeHuman UV layout is shared by every body, so one authored mask can say where skin is
oily. That mask is `tools/blender/npc_skin_roughness.png` (1024 px, MakeHuman UV):

| Area | Roughness |
|---|---|
| Nose, forehead, lips, T-zone | 0.42 |
| Cheeks, chin | 0.55 |
| Scalp, neck, body | 0.62 |

The mask goes into the normal map's alpha channel. That makes 5 textures per body (was 4,
budget raised in `npcs.json`), about +150 KB of WebP each.

**The material** is built at import: `setup_npc_import.gd` gives the character glbs a post-import
step that swaps the skin and eye materials for ones built from templates, keeping each body's
textures.

| `character_skin.tres` | Value |
|---|---|
| Normal | the skin normal, strength 1.0 |
| Roughness | the normal map's alpha |
| Specular | 0.42. Godot's F0 is 0.16 x specular², so 0.028: the `.mhmat`'s 0.027. |
| Subsurface scattering | on, skin mode, strength 0.30 |
| Transmittance | colour (0.9, 0.35, 0.25), depth 0.2, boost 0.3, so ears glow against a rim gel |

| `character_eye.tres` | Value |
|---|---|
| Roughness | 0.08 |
| Specular | 0.5, a wet catchlight from the key |

### 2. Characters on their own visual layer

NPC meshes render on layers 1 (the world) and 2 (characters), so the level's lights still light
them. The new lights use `light_cull_mask = 2`: they light characters and nothing else. The
runner's viewmodel stays on layer 1, so the wrist light doesn't wash it out.

### 3. The player's light: the wrist-deck glow

The runner's wrist-deck is the inventory device they already use. Its screen is the light
source.
- An OmniLight3D on the camera rig at (-0.25, -0.35, -0.30) m: low, left, forward.
- Colour `deck_glow` (#9fe8ff), energy 0.6, range 4.5 m, attenuation 1.2, no shadow.
- Characters layer only.
- At 2 m it adds a cool fill: about a third of the conversation key, the guide's key-to-fill
  ratio for loop lighting.

It is always on (survey I9 asks about a toggle). It is not counted by perception: it lights no
world surface, and the story says it's a screen glow.

### 4. The conversation rig: key and two gels

`scenes/undercity/conversation_rig.tscn` is three lights, characters layer only. The dialog
screen adds it when a conversation opens and ramps it in over 0.3 s. It is placed around the
speaker's head bone, and the angles are measured around the head from the camera's line (0° is
the camera's side).

| Light | Type | Where | Colour | Energy | Notes |
|---|---|---|---|---|---|
| Key | spot, 35° cone | 40° to the key side, 30° up, 1.4 m | `key_warm` #ffe2c4 | 2.0 | soft: size 0.25 m, shadows on |
| Rim gel | omni | 140° (behind, the far side), 15° up, 1.2 m | the district's gel | 1.6 | hard: size 0.05 m |
| Accent gel | omni | -150° (behind, the key's side), 5° up, 1.3 m | the district's complement | 0.7 | hard |

**The key side is motivated.** When the rig opens, it sums `energy / distance²` for the level's
lights within 12 m on each side of the speaker, and puts the key on the brighter side. The face
then agrees with the scene it sits in.

**District gels,** the neon the district already shows:

| District | Rim gel | Accent gel |
|---|---|---|
| Lantern Row (and the Rusty Anchor) | magenta #ff3fa8 | cyan #35e0ff |
| Sump Market | cyan #35e0ff | magenta #ff3fa8 |
| Tin Stacks | amber #ffa640 | blue #4a6bff |
| Kiln | ember #ff5a2e | blue #4a6bff |
| Drydock | sodium #ffb347 | violet #8a6bff |
| Spire Foundations | violet #8a6bff | amber #ffa640 |

A building can name its own gel pair in the layout, as the Anchor would.

### 5. The targets, and how they're checked

| Target | Value |
|---|---|
| Face mean luma, in conversation | 95-150 |
| Lit side / shadow side | 2.0-4.0 |
| The rim | a strip just outside the far edge of the head is at least 20 luma above the background beside it |
| The world | whole-frame luma outside the face box changes by less than 2 % with the rig on versus off |

The check:
- A new AutoTest step, `{"face_box": "hub:tank"}`, projects the head bone's box (±0.12 m wide,
  -0.12 to +0.14 m tall, in the camera plane) to the screen. It writes it, with the key side, to
  a JSON file beside the shot.
- `tools/measure/face_luma.py` reads the shot and the JSON and prints the four numbers.
- The capture script takes each conversation twice, rig on and off (`{"rig": false}`), for the
  world check.
- Five speakers make the set: Tank at the bar, Silk, Petra, Nguyen at his stall, and Lin in the
  shrine. That's inside and out, lit and dark districts.

The energies above are starting values; the task that builds the rig tunes them to the targets
on these captures.

### 6. Framing the conversation (mockup D9, approved by the owner, survey I11)

On opening, the field of view narrows from 67° to 48° over 0.4 s, and the pitch recentres so the
face sits 34 % from the top, above the dialog band. It returns on close. The camera doesn't
move.

### 7. Data

`game/data/character_lighting.json`, validated on load (unknown keys refused, colours by
role):

```json
{
  "characters_layer": 2,
  "colors": {"deck_glow": "#9fe8ff", "key_warm": "#ffe2c4", "magenta": "#ff3fa8", "cyan": "#35e0ff",
             "amber": "#ffa640", "ember": "#ff5a2e", "sodium": "#ffb347", "violet": "#8a6bff", "blue": "#4a6bff"},
  "wrist": {"color": "deck_glow", "energy": 0.6, "range_m": 4.5, "attenuation": 1.2, "offset_m": [-0.25, -0.35, -0.30]},
  "conversation": {
    "ramp_s": 0.3, "key_side": "motivated", "motivation_radius_m": 12.0,
    "key":    {"color": "key_warm", "energy": 2.0, "azimuth_deg": 40, "elevation_deg": 30, "distance_m": 1.4, "size_m": 0.25, "spot_angle_deg": 35, "shadow": true},
    "rim":    {"color": "gel", "energy": 1.6, "azimuth_deg": 140, "elevation_deg": 15, "distance_m": 1.2, "size_m": 0.05, "shadow": false},
    "accent": {"color": "gel_accent", "energy": 0.7, "azimuth_deg": -150, "elevation_deg": 5, "distance_m": 1.3, "size_m": 0.05, "shadow": false}
  },
  "gels": {"lantern_row": ["magenta", "cyan"], "sump_market": ["cyan", "magenta"], "tin_stacks": ["amber", "blue"],
           "kiln": ["ember", "blue"], "drydock": ["sodium", "violet"], "spire_foundations": ["violet", "amber"]},
  "targets": {"face_mean_luma": [95, 150], "key_to_shadow": [2.0, 4.0], "rim_over_background_luma": 20, "world_luma_change_pct": 2.0}
}
```

## Risks / Trade-offs

- **A normal map from albedo detail is an approximation.** It gives pores and fine creases, not
  real sculpted shape. The CC0 pack has nothing better, and a sculpt per body would break the
  byte-identical rebuild.
- **Subsurface scattering is a screen-space pass.** It costs frame time on a GPU, which the
  performance task in `combat-and-enemies` (5.1) measures. On lavapipe, captures use the low
  quality setting.
- **Three extra lights in conversation** are only in conversation, and light only characters.
  Shadows are on the key alone.
- **Gels can look garish.** The energies are data, and the captures show them to the owner
  before anything is archived.

## Owner decisions (survey, 2026-09-28)

All recommendations accepted: I9, the wrist glow always on; I10, the key and two gels; I11,
mockup D9 approved; I12, the skin as designed. I1 builds this third.
