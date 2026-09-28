#!/usr/bin/env python3
"""Measures how a face reads in a conversation shot (openspec/changes/character-lighting,
design section 5): the four numbers the targets are set on.

    python3 tools/measure/face_luma.py shot.png [--off shot_rig_off.png]

It reads the shot and the box the AutoTest `face_box` step wrote beside it (shot.png.face.json:
{"who": "hub:tank", "box": [x0, y0, x1, y1], "key_side": "left" | "right"}, pixels, the head
bone's box projected to the screen) and prints:

  mean       the face box's mean luma
  lit/shadow the key side's half over the other half
  rim        a strip just outside the head's far edge (away from the key) over the background
             a strip further out
  world      with --off (the same view with the rig off): how much the frame outside the face
             box changed, percent

Luma is Rec. 709 on the stored (gamma-encoded) 0-255 values, as the baseline in the design was
measured. When game/data/character_lighting.json exists, each number is checked against its
"targets" and the tool exits 1 if any misses.

It lives in tools/measure because it is an instrument (CLAUDE.md 3): it only produces numbers.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGETS = os.path.join(ROOT, "game", "data", "character_lighting.json")
RIM_STRIP = 0.08    # the rim and background strips, as a fraction of the box's width (at least 3 px)


def luma(path):
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def load_json(path):
    """A JSON file whose whole-line // comments JSON can't parse (the game's data files)."""
    with open(path) as f:
        return json.loads("\n".join(line for line in f if not line.lstrip().startswith("//")))


def clamp_box(box, w, h):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    return max(0, x0), max(0, y0), min(w, x1), min(h, y1)


def measure(shot, face, off=None):
    y = luma(shot)
    h, w = y.shape
    x0, y0, x1, y1 = clamp_box(face["box"], w, h)
    if x1 - x0 < 4 or y1 - y0 < 4:
        raise SystemExit(f"{shot}: the face box {face['box']} is off screen or too small")
    box = y[y0:y1, x0:x1]
    mid = (x1 - x0) // 2
    left, right = box[:, :mid].mean(), box[:, mid:].mean()
    lit, shadow = (left, right) if face["key_side"] == "left" else (right, left)
    out = {"who": face.get("who", "?"), "mean": box.mean(), "lit_over_shadow": lit / max(shadow, 1.0)}

    # The rim: outside the far edge, over the upper two thirds of the box where the hair and ears are.
    s = max(3, int(round((x1 - x0) * RIM_STRIP)))
    top, bottom = y0, y0 + (y1 - y0) * 2 // 3
    if face["key_side"] == "left":
        rim, bg = y[top:bottom, x1:x1 + s], y[top:bottom, x1 + 2 * s:x1 + 3 * s]
    else:
        rim, bg = y[top:bottom, max(0, x0 - s):x0], y[top:bottom, max(0, x0 - 3 * s):max(0, x0 - 2 * s)]
    out["rim_over_background"] = rim.mean() - bg.mean() if rim.size and bg.size else float("nan")

    if off is not None:
        y_off = luma(off)
        if y_off.shape != y.shape:
            raise SystemExit(f"{off}: {y_off.shape} isn't the shot's size {y.shape}")
        mask = np.ones_like(y, dtype=bool)
        mask[y0:y1, x0:x1] = False
        on_mean, off_mean = y[mask].mean(), y_off[mask].mean()
        out["world_change_pct"] = abs(on_mean - off_mean) / max(off_mean, 1.0) * 100.0
    return out


def check(m, targets):
    """Each number against data/character_lighting.json's targets: (name, value, ok)."""
    lo, hi = targets["face_mean_luma"]
    klo, khi = targets["key_to_shadow"]
    rows = [("mean", m["mean"], lo <= m["mean"] <= hi),
            ("lit/shadow", m["lit_over_shadow"], klo <= m["lit_over_shadow"] <= khi),
            ("rim", m["rim_over_background"], m["rim_over_background"] >= targets["rim_over_background_luma"])]
    if "world_change_pct" in m:
        rows.append(("world %", m["world_change_pct"], m["world_change_pct"] < targets["world_luma_change_pct"]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("shot", help="the conversation shot (.png); its .face.json sits beside it")
    ap.add_argument("--off", help="the same view with the conversation rig off, for the world check")
    a = ap.parse_args()
    face_json = a.shot + ".face.json"
    if not os.path.exists(face_json):
        raise SystemExit(f"{face_json}: no face box (the AutoTest face_box step writes it)")
    m = measure(a.shot, load_json(face_json), a.off)
    targets = load_json(TARGETS).get("targets") if os.path.exists(TARGETS) else None
    print(f"{m['who']}: mean {m['mean']:.0f}, lit/shadow {m['lit_over_shadow']:.2f}, "
          f"rim {m['rim_over_background']:+.0f}" + (f", world {m['world_change_pct']:.2f} %" if "world_change_pct" in m else ""))
    if targets is None:
        return 0
    missed = [f"{name} {value:.2f}" for name, value, ok in check(m, targets) if not ok]
    print("  targets: " + ("met" if not missed else "missed: " + ", ".join(missed)))
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
