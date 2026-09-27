#!/usr/bin/env python3
"""Sky layers for the Quake/Unreal-style "sky surfaces" (see game/shaders/sky_surface.gdshader).

Old-school engines didn't draw skies behind the world; a brush face tagged "sky" rendered two
scrolling, tileable layers (Quake) or a skybox zone (Unreal). We do the Quake version: each sky
is a tileable back layer (RGB) and a tileable cloud layer (RGBA) that scroll at different speeds,
plus an optional moon/planet drawn analytically by the shader. Noise is FFT-filtered white noise,
so every layer tiles seamlessly.

    python3 tools/fx/generate_skies.py   # writes game/textures/sky/*.png and the preview
                                         # textures game/textures/sky_*.png (TrenchBroom/Blender)
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "game", "textures", "sky")
TEX = os.path.join(ROOT, "game", "textures")
N = 512


def fbm(seed, beta=2.2, lo=2.0):
    """Periodic 1/f^beta noise in [0, 1]."""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(N)[:, None] ** 2 + np.fft.fftfreq(N)[None, :] ** 2
    f = np.sqrt(f) * N
    amp = np.where(f < lo, 0.0, 1.0 / np.maximum(f, 1.0) ** (beta / 2))
    spec = (rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))) * amp
    n = np.real(np.fft.ifft2(spec))
    lo_p, hi_p = np.percentile(n, (1, 99))
    return np.clip((n - lo_p) / (hi_p - lo_p), 0, 1)


def ramp(t, stops):
    """Colour ramp: stops = [(t, (r, g, b)), ...] with t ascending."""
    ts = [s[0] for s in stops]
    out = np.zeros(t.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(t, ts, [s[1][c] for s in stops])
    return out


def stars(seed, count, bright=1.0):
    rng = np.random.default_rng(seed)
    img = np.zeros((N, N))
    ys, xs = rng.integers(0, N, count), rng.integers(0, N, count)
    mag = rng.uniform(0.15, 1.0, count) ** 3 * bright
    np.add.at(img, (ys, xs), mag)
    big = mag > 0.45 * bright  # a few bright stars get a tiny cross
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        np.add.at(img, ((ys[big] + dy) % N, (xs[big] + dx) % N), mag[big] * 0.35)
    return np.clip(img, 0, 1)


def save(name, arr):
    os.makedirs(OUT, exist_ok=True)
    arr = np.clip(arr, 0, 1)
    mode = "RGBA" if arr.shape[-1] == 4 else "RGB"
    Image.fromarray((arr * 255 + 0.5).astype(np.uint8), mode).save(os.path.join(OUT, name + ".png"), optimize=True)
    print("wrote sky/" + name)


def preview(name, back, front):
    """Composite used as the editor texture (TrenchBroom face / Blender viewport)."""
    a = front[..., 3:4]
    img = back * (1 - a) + front[..., :3] * a
    small = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB").resize((128, 128), Image.LANCZOS)
    small.save(os.path.join(TEX, name + ".png"), optimize=True)
    print("wrote " + name)


def night():
    """Pump Station: deep blue/violet nebula over a starfield (UT's DM-Gothic / Face palette)."""
    n1, n2 = fbm(11, 3.4), fbm(12, 3.6)
    neb = np.clip((n1 - 0.45) * 2.2, 0, 1) ** 1.6
    back = ramp(n2, [(0, (0.01, 0.01, 0.03)), (0.5, (0.03, 0.03, 0.08)), (1, (0.06, 0.04, 0.12))])
    back += neb[..., None] * ramp(n2, [(0, (0.25, 0.08, 0.35)), (0.6, (0.12, 0.18, 0.45)), (1, (0.35, 0.3, 0.7))])
    back += stars(13, 900)[..., None] * np.array([0.9, 0.95, 1.0])
    save("night_back", back)
    c = fbm(14, 3.4)
    alpha = np.clip((c - 0.5) * 2.5, 0, 0.75)
    front = np.dstack([ramp(c, [(0, (0.05, 0.06, 0.12)), (1, (0.18, 0.2, 0.32))]), alpha])
    save("night_clouds", front)
    preview("sky_night", back, front)


def storm():
    """Slag Works: furnace smoke lit orange from below (DM-Barricade storm, Lian-X colours)."""
    n1, n2 = fbm(21, 3.0), fbm(22, 3.6)
    back = ramp(n1, [(0, (0.06, 0.02, 0.01)), (0.5, (0.25, 0.07, 0.03)), (0.8, (0.55, 0.18, 0.05)),
                     (1, (0.9, 0.45, 0.12))])
    back *= (0.6 + 0.4 * n2)[..., None]
    save("storm_back", back)
    c = fbm(23, 3.2)
    alpha = np.clip((c - 0.35) * 1.8, 0, 0.9)
    front = np.dstack([ramp(c, [(0, (0.08, 0.04, 0.03)), (0.7, (0.16, 0.07, 0.04)), (1, (0.35, 0.14, 0.06))]), alpha])
    save("storm_clouds", front)
    preview("sky_storm", back, front)


def moon():
    """Cistern: clear moonlit night with grey-blue clouds (the shader adds the moon)."""
    n1 = fbm(31, 3.6)
    back = ramp(n1, [(0, (0.01, 0.015, 0.035)), (1, (0.03, 0.05, 0.1))])
    back += stars(32, 1400, 0.9)[..., None] * np.array([0.85, 0.9, 1.0])
    save("moon_back", back)
    c = fbm(33, 3.4)
    alpha = np.clip((c - 0.45) * 2.2, 0, 0.85)
    front = np.dstack([ramp(c, [(0, (0.07, 0.09, 0.14)), (1, (0.42, 0.48, 0.6))]), alpha])
    save("moon_clouds", front)
    preview("sky_moon", back, front)


if __name__ == "__main__":
    night()
    storm()
    moon()
