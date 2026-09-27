#!/usr/bin/env python3
"""Small effect textures (particles, muzzle flash, bullet-hole decal) generated procedurally.

    python3 tools/fx/generate_fx_textures.py   # writes game/textures/fx/*.png
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "game", "textures", "fx")
rng = np.random.default_rng(7)


def grid(n):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    return (x + 0.5) / n * 2 - 1, (y + 0.5) / n * 2 - 1


def save_rgba(name, rgba):
    os.makedirs(OUT, exist_ok=True)
    img = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")
    img.save(os.path.join(OUT, name + ".png"), optimize=True)
    print("wrote", name)


def soft_particle():
    x, y = grid(64)
    r = np.sqrt(x * x + y * y)
    a = np.clip(1 - r, 0, 1) ** 2
    rgba = np.dstack([np.ones_like(a)] * 3 + [a])
    save_rgba("soft_particle", rgba)


def smoke_puff():
    n = 128
    x, y = grid(n)
    r = np.sqrt(x * x + y * y)
    noise = np.zeros((n, n))
    for octave, amp in ((4, 0.5), (8, 0.3), (16, 0.2)):
        small = rng.uniform(0, 1, (octave, octave))
        noise += np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)) / 255 * amp
    a = np.clip(1 - r * 1.1, 0, 1) ** 1.5 * np.clip(noise * 1.6 - 0.2, 0, 1)
    rgba = np.dstack([np.ones_like(a)] * 3 + [a])
    save_rgba("smoke_puff", rgba)


def muzzle_flash():
    n = 128
    x, y = grid(n)
    r = np.sqrt(x * x + y * y)
    ang = np.arctan2(y, x)
    spikes = 0.55 + 0.45 * np.abs(np.cos(ang * 3.5)) ** 6
    a = np.clip(1 - r / spikes, 0, 1) ** 1.6
    core = np.clip(1 - r * 2.5, 0, 1)
    rgb = np.dstack([np.ones_like(a), 0.75 + 0.25 * core, 0.35 + 0.65 * core])
    save_rgba("muzzle_flash", np.dstack([rgb, np.clip(a + core, 0, 1)]))


def bullet_hole():
    n = 64
    x, y = grid(n)
    r = np.sqrt(x * x + y * y) + rng.normal(0, 0.03, (n, n))
    hole = np.clip((0.28 - r) / 0.05, 0, 1)
    scorch = np.clip((0.95 - r) / 0.5, 0, 1) ** 1.5
    alpha = np.clip(hole + scorch * 0.75, 0, 1)
    shade = 0.05 + 0.25 * (1 - scorch) * (1 - hole)
    rgba = np.dstack([shade, shade * 0.95, shade * 0.9, alpha])
    save_rgba("bullet_hole", rgba)
    # normal map: a crater (rim up, centre down)
    h = np.exp(-((r - 0.35) ** 2) / 0.01) * 0.6 - hole * 0.8
    gy, gx = np.gradient(h)
    nx, ny, nz = -gx * 8, gy * 8, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.dstack([nx / ln, ny / ln, nz / ln]) * 0.5 + 0.5
    Image.fromarray((nrm * 255).astype(np.uint8), "RGB").save(os.path.join(OUT, "bullet_hole_normal.png"))
    print("wrote bullet_hole_normal")


def scorch():
    n = 128
    x, y = grid(n)
    r = np.sqrt(x * x + y * y)
    noise = rng.uniform(0, 1, (16, 16))
    noise = np.asarray(Image.fromarray((noise * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)) / 255
    a = np.clip((1 - r) * 1.4 - noise * 0.5, 0, 1)
    rgba = np.dstack([np.full_like(a, 0.03), np.full_like(a, 0.03), np.full_like(a, 0.03), a * 0.9])
    save_rgba("scorch", rgba)


if __name__ == "__main__":
    soft_particle()
    smoke_puff()
    muzzle_flash()
    bullet_hole()
    scorch()
