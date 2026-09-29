# Proposal: a crowd, not six twins

## Why

The owner, playtesting on 2026-09-28: "Would be cool to have some variety in NPCs too."

Measured:
- **31 civilians share 6 bodies** (civ_a to civ_f), about 5 identical copies of each. Nothing
  varies a civilian at runtime: same face, clothes, colours, height and idle.
- **5 MerSec troopers share one body.** A uniform is right, the same face under it isn't.
- **Every civilian plays the same idle.** None sits, smokes, takes a call or talks to another.
- **The CC0 packs have more than the generator uses:**
  - hair: afro01, bob02, braid01 and long01;
  - clothes: five casual suits and both fedoras;
  - three eye colours, three eyelash sets, and seven skin tones;
  - UAL clips: sitting, sitting and talking, idle-with-torch, kneeling repair, and more.

## What Changes

- **More bodies.** 18 civilian bodies, up from 6, generated from seeds across every age band,
  ethnicity and sex the CC0 skins cover, with the unused hair and clothes. MerSec get 3 bodies
  (different faces, one kit).
- **Runtime variation for every civilian,** chosen by a rule in the core from the world seed and
  the civilian's stable id, so a save and a replay reproduce the crowd:
  - an outfit palette, a hue and saturation shift of the outfit material within named ranges;
  - 0-2 accessories attached to bones: an umbrella (in the rain), caps, beanies, headphones,
    respirators, a shopping bag, a briefcase, a lit cigarette, AR visors, and cyber-mods (glowing
    temple and cheek implants, an illuminated prosthetic forearm);
  - a height scale of 0.95-1.05;
  - an idle from their role: phone, smoke, lean, look around, sit where a seat is, or talk with a
    neighbour.
- **No lookalikes nearby.** No two civilians within 15 m share a body and a palette, and no body
  is used more than 3 times in the hub. A core test checks both on the hub's real placements.
- **A lineup capture** of the 18 civilian bodies, and a crowd capture of the market.

## Capabilities

### New Capabilities
- `crowd-variety`: the civilian pool, runtime variation, and the no-lookalike rule.

### Modified Capabilities
- None.

## Impact

- **Blender:** `tools/blender/npcs.json` gains 12 civilian rows and 2 MerSec rows;
  `tools/blender/build_npc_props.py` builds the accessories (glbs and a `.blend`), tagged by the
  bone they attach to.
- **Core:** `World/CrowdPicker.cs` chooses body, palette, accessories, scale and idle.
- **Godot:** `NpcActor` applies the choice: the outfit shader's instance uniforms, accessory
  scenes on `BoneAttachment3D`s, the scale, and the idle clip. `shaders/character_outfit.gdshader`
  does the hue shift.
- **Data:** `data/crowd.json` holds the palettes, accessory sets by role and the idle sets.
- **Size:** about 14 more bodies at about 1 MB each, and small accessory glbs.
