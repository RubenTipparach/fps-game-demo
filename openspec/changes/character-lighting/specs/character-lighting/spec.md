## ADDED Requirements

### Requirement: Faces read in conversation
In every conversation, the rig SHALL raise the mean Rec. 709 luma of the speaker's face over the
same frame with the rig off, and a gel rim SHALL add at least 20 luma (0-255) to the far edge
of the head. The rig SHALL change the luma of the frame outside the speaker by less than 2 %.
Each speaker's face mean and lit-to-shadow ratio SHALL be recorded; they are not held to one
band, since one key can't put dark and pale skin in the same band (owner J1). The targets SHALL
come from `data/character_lighting.json`, and SHALL be measured on captures by
`tools/measure/face_luma.py` using face boxes projected from the head bone.

#### Scenario: Tank at the bar
- **WHEN** the runner talks to Tank at the Rusty Anchor's bar
- **THEN** Tank's face measures brighter with the rig than without, and his far edge shows the
  district's gel

#### Scenario: The world keeps its mood
- **WHEN** the same conversation is captured with the rig on and with it off
- **THEN** the luma of the frame outside the speaker differs by less than 2 %

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
of F0 0.028; its eyes SHALL have a roughness of 0.08, carried in the outfit normal map's alpha
because they share the outfit's material; and every body SHALL stay within its texture budget
of 5.

#### Scenario: Rebuilding the bodies
- **WHEN** `build_npcs.py -- --verify` runs
- **THEN** every body rebuilds byte for byte with its skin normal and roughness, within budget

### Requirement: Characters are dry under a roof and wet in the rain
Every NPC SHALL carry a wetness from 0 to 1 that rises toward 1 while no roof is over them and
falls toward 0 while one is, at the rates in `data/character_lighting.json`. A roof is a
building's footprint, an awning, a kiosk's roof, the Skyway's deck or a walkway, from the
shelter shapes the level data exports. A roof SHALL count only when its underside is at least
the data's headroom above the character's feet, so a roof never shelters the people standing on
it. The core SHALL decide it. Wetness SHALL lower the roughness of skin and cloth and darken
cloth, between the dry and wet values in the same file, and SHALL leave the eyes as they are. A
level SHALL start everyone at the wetness of where they stand.

#### Scenario: Tank indoors
- **WHEN** Tank stands behind the Anchor's bar
- **THEN** his wetness is 0 and his skin's T-zone roughness is 0.60, where it was 0.42 before
  this change

#### Scenario: Dace in the rain
- **WHEN** Dace stands at the checkpoint gate with nothing overhead
- **THEN** Dace's wetness is 1 and Dace's skin looks as it did before this change

#### Scenario: On a roof
- **WHEN** someone stands on the Rusty Anchor's roof
- **THEN** no roof is over them, though the Anchor shelters everyone inside it

#### Scenario: A civilian runs indoors
- **WHEN** a civilian in the rain runs into the Fish Hall
- **THEN** their wetness falls from 1 to 0 over 240 s, not at once
