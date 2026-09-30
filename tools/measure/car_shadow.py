#!/usr/bin/env python3
"""Measures how much a parked car darkens the baked ground under it (openspec/changes/archive/2026-09-30-vehicle-fixes,
design section 2.3): the ground between its wheels over the ground 1 m beside it.

    python3 tools/measure/car_shadow.py with.png without.png --model <variant id>

The two stills look straight down on one car from the same free camera (the AutoTest `camera`
step), with the car and with it hidden (`hide`): the ground's lightmap holds the car's shadow
either way, because the bake saw the car. It finds the car's silhouette as the pixels the two
stills disagree on (the largest such region), takes the metre from the silhouette's long side and
the model's length (tools/blender/vehicle_data.py, model_bounds: the committed glb), and prints
one JSON line:

  under    the hidden still's median linear luminance inside the silhouette shrunk by a quarter of
           its width from each side: the ground between the wheels
  beside   the same in a band round the silhouette from 0.3 m to 1.3 m out
  ratio    under over beside; the design's threshold is 0.6

Luminance is Rec. 709 on the stills' values decoded from sRGB. A median, not a mean: the HUD's
crosshair sits in the middle of the view, right over the car, and rain streaks cross the frame;
at night the ground is so dark (about 0.002) that a few near-white pixels would outweigh it. It lives in tools/measure beside the
other instruments that read the game's captures, and changes nothing in the game.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "blender"))
import vehicle_data  # noqa: E402

DIFFER = 10 / 255.0      # a pixel is the car's when the stills' stored values differ by more than this
BAND_M = (0.3, 1.3)      # the ground beside the car: this far out from its silhouette, metres
SHRINK = 0.25            # the ground under it: the silhouette shrunk by this share of its width, each side


def linear_luma(img):
    a = np.asarray(img.convert("RGB"), np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def measure(with_path, without_path, model):
    a, b = Image.open(with_path), Image.open(without_path)
    sa = np.asarray(a.convert("RGB"), np.float64) / 255.0
    sb = np.asarray(b.convert("RGB"), np.float64) / 255.0
    mask = np.abs(sa - sb).max(axis=2) > DIFFER
    mask = ndimage.binary_opening(mask, iterations=2)
    labels, n = ndimage.label(mask)
    if n == 0:
        raise SystemExit(f"{with_path}: the two stills don't differ; is the car in view?")
    car = labels == (np.argmax(ndimage.sum(mask, labels, range(1, n + 1))) + 1)
    car = ndimage.binary_fill_holes(car)
    ys, xs = np.nonzero(car)
    pts = np.stack([xs, ys], 1).astype(np.float64)
    pts -= pts.mean(0)
    _, _, axes = np.linalg.svd(pts, full_matrices=False)
    along, across = pts @ axes[0], pts @ axes[1]
    length_px, width_px = np.ptp(along), np.ptp(across)
    (_, y0, _), (_, y1, _) = vehicle_data.model_bounds(model)
    px_per_m = length_px / (y1 - y0)
    inside = ndimage.distance_transform_edt(car) > SHRINK * width_px
    out = ndimage.distance_transform_edt(~car)
    band = (out > BAND_M[0] * px_per_m) & (out <= BAND_M[1] * px_per_m)
    lum = linear_luma(b)
    under, beside = float(np.median(lum[inside])), float(np.median(lum[band]))
    return {"model": model, "under": round(under, 4), "beside": round(beside, 4), "ratio": round(under / beside, 3),
            "px_per_m": round(px_per_m, 1), "under_px": int(inside.sum()), "beside_px": int(band.sum())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("with_car")
    ap.add_argument("without_car")
    ap.add_argument("--model", required=True, help="the car's variant id (vehicles.json)")
    args = ap.parse_args(argv)
    print(json.dumps(measure(args.with_car, args.without_car, args.model)))


if __name__ == "__main__":
    main()
