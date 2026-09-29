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
2. High-pass it: `H = L - blur(L, σ = 6 px)`. Pores and fine creases are darker, so `h = -H`
   serves as height. (Designed with a normalisation by the local standard deviation; built
   without it, see section 8.)
3. Compute the tangent-space normal `n = normalize(-s · ∂h/∂x, -s · ∂h/∂y, 1)`, with s = 16
   (designed 2.0 on the normalised height; section 8).
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

(Built as `character_outfit.tres`: the eyes share the outfit's material, section 8.)

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
| Rim gel | omni | -140° (behind, the far side), 15° up, 1.2 m | the district's gel | 1.6 | hard: size 0.05 m |
| Accent gel | omni | 150° (behind, the key's side), 5° up, 1.3 m | the district's complement | 0.7 | hard |

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
| Lit side / shadow side | 2.0-4.0, in linear light (section 8) |
| The rim | the rig adds at least 20 luma to the head's far edge (section 8) |
| The world | frame luma outside the speaker changes by less than 2 % with the rig on versus off (section 8) |

The check:
- A new AutoTest step, `{"face_box": "hub:tank"}`, projects two boxes from the eyes to the
  screen, in the camera plane: the face (0.15 m wide, from the chin 0.12 m below to the
  hairline 0.07 m above) and the head (0.22 m wide, 0.14 m either way). It writes them, with the
  key side, to a JSON file beside the shot. (Designed as one head box, ±0.12 m by -0.12 to
  +0.14 m from the head bone; section 8.)
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
    "rim":    {"color": "gel", "energy": 1.6, "azimuth_deg": -140, "elevation_deg": 15, "distance_m": 1.2, "size_m": 0.05, "shadow": false},
    "accent": {"color": "gel_accent", "energy": 0.7, "azimuth_deg": 150, "elevation_deg": 5, "distance_m": 1.3, "size_m": 0.05, "shadow": false}
  },
  "gels": {"lantern_row": ["magenta", "cyan"], "sump_market": ["cyan", "magenta"], "tin_stacks": ["amber", "blue"],
           "kiln": ["ember", "blue"], "drydock": ["sodium", "violet"], "spire_foundations": ["violet", "amber"]},
  "targets": {"face_mean_luma": [95, 150], "key_to_shadow": [2.0, 4.0], "rim_over_background_luma": 20, "world_luma_change_pct": 2.0}
}
```

### 8. Found in building

- **The gels' signs.** Angles are positive toward the key side. The table first gave the rim
  +140° and the accent -150°, which put the rim behind the key's own side, against its
  description ("behind, the far side"), the reference's loop with a rim light, and the rim check
  (`face_luma.py` measures the rim outside the head's far edge). The rim is -140° and the accent
  +150°.
- **The skin's normal was far too strong as designed.** Normalised by the local standard
  deviation and scaled by 2.0, the derived normal tilts a median 37 degrees (95th percentile 70):
  every patch of skin reads as rough stone, oily lips as much as the scalp. Measured on
  `middleage_african_male` at 2,048 px: without the normalisation and with a slope scale of 16,
  the median tilt is 3 degrees and the 95th percentile 15, which shows pores and keeps skin.
  `npcs.json`'s `skin_normal` holds the blur (6 px) and the scale (16).
- **Framing is data.** Mockup D9's numbers (48°, 0.4 s, the face 34 % from the top) are
  `character_lighting.json`'s `framing`.
- **The eyes have no material of their own.** A body has three materials: skin, outfit and
  hair (npc-characters' budget). The eyes are a tile of the outfit atlas and share the outfit
  material, so a `character_eye.tres` would have nothing to replace. The eye's numbers go into
  the outfit instead:
  - `build_npcs.py` writes the outfit normal map's alpha as its roughness: 0.08 on the eyes'
    tile, 0.7 on clothes and gear (`npcs.json`'s `outfit_roughness`; 0.7 is what the outfit had).
  - `character_outfit.tres` reads it, with specular 0.5.

  That is 3 materials and 5 textures still. Measured in silk's glb: alpha 20 (0.08) on the eye
  tile and 179 (0.70) on cloth.
- **The skin material's numbers had drifted from the table above.** The generator was first
  written with specular 0.35 (an F0 of 0.020, not MakeHuman's 0.027), scattering 0.35 and
  transmittance depth 0.08 with no boost. It now writes the table's 0.42, 0.30, 0.2 and 0.3,
  from one `SKIN` dict.
- **The face box was in the wrong units.** `Camera3D.UnprojectPosition` answers in the
  viewport's own size, the project's 1920 x 1080 base stretched to the window, while a shot is
  the window's pixels. At 1280 x 720 the first boxes sat 1.5 times too far right and down. The
  `face_box` step now scales by the shot's size over the viewport's.
- **The instrument, corrected on the first captures:**
  - *Where the face is.* 0.1 m up the head bone is the eyes on every body, not the middle of
    the head, so the designed box ran from the eyes to above the crown. The point is now
    `FaceCentre`, and the step writes a face box (chin to hairline, 0.15 m wide) for the mean
    and the ratio, and a head box for the rim. The design's baseline was hand-placed on faces,
    so the face box is what it measured.
  - *The ratio is of light.* A lighting ratio in the reference (2:1 to 4:1, loop lighting) is a
    ratio of light. Taken on stored values, 2.0 would demand 4.6:1 in light. `face_luma.py`
    decodes sRGB before it divides the halves.
  - *The rim is on the head.* The rig lights only characters, so the background beside the head
    can't brighten; the head's own far edge does. The rim is what the rig adds there: the band
    between the face box and the head box, rig on less rig off.
  - *The world is what isn't the speaker.* The key's cone lights the speaker's shoulders by
    design, and that counted as the world changing (4-8 %). The world is now the frame outside
    the speaker: the head box widened threefold and run down to the frame's foot.
    `lighting_test.tscn` already proves the rig lights only characters.
- **Districts are level data.** `export_level_data.py` writes the layout's district outlines, and
  the core finds a speaker's district with the same polygon rule as water (`LayoutPolygon`). A
  data check refuses a gel pair for a district no level has.

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

Open: **J1** (survey, 2026-09-29), how dark skin meets the face target. One key can't: Tank's
face measured 21 without the rig and 54 with it, Petra's 100 and 140, and a key that takes Tank
to 95 takes Petra to about 216. Recommended, provisionally: expose each face, the key scaled by
the speaker's skin reflectance (measured from the body's skin atlas at build time), capped at 4
times. Nothing is built for it until the answer.
