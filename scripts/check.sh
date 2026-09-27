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

  step "Design maps and page"
  python3 tools/levels/render_map.py
  python3 tools/design/build_page.py
fi

printf '\nAll checks passed.\n'
