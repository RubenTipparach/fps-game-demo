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

`Undercity.Core/World/CrowdPicker.cs`:
`Pick(worldSeed, stableId, role, placement) -> (body, palette, accessories, scale, idle)`. It is
a pure function of its inputs, with no hash order, so a save and a replay agree.

| Aspect | Range | Applied by |
|---|---|---|
| Body | the pool for the role, honouring the lookalike rule below | the model loaded |
| Outfit palette | 8 palettes of hue shift and saturation, named in `crowd.json` | instance uniforms on `character_outfit.gdshader` |
| Accessories | 0-2 from the role's set, each tagged with its bone | `BoneAttachment3D` scenes |
| Height scale | 0.95-1.05 | the model root |
| Idle | from the role's set | the AnimationPlayer |

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

Two civilians within 2 m of each other with the talk idle face each other and play
`Idle_Talking`.

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
