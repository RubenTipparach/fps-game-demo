# Proposal: faces you can read, lit like a portrait

## Why

The owner, playtesting on 2026-09-28: "Characters' faces are too dark when we are talking to
them, skin needs normal maps, and the player needs some sort of light source to light NPC faces
in a nice way. Coloured gels seem apt for a cyberpunk game." They sent a studio lighting guide
(Digital Camera magazine's "Lighting Guide: master pro portrait lighting with these 24 essential
studio set-ups", digitalcameraworld.com) and pointed at its COLOURED GELS set-up.

Measured on the committed captures: the mean Rec. 709 luma of each face, 0-255, over the face's
box in a 1280 x 720 still.

| Face | Where | Mean | Brightest tenth | Darkest tenth |
|---|---|---|---|---|
| Tank, in conversation | the Rusty Anchor, at the bar | **23** | 46 | 10 |
| Silk | Lantern Row, at night | 60 | 77 | 26 |
| Petra | outside the depot, at night | 112 | 170 | 48 |
| Sister Lin | the shrine hall, under its lights | 161 | 194 | 129 |

A face is readable only where the level happens to light it, and the conversation, where
the face matters most, does nothing to help.

Why:
- **Nothing lights characters on purpose.** They take the level's real-time lights and the
  lightmap probes. The player's flashlight exists, but it is off by default and lights the whole
  world.
- **Skin is flat.** Each body's skin is a single albedo texture with a constant roughness of 0.7:
  no normal map, no roughness variation, no subsurface scattering. The CC0 MakeHuman skins ship
  only a colour map (2048 px), though their material files ask for subsurface scattering and a
  specular of 0.027.

## What Changes

- **Skin that takes light.** Each body gets:
  - a skin normal map, derived at build time from the fine detail in its CC0 skin texture;
  - a roughness map from one mask authored in the MakeHuman UV layout that every body shares
    (oilier nose, forehead and lips, drier cheeks);
  - Godot's subsurface scattering in skin mode, and a skin specular (F0 0.028, as the MakeHuman
    material says);
  - eyes with a wet specular, so they catch the lights.
- **Characters on their own visual layer**, so lights can reach faces without touching the
  world.
- **The player's light: a wrist-deck glow.** A soft cyan light from the runner's wrist lights
  characters within 4.5 m, and only characters. It is always on: faces read at talking range
  anywhere, and the scene keeps its mood.
- **A conversation rig with coloured gels.** When a conversation opens, three lights ramp in
  around the speaker, following the guide's LOOP, KEY WITH A CLOSE SOFTBOX and COLOURED GELS
  set-ups:
  - a soft warm key, 40° off the camera and 30° up;
  - a rim gel in the district's neon colour behind the far shoulder;
  - a complementary accent gel from the other side.

  They light characters only and ramp out when the conversation ends.
- **Targets that a check measures.** In conversation, a face's mean luma is 95-150, its lit side
  is 2-4 times its shadow side, and the gel rim shows. The world's luma stays within 2 %.
- **Optional: a conversation framing** that narrows the view onto the speaker's face above the
  dialog band. It is new camera behaviour for an approved screen, so it waits for mockup D9
  (survey I11).

## Capabilities

### New Capabilities
- `character-lighting`: skin materials, the characters layer, the wrist light, the conversation
  rig and the face luma targets.

### Modified Capabilities
- None.

## Impact

- **Blender:** `tools/blender/build_npcs.py` derives the skin normal and packs roughness into its
  alpha, within a budget of 5 textures (was 4). The roughness mask is authored once
  (`tools/blender/npc_skin_roughness.png`, MakeHuman UV).
- **Godot:** an import step swaps each body's skin and eye materials for ones built from
  `materials/character_skin.tres` and `materials/character_eye.tres`; NPC meshes go on visual
  layer 2; the wrist light goes on the player scene, and the conversation rig is a scene added
  by the dialog screen.
- **Data:** `data/character_lighting.json` holds the wrist light, the rig and the district gels.
- **Checks:** an AutoTest step prints each face's screen box, and `tools/measure/face_luma.py`
  measures it, so the targets are checked on real captures.
