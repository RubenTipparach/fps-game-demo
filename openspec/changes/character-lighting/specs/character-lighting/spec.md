## ADDED Requirements

### Requirement: Faces read in conversation
In every conversation, the speaker's face SHALL have a mean Rec. 709 luma of 95-150 (0-255),
its lit side SHALL be 2 to 4 times as bright as its shadow side, and a gel rim SHALL show
beside the far edge of the head. The rig SHALL change the rest of the frame's luma by less
than 2 %. The targets SHALL come from `data/character_lighting.json`, and SHALL be measured on
captures by `tools/measure/face_luma.py` using face boxes projected from the head bone.

#### Scenario: Tank at the bar
- **WHEN** the runner talks to Tank at the Rusty Anchor's bar
- **THEN** Tank's face measures 95-150 mean luma with a lit-to-shadow ratio of 2-4, where it
  measured 23 before this change

#### Scenario: The world keeps its mood
- **WHEN** the same conversation is captured with the rig on and with it off
- **THEN** the luma of the frame outside the face box differs by less than 2 %

### Requirement: New lights touch only characters
Characters SHALL render on a visual layer of their own as well as the world's, and the wrist
light and the conversation rig SHALL light only that layer.

#### Scenario: The wrist light in a dark alley
- **WHEN** the runner stands 2 m from a civilian in the darkest part of Tin Stacks
- **THEN** the civilian's face is lit by the wrist light, and the alley's walls are not

### Requirement: The conversation rig is motivated and coloured by district
When a conversation opens, a key light SHALL ramp in on the side of the speaker where the
level's nearby lights are stronger, with a rim gel and an accent gel in the colours the
speaker's district names in `data/character_lighting.json`; the rig SHALL ramp out when the
conversation ends.

#### Scenario: Silk in Lantern Row
- **WHEN** the runner talks to Silk in Lantern Row
- **THEN** a magenta rim and a cyan accent light her from behind, and the key sits on the side
  of the brighter street lights

### Requirement: Skin has normals, roughness and scattering
Every NPC body's skin SHALL have a normal map derived at build time from its CC0 skin texture,
a roughness from the shared MakeHuman-UV mask, subsurface scattering in skin mode and a specular
of F0 0.028, and every body SHALL stay within its texture budget of 5.

#### Scenario: Rebuilding the bodies
- **WHEN** `build_npcs.py -- --verify` runs
- **THEN** every body rebuilds byte for byte with its skin normal and roughness, within budget
