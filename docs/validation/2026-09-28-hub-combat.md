# Validation: the Kestrel fires in the hub

The owner, playtesting the hub on 2026-09-28: "I wish I had a gun in the main hub to actually do
stuff." The survey put this change second (I1), after water, and settled that the Kestrel fires
in the hub, everyone can be shot, gunfire is a crime and MerSec fight back (I2), and that death
fades out and loads the newest save (I15). This record covers `openspec/changes/archive/2026-09-28-hub-combat`,
built on branch `claude/elegant-gauss-qwjhk1`.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe), Xvfb |
| Blender | 5.2.2 |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| .NET | 8.0.425 |
| Seed | `BRUSHFIRE_SEED=7` for the combat test and the capture |

## The checks

| Check | Command | Result |
|---|---|---|
| Core tests | `dotnet test core/Undercity.sln` | 173 of 173: the damage rule, zones and caps, magazines and the timed reload, NPC health under each person's own key, violence and reputation, the runner's health and death, who does what (`DefenceOf`, `Respond`), the seeded NPC shot, and every sound, scene, hand model and clip the data names existing on disk |
| Format | `dotnet format core/Undercity.sln --verify-no-changes` | clean |
| Prop kit | `blender -b --factory-startup -P tools/blender/build_undercity_props.py` | z-fighting clean; the Kestrel 416 triangles, the baton 144, the scattergun 276 |
| Combat test | `godot --headless --path game res://scenes/undercity/tests/combat_test.tscn` | 23 of 23 (below) |
| Placement test | `placement_test.tscn` | 434 of 434, with the NPC scene's new navigation agent and hand attachment |
| Swim test | `swim_test.tscn` | 18 of 18, after the splash became a shared particle burst |
| UI panel sizes | `ui_size_test.tscn` | 312 passed, the D3 weapon panel's rounds among them |
| OpenSpec | `openspec validate --all` | all valid |
| Dashes | CLAUDE.md 4 | none |

`scripts/check.sh` runs the combat test after the swim test.

### The combat test, in the hub, with the real keys

| Check | Requirement | Result |
|---|---|---|
| Drawing the Kestrel puts it in the runner's hand | The Kestrel fires from the pack's ammunition | the Kestrel, raised |
| It comes loaded, the kit's rounds in the pack | | 12 / 24 |
| A torso shot takes the rule's damage | Damage uses zones and capped resistances | 22 of a civilian's 60 |
| The civilian's health is kept under their own stable id | Everyone can be shot | `hub:civ_02` |
| A shot no trooper hears leaves MerSec calm | Gunfire is a crime | the nearest trooper 30 m, noise 20 m |
| A civilian who flees runs when shot | Those who can defend themselves do | fleeing |
| A shot at 1.64 m takes the head's damage | Damage uses zones and capped resistances | 44 |
| A civilian who cowers drops where they are | Those who can defend themselves do | cowering |
| The civilian dies, and every other civilian is still alive | Everyone can be shot | dead and fallen; 30 of 30 others alive |
| Killing costs the assault and the murder reputation | Gunfire is a crime | residents -20 to -85 (-65) |
| A fleeing civilian ends at least 25 m from the shot, cowering | Those who can defend themselves do | 31.1 m from the shot, after a 28.8 m run |
| An empty magazine's trigger starts a reload, still under way before its time, then full from the pack | The Kestrel fires from the pack's ammunition | 0.09 s left of 1.4 s; then 12 / 12 |
| The HUD reads the rounds | | "12" |
| A shot heard in the bar makes Silk surrender | Those who can defend themselves do | surrendered, 9.2 m away |
| Tank, who only heard it, holds | Those who can defend themselves do | not hostile |
| Shot, Tank comes at the runner and lands his baton | Those who can defend themselves do | fighting; the runner at 82 |
| A shot a trooper hears makes MerSec hostile at once | Gunfire is a crime | Officer Dace, 12 m away |
| A hostile trooper fires back and hits | Gunfire is a crime | the runner at 64 |
| The runner dies at no health, and the screen fades | Death loads the newest save | holstered; the fade half dark at half its time |

## What building found

Each is in the design's section 10.

- **People didn't climb kerbs.** The first fleeing civilian stopped at the first kerb: its edge
  meets a 0.35 m capsule at 55 degrees from level, a wall to CharacterBody3D's default 45. The
  NPC scene's floor angle is now worked out from the kerb height and the capsule (58.2 degrees).
- **The navigation agent never reached a waypoint** when its radius was tightened: the navmesh
  lies 0.3 m above the street and the agent measures in 3D. The path is lowered to the feet, and
  a waypoint is reached within 0.35 m, so a sprinter no longer clips a stall's corner.
- **The grip was fitted to the rest pose** at first: a skeleton outside the scene tree doesn't
  update its global poses. The generator now composes the hand's pose itself, and the barrel
  points along the fingers in UAL's pistol aim.
- **The Kestrel's first serrations z-fought** by the checker's rule (1.5 mm proud, within its
  5 mm): they are now 11 mm steps in the slide, and the round counter a small lens.
- **The AutoTest `kill` step had the civilian bug too**, writing every civilian's death under
  "civ". It uses the target key now.

## Captures

`docs/screenshots/hub_combat/hub_combat.mp4` comes from `docs/playtest/scripts/hub_combat.json`,
written with `--write-movie` at 30 fps with `BRUSHFIRE_SEED=7`: 1,098 frames, 36.6 s, rendered
in 64 minutes on lavapipe at 1600 x 900 with the 3D view at 0.67 scale, encoded to H.264 at
1280 x 720 with its sound. The run quit with exit 0 and logged no errors. The stills beside it:

| Still | Shows | Requirement |
|---|---|---|
| `01_kestrel_drawn.png` | The Kestrel drawn in the Sump Market, 12 / 24; a trooper who sees it barks "Put it away." | The Kestrel fires from the pack's ammunition |
| `02_the_shot.png` | The shot, 11 / 24. The market-goer the script aims at had walked on in this run, so the shot hits nobody; it is heard. | Gunfire is a crime |
| `03_people_flee.png`, `04_people_cower.png` | A civilian across the square drops and cowers at the sound. | Those who can defend themselves do |
| `05_mersec_fires_back.png` | Outside Low Harbor Station, a shot a trooper hears: "MerSec is hostile", "Hostile in the Sump!" | Gunfire is a crime |
| `06_reloading.png`, `07_reloaded.png` | The magazine emptied, 0 / 24 and RELOADING, then 12 / 12. | The Kestrel fires from the pack's ammunition |
| `08_tank_swings.png` | The Rusty Anchor: the runner shoots Tank behind his bar. | Those who can defend themselves do |
| `09_fading.png` | Frame 1,036 of the movie: the screen half dark after the killing blow. | Death loads the newest save |
| `10_the_newest_save.png` | The newest save loaded: full health, holstered, the law calm, MerSec's reputation as it was. | Death loads the newest save |

What the video shows that the stills don't, and what it doesn't show:
- **The death takes longer than the script says.** The script sets the runner's health to 4 and
  calls the next blow a kill. Health first climbs to 22 (the regeneration up to the 25 % floor,
  owner B1) while Tank comes round the bar, and then two baton blows take it to 6 and 0. The
  fade starts at 33.8 s and lasts 1.5 s, and the save loads at 35.3 s. The script's own still
  09 came 5 s before the blow, showing health 14 and no fade; the still above is the movie's
  own frame, and the script's is not kept.
- **The trooper doesn't hit in this run.** MerSec turns hostile and the trooper barks, but the
  runner's health stays 100 through the stand-off. The combat test's run (the table above) is
  the one where the trooper fires back and hits.
- **Tank's swing is off screen.** The view stays on the bar while he comes round it, so the
  blows show as the health bar falling.

## What the checks establish

- The runner can draw, fire and reload the Kestrel anywhere in the hub, with rounds from the
  pack, and the HUD shows them.
- A shot hurts whoever it hits by the one damage rule, in the zone its height says, and each
  person's health and death are kept under their own key: killing one civilian kills no other.
- People answer violence as their data says: civilians flee at least 25 m along the navmesh or
  cower, Silk surrenders, Tank holds at a shot he only hears and fights when hurt, and MerSec
  turn hostile at a shot a trooper hears and fire back.
- The runner dies at no health and the screen fades.

## What they don't establish

- **The load after death, headless.** The test checks the fade; the newest save loading after
  it is `SaveStore.Newest`'s (its core tests) and the capture's (still 10), not the headless
  test's, which would lose its own scene to the load.
- **Kessler's scattergun, surrender's end and a fighter losing the runner** (pursuit ends 20 s
  after the last shot or hit) are built and not checked.
- **Frame cost.** Lavapipe doesn't measure it.
- **How it sounds.** The Kestrel's shot and reload, MerSec's pistol and the baton's swing were
  generated and wired, not listened to.
- **How it feels.** Nine torso shots per trooper is the design's number (I2: outsmart, don't
  outshoot); nobody has played a fight through yet.
