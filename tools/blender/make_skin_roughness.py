"""Authors tools/blender/npc_skin_roughness.png: how rough the skin is where, in the MakeHuman UV
layout every body shares (openspec/changes/character-lighting, design section 1). Faces are oily
down the T-zone (forehead, nose, lips), less so on the cheeks and chin, and dry elsewhere, so a
key light picks out the T-zone as a portrait's does.

Run:  blender -b --factory-startup --python tools/blender/make_skin_roughness.py [-- --body civ_a]

It builds one body with build_npcs.prepare_body (the same code the build uses), sorts the skin's
polygons by where their centres sit against the eyes (eye spacing w, the eyes' midpoint E):

  T-zone   facing forward: within 0.55 w of the face's middle line from 2.4 w below E to 1.4 w
           above (nose, lips, chin), and within 1.5 w of it from 0.6 w to 1.6 w above (the brow)
  cheeks   the rest of the face below 0.3 w above E, facing forward
  body     everything else

and paints each class's roughness (npcs.json "skin_roughness") into their UV triangles, blurred by
blur_px so the areas blend. It lives in tools/blender because it is authoring (CLAUDE.md 6.1): the
committed PNG is what the build reads, and re-running rewrites it.
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_npcs as B  # noqa: E402  (also puts tools/deps on sys.path)
import npc_data  # noqa: E402

deps = B.deps
SIZE = 1024
OUT = os.path.join(B.HERE, "npc_skin_roughness.png")


def classify(skin, rig, eyes):
    """Per polygon of the skin: 0 T-zone, 1 cheeks, 2 body."""
    bones = [b.name for b in rig.data.bones]
    head = next((b for b in bones if b.lower() == "head"), None)
    if head is None:
        raise B.BuildError(f"{rig.name}: no head bone")
    co = B.world_coords(skin)
    dom = B.dominant_bones(skin, bones)
    marks = B.landmarks(rig, skin, eyes, bones)
    e = np.array(marks["eyes"])
    across = np.array(marks["eye_l"]) - np.array(marks["eye_r"])
    w = float(np.linalg.norm(across))
    across /= w
    centre = np.array(marks["centroid"][head])
    front = e - centre
    front[2] = 0.0
    front /= np.linalg.norm(front)
    out = np.full(len(skin.data.polygons), 2, np.int8)
    for p in skin.data.polygons:
        vs = list(p.vertices)
        if sum(dom[v] == head for v in vs) * 2 < len(vs):
            continue
        c = co[vs].mean(axis=0)
        rel = c - e
        forward = float(np.dot(c - centre, front)) > 0.0
        lateral = abs(float(np.dot(rel, across)))
        up = float(rel[2])
        if forward and (lateral < 0.55 * w and -2.4 * w < up < 1.4 * w or lateral < 1.5 * w and 0.6 * w < up < 1.6 * w):
            out[p.index] = 0
        elif forward and up < 0.3 * w:
            out[p.index] = 1
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    table = npc_data.load()
    body_id = argv[argv.index("--body") + 1] if "--body" in argv else table["bodies"][0]["id"]
    body = next(b for b in table["bodies"] if b["id"] == body_id)
    cfg = table["skin_roughness"]
    B.ensure_private_blender()
    packs = deps.load_packs()
    allow = B.install_packs([deps.pack_by_id(B.MPFB_PACK, packs), deps.pack_by_id(B.ASSET_PACK, packs)])
    prepared = B.prepare_body(table, body, B.mpfb(), allow)
    skin, rig, eyes = prepared["skin"], prepared["rig"], prepared["eyes"]
    cls = classify(skin, rig, eyes)
    tris, polys = B.uv_triangles(skin)
    rough = np.full((SIZE, SIZE), cfg["body"], np.float64)
    for k, name in ((1, "cheeks"), (0, "t_zone")):
        mask = B.raster_mask(tris[cls[polys] == k], SIZE)
        rough[mask] = cfg[name]
    rough = B.blur(rough, cfg["blur_px"])
    img = bpy.data.images.new("npc_skin_roughness", SIZE, SIZE, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    px = np.repeat(np.clip(rough, 0.0, 1.0)[..., None], 4, axis=-1).astype(np.float32)
    px[..., 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = OUT
    img.file_format = 'PNG'
    img.save()
    counts = np.bincount(cls, minlength=3)
    print(f"[skin_roughness] {body_id}: {counts[0]} T-zone, {counts[1]} cheek, {counts[2]} body polygons; wrote {OUT}")


if __name__ == "__main__":
    try:
        main()
    except (B.BuildError, npc_data.DataError) as e:
        print("FAIL", e, flush=True)
        sys.exit(1)
