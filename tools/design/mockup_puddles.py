#!/usr/bin/env python3
"""Draw the street-puddles mockup for the design page (openspec/changes/archive/2026-09-30-street-puddles, design
section 2): one real stretch of the hub, 48 x 30 m round the garage under the Skyway, twice.

    python3 tools/design/mockup_puddles.py

Left, today: the standing water the committed street textures paint, sampled from
game/textures/asphalt_orm.png and paving_wet_orm.png at the world UVs every street face takes
(tools/blender/blendkit.py, world_uv), wherever the tile falls. Right, the proposal as a sketch:
puddles along the kerbs, under the drip edges of the awnings and the Skyway's deck, and round
the kerb gullies, never under a roof. The sketch draws the design's rules on the plan's real
shapes; it is not the placement code, which doesn't exist yet.

Writes docs/design/maps/puddles_mockup.svg, which the page inlines (<!--MAP:puddles_mockup-->).
It lives in tools/design because it only draws the write-up's figure (CLAUDE.md 3).
"""
import base64
import contextlib
import io
import math
import os
import random
import sys

import numpy as np
from PIL import Image
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "levels"))
import city_plan as CP  # noqa: E402
import render_map as RM  # noqa: E402

X0, Y0, W, H = 144.0, 102.0, 48.0, 30.0     # the window, layout metres
S = 14.0                                    # pixels a metre
OUT = os.path.join(ROOT, "docs", "design", "maps", "puddles_mockup.svg")
TEXTURES = {"asphalt": (4.0, 0.35), "paving_wet": (2.0, 0.2)}   # tile_m (materials.json), puddle roughness under
WATER = "#3fa9d6"


def puddle_mask(name):
    """The committed texture's standing water: roughness (ORM green) under the threshold."""
    tile, under = TEXTURES[name]
    orm = np.asarray(Image.open(os.path.join(ROOT, "game", "textures", f"{name}_orm.png")).convert("RGB"), np.float32)
    return orm[..., 1] / 255.0 < under, tile


def before_image(road, paving):
    """Today's puddles as a transparent PNG over the window: sampled at the world UVs."""
    w, h = int(W * S), int(H * S)
    img = np.zeros((h, w, 4), np.uint8)
    masks = {k: puddle_mask(k) for k in TEXTURES}
    rp, pp = CP.prep(road), CP.prep(paving)
    for j in range(h):
        for i in range(w):
            x, y = X0 + (i + 0.5) / S, Y0 + (j + 0.5) / S
            pt = Point(x, y)
            name = "asphalt" if rp.contains(pt) else ("paving_wet" if pp.contains(pt) else None)
            if name is None:
                continue
            m, tile = masks[name]
            n = m.shape[0]
            if m[int((y / tile) % 1.0 * n), int((x / tile) % 1.0 * n)]:
                img[j, i] = (0x3f, 0xa9, 0xd6, 200)
    buf = io.BytesIO()
    Image.fromarray(img, "RGBA").save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def after_shapes(road, paving, roofs, awnings, deck, rng):
    """The proposal's rules drawn on the window: kerb puddles, drip lines and gullies."""
    out = []
    ground = road.union(paving)
    kerb = road.boundary.intersection(paving.buffer(0.05))
    for line in getattr(kerb, "geoms", [kerb]):
        if line.length < 1.0:
            continue
        d = rng.uniform(1.0, 4.0)
        while d < line.length - 1.0:
            ln = rng.uniform(1.5, 3.5)
            seg = LineString([line.interpolate(d), line.interpolate(min(d + ln, line.length))])
            pg = seg.buffer(0.3, cap_style=1).intersection(road)
            out.append(("gutter", pg))
            d += ln + rng.uniform(4.0, 9.0)
        for q in range(1, int(line.length // 25) + 1):
            p = line.interpolate(q * 25 - 12.5)
            out.append(("gully", p.buffer(0.7).intersection(road)))
    for g in list(getattr(awnings, "geoms", [awnings])) + list(getattr(deck, "geoms", [deck])):
        edge = g.exterior
        d = rng.uniform(0.0, 2.0)
        while d < edge.length:
            ln = rng.uniform(1.0, 2.5)
            seg = LineString([edge.interpolate(d), edge.interpolate(min(d + ln, edge.length))])
            drip = seg.buffer(0.3, cap_style=1).difference(g.buffer(0.05))
            out.append(("drip", drip.intersection(ground)))
            d += ln + rng.uniform(1.5, 4.0)
    out = [(k, pg.difference(roofs)) for k, pg in out]
    return [(k, pg) for k, pg in out if not pg.is_empty and pg.area > 0.05]


def path(g):
    d = []
    for pg in RM.polygons(g):
        for ring in [pg.exterior] + list(pg.interiors):
            pts = [((x - X0) * S, (y - Y0) * S) for x, y in ring.coords]
            d.append("M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + " Z")
    return " ".join(d)


def main():
    m, ents = CP.load("hub")
    city = CP.City(m, ents)
    with contextlib.redirect_stdout(io.StringIO()):
        plan = city.build()
    win = box(X0, Y0, X0 + W, Y0 + H)
    road = city.street.difference(city.rail_geom).intersection(win)
    paving = city.paved.union(city.plaza).intersection(win)
    roofs = unary_union([g for label, g, z in plan.shelters if z - CP.PAVED_Z >= 1.0]).intersection(win)
    open_roofs = roofs.difference(city.B)          # the roofs over open ground: awnings, the deck
    awnings = unary_union([g for label, g, z in plan.shelters if "awning" in label]).intersection(win)
    deck = unary_union([g for label, g, z in plan.shelters if label == "Skyway deck"])
    buildings = city.B.intersection(win)
    water_now = before_image(road, paving)
    shapes = after_shapes(road, paving, roofs, awnings, deck, random.Random("puddles-mockup"))
    pw, ph, gap, top = W * S, H * S, 40, 46
    svg = [f'<svg viewBox="0 0 {2 * pw + gap:.0f} {ph + top + 40:.0f}" xmlns="http://www.w3.org/2000/svg">',
           f'<rect width="100%" height="100%" fill="{RM.ROLE["bg"]}"/>']
    for k, (title, extra) in enumerate((("TODAY: THE TEXTURE'S PUDDLES, WHEREVER THE TILE FALLS", "before"),
                                        ("PROPOSED: WHERE WATER GATHERS (SKETCH)", "after"))):
        ox = k * (pw + gap)
        svg.append(f'<g transform="translate({ox:.0f} {top})">')
        svg.append(f'<path d="{path(paving)}" fill="{RM.ROLE["ground"]}"/>')
        svg.append(f'<path d="{path(road)}" fill="{RM.ROLE["street"]}" stroke="{RM.ROLE["curb"]}" stroke-width="2"/>')
        svg.append(f'<path d="{path(buildings)}" fill="{RM.ROLE["bld"]}" stroke="{RM.ROLE["bld_edge"]}" stroke-width="1"/>')
        if extra == "before":
            svg.append(f'<image href="data:image/png;base64,{water_now}" width="{pw:.0f}" height="{ph:.0f}"/>')
        else:
            for kind, pg in shapes:
                svg.append(f'<path d="{path(pg)}" fill="{WATER}" fill-opacity="{0.9 if kind != "drip" else 0.7}"/>')
            for kind, pg in shapes:
                if kind == "gully":
                    c = pg.centroid
                    svg.append(f'<rect x="{(c.x - X0) * S - 4:.1f}" y="{(c.y - Y0) * S - 4:.1f}" width="8" height="8" '
                               f'fill="none" stroke="{RM.ROLE["text"]}" stroke-width="1.2"/>')
        svg.append(f'<path d="{path(open_roofs)}" fill="none" stroke="{RM.ROLE["accent"]}" stroke-width="1.5" stroke-dasharray="6 4"/>')
        svg.append(f'<text x="0" y="-14" font-family="IBM Plex Mono, monospace" font-size="15" fill="{RM.ROLE["text"]}">{title}</text>')
        svg.append("</g>")
    svg.append(f'<text x="0" y="{ph + top + 28:.0f}" font-family="IBM Plex Mono, monospace" font-size="13" '
               f'fill="{RM.ROLE["dim"]}">x {X0:g}-{X0 + W:g}, y {Y0:g}-{Y0 + H:g} m. Blue: standing water. '
               f'Dashed: a roof (the Skyway\'s deck, awnings), where no rain falls. Squares: kerb gullies.</text>')
    svg.append("</svg>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(svg) + "\n")
    area = sum(pg.area for _, pg in shapes)
    print(f"wrote {OUT}: {len(shapes)} sketched puddles, {area:.0f} m2 in the window")


if __name__ == "__main__":
    main()
