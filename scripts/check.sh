#!/usr/bin/env bash
# Every check in CLAUDE.md section 9, in order, stopping at the first failure (Pale-Blue-Dot's
# check_all). Run it before every push. CI, when it exists, calls this and nothing else.
#
#   scripts/check.sh          everything
#   scripts/check.sh --fast   skips the Godot project build and the design page
set -euo pipefail
cd "$(dirname "$0")/.."

FAST=0
[[ "${1:-}" == "--fast" ]] && FAST=1

step() { printf '\n== %s\n' "$1"; }

step "Format (core)"
dotnet format core/Undercity.sln --verify-no-changes

step "Build and test the core (warnings are errors)"
dotnet test core/Undercity.sln --nologo -v quiet

step "Level plans: z-fighting, carved rooms, ways out of the water, people clear of the level (CLAUDE.md 7.2, 7.4)"
python3 tools/levels/city_plan.py hub --stats >/dev/null
python3 -m unittest discover -s tools/levels -p 'test_*.py'

step "Generated materials are current (character-lighting, the water and the ground, no standing water in its textures)"
python3 -m unittest discover -s tools/godot -p 'test_*.py'
python3 -m unittest discover -s tools/material_maker -p 'test_*.py'
python3 -m unittest discover -s tools/fx -p 'test_*.py'

step "Generated level data is current"
python3 tools/levels/export_level_data.py >/dev/null
git diff --exit-code -- game/data/levels/ || { echo "game/data/levels changed: commit the regenerated files"; exit 1; }

step "OpenSpec"
openspec validate --all

step "No em or en dashes (CLAUDE.md 4)"
if LC_ALL=C.UTF-8 grep -rnIP '\x{2014}|\x{2013}' --exclude-dir=.git --exclude-dir=.godot \
    --exclude-dir=.claude --exclude-dir=bin --exclude-dir=obj .; then
  echo "FAIL: dashes found"; exit 1
fi

if [[ $FAST == 0 ]]; then
  step "Build the Godot project"
  (cd game && dotnet build --nologo -v quiet)
  step "People placed in the built level, with their own colliders (placement_test.tscn)"
  # pipefail carries Godot's exit code through the filter
  (cd game && flock /tmp/undercity-godot.lock timeout 900 godot --headless --path . \
      res://scenes/undercity/tests/placement_test.tscn 2>&1 | grep -E "FAIL|placement_test\] [0-9]")
  step "UI panels keep their size with overlong text (CLAUDE.md 8, ui_size_test.tscn)"
  (cd game && flock /tmp/undercity-godot.lock timeout 600 godot --headless --path . \
      res://ui/undercity/ui_size_test.tscn 2>&1 | grep -E "^FAIL|ui_size_test\] [0-9]+ passed, 0 failed")
  step "Water: falling in, swimming, breath, ladders, mantling, floating bodies (swim_test.tscn)"
  (cd game && flock /tmp/undercity-godot.lock timeout 600 godot --headless --path . \
      res://scenes/undercity/tests/swim_test.tscn 2>&1 | grep -E "FAIL|swim_test\] [0-9]")
  step "Combat: the Kestrel, damage by the rule, fleeing and cowering, MerSec, death (combat_test.tscn)"
  (cd game && flock /tmp/undercity-godot.lock timeout 900 godot --headless --path . \
      res://scenes/undercity/tests/combat_test.tscn 2>&1 | grep -E "FAIL|combat_test\] [0-9]")

  step "Character lighting: the characters layer, the wrist light, the conversation rig (lighting_test.tscn)"
  (cd game && flock /tmp/undercity-godot.lock timeout 600 godot --headless --path . \
      res://scenes/undercity/tests/lighting_test.tscn 2>&1 | grep -E "FAIL|lighting_test\] [0-9]")

  step "Sliding entrances: every one timed from data, the runner and a person walk through (door_test.tscn)"
  (cd game && flock /tmp/undercity-godot.lock timeout 900 godot --headless --path . \
      res://scenes/undercity/tests/door_test.tscn 2>&1 | grep -E "FAIL|door_test\] [0-9]")

  step "Design maps and page"
  python3 tools/levels/render_map.py
  python3 tools/design/build_page.py
fi

printf '\nAll checks passed.\n'
