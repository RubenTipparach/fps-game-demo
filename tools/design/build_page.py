"""Build the Undercity design page: docs/design/src/* plus the generated maps.

    python3 tools/levels/render_map.py && python3 tools/design/build_page.py

Writes docs/design/undercity_systems.html. The maps are inlined from docs/design/maps/*.svg,
so the page always shows what the layouts say (CLAUDE.md 7.1).
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "design" / "src"
MAPS = ROOT / "docs" / "design" / "maps"
OUT = ROOT / "docs" / "design" / "undercity_systems.html"


def main():
    body = (SRC / "body.html").read_text()
    body = re.sub(r"<!--MAP:(\w+)-->", lambda m: (MAPS / f"{m.group(1)}.svg").read_text(), body)
    page = (SRC / "head.html").read_text() + "\n" + body + "\n<script>\n" + (SRC / "script.js").read_text() + "</script>\n"
    bad = [hex(ord(c)) for c in (chr(0x2014), chr(0x2013)) if c in page]
    if bad:
        raise SystemExit(f"em or en dash in the page: {bad} (CLAUDE.md section 4)")
    OUT.write_text(page)
    print(f"wrote {OUT} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
