#!/usr/bin/env bash
# Render every Material Maker graph in tools/material_maker/ptex with Material Maker's
# command-line exporter, then convert the result into Godot textures + materials.
#
#   MATERIAL_MAKER_DIR   Material Maker install/source dir (contains project.godot or the binary)
#   GODOT                Godot 4.7 binary used to run Material Maker from source (optional)
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
if [ -x "$MM/material_maker.x86_64" ]; then
  "$MM/material_maker.x86_64" --export-material -o "$RAW" "${files[@]}"
else
  # Running Material Maker from a source checkout with a Godot 4.7 binary.
  "${GODOT:-godot}" --path "$MM" --rendering-driver vulkan --export-material -o "$RAW" "${files[@]}"
fi

python3 "$HERE/postprocess.py" "$RAW" "$ROOT/game"
