"""Export the design page's item icons as standalone SVG files for the game.

    python3 tools/design/export_icons.py

Reads every <symbol id="i-NAME"> in docs/design/src/body.html and writes
game/ui/undercity/icons/NAME.svg: one standalone SVG with the symbol's viewBox, carrying any
gradient from the page's <defs> that the drawing references (such as "gmetal").

It lives with the design tools because the design page is the one source of the drawings
(ItemDef.Icon names a symbol there); the game's SVGs are generated from it, never edited by
hand (CLAUDE.md 11). It also writes each icon's Godot import settings: the SVG is rasterised
at ICON_SCALE times its viewBox (a 48-unit cell becomes 96 px), with mipmaps, so it stays crisp
where the UI draws it at 44 to 58 px per cell. Finally it checks the real data: every "icon" in
game/data/items.json must name an exported drawing (CLAUDE.md 5.6, validate the real artifact).
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BODY = ROOT / "docs" / "design" / "src" / "body.html"
ITEMS = ROOT / "game" / "data" / "items.json"
OUT = ROOT / "game" / "ui" / "undercity" / "icons"

# Raster scale for Godot's SVG importer: viewBox units to pixels.
ICON_SCALE = 2.0

SYMBOL = re.compile(r'<symbol\s+id="i-([a-z0-9_-]+)"\s+viewBox="([^"]+)"\s*>(.*?)</symbol>', re.S)
DEFS = re.compile(r"<defs>(.*?)</defs>", re.S)
GRADIENT = re.compile(r'<(linearGradient|radialGradient)\s+id="([^"]+)".*?</\1>', re.S)

# Godot fills in every other import parameter (and the uid) on first import and keeps these.
IMPORT_TEMPLATE = """[remap]

importer="texture"
type="CompressedTexture2D"

[params]

mipmaps/generate=true
svg/scale={scale}
"""


def page_gradients(body):
    """The gradients in the page's first <defs>, the one that holds the icon symbols, by id."""
    defs = DEFS.search(body)
    if defs is None:
        raise SystemExit(f"{BODY}: no <defs> block")
    return {m.group(2): m.group(0) for m in GRADIENT.finditer(defs.group(1))}


def standalone(view_box, drawing, gradients):
    """One SVG document: the symbol's drawing, plus the gradients it references."""
    used = [g for gid, g in sorted(gradients.items()) if f"url(#{gid})" in drawing]
    missing = sorted(set(re.findall(r"url\(#([^)]+)\)", drawing)) - set(gradients))
    if missing:
        raise SystemExit(f"a drawing references {missing}, which the page's <defs> doesn't define")
    _, _, w, h = view_box.split()
    defs = f"<defs>{''.join(used)}</defs>" if used else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{view_box}">'
            f"{defs}{drawing}</svg>\n")


def write_import(svg_path):
    """Sets the import scale, keeping an existing import file's uid and other settings."""
    imp = svg_path.with_name(svg_path.name + ".import")
    if not imp.exists():
        imp.write_text(IMPORT_TEMPLATE.format(scale=ICON_SCALE))
        return
    text = imp.read_text()
    line = f"svg/scale={ICON_SCALE}"
    text = re.sub(r"^svg/scale=.*$", line, text, flags=re.M) if "svg/scale=" in text else text.rstrip("\n") + f"\n{line}\n"
    text = re.sub(r"^mipmaps/generate=.*$", "mipmaps/generate=true", text, flags=re.M)
    imp.write_text(text)


def item_icons():
    """The icon names game/data/items.json uses. The file allows // comment lines."""
    lines = [l for l in ITEMS.read_text().splitlines() if not l.lstrip().startswith("//")]
    return sorted({i["icon"] for i in json.loads("\n".join(lines))["items"]})


def main():
    body = BODY.read_text()
    gradients = page_gradients(body)
    symbols = SYMBOL.findall(body)
    if not symbols:
        raise SystemExit(f"{BODY}: no <symbol id=\"i-...\"> found")
    OUT.mkdir(parents=True, exist_ok=True)
    names = []
    for name, view_box, drawing in symbols:
        path = OUT / f"{name}.svg"
        path.write_text(standalone(view_box, drawing.strip(), gradients))
        write_import(path)
        names.append(name)
    missing = [i for i in item_icons() if i not in names]
    if missing:
        raise SystemExit(f"items.json names icons the page doesn't draw: {missing}")
    print(f"wrote {len(names)} icons to {OUT.relative_to(ROOT)}: {' '.join(sorted(names))}")


if __name__ == "__main__":
    sys.exit(main())
