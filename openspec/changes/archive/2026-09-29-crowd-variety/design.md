# Design: a crowd, not six twins

## Context

Measured (2026-09-28):
- **Bodies.** 22 generated bodies: 14 named NPCs, `kings_grunt` and `rat_grunt` (not placed in
  the hub), and 6 civilians.
  - `civ_a`: seed 1101, male, African, raincoat.
  - `civ_b`: 2203, female, Caucasian, blond ponytail, red jacket.
  - `civ_c`: 3312, male, Asian, overalls and beanie.
  - `civ_d`: 4413, female, Caucasian, bob, grey top.
  - `civ_e`: 5505, male, African, hi-vis and beanie.
  - `civ_f`: 6609, female, African, magenta bob, black. The Oracle uses it too.
- **The pick.** 31 civilians in the hub each pick one of the 6 models by
  `SeededRandom(world seed, stable id)` (`NpcActor.cs:111-120`). That's about 5 per model.
- **Troopers.** The 5 `mersec_*` NPCs all use `mersec`.
- **What a civilian's seed varies at build time:** MPFB age 19-74, the race mix (70 % pinned),
  height (1.55-1.95 m), eyebrows (12) and eyes (6 of 9). It pins sex, race, skin tone, hair,
  tint, clothes and gear.
- **Unused CC0 assets:**
  - hair: afro01, bob02, braid01, long01;
  - clothes: male_casualsuit01, 02, 04, female_casualsuit01, 02, the fedoras;
  - eyes: bluegreen, deepblue, ice;
  - eyelashes 02-04, and seven skin tones.
- **The idle.** Every placed NPC plays its data idle, `Idle` for civilians.
- **Unused UAL clips:** `Sitting_Idle`, `Sitting_Talking`, `Idle_Torch`, `Fixing_Kneeling`,
  `Interact`, `Idle_Talking` and `Walk_Formal`.

## Goals / Non-Goals

**Goals**
- A market crowd where the eye doesn't catch a twin.
- Variety that costs little memory: most of it is chosen at runtime, from few bodies.
- Deterministic: the same seed gives the same crowd, in a save or a replay.
- Cyberpunk in the details: umbrellas in the rain, visors, implants.

**Non-Goals**
- Crowd simulation, pathing civilians or a day and night schedule.
- Named NPCs change nothing: they keep their authored looks.

## Decisions

### 1. More bodies

- **18 civilian bodies,** `civ_a` to `civ_r`. The 12 new rows are seeded to cover the CC0 skin
  grid, three age bands x three ethnicities x two sexes, as evenly as 18 allows. They use the
  unused hair (afro01, bob02, braid01, long01) and clothes (the five casual suits), and draw eye
  colour and eyelashes from the seed.
- **MerSec:** `mersec_a`, `mersec_b` and `mersec_c`, three faces and skins under the one kit and
  helmet. The five troopers and Dace's squad pick among them.
- The same generator, table and budget apply (16,000 triangles, 3 materials, 5 textures with
  `character-lighting`), and `--verify` rebuilds them byte for byte.

### 2. Runtime variation (the core picks, Godot applies)

`Undercity.Core/World/Crowd.cs`: `CrowdPicker.Assign(worldSeed, crowd, table)` gives every
civilian of a level its (role, body, palette, accessories, scale, idle, partner) at once
(section 5 says why at once). It is a pure function of its inputs, with no hash order, so a
save and a replay agree.

| Aspect | Range | Applied by |
|---|---|---|
| Body | the pool for the role, honouring the lookalike rule below | the model loaded |
| Outfit palette | 8 palettes of hue shift and saturation, named in `crowd.json` | instance uniforms on `character_outfit.gdshader` (1) |
| Accessories | 0-2 from the role's set, each hung from a mount | its prop on the NPC scene's mount node (section 5) |
| Height scale | 0.95-1.05 | the model root |
| Idle | from the role's set | the AnimationPlayer |

(1) character-lighting already gives every body a generated `<id>_outfit.tres`
(StandardMaterial3D, `gen_character_materials.py`), whose roughness is the outfit normal
map's alpha: 0.08 on the eyes, which share the outfit's atlas, and 0.7 on cloth. The shader
that replaces it keeps reading that alpha, or the eyes lose their catchlight.

**Accessories** (Blender, `build_npc_props.py`, each within 800 triangles):

| Accessory | Bone | Notes |
|---|---|---|
| Umbrella, open | right hand | 35 % of outdoor civilians; the hub always rains; `Idle_Torch` holds it |
| Cap, beanie, fedora | head | |
| Headphones, AR visor | head | the visor glows cyan |
| Respirator | head | common in the Kiln |
| Shopping bag, briefcase | hand | |
| Cigarette | right hand | a tiny emissive tip; the idle is smoking |
| Temple or cheek implant | head | emissive |
| Prosthetic forearm | left forearm | illuminated seams |

**Idles by role:**

| Role | Idles |
|---|---|
| Shopper | idle, look around, phone |
| Resident | lean, smoke, talk |
| Dock worker | idle, `Fixing_Kneeling` |
| Seated | `Sitting_Idle`, `Sitting_Talking` (where a seat is placed) |

Two civilians placed within 2 m of each other face each other and play `Idle_Talking` (section
5: the layout places such pairs).

### 3. No lookalikes nearby

On the hub's real placements, with any world seed:
- no two civilians within 15 m share both body and palette;
- no civilian body is used more than 3 times.

`CrowdPicker` assigns in stable id order and skips a candidate that would break either rule.
A core test runs the hub's placement data with seeds 1-100 and asserts both.

### 4. Data

`game/data/crowd.json`, validated on load:

```json
{
  "lookalike_radius_m": 15.0, "max_per_body": 3, "scale_range": [0.95, 1.05],
  "palettes": {"rust": {"hue_deg": 18, "sat": 0.9}, "teal": {"hue_deg": 170, "sat": 0.8}, "...": {}},
  "roles": {
    "shopper":  {"bodies": "civilian", "accessories": ["umbrella", "bag", "headphones", "visor", "cap"], "idles": ["idle", "look_around", "phone"]},
    "resident": {"bodies": "civilian", "accessories": ["umbrella", "cigarette", "beanie", "implant"], "idles": ["lean", "smoke", "talk"]},
    "dockhand": {"bodies": "civilian", "accessories": ["respirator", "beanie", "prosthetic"], "idles": ["idle", "fixing"]}
  },
  "rain_umbrella_share": 0.35
}
```

Each civilian's role comes from its placement's district (market: shopper; Tin Stacks and
Lantern Row: resident; Drydock and Kiln: dockhand), or a `role` prop in `hub_entities.py`.

### 5. Found in building

- **The age band is pinned, not found by seed.** MPFB's skin bands are slider ages 0.65 and
  0.85, 44.5 and 70.5 years, and the civilian range stops at 74, so almost no seed lands "old"
  (none of the first six did; civ_a at 65.8 years is middle-aged). A civilian row may now name
  an `age_band`, and the age is drawn inside the table's `age_bands_years` for it, with the
  same single draw, so the first six rebuild byte for byte. The build refuses a body whose skin
  band isn't the row's.
- **The grid, as built.** The first six held five cells (civ_b and civ_d are both young
  Caucasian women), so the twelve new rows take twelve of the thirteen empty cells, leaving
  middle-aged Caucasian women out: 6 bodies per ethnicity, 9 men and 9 women, 7 young,
  5 middle-aged and 6 old.
- **Eyelashes stay the default.** Drawing them from the seed would move every later draw and
  change the first six bodies.
- **MerSec's three faces are `mersec`, `mersec_b` and `mersec_c`**, keeping the first body's id
  (the troopers' data and scenes name it). mersec_c is a woman; the kit's shoulder plate cut her
  body at the stress pose until her proportions were slimmed (muscle 0.6, weight 0.4).
- **`male_casualsuit01` is decimated to 0.4**: it has 8,336 faces, and civ_j came to 22,714
  triangles against the 16,000 budget.
- **The level data carries no positions for civilians** (`levels/hub.json` maps each stable id
  to "civ"), and the lookalike rule is about distance. The export gains a `crowd` block: each
  civilian's stable id, place (layout metres), district and whether it stands indoors. The core
  assigns the whole crowd at once, in stable id order, since a rule between neighbours can't
  be kept by a function of one civilian: `CrowdPicker.Assign(worldSeed, crowd, table)`.
  Each civilian, in ordinal stable-id order, shuffles its role's bodies and the palettes from
  its own seeded stream and takes the first pair that keeps both rules (the body cap gives way
  first if none can). On the hub's 31 civilians, seeds 1-100, both rules hold.
- **The idles are the clips UAL Standard has.** It has no phone, lean, smoke or look-around
  clip: shoppers and residents idle or talk, dockhands idle or kneel at a repair
  (`Fixing_Kneeling`), and an umbrella forces `Idle_Torch`, which holds it up. The body table
  gains the states `fixing` and `torch`.
- **Accessories carry a slot as well as a mount** (hat, ears, eyes, mouth, temple, a hand, the
  left forearm), so a cap and headphones can share the head but two hats can't. The umbrella
  is drawn first, outdoors only, then up to two in all.
- **Accessories hang from mounts, not bare bones.** A hand's orientation depends on the pose
  (the umbrella is held up in `Idle_Torch`, a bag hangs in the idle), so `npc_bodies.json`
  gains `mounts`: a bone, a point along it and the pose it is fitted in. The NPC scene generator
  puts a node there on every body with the body's axes in that pose, the same way it already
  fitted the weapon grip in the aim pose (the grip is now one mount among six). The prosthetic
  sleeve uses the forearm bone's own axes. Each accessory is built at its mount's origin, so one
  prop fits every body.
- **`Idle_Torch` raises the left hand,** to 1.3 m and 0.45 m forward, with the right hand at the
  side, so the umbrella is held in the left (slot `hand_l`: an umbrella and a bag don't go
  together). `Idle_Talking` swings both hands up to about 1.17 m, which would wave a bag at
  chest height, so a bag or a briefcase forces the plain idle, as the umbrella forces the torch
  idle.
- **Accessories join the Undercity prop kit** (`build_undercity_props.py`), which already makes
  the weapons NPCs hold, instead of a new `build_npc_props.py`: the same modelling kit,
  z-fighting check, glTF export and import presets. Budget 800 triangles each; they came to
  52-244. The umbrella's shaft glows cyan.
- **Head sizes, measured on eleven bodies:** the head bone's joint sits at the top of the neck;
  the skull is 0.16 m wide, its top 0.145-0.18 m up (with hair), the face 0.10-0.126 m forward.
  Hats are sized to the largest.
- **No two hub civilians stood within 10 m of each other** (the closest pair, civilians 18 and
  19, 10.3 m), so a pair rule by idle would never fire. Instead, talking pairs are placed: the
  layout adds four partners, 1.4 m from civilians 10, 12, 19 and 31 (35 civilians in all), and
  any two civilians within `talk_pair_radius_m` (2.0 m) stand talking, face to face, whatever
  the seed (the umbrella's held-up idle still wins).
- **The civilian model list is gone.** `npcs.json` `civilians.models` duplicated the crowd's
  body pool; the pool is the one list now.
- **MerSec's faces are authored, not drawn.** The five troopers are named NPCs with their own
  rows, so each row names its face: the station guard `mersec`, the patrols `mersec_b` and
  `mersec_c`, the desk `mersec_c` and the gate `mersec_b`.
- **The outfit shader** (`character_outfit.gdshader`) reads the roughness from the outfit
  normal map's alpha, as the old material did, and recolours only texels whose alpha is 0.3 or
  more: under that is an eye (0.08), which keeps its colour and its catchlight.

## Risks / Trade-offs

- **Hue shifts can make clothes look dyed wrong.** The palettes are ranges tuned on the lineup
  capture, and skin, hair and eyes are never shifted.
- **Accessories can clip through clothes.** Each is fitted to the MakeHuman base mesh's
  proportions and checked at the stress pose, as the gear already is.
- **More bodies, more memory.** About 14 MB of glb and textures on disk. At runtime only the
  bodies in use load, at most 18 civilians at once in the hub.

## Owner decisions (survey, 2026-09-28)

- I13: 18 civilian bodies, 3 MerSec faces and the runtime variation, as designed
  (recommendation accepted).
- I14: cyber-mod accessories on civilians (recommendation accepted).
- I1 builds this fifth.
