#!/usr/bin/env python3
"""The puddle mask a city level's ground shader reads (openspec/changes/street-puddles, design
section 3.4), written from the level plan's puddles (city_plan.py City.puddles()).

    python3 tools/levels/puddle_mask.py hub     # writes game/levels/undercity/hub/hub_puddles.png

An 8-bit grey-and-alpha PNG over the whole level, TEXEL_M metres a texel, row 0 at layout y 0
(layout (x, y) is Godot (x, z)):
  * grey: the signed distance to the nearest puddle's edge, negative inside, clamped to
    +-RANGE_M. A distance rather than a coverage, so a 0.6 m gutter puddle keeps its shape when
    the shader filters between texels;
  * alpha: the height of the ground the nearest puddle lies on, HEIGHT_M[0]-HEIGHT_M[1] metres,
    so the shader leaves a kerb top or a deck over the same x and z dry.

It lives with the level tools because where a puddle lies is level construction; how it looks
is the ground shader's (game/shaders/city_ground.gdshader), which decodes both channels with the
numbers the level data carries (export_level_data.py), so the two can't drift apart.
"""
import os
import sys

import numpy as np
import shapely
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TEXEL_M = 0.125           # a texel's side, metres
RANGE_M = 0.5             # the distance is clamped to +-this, metres
HEIGHT_M = (-1.0, 3.0)    # the heights alpha spans, metres


def path(level_id):
    return os.path.join(ROOT, "game", "levels", "undercity", level_id, f"{level_id}_puddles.png")


def res_path(level_id):
    return f"res://levels/undercity/{level_id}/{level_id}_puddles.png"


def encode_distance(d):
    return np.round((np.clip(d, -RANGE_M, RANGE_M) / (2 * RANGE_M) + 0.5) * 255).astype(np.uint8)


def decode_distance(v):
    return (np.asarray(v, np.float64) / 255.0 - 0.5) * 2 * RANGE_M


def encode_height(z):
    lo, hi = HEIGHT_M
    return np.round((np.clip(z, lo, hi) - lo) / (hi - lo) * 255).astype(np.uint8)


def decode_height(v):
    lo, hi = HEIGHT_M
    return lo + np.asarray(v, np.float64) / 255.0 * (hi - lo)


def rasterize(puddles, size_m):
    """(distance, height) arrays, rows along y, for puddles ({"g": polygon, "ground_m": z})
    over a level size_m = (width, depth) metres. Puddles never overlap, so the field of their
    union is the smallest of their own signed distances, and a texel takes the height of the
    puddle nearest it."""
    w, h = (int(round(s / TEXEL_M)) for s in size_m)
    dist = np.full((h, w), RANGE_M, np.float64)
    height = np.zeros((h, w), np.float64)
    for p in puddles:
        x0, y0, x1, y1 = p["g"].bounds
        i0, i1 = max(int((x0 - RANGE_M) / TEXEL_M), 0), min(int((x1 + RANGE_M) / TEXEL_M) + 1, w)
        j0, j1 = max(int((y0 - RANGE_M) / TEXEL_M), 0), min(int((y1 + RANGE_M) / TEXEL_M) + 1, h)
        if i0 >= i1 or j0 >= j1:
            continue
        xs, ys = np.meshgrid((np.arange(i0, i1) + 0.5) * TEXEL_M, (np.arange(j0, j1) + 0.5) * TEXEL_M)
        d = shapely.distance(shapely.points(xs, ys), p["g"].boundary)
        d = np.where(shapely.contains_xy(p["g"], xs, ys), -d, d)
        nearer = d < dist[j0:j1, i0:i1]
        dist[j0:j1, i0:i1] = np.where(nearer, d, dist[j0:j1, i0:i1])
        height[j0:j1, i0:i1] = np.where(nearer, p["ground_m"], height[j0:j1, i0:i1])
    return dist, height


def write(level_id, city=None, out=None):
    """Write a city level's mask from its built plan (built here when not given). Returns the path."""
    if city is None:
        import contextlib
        import io
        sys.path.insert(0, HERE)
        import city_plan
        m, ents = city_plan.load(level_id)
        city = city_plan.City(m, ents)
        with contextlib.redirect_stdout(io.StringIO()):
            city.build()
    dist, height = rasterize(city.puddle_list, (city.P.W, city.P.H))
    out = out or path(level_id)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.fromarray(np.dstack([encode_distance(dist), encode_height(height)]), "LA").save(out, optimize=True)
    # Lossless, with 3D detection off: a VRAM-compressed distance would move the puddles' edges.
    sys.path.insert(0, os.path.join(ROOT, "tools", "material_maker"))
    import postprocess
    postprocess.write_import(os.path.dirname(out), os.path.basename(out), lossless=True,
                             res_dir=os.path.dirname(res_path(level_id)))
    return out


if __name__ == "__main__":
    for lid in sys.argv[1:] or ["hub"]:
        print(f"wrote {os.path.relpath(write(lid), ROOT)}")
