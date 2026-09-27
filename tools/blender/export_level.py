"""Export the currently open level .blend to Godot (glTF), applying booleans on a copy.

  blender tools/blender/cistern.blend -b -P tools/blender/export_level.py -- game/levels/blender/cistern.glb

or open the .blend, switch to the Scripting workspace, load this file and Run Script
(it exports next to the default path below). The .blend itself is not modified.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blendkit import GAME, export_level  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
target = argv[0] if argv else os.path.join(GAME, "levels", "blender",
                                           os.path.splitext(os.path.basename(bpy.data.filepath))[0] + ".glb")
export_level(os.path.abspath(target))
# Throw away the temporary export objects so an interactive session stays clean.
bpy.ops.ed.undo_push(message="Export level")
