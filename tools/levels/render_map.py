"""Render a level layout (tools/levels/layouts/<id>.py) as a Deus Ex style design map (SVG).

The layout module is the single source for a level's plan: this renderer draws it for the
design page, and the Blender build reads the same data, so the map and the level cannot
disagree (CLAUDE.md section 7.1).

    python3 tools/levels/render_map.py            # every layout
    python3 tools/levels/render_map.py hub drains # some of them

Writes docs/design/maps/<id>.svg. Units in the layouts are metres, x east, y south.

Three base modes:
    city    solid ground between the open spaces is split into building lots
    rock    solid is rock (hatched); open spaces are floors with walls drawn on their edges
    ground  everything is open ground; buildings and props are placed explicitly
"""
import importlib
import math
import pathlib
import random
import sys

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import split, unary_union

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "design" / "maps"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

MARGIN = 36          # px around the map for grid labels
GRID_M = 20          # grid spacing, metres

# Colour roles. The page and the maps share these names; only this table says what they are.
ROLE = {
    "bg": "#05070a", "ground": "#0d1217", "street": "#080b0f", "curb": "#1d2630",
    "lot": ["#222a33", "#262f39", "#2a3440", "#2e3945", "#242d37"],
    "lot_edge": "#45535f", "roof": "#35414e", "bld": "#27313c", "bld_edge": "#6b7f92",
    "floor": "#141b22", "wall": "#9fb3c4", "rock": "#090c10", "rock_hatch": "#18212a",
    "water": "#0a2630", "water_hatch": "#123c48", "text": "#dbe4ec", "dim": "#7d8e9e",
    "faint": "#4a5a69", "district": "#8193a4", "accent": "#ff9e2e", "gold": "#f2b33d",
}
CATS = {
    # category: (legend heading, colour)
    "service": ("SERVICES", "#5fd38a"),
    "contact": ("CONTACTS", "#4aa8ff"),
    "objective": ("OBJECTIVES", "#f2b33d"),
    "access": ("ACCESS", "#dfe7ee"),
    "lock": ("LOCKS AND TERMINALS", "#ff9e2e"),
    "loot": ("LOOT", "#3fd1c7"),
    "secret": ("SECRETS", "#b78cff"),
    "security": ("SECURITY", "#ff5b4f"),
    "restricted": ("RESTRICTED", "#ff5b4f"),
}
CAT_ORDER = ["objective", "service", "contact", "access", "lock", "loot", "secret", "security", "restricted"]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


class Canvas:
    def __init__(self, m):
        self.m = m
        self.S = m.get("scale_px", 6)
        self.W, self.H = m["size"]
        self.out = []

    def X(self, x):
        return MARGIN + x * self.S

    def Y(self, y):
        return MARGIN + y * self.S

    def pt(self, p):
        return f"{self.X(p[0]):.1f},{self.Y(p[1]):.1f}"

    def ring(self, coords):
        pts = list(coords)
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        return "M" + " L".join(self.pt(p) for p in pts) + " Z"

    def path(self, geom):
        if geom.is_empty:
            return ""
        if isinstance(geom, Polygon):
            return " ".join([self.ring(geom.exterior.coords)] + [self.ring(i.coords) for i in geom.interiors])
        if hasattr(geom, "geoms"):
            return " ".join(self.path(g) for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon"))
        return ""

    def line(self, pts):
        return "M" + " L".join(self.pt(p) for p in pts)

    def add(self, s):
        self.out.append(s)


# ---------------------------------------------------------------- geometry helpers

def street_geom(s):
    ls = LineString(s["pts"])
    return ls.buffer(s["w"] / 2, cap_style=2, join_style=2, mitre_limit=3)


def poly(pts):
    return Polygon(pts)


def rect(x0, y0, x1, y1):
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def shape_geom(sh):
    k = sh[0]
    if k == "rect":
        return rect(*sh[1:5])
    if k == "poly":
        return Polygon(sh[1])
    if k == "circle":
        return Point(sh[1], sh[2]).buffer(sh[3], 16)
    if k == "orect":   # centre, size, angle
        cx, cy, w, h, a = sh[1:6]
        return affinity.rotate(rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), a, origin=(cx, cy))
    raise ValueError(k)


def subdivide(pg, rng, amin, amax, jitter=0.0, depth=0):
    target = rng.uniform(amin, amax)
    if pg.area <= target or depth > 14:
        return [pg]
    mrr = pg.minimum_rotated_rectangle
    c = list(mrr.exterior.coords)[:4]
    e0 = (c[1][0] - c[0][0], c[1][1] - c[0][1])
    e1 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l0, l1 = math.hypot(*e0), math.hypot(*e1)
    if l0 < 0.01 or l1 < 0.01:
        return [pg]
    if l0 >= l1:
        base, along, across = c[0], e0, e1
    else:
        base, along, across = c[1], e1, e0
    t = rng.uniform(0.36, 0.64)
    p = (base[0] + along[0] * t, base[1] + along[1] * t)
    la = math.hypot(*across)
    d = (across[0] / la, across[1] / la)
    if jitter:
        a = math.radians(rng.uniform(-jitter, jitter))
        d = (d[0] * math.cos(a) - d[1] * math.sin(a), d[0] * math.sin(a) + d[1] * math.cos(a))
    cut = LineString([(p[0] - d[0] * 500, p[1] - d[1] * 500), (p[0] + d[0] * 500, p[1] + d[1] * 500)])
    try:
        parts = [g for g in split(pg, cut).geoms if g.geom_type == "Polygon" and g.area > 0.5]
    except Exception:
        return [pg]
    if len(parts) < 2:
        return [pg]
    out = []
    for g in parts:
        out += subdivide(g, rng, amin, amax, jitter, depth + 1)
    return out


def random_point_in(pg, rng, tries=30):
    x0, y0, x1, y1 = pg.bounds
    for _ in range(tries):
        p = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
        if pg.contains(p):
            return p
    return None


def polygons(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    return [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]


# ---------------------------------------------------------------- drawing

def defs(c):
    S = c.S
    c.add(f"""<defs>
<pattern id="hatch-water-{c.m['id']}" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
  <rect width="7" height="7" fill="{ROLE['water']}"/><line x1="0" y1="0" x2="0" y2="7" stroke="{ROLE['water_hatch']}" stroke-width="1.2"/></pattern>
<pattern id="hatch-rock-{c.m['id']}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
  <rect width="6" height="6" fill="{ROLE['rock']}"/><line x1="0" y1="0" x2="0" y2="6" stroke="{ROLE['rock_hatch']}" stroke-width="1"/></pattern>
<pattern id="hatch-restricted-{c.m['id']}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
  <line x1="0" y1="0" x2="0" y2="8" stroke="#ff5b4f" stroke-opacity="0.35" stroke-width="2"/></pattern>
<pattern id="hatch-grate-{c.m['id']}" width="4" height="4" patternUnits="userSpaceOnUse">
  <rect width="4" height="4" fill="#1a232c"/><line x1="0" y1="0" x2="4" y2="0" stroke="#3c4a57" stroke-width="1"/></pattern>
<marker id="arrow-{c.m['id']}" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
  <path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker>
</defs>""")


STYLE = """
.m-lbl{font-family:'Barlow Condensed','Arial Narrow',sans-serif;}
.m-mono{font-family:'IBM Plex Mono',ui-monospace,monospace;}
.lot{stroke:%(lot_edge)s;stroke-width:0.7}
.roofbox{fill:%(roof)s;stroke:#3a4654;stroke-width:0.6}
.bld{fill:%(bld)s;stroke:%(bld_edge)s;stroke-width:1.3}
.bld-enter{fill:#1a232c;stroke:%(bld_edge)s;stroke-width:1.3}
.floor{fill:%(floor)s}
.wall{fill:%(wall)s}
.fix{fill:#2f3b48;stroke:#56697b;stroke-width:0.7}
.fix-lt{fill:#3b4a59;stroke:#7a8fa3;stroke-width:0.7}
.fix-neon{fill:none;stroke:#ff4fa3;stroke-width:1.4;stroke-opacity:.85}
.fix-cyan{fill:none;stroke:#35e0ff;stroke-width:1.4;stroke-opacity:.8}
.fix-hot{fill:#4a2a14;stroke:#ff9e2e;stroke-width:0.8}
.fix-dark{fill:#0b0f13;stroke:#3a4654;stroke-width:0.7}
.car{fill:#303c49;stroke:#5a6d80;stroke-width:0.7}
.crate{fill:#3a3322;stroke:#6f6040;stroke-width:0.6}
.container{fill:#3b4b3a;stroke:#0b0f13;stroke-width:0.8}
.stall{fill:#34302a;stroke:#8a7456;stroke-width:0.7}
.pillar{fill:#56687a;stroke:#8fa3b5;stroke-width:0.6}
.bridge{fill:#1c252e;stroke:#6b7f92;stroke-width:1}
.rail{fill:none;stroke:#46525e;stroke-width:1.2}
.sleepers{fill:none;stroke:#2c353f;stroke-width:5;stroke-dasharray:1.2 3.4}
.viaduct{fill:#8fb4d0;fill-opacity:.07;stroke:#6f93ad;stroke-width:1.1;stroke-dasharray:10 5}
.walkway{fill:none;stroke:#35e0ff;stroke-width:1.6;stroke-dasharray:5 4;stroke-opacity:.8}
.vent{fill:none;stroke:#b78cff;stroke-width:1.8;stroke-dasharray:2 4;stroke-linecap:round}
.catwalk{fill:#35e0ff;fill-opacity:.07;stroke:#35e0ff;stroke-width:1;stroke-opacity:.6;stroke-dasharray:4 3}
.water-lower{fill:url(#hatch-water-%(id)s);fill-opacity:.75;stroke:#35e0ff;stroke-opacity:.55;stroke-width:1;stroke-dasharray:3 3}
.cage{fill:url(#hatch-grate-%(id)s);stroke:#f2b33d;stroke-width:1.2}
.trip{fill:none;stroke:#ff5b4f;stroke-width:1.4;stroke-dasharray:1.5 1.5}
.stairs{fill:none;stroke:#6b7f92;stroke-width:1}
.pump{fill:#23303b;stroke:#8fa3b5;stroke-width:1.2}
.boom{fill:#f2b33d;fill-opacity:.08;stroke:#f2b33d;stroke-opacity:.7;stroke-width:1;stroke-dasharray:2 2}
.lid2{fill:#fff;fill-opacity:.10;stroke:none}
.lid3{fill:#fff;fill-opacity:.20;stroke:none}
.stack1{fill:#3a2f2a;stroke:#6e5a4c;stroke-width:.6}
.stack2{fill:#46382f;stroke:#86705e;stroke-width:.6}
.stack3{fill:#524237;stroke:#a08672;stroke-width:.6}
.pipe{fill:none;stroke:#4c5a3a;stroke-width:3;stroke-opacity:.8}
.fence{fill:none;stroke:#8a98a6;stroke-width:1.2;stroke-dasharray:1 2.5}
.wallsolid{fill:none;stroke:#8fa3b5;stroke-width:2.2}
.route-stealth{fill:none;stroke:#b78cff;stroke-width:2.2;stroke-dasharray:1 5;stroke-linecap:round}
.route-social{fill:none;stroke:#4aa8ff;stroke-width:2.2;stroke-dasharray:9 5}
.route-force{fill:none;stroke:#ff5b4f;stroke-width:2.2;stroke-dasharray:14 4 2 4}
.route-tech{fill:none;stroke:#35e0ff;stroke-width:2.2;stroke-dasharray:6 3 1 3}
.route-main{fill:none;stroke:#f2b33d;stroke-width:2.2;stroke-dasharray:12 5}
.patrol{fill:none;stroke:#ff5b4f;stroke-width:1.3;stroke-dasharray:2 3;stroke-opacity:.9}
.cone{fill:#ff5b4f;fill-opacity:.13;stroke:#ff5b4f;stroke-opacity:.5;stroke-width:.8}
.cone-light{fill:#fff3b0;fill-opacity:.10;stroke:#fff3b0;stroke-opacity:.45;stroke-width:.8}
.restricted{fill:url(#hatch-restricted-%(id)s);stroke:#ff5b4f;stroke-opacity:.6;stroke-width:1;stroke-dasharray:4 3}
.lbl-district{fill:%(district)s;fill-opacity:.62;font-size:22px;letter-spacing:7px;font-weight:600}
.lbl-street{fill:#6c7e8f;font-size:9px;letter-spacing:2.2px;font-weight:600}
.lbl-bld{fill:%(text)s;font-size:10.5px;letter-spacing:1.2px;font-weight:600}
.lbl-room{fill:#7d8e9e;font-size:7.5px;letter-spacing:.6px}
.lbl-water{fill:#3c8a9c;font-size:13px;letter-spacing:6px;font-style:italic}
.lbl-note{fill:#9aaaba;font-size:8.5px;letter-spacing:.4px}
.lbl-warn{fill:#ff8a7f;font-size:8.5px;letter-spacing:.4px;font-weight:600}
.lbl-grid{fill:#3d4b58;font-size:10px;letter-spacing:1px}
.gridline{stroke:#1a232c;stroke-width:.6}
.poi circle{stroke:#05080b;stroke-width:1.6}
.num{fill:#05080b;font-size:9px;font-weight:700;text-anchor:middle;dominant-baseline:central}
.poi,.mission,.enemy{cursor:pointer}
.poi.hl circle{stroke:#fff;stroke-width:3}
.mission.hl rect{stroke:#fff;stroke-width:3}
.leader{stroke:#f2b33d;stroke-width:1;stroke-dasharray:2 2;fill:none}
.enemy path{stroke:#05080b;stroke-width:1}
.lg-h{fill:%(dim)s;font-size:11px;letter-spacing:3px;font-weight:600}
.lg-t{fill:%(text)s;font-size:11.5px;letter-spacing:.3px}
.lg-n{fill:%(dim)s;font-size:9.5px}
""" % {**ROLE, "id": "%(id)s"}


def scoped_style(css, map_id):
    """Prefix every selector with the map's own svg, so several maps can share one HTML page."""
    out = []
    for line in css.strip().splitlines():
        sel, _, body = line.partition("{")
        scoped = ",".join(f'svg[data-map="{map_id}"] {s.strip()}' for s in sel.split(","))
        out.append(scoped + "{" + body)
    return "\n".join(out)


def draw_grid(c):
    W, H, S = c.W, c.H, c.S
    g = ['<g data-layer="grid">']
    for i, x in enumerate(range(0, int(W) + 1, GRID_M)):
        g.append(f'<line class="gridline" x1="{c.X(x)}" y1="{c.Y(0)}" x2="{c.X(x)}" y2="{c.Y(H)}"/>')
        if x < W:
            g.append(f'<text class="lbl-grid m-mono" x="{c.X(x + GRID_M / 2)}" y="{MARGIN - 12}" text-anchor="middle">{chr(65 + i)}</text>')
    for j, y in enumerate(range(0, int(H) + 1, GRID_M)):
        g.append(f'<line class="gridline" x1="{c.X(0)}" y1="{c.Y(y)}" x2="{c.X(W)}" y2="{c.Y(y)}"/>')
        if y < H:
            g.append(f'<text class="lbl-grid m-mono" x="{MARGIN - 12}" y="{c.Y(y + GRID_M / 2) + 4}" text-anchor="middle">{j + 1}</text>')
    g.append("</g>")
    c.add("\n".join(g))


def draw_shapes(c, shapes, default_cls="fix"):
    for sh in shapes:
        k = sh[0]
        cls = sh[-1] if isinstance(sh[-1], str) and k != "text" else default_cls
        if k == "line":
            c.add(f'<path class="{cls}" d="{c.line(sh[1])}"/>')
        elif k == "text":
            _, x, y, txt, tcls = sh[:5]
            rot = sh[5] if len(sh) > 5 else 0
            tr = f' transform="rotate({rot} {c.X(x):.1f} {c.Y(y):.1f})"' if rot else ""
            c.add(f'<text class="{tcls} m-lbl" x="{c.X(x):.1f}" y="{c.Y(y):.1f}" text-anchor="middle"{tr}>{esc(txt)}</text>')
        elif cls.startswith("#"):
            c.add(f'<path class="container" style="fill:{cls}" d="{c.path(shape_geom(sh))}"/>')
        else:
            c.add(f'<path class="{cls}" d="{c.path(shape_geom(sh))}"/>')


def draw_rooms(c, b):
    """Floor plan: room floors, walls on every room edge, gaps where the doors are."""
    rooms = [rect(*r["rect"]) if "rect" in r else Polygon(r["poly"]) for r in b["rooms"]]
    fl = unary_union(rooms)
    c.add(f'<path class="floor" d="{c.path(fl)}"/>')
    walls = unary_union([r.exterior.buffer(0.22, cap_style=2, join_style=2) for r in rooms])
    for d in b.get("doors", []):
        w = d[2] if len(d) > 2 else 1.4
        walls = walls.difference(Point(d[0], d[1]).buffer(w / 2, cap_style=3))
    c.add(f'<path class="wall" d="{c.path(walls)}"/>')


def draw_city(c, m, blocked):
    """Split the solid ground between open spaces into building lots, district by district."""
    W, H = m["size"]
    solid = box(0, 0, W, H).difference(blocked)
    districts = [(d, Polygon(d["poly"])) for d in m["districts"]]
    g = ['<g data-layer="lots">']
    for bi, piece in enumerate(polygons(solid)):
        if piece.area < 4:
            continue
        cen = piece.representative_point()
        dist = next((d for d, pg in districts if pg.contains(cen)), m["districts"][0])
        rng = random.Random(f"{m['seed']}:{bi}:{dist['name']}")
        amin, amax = dist["lot"]
        for lot in subdivide(piece, rng, amin, amax, dist.get("jitter", 0)):
            shr = lot.buffer(-rng.choice((0.3, 0.35, 0.45, 0.7)), join_style=2)
            for lp in polygons(shr):
                if lp.area < 3:
                    continue
                if lp.area > dist.get("court_min", 1e9) and rng.random() < dist.get("court_p", 0):
                    hole = lp.buffer(-rng.uniform(3.5, 5.5), join_style=2)
                    if not hole.is_empty and hole.area > 20:
                        lp = lp.difference(hole)
                shade = ROLE["lot"][rng.randrange(len(ROLE["lot"]))]
                if dist.get("shade"):
                    shade = dist["shade"][rng.randrange(len(dist["shade"]))]
                g.append(f'<path class="lot" fill="{shade}" d="{c.path(lp)}"/>')
                # rooftop plant: AC boxes, vents, water tanks
                inner = lp.buffer(-1.3, join_style=2)
                if inner.is_empty or inner.area < 6:
                    continue
                for _ in range(rng.randint(0, dist.get("roof_n", 3))):
                    p = random_point_in(inner, rng)
                    if p is None:
                        continue
                    if rng.random() < 0.18:
                        r = rng.uniform(0.8, 1.5)
                        g.append(f'<circle class="roofbox" cx="{c.X(p.x):.1f}" cy="{c.Y(p.y):.1f}" r="{r * c.S:.1f}"/>')
                    else:
                        w, h = rng.uniform(1.0, 3.0), rng.uniform(0.8, 2.2)
                        g.append(f'<rect class="roofbox" x="{c.X(p.x - w / 2):.1f}" y="{c.Y(p.y - h / 2):.1f}" width="{w * c.S:.1f}" height="{h * c.S:.1f}"/>')
    g.append("</g>")
    c.add("\n".join(g))


def cone(at, direction, fov, rng_m, steps=10):
    pts = [at]
    for i in range(steps + 1):
        a = math.radians(direction - fov / 2 + fov * i / steps)
        pts.append((at[0] + math.cos(a) * rng_m, at[1] + math.sin(a) * rng_m))
    return Polygon(pts)


ENEMY_GLYPH = {
    # kind: (colour, size px)
    "grunt": ("#ff5b4f", 7), "heavy": ("#ff5b4f", 9), "boss": ("#ff2d6f", 11),
    "dog": ("#ff9e2e", 7), "turret": ("#ff9e2e", 8), "civ": ("#4aa8ff", 6),
    "hostage": ("#f2b33d", 7), "lookout": ("#ff5b4f", 7),
}


def draw_enemy(c, e, idx):
    col, s = ENEMY_GLYPH[e["kind"]]
    x, y = c.X(e["at"][0]), c.Y(e["at"][1])
    a = e.get("dir", 0)
    tip = f"{x + s:.1f},{y:.1f} {x - s * 0.7:.1f},{y - s * 0.7:.1f} {x - s * 0.35:.1f},{y:.1f} {x - s * 0.7:.1f},{y + s * 0.7:.1f}"
    if e["kind"] in ("hostage", "civ"):
        shape = f'<path d="M{x - s * .7:.1f},{y:.1f} a{s * .7:.1f},{s * .7:.1f} 0 1,0 {s * 1.4:.1f},0 a{s * .7:.1f},{s * .7:.1f} 0 1,0 {-s * 1.4:.1f},0" fill="{col}"/>'
    elif e["kind"] == "turret":
        shape = f'<path d="M{x - s * .7:.1f},{y - s * .7:.1f} h{s * 1.4:.1f} v{s * 1.4:.1f} h{-s * 1.4:.1f} z M{x:.1f},{y:.1f} L{x + s * 1.3:.1f},{y:.1f}" fill="{col}" stroke="{col}" stroke-width="2" transform="rotate({a} {x:.1f} {y:.1f})"/>'
    else:
        shape = f'<path d="M{tip.replace(" ", " L")} Z" fill="{col}" transform="rotate({a} {x:.1f} {y:.1f})"/>'
    tip_txt = esc(e.get("label", e["kind"]))
    c.add(f'<g class="enemy" data-enemy="{idx}"><title>{tip_txt}</title>{shape}')
    if e.get("tag"):
        c.add(f'<text class="lbl-warn m-lbl" x="{x + s + 3:.1f}" y="{y - s:.1f}">{esc(e["tag"])}</text>')
    c.add("</g>")


def render(m):
    c = Canvas(m)
    W, H, S = c.W, c.H, c.S
    LW = m.get("legend_width", 520)
    vw = MARGIN * 2 + W * S + LW
    vh = max(MARGIN * 2 + H * S, m.get("min_height", 0))
    c.add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:.0f} {vh:.0f}" data-map="{m["id"]}" role="img" aria-label="{esc(m["title"])} map">')
    c.add(f"<style>{scoped_style(STYLE % {'id': m['id']}, m['id'])}</style>")
    defs(c)
    c.add(f'<rect width="{vw:.0f}" height="{vh:.0f}" fill="{ROLE["bg"]}"/>')
    base = m.get("base", "city")
    c.add(f'<rect x="{c.X(0)}" y="{c.Y(0)}" width="{W * S}" height="{H * S}" fill="{ROLE["ground"] if base != "rock" else "url(#hatch-rock-" + m["id"] + ")"}"/>')

    open_geoms = []
    for o in m.get("open", []):
        g = street_geom(o) if "pts" in o else Polygon(o["poly"])
        o["_g"] = g
        open_geoms.append(g)
    open_u = unary_union(open_geoms) if open_geoms else Polygon()
    def water_geom(w):
        return street_geom(w) if "pts" in w else Polygon(w["poly"])
    water_u = unary_union([water_geom(w) for w in m.get("water", []) if not w.get("lower")]) if m.get("water") else Polygon()
    lower_u = unary_union([water_geom(w) for w in m.get("water", []) if w.get("lower")]) if m.get("water") else Polygon()

    # ground layer
    c.add('<g data-layer="ground">')
    for gr in m.get("ground", []):
        c.add(f'<path fill="{gr.get("fill", ROLE["street"])}" d="{c.path(Polygon(gr["poly"]))}"/>')
    if base == "rock":
        c.add(f'<path class="floor" d="{c.path(open_u)}"/>')
    else:
        c.add(f'<path fill="{ROLE["street"]}" stroke="{ROLE["curb"]}" stroke-width="1" d="{c.path(open_u)}"/>')
    c.add("</g>")

    draw_grid(c)

    # water
    if not water_u.is_empty:
        c.add(f'<g data-layer="water"><path fill="url(#hatch-water-{m["id"]})" stroke="#1d5664" stroke-width="1.2" d="{c.path(water_u)}"/></g>')

    if not lower_u.is_empty:
        c.add(f'<g data-layer="water"><path class="water-lower" d="{c.path(lower_u)}"><title>Flooded, one level down</title></path></g>')

    # walls around open space (rock maps)
    if base == "rock":
        edge = open_u.boundary.buffer(0.35, cap_style=2, join_style=2)
        for d in m.get("wall_gaps", []):
            edge = edge.difference(Point(d[0], d[1]).buffer(d[2] / 2 if len(d) > 2 else 0.8, cap_style=3))
        c.add(f'<path class="wall" d="{c.path(edge)}"/>')

    bld_geoms = [Polygon(b["poly"]) if "poly" in b else rect(*b["rect"]) for b in m.get("buildings", [])]
    for b, g in zip(m.get("buildings", []), bld_geoms):
        b["_g"] = g

    if base == "city":
        blocked = unary_union([open_u, water_u] + [g.buffer(0.9, join_style=2) for g in bld_geoms] +
                              [shape_geom(k).buffer(0.9, join_style=2) for k in m.get("keep_clear", [])])
        draw_city(c, m, blocked)

    c.add('<g data-layer="bridges">')
    draw_shapes(c, m.get("bridges", []), "bridge")
    c.add("</g>")

    c.add('<g data-layer="props">')
    draw_shapes(c, m.get("props", []), "fix")
    c.add("</g>")

    # named buildings, floor plans for the ones you can enter
    c.add('<g data-layer="buildings">')
    for b in m.get("buildings", []):
        g = b["_g"]
        cls = "bld-enter" if b.get("rooms") else "bld"
        c.add(f'<path class="{cls}" d="{c.path(g)}"><title>{esc(b["name"])}</title></path>')
        if b.get("rooms"):
            draw_rooms(c, b)
        draw_shapes(c, b.get("fixtures", []), "fix")
        for r in b.get("rooms", []):
            if r.get("name"):
                rg = rect(*r["rect"]) if "rect" in r else Polygon(r["poly"])
                p = r.get("label_at") or (rg.centroid.x, rg.centroid.y)
                c.add(f'<text class="lbl-room m-lbl" x="{c.X(p[0]):.1f}" y="{c.Y(p[1]):.1f}" text-anchor="middle">{esc(r["name"])}</text>')
    c.add("</g>")

    # restricted zones
    c.add('<g data-layer="restricted">')
    for z in m.get("restricted", []):
        c.add(f'<path class="restricted" d="{c.path(shape_geom(z["shape"]))}"><title>Restricted: {esc(z["name"])}</title></path>')
    c.add("</g>")

    # elevated structure
    c.add('<g data-layer="elevated">')
    for e in m.get("elevated", []):
        k = e["kind"]
        if k == "viaduct":
            ls = LineString(e["pts"])
            c.add(f'<path class="viaduct" d="{c.path(ls.buffer(e["w"] / 2, cap_style=2, join_style=2))}"><title>{esc(e.get("name", "Viaduct"))}</title></path>')
            step = e.get("pillar_every", 24)
            d = step / 2
            while d < ls.length:
                p = ls.interpolate(d)
                q = ls.interpolate(min(d + 0.5, ls.length))
                ang = math.degrees(math.atan2(q.y - p.y, q.x - p.x))
                for off in (-e["w"] * 0.3, e["w"] * 0.3):
                    ox = -math.sin(math.radians(ang)) * off
                    oy = math.cos(math.radians(ang)) * off
                    c.add(f'<path class="pillar" d="{c.path(shape_geom(("orect", p.x + ox, p.y + oy, 1.6, 1.6, ang)))}"/>')
                d += step
        elif k == "catwalk":
            g = Polygon(e["poly"]) if "poly" in e else street_geom(e)
            c.add(f'<path class="catwalk" d="{c.path(g)}"><title>{esc(e.get("name", "Catwalk"))}</title></path>')
        elif "w" in e:
            c.add(f'<path class="{k}" d="{c.path(street_geom(e))}"><title>{esc(e.get("name", k))}</title></path>')
        else:
            c.add(f'<path class="{k}" d="{c.line(e["pts"])}"><title>{esc(e.get("name", k))}</title></path>')
    c.add("</g>")

    # security: cameras, searchlights, patrols, enemies
    c.add('<g data-layer="security">')
    for cm in m.get("cameras", []):
        cls = "cone-light" if cm.get("light") else "cone"
        c.add(f'<path class="{cls}" d="{c.path(cone(cm["at"], cm["dir"], cm.get("fov", 60), cm.get("range", 10)))}"><title>{esc(cm.get("name", "Camera"))}</title></path>')
        c.add(f'<circle cx="{c.X(cm["at"][0]):.1f}" cy="{c.Y(cm["at"][1]):.1f}" r="2.6" fill="{"#fff3b0" if cm.get("light") else "#ff5b4f"}"/>')
    for p in m.get("patrols", []):
        pts = p["pts"] + ([p["pts"][0]] if p.get("closed") else [])
        c.add(f'<path class="patrol" d="{c.line(pts)}"><title>Patrol: {esc(p.get("who", ""))}</title></path>')
    for i, e in enumerate(m.get("enemies", [])):
        draw_enemy(c, e, i)
    c.add("</g>")

    # routes
    c.add('<g data-layer="routes">')
    for r in m.get("routes", []):
        c.add(f'<path class="route-{r["type"]}" marker-end="url(#arrow-{m["id"]})" d="{c.line(r["pts"])}"><title>{esc(r.get("name", r["type"]))}</title></path>')
    c.add("</g>")

    # labels
    c.add('<g data-layer="labels">')
    for i, o in enumerate(m.get("open", [])):
        if o.get("label") and "pts" in o:
            pid = f'st-{m["id"]}-{i}'
            pts = o["pts"] if o["pts"][0][0] <= o["pts"][-1][0] else list(reversed(o["pts"]))
            c.add(f'<path id="{pid}" d="{c.line(pts)}" fill="none"/>')
            off = o.get("label_offset", "50%")
            c.add(f'<text class="lbl-street m-lbl" dy="3"><textPath href="#{pid}" startOffset="{off}" text-anchor="middle">{esc(o["name"])}</textPath></text>')
        elif o.get("label") and "poly" in o and o.get("label_at"):
            x, y = o["label_at"]
            c.add(f'<text class="lbl-street m-lbl" x="{c.X(x):.1f}" y="{c.Y(y):.1f}" text-anchor="middle">{esc(o["name"])}</text>')
    for w in m.get("water", []):
        if w.get("label_at"):
            x, y = w["label_at"]
            rot = w.get("rot", 0)
            c.add(f'<text class="lbl-water m-lbl" x="{c.X(x):.1f}" y="{c.Y(y):.1f}" text-anchor="middle" transform="rotate({rot} {c.X(x):.1f} {c.Y(y):.1f})">{esc(w["name"])}</text>')
    for d in m.get("districts", []):
        if d.get("label_at"):
            x, y = d["label_at"]
            rot = d.get("rot", 0)
            c.add(f'<text class="lbl-district m-lbl" x="{c.X(x):.1f}" y="{c.Y(y):.1f}" text-anchor="middle" transform="rotate({rot} {c.X(x):.1f} {c.Y(y):.1f})">{esc(d["name"])}</text>')
    for b in m.get("buildings", []):
        if b.get("label", True):
            p = b.get("label_at") or (b["_g"].centroid.x, b["_g"].centroid.y)
            rot = b.get("rot", 0)
            lines = b["name"].split("\n")
            for li, line in enumerate(lines):
                yy = c.Y(p[1]) + (li - (len(lines) - 1) / 2) * 12
                c.add(f'<text class="lbl-bld m-lbl" x="{c.X(p[0]):.1f}" y="{yy:.1f}" text-anchor="middle" transform="rotate({rot} {c.X(p[0]):.1f} {c.Y(p[1]):.1f})">{esc(line)}</text>')
    for lb in m.get("labels", []):
        x, y = lb["at"]
        rot = lb.get("rot", 0)
        anchor = lb.get("anchor", "middle")
        c.add(f'<text class="{lb.get("cls", "lbl-note")} m-lbl" x="{c.X(x):.1f}" y="{c.Y(y):.1f}" text-anchor="{anchor}" transform="rotate({rot} {c.X(x):.1f} {c.Y(y):.1f})">{esc(lb["text"])}</text>')
    c.add("</g>")

    # points of interest and mission markers
    c.add('<g data-layer="pois">')
    for p in m.get("pois", []):
        col = CATS[p["cat"]][1]
        x, y = c.X(p["at"][0]), c.Y(p["at"][1])
        c.add(f'<g class="poi" data-poi="{m["id"]}-{p["n"]}"><title>{p["n"]}. {esc(p["name"])}{": " + esc(p["note"]) if p.get("note") else ""}</title>'
              f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{col}"/><text class="num m-lbl" x="{x:.1f}" y="{y + 0.5:.1f}">{p["n"]}</text></g>')
    c.add("</g>")
    c.add('<g data-layer="missions">')
    for ms in m.get("missions", []):
        x, y = c.X(ms["at"][0]), c.Y(ms["at"][1])
        if ms.get("anchor"):
            ax, ay = c.X(ms["anchor"][0]), c.Y(ms["anchor"][1])
            c.add(f'<path class="leader" d="M{x:.1f},{y:.1f} L{ax:.1f},{ay:.1f}"/><circle cx="{ax:.1f}" cy="{ay:.1f}" r="2.5" fill="{ROLE["gold"]}"/>')
        c.add(f'<g class="mission" data-poi="{m["id"]}-{ms["code"]}"><title>{ms["code"]} {esc(ms["name"])}: {esc(ms.get("note", ""))}</title>'
              f'<rect x="{x - 10:.1f}" y="{y - 10:.1f}" width="20" height="20" fill="{ms.get("colour", ROLE["gold"])}" stroke="#05080b" stroke-width="1.6" transform="rotate(45 {x:.1f} {y:.1f})"/>'
              f'<text class="num m-lbl" x="{x:.1f}" y="{y + 0.5:.1f}">{ms["code"]}</text></g>')
    c.add("</g>")

    draw_compass_scale(c)
    draw_legend(c, m, MARGIN * 2 + W * S, LW, vh)
    c.add("</svg>")
    return "\n".join(c.out)


def draw_compass_scale(c):
    W, H, S = c.W, c.H, c.S
    x0, y0 = c.X(4), c.Y(H) - 16
    c.add('<g data-layer="scale">')
    c.add(f'<rect x="{x0 - 6}" y="{y0 - 20}" width="{50 * S + 44}" height="30" fill="#06090c" fill-opacity=".8"/>')
    for i, (a, b) in enumerate([(0, 10), (10, 25), (25, 50)]):
        c.add(f'<rect x="{x0 + a * S:.1f}" y="{y0}" width="{(b - a) * S:.1f}" height="4" fill="{"#dbe4ec" if i % 2 == 0 else "#4a5a69"}"/>')
    for v in (0, 10, 25, 50):
        c.add(f'<text class="lbl-grid m-mono" x="{x0 + v * S:.1f}" y="{y0 - 5}" text-anchor="middle">{v}</text>')
    c.add(f'<text class="lbl-grid m-mono" x="{x0 + 50 * S + 12:.1f}" y="{y0 + 5}">m</text>')
    cx, cy = c.X(W) - 26, c.Y(0) + 30
    c.add(f'<circle cx="{cx}" cy="{cy}" r="16" fill="#06090c" fill-opacity=".8" stroke="#35414e"/>'
          f'<path d="M{cx},{cy - 13} L{cx + 5},{cy + 4} L{cx},{cy} L{cx - 5},{cy + 4} Z" fill="{ROLE["accent"]}"/>'
          f'<text class="lbl-grid m-lbl" x="{cx}" y="{cy - 20}" text-anchor="middle" fill="#dbe4ec">N</text>')
    c.add("</g>")


KEY_STYLES = {
    "viaduct": ("Elevated: viaduct", '<rect x="0" y="-5" width="26" height="10" class="viaduct"/>'),
    "walkway": ("Upper walkway, roofs", '<path class="walkway" d="M0,0 H26"/>'),
    "catwalk": ("Catwalk", '<rect x="0" y="-4" width="26" height="8" class="catwalk"/>'),
    "vent": ("Vent or crawlspace", '<path class="vent" d="M0,0 H26"/>'),
    "pipe": ("Pipe run", '<path class="pipe" d="M0,0 H26"/>'),
    "fence": ("Fence", '<path class="fence" d="M0,0 H26"/>'),
    "route-main": ("Route: main", '<path class="route-main" d="M0,0 H26"/>'),
    "route-social": ("Route: social", '<path class="route-social" d="M0,0 H26"/>'),
    "route-stealth": ("Route: stealth", '<path class="route-stealth" d="M0,0 H26"/>'),
    "route-force": ("Route: force", '<path class="route-force" d="M0,0 H26"/>'),
    "route-tech": ("Route: tech (hack, power)", '<path class="route-tech" d="M0,0 H26"/>'),
    "wallsolid": ("Corrugated wall", '<path class="wallsolid" d="M0,0 H26"/>'),
    "crane": ("Crane boom (+18 m)", '<rect x="0" y="-3" width="26" height="6" class="boom"/>'),
    "patrol": ("Patrol", '<path class="patrol" d="M0,0 H26"/>'),
    "cone": ("Camera or turret view", '<path class="cone" d="M0,0 L26,-7 L26,7 Z"/>'),
    "cone-light": ("Searchlight", '<path class="cone-light" d="M0,0 L26,-7 L26,7 Z"/>'),
    "restricted": ("Restricted zone", '<rect x="0" y="-6" width="26" height="12" class="restricted"/>'),
    "water": ("Water", '<rect x="0" y="-6" width="26" height="12" fill="url(#hatch-water-ID)"/>'),
    "water-lower": ("Flooded, one level down", '<rect x="0" y="-5" width="26" height="10" class="water-lower"/>'),
    "trip": ("Tripwire or can rattle", '<path class="trip" d="M0,0 H26"/>'),
    "turret": ("Scrap turret", '<rect x="7" y="-5" width="10" height="10" fill="#ff9e2e"/>'),
    "boss": ("Named or boss", '<path d="M22,0 L6,-9 L11,0 L6,9 Z" fill="#ff2d6f"/>'),
    "cage": ("Cage", '<rect x="4" y="-6" width="18" height="12" class="cage"/>'),
    "enemy": ("Hostile (facing)", '<path d="M20,0 L8,-7 L12,0 L8,7 Z" fill="#ff5b4f"/>'),
    "dog": ("Robot dog", '<path d="M20,0 L8,-7 L12,0 L8,7 Z" fill="#ff9e2e"/>'),
    "hostage": ("Hostage", '<circle cx="13" cy="0" r="5" fill="#f2b33d"/>'),
    "civ": ("Neutral NPC", '<circle cx="13" cy="0" r="4.5" fill="#4aa8ff"/>'),
}


def draw_legend(c, m, x0, LW, vh):
    c.add(f'<g data-layer="legend" transform="translate({x0},0)">')
    c.add(f'<rect x="0" y="0" width="{LW}" height="{vh}" fill="#0a0e13"/><line x1="0" y1="0" x2="0" y2="{vh}" stroke="#1f2933"/>')
    c.add(f'<rect x="24" y="30" width="4" height="46" fill="{ROLE["accent"]}"/>')
    c.add(f'<text class="m-lbl" x="38" y="58" fill="#e8eef3" font-size="34" font-weight="700" letter-spacing="5">{esc(m["title"])}</text>')
    c.add(f'<text class="m-lbl" x="39" y="76" fill="{ROLE["dim"]}" font-size="12" letter-spacing="3.5">{esc(m["subtitle"])}</text>')
    y = 104
    if m.get("blurb"):
        for line in m["blurb"]:
            c.add(f'<text class="lg-n m-lbl" x="24" y="{y}">{esc(line)}</text>')
            y += 13
        y += 8
    col_w = (LW - 48) / 2

    # missions, full width
    if m.get("missions"):
        c.add(f'<text class="lg-h m-lbl" x="24" y="{y}">MISSIONS</text>')
        y += 16
        for ms in m["missions"]:
            c.add(f'<g class="mission lg" data-poi-ref="{m["id"]}-{ms["code"]}">'
                  f'<rect x="28" y="{y - 7}" width="13" height="13" fill="{ms.get("colour", ROLE["gold"])}" transform="rotate(45 34.5 {y - 0.5})"/>'
                  f'<text class="lg-t m-lbl" x="50" y="{y + 4}"><tspan font-weight="700">{ms["code"]}</tspan>  {esc(ms["name"])}</text>'
                  f'<text class="lg-n m-lbl" x="{LW - 24}" y="{y + 4}" text-anchor="end">{esc(ms.get("kind", ""))}</text></g>')
            y += 19
        y += 10

    # POIs by category, flowing into two columns
    items = []
    for cat in CAT_ORDER:
        ps = [p for p in m.get("pois", []) if p["cat"] == cat]
        if not ps:
            continue
        items.append(("h", cat))
        items += [("p", p) for p in ps]
    key_rows = m.get("key", [])
    key_h = 22 + ((len(key_rows) + 1) // 2) * 18
    col_top = y
    col_bottom = vh - key_h - 24
    rows_h = sum(24 if k == "h" else 16 for k, _ in items)
    single = col_top + rows_h <= col_bottom
    if single:
        col_w = LW - 48
    col = 0
    cy = col_top
    for kind, it in items:
        need = 22 if kind == "h" else 16
        if not single and cy + need > col_bottom and col == 0:
            col, cy = 1, col_top
        cx = 24 + col * (col_w + 8)
        if kind == "h":
            label, colour = CATS[it]
            c.add(f'<rect x="{cx}" y="{cy + 2}" width="{col_w - 4}" height="1" fill="#1f2933"/>')
            c.add(f'<text class="lg-h m-lbl" x="{cx}" y="{cy + 16}" fill="{colour}">{label}</text>')
            cy += 24
        else:
            colour = CATS[it["cat"]][1]
            c.add(f'<g class="poi lg" data-poi-ref="{m["id"]}-{it["n"]}"><circle cx="{cx + 8}" cy="{cy}" r="7" fill="{colour}"/>'
                  f'<text class="num m-lbl" x="{cx + 8}" y="{cy + 0.5}">{it["n"]}</text>'
                  f'<text class="lg-t m-lbl" x="{cx + 21}" y="{cy + 4}">{esc(it["name"])}'
                  + (f'<tspan class="lg-n" dx="8">{esc(it["note"])}</tspan>' if single and it.get("note") else "")
                  + '</text></g>')
            cy += 16
    # key
    ky = vh - key_h - 8
    c.add(f'<rect x="24" y="{ky - 14}" width="{LW - 48}" height="1" fill="#1f2933"/>')
    c.add(f'<text class="lg-h m-lbl" x="24" y="{ky + 2}">KEY</text>')
    for i, k in enumerate(key_rows):
        label, glyph = KEY_STYLES[k]
        kx = 24 + (i % 2) * ((LW - 48) / 2 + 8)
        kyy = ky + 20 + (i // 2) * 18
        c.add(f'<g transform="translate({kx},{kyy})">{glyph.replace("ID", m["id"])}</g><text class="lg-n m-lbl" x="{kx + 34}" y="{kyy + 4}">{esc(label)}</text>')
    c.add("</g>")


def main(ids):
    OUT.mkdir(parents=True, exist_ok=True)
    for i in ids:
        mod = importlib.import_module(f"layouts.{i}")
        svg = render(mod.MAP)
        (OUT / f"{i}.svg").write_text(svg)
        print(f"wrote {OUT / (i + '.svg')} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1:] or ["hub", "drains", "yard"])
