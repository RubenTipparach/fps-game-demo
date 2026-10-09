#!/usr/bin/env bash
# Render every Material Maker graph in tools/material_maker/ptex with Material Maker's
# command-line exporter, then convert the result into Godot textures + materials.
#
#   MATERIAL_MAKER_DIR   Material Maker install/source dir (contains project.godot or the binary)
#   GODOT                Godot 4.7 binary used to run Material Maker from source (optional)
#
# Headless (no screen, no GPU), after the material-maker-headless skill's setup.sh:
#   eval "$(bash .claude/skills/material-maker-headless/scripts/setup.sh | grep ^export)"
#   MATERIAL_MAKER_DIR=$MM_DIR tools/material_maker/export_materials.sh
#
# Usage: tools/material_maker/export_materials.sh [name ...]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RAW="$HERE/raw"
mkdir -p "$RAW"

files=()
if [ $# -gt 0 ]; then
  for n in "$@"; do files+=("$HERE/ptex/$n.ptex"); done
else
  for f in "$HERE"/ptex/*.ptex; do files+=("$f"); done
fi

MM="${MATERIAL_MAKER_DIR:?set MATERIAL_MAKER_DIR to your Material Maker folder}"
# No screen (a Claude Code cloud session): Material Maker renders on a RenderingDevice, which
# needs a (virtual) display, so the render runs under xvfb-run. The material-maker-headless
# skill's setup.sh makes the patched checkout and the software Vulkan driver it needs.
xvfb=()
if [ -z "${DISPLAY:-}" ]; then xvfb=(xvfb-run -a -s "-screen 0 1280x800x24"); fi
if [ -x "$MM/material_maker.x86_64" ]; then
  "${xvfb[@]}" "$MM/material_maker.x86_64" --export-material -o "$RAW" "${files[@]}"
else
  # Running Material Maker from a source checkout with a Godot 4.7 binary.
  "${xvfb[@]}" "${GODOT:-godot}" --path "$MM" --rendering-driver vulkan --export-material -o "$RAW" "${files[@]}"
fi

python3 "$HERE/postprocess.py" "$RAW" "$ROOT/game"
