#!/usr/bin/env python3
"""Procedural PBR maps for the Undercity city kit: the surfaces Material Maker's set lacks.

    python3 tools/fx/generate_city_materials.py

Writes raw maps (<name>_albedo/_normal/_orm/_emission.png) to tools/material_maker/raw/, then
runs tools/material_maker/postprocess.py's process() on them, which writes
game/textures/<name>*.png, their import presets, and game/materials/<name>.tres. That is the
same path the Material Maker materials take, so texel density (tile_m in materials.json) and the
emission rule (emission_operator = 1, Multiply; CLAUDE.md 11) cannot differ between the two.

Materials (tile_m is metres per texture repeat, see materials.json):
  asphalt           wet asphalt with aggregate, cracks and puddles (streets)
  paving_wet        0.5 m slabs, wet, puddles in the joints (sidewalks and squares)
  window_lit_warm   a lit window behind blinds, warm (emissive)
  window_lit_cool   a lit window, cool television or strip light (emissive)
  window_dark       an unlit pane: near-black glass that reflects the street
  glass             a shop window: dark, glossy, faintly blue
  neon_pink         neon tube, pink #ff4fa3 (emissive)
  neon_cyan         neon tube, cyan #35e0ff (emissive)
  water             canal water: black-green, rippled, mirror-smooth
  awning            striped canvas
Every map is seeded, so the same script writes the same files.
"""
import os
import sys
import zlib

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "tools", "material_maker", "raw")
GAME = os.path.join(ROOT, "game")
sys.path.insert(0, os.path.join(ROOT, "tools", "material_maker"))
import postprocess  # noqa: E402

N = postprocess.TEXTURE_SIZE


def rng_for(name):
    return np.random.default_rng(zlib.crc32(name.encode()))


def value_noise(rng, cells, n=N):
    """Tileable smooth noise: random values on a cells x cells lattice, bicubic-upsampled."""
    g = rng.uniform(0, 1, (cells, cells))
    g = np.tile(g, (3, 3))
    img = Image.fromarray((g * 65535).astype(np.uint16)).resize((n * 3, n * 3), Image.BICUBIC)
    a = np.asarray(img, dtype=np.float32) / 65535.0
    return a[n:2 * n, n:2 * n]


def fbm(rng, octaves, n=N):
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for cells in octaves:
        out += value_noise(rng, cells, n) * amp
        tot += amp
        amp *= 0.55
    return out / tot


def normal_from_height(h, strength):
    gy, gx = np.gradient(np.pad(h, 1, mode="wrap"))
    gx, gy = gx[1:-1, 1:-1], gy[1:-1, 1:-1]
    nx, ny, nz = -gx * strength, gy * strength, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([nx / ln, ny / ln, nz / ln]) * 0.5 + 0.5


def save(name, kind, arr):
    os.makedirs(RAW, exist_ok=True)
    img = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
    img.save(os.path.join(RAW, f"{name}_{kind}.png"))


def orm(rough, metal=0.0, ao=None):
    ao = np.ones_like(rough) if ao is None else ao
    return np.dstack([ao, rough, np.full_like(rough, metal)])


def cracks(rng, count, n=N):
    m = np.zeros((n, n), np.float32)
    for _ in range(count):
        x, y = rng.uniform(0, n, 2)
        a = rng.uniform(0, 2 * np.pi)
        for _ in range(int(rng.uniform(60, 220))):
            a += rng.normal(0, 0.35)
            x, y = (x + np.cos(a) * 2) % n, (y + np.sin(a) * 2) % n
            m[int(y), int(x)] = 1.0
    img = Image.fromarray((m * 255).astype(np.uint8)).resize((n, n))
    img = img.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    return np.asarray(img, np.float32) / 255.0


def asphalt():
    r = rng_for("asphalt")
    grain = r.uniform(0, 1, (N, N)).astype(np.float32)
    patch = fbm(r, (4, 8))
    puddle = np.clip((fbm(r, (3, 6, 12)) - 0.56) * 9, 0, 1)
    ck = cracks(r, 14)
    base = 0.05 + 0.03 * patch + 0.035 * (grain - 0.5) - 0.03 * ck
    base = base * (1 - 0.35 * puddle)
    alb = np.dstack([base, base * 1.02, base * 1.06])
    rough = np.clip(0.62 - 0.12 * patch - 0.52 * puddle + 0.05 * (grain - 0.5), 0.05, 1)
    h = 0.4 * grain * (1 - puddle) - 1.2 * ck + 0.3 * patch
    save("asphalt", "albedo", alb)
    save("asphalt", "orm", orm(rough, 0.0, 1 - 0.4 * ck))
    save("asphalt", "normal", normal_from_height(h, 1.6))


def paving_wet():
    r = rng_for("paving_wet")
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    slabs = 4
    fx, fy = (x * slabs) % 1.0, (y * slabs) % 1.0
    edge = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))
    joint = np.clip(1 - edge / 0.022, 0, 1)
    ix, iy = (x * slabs).astype(int), (y * slabs).astype(int)
    tone = r.uniform(-0.03, 0.03, (slabs, slabs))[iy, ix]
    grain = fbm(r, (32, 64))
    puddle = np.clip((fbm(r, (2, 4, 8)) - 0.6) * 8, 0, 1)
    base = 0.2 + tone + 0.05 * (grain - 0.5) - 0.12 * joint
    base = base * (1 - 0.3 * puddle)
    alb = np.dstack([base * 0.96, base, base * 1.05])
    rough = np.clip(0.34 + 0.08 * grain + 0.2 * joint - 0.28 * puddle, 0.05, 1)
    h = -joint * 1.0 + 0.2 * grain + 0.3 * np.clip(edge * 20, 0, 1)
    save("paving_wet", "albedo", alb)
    save("paving_wet", "orm", orm(rough, 0.0, 1 - 0.5 * joint))
    save("paving_wet", "normal", normal_from_height(h, 2.0))


def window(name, colour, blinds):
    r = rng_for(name)
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    glow = 0.55 + 0.45 * fbm(r, (2, 4))
    if blinds:
        slat = 0.82 + 0.18 * (np.sin(y * np.pi * 2 * 22) > -0.6)
    else:
        slat = 0.85 + 0.15 * fbm(r, (16, 32))
    # dark mullions: a thin cross every tile keeps big panes from reading as flat light boxes
    mull = np.clip(1 - (np.minimum(np.abs(x - 0.5), np.abs(y - 0.5)) < 0.006), 0, 1)
    e = glow * slat * mull
    col = np.array(colour, np.float32)
    save(name, "albedo", np.dstack([0.04 + 0.1 * e] * 3) * col)
    save(name, "emission", e[..., None] * col)
    save(name, "orm", orm(np.full((N, N), 0.25, np.float32)))
    save(name, "normal", normal_from_height(np.zeros((N, N), np.float32), 1.0))


def dark_glass(name, tint, rough):
    r = rng_for(name)
    wav = fbm(r, (2, 4))
    save(name, "albedo", np.dstack([np.full((N, N), t) * (0.9 + 0.2 * wav) for t in tint]))
    save(name, "orm", orm(np.full((N, N), rough, np.float32) + 0.03 * wav))
    save(name, "normal", normal_from_height(wav * 0.3, 1.0))


def neon(name, colour):
    r = rng_for(name)
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    band = 0.85 + 0.15 * np.cos(y * np.pi * 2 * 6) ** 2
    e = band * (0.95 + 0.05 * fbm(r, (8,)))
    col = np.array(colour, np.float32)
    save(name, "albedo", np.dstack([np.full((N, N), c * 0.8) for c in colour]))
    save(name, "emission", e[..., None] * col)
    save(name, "orm", orm(np.full((N, N), 0.3, np.float32)))
    save(name, "normal", normal_from_height(np.zeros((N, N), np.float32), 1.0))


def water():
    r = rng_for("water")
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    h = np.zeros((N, N), np.float32)
    for k in range(9):
        fx, fy = r.integers(1, 7, 2) * r.choice([-1, 1], 2)
        ph = r.uniform(0, 2 * np.pi)
        h += np.sin(2 * np.pi * (fx * x + fy * y) + ph) / (1 + k * 0.4)
    h = h * 0.05 + 0.4 * fbm(r, (16, 32))
    save("water", "albedo", np.dstack([np.full((N, N), 0.008), np.full((N, N), 0.02), np.full((N, N), 0.022)]))
    save("water", "orm", orm(np.full((N, N), 0.04, np.float32)))
    save("water", "normal", normal_from_height(h, 1.5))


def awning():
    r = rng_for("awning")
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    stripe = ((x * 4) % 1.0) < 0.5
    a = np.array([0.42, 0.06, 0.07], np.float32)
    b = np.array([0.62, 0.55, 0.42], np.float32)
    weave = 0.9 + 0.1 * fbm(r, (64, 128))
    alb = np.where(stripe[..., None], a, b) * weave[..., None] * (0.8 + 0.2 * fbm(r, (4,)))[..., None]
    save("awning", "albedo", alb)
    save("awning", "orm", orm(np.full((N, N), 0.7, np.float32)))
    save("awning", "normal", normal_from_height(weave, 3.0))


MATERIALS = {
    "asphalt": asphalt,
    "paving_wet": paving_wet,
    "window_lit_warm": lambda: window("window_lit_warm", (1.0, 0.72, 0.42), True),
    "window_lit_cool": lambda: window("window_lit_cool", (0.55, 0.76, 1.0), False),
    "window_dark": lambda: dark_glass("window_dark", (0.018, 0.022, 0.028), 0.06),
    "glass": lambda: dark_glass("glass", (0.03, 0.045, 0.06), 0.03),
    "neon_pink": lambda: neon("neon_pink", (1.0, 0.31, 0.64)),
    "neon_cyan": lambda: neon("neon_cyan", (0.21, 0.88, 1.0)),
    "water": water,
    "awning": awning,
}


def main():
    names = sys.argv[1:] or list(MATERIALS)
    for n in names:
        MATERIALS[n]()
        print("maps:", n)
    postprocess.process(RAW, GAME, names)


if __name__ == "__main__":
    main()
