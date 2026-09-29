# Validation: the Blender level and character skills (2026-09-29)

Two Claude Code skills, `.claude/skills/blender-csg-levels` and
`.claude/skills/blender-humanoid-characters`, written on the owner's request ("make a skill for
csg level design in blender, and a skill for humanoid characters generation and rigging in
blender"). They document the existing pipelines and add example, render and kit-copy scripts.
They change no game code, data or generated asset.

## Environment

- Claude Code cloud session, Intel Xeon 2.1 GHz, 4 cores, no GPU (renders are Cycles on the CPU).
- Blender 5.2.2 LTS (linux-x64, downloaded for the session). Python 3 (system).
- Packs: MPFB 2.0.17 and the MakeHuman CC0 system assets, fetched by
  `tools/deps/fetch_character_tools.py`, SHA-256 matching their pins. UAL is a manual pack and
  was not available, so no clip was built.
- Godot and .NET were not run: nothing here touches the Godot project.

## Checks

| Check | Result |
|---|---|
| Baseline: `build_npcs.py -- --verify --only silk,civ_a` | OK, both match their committed glbs byte for byte |
| `templates/example_level.py` builds against the repo's kit | OK: z-fighting clean (5 air volumes, 83 detail boxes, 16 prop boxes), glb about 4,644 triangles, 10 materials |
| `scripts/render_level.py` on that glb | OK: `level_example_eye.png`, `level_example_top.png` |
| `copy_kit.py kit.json --check`, both kits | OK: 12 and 22 files present |
| Level kit copied into an empty project, plus a minimal `materials.json`, builds the example there | OK, same z-fighting result and triangle count |
| `templates/example_table.json` validates (`npc_data.py`) | OK: 3 bodies, 6 gear pieces, 14 colours |
| `build_npcs.py -- --table <example>` into scratch | OK, all inside the budget (below), gear passed its poke-through test at rest and at the stress pose |
| `scripts/render_character.py` on the three bodies with the stress pose | OK: `characters_example_turnaround.png` |
| Dash check (CLAUDE.md 4), including the new `.claude/skills` files | clean |

| Body | Triangles | Materials | Textures | Bones | glb | Fitted height | Gear triangles |
|---|---|---|---|---|---|---|---|
| guard | 10,971 | 3 | 5 x 1024 | 53 | 803 KB | 1.821 m (asked 1.82) | 988 |
| vendor | 13,464 | 3 | 5 x 1024 | 53 | 796 KB | 1.656 m (asked 1.66) | 0 |
| passerby | 13,864 | 3 | 5 x 1024 | 53 | 1,038 KB | 1.669 m (drawn) | 0 |

## Captures

- `docs/screenshots/blender_skills/level_example_eye.png`: the example level from its player
  start: groin vaults, the column, pilasters with plinths and capitals, baseboards, the door
  into the lit corridor.
- `docs/screenshots/blender_skills/level_example_top.png`: its plan, ceilings see-through.
- `docs/screenshots/blender_skills/characters_example_turnaround.png`: the three example bodies
  front, three-quarter, side, back and at the stress pose.

## What this establishes, and what it doesn't

- The skills' scripts run as documented, on Blender 5.2.2, in a cloud session, and the level
  kit works outside this repository.
- The first render of the example level showed a trough in the hall floor: a radius 7.99 m
  vault cutter sprung at 6 m carved 2 m below the floor. The example was rebuilt with 4 m groin
  bays and the rule is written into the skill. The z-fighting check can't see this (cylinders
  aren't boxes): the render is what caught it.
- Not established: the example level and bodies in Godot (import, bake, retarget, ragdoll),
  and any clip build (no UAL pack here). The example level and the three bodies are not game
  content and are not committed as assets.
