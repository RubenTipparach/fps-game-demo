"""Undercity's prop kit: the doors, containers, consoles and gates of Meridian's flooded
underbelly, modelled in Blender as low-poly, bevelled, UT99-era pieces.

Run:  blender -b --factory-startup -P tools/blender/build_undercity_props.py
Writes:
  tools/blender/undercity_props.blend               editable source, one collection per prop
  game/models/undercity/props/<name>.glb            one prop per file (PROPS below)
  game/models/undercity/props/<name>.glb.import     its import preset (tools/godot/import_presets.py)
  game/materials/props/<name>.tres                  the kit's own materials (MATERIALS below)
  game/textures/props/*.png                         paint, screen, lens, stencil and label textures

It lives in tools/blender because meshes are files built by a committed script (CLAUDE.md 6.1),
and it reuses build_props.py's Kit (bevelled boxes joined into one object, world UVs at the
shared texel density) and its glTF export settings, so both prop kits come out the same way.

Conventions (the brief every prop follows):
  * Metres, Blender axes: x right, y front, z up. The front (the side the player uses) faces +Y,
    which the glTF export (+Y up) turns into Godot -Z, the node's forward.
  * The origin is the floor centre of the footprint unless PROPS says otherwise.
  * Material names are the game's: the import preset maps each onto res://materials/*.tres or
    res://materials/props/*.tres. The Blender preview of a prop material is built from that
    .tres file, so the .blend and the contact sheet show what Godot will draw.
  * Collision is a "<Name>Collision-colonly" object of plain boxes, as in build_props.py; Godot
    turns it into a StaticBody3D. A moving part's collision is its child, so it moves with it.
  * Moving parts are separate objects with their pivot as their origin and an identity
    rotation. Lights the game recolours are separate objects named "Status" (prop_import.gd
    keeps them out of the lightmap bake).
  * Every box is registered with detailing.assert_no_zfighting (CLAUDE.md 7.2), which refuses
    to write a prop with coplanar overlapping faces. Cylinders and sloped hulls are not covered
    by the check, so they are kept clear of other faces by construction.
  * Emissive materials use emission_operator = 1 (Multiply) and an emission texture: Godot's
    emission texture defaults to black, so Multiply needs one (CLAUDE.md 11).
"""
import math
import os
import re
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blendkit import GAME, HERE, MANIFEST, collection, material  # noqa: E402
from build_props import Kit, export, reset  # noqa: E402  (also puts tools/godot on sys.path)

import import_presets  # noqa: E402  (tools/godot: the one writer of .glb.import presets)
from detailing import assert_no_zfighting  # noqa: E402

OUT = os.path.join(GAME, "models", "undercity", "props")
TEX_DIR = os.path.join(GAME, "textures", "props")
MAT_DIR = os.path.join(GAME, "materials", "props")
BLEND = os.path.join(HERE, "undercity_props.blend")
MAX_TRIS = 1500          # per prop, visible meshes (the brief's low-poly budget)
SEED = 7713              # the generated textures' wear and screen noise


# ----------------------------------------------------------------------------- materials

# The kit's own materials. Everything else a prop names comes from the shared set
# (game/materials/*.tres, game/materials/props/*.tres). Colours are sRGB, as Godot stores them.
#   base:      a Material Maker set (game/textures/<base>*.png): albedo, ORM and normal maps
#   albedo:    this kit's albedo texture (game/textures/props/<albedo>.png), replacing base's
#   color:     the albedo colour, or the tint of the albedo texture
#   normal:    a Material Maker set whose normal map to use, when there is no base
#   emission:  emissive colour, multiplied by the kit's texture `emission_tex` and by `energy`


def paint(rgb, roughness=0.5):
    """Painted steel: the kit's painted_metal texture (chipped paint over the rust set) tinted
    to a paint colour. Paint is a dielectric, so no metallic."""
    return dict(albedo="painted_metal", color=rgb, normal="rust_metal", normal_scale=0.3, roughness=roughness)


MATERIALS = {
    "paint_grimy": paint((0.55, 0.62, 0.55), 0.55),
    "paint_safe": paint((0.22, 0.38, 0.28), 0.4),
    "paint_red": paint((0.72, 0.1, 0.07)),
    "paint_navy": paint((0.16, 0.22, 0.45)),
    "crate_stencil": dict(base="crate", albedo="crate_stencil"),
    "mersec_label": dict(albedo="mersec_label", roughness=0.6),
    "lacquer_red": dict(color=(0.55, 0.06, 0.04), roughness=0.25),
    "lacquer_black": dict(color=(0.05, 0.04, 0.04), roughness=0.3),
    "canvas": dict(color=(0.36, 0.37, 0.24), roughness=0.95),
    "cardboard": dict(color=(0.52, 0.39, 0.25), roughness=0.9),
    "box_blue": dict(color=(0.22, 0.38, 0.66), roughness=0.5),
    "box_green": dict(color=(0.13, 0.56, 0.3), roughness=0.5),
    "bottle_amber": dict(color=(0.55, 0.27, 0.06), roughness=0.15),
    "terminal_screen": dict(color=(0.02, 0.03, 0.03), roughness=0.2, emission=(0.3, 0.95, 1.0), energy=2.5,
                            emission_tex="terminal_screen_emission"),
    "led_red": dict(color=(0.35, 0.03, 0.02), roughness=0.3, emission=(1.0, 0.12, 0.06), energy=5.0,
                    emission_tex="led_lens_emission"),
    "led_amber": dict(color=(0.4, 0.22, 0.02), roughness=0.3, emission=(1.0, 0.62, 0.12), energy=5.0,
                      emission_tex="led_lens_emission"),
}

# Faces of these materials get UVs fitted to their own rectangle (0..1 across the face, read
# upright from outside) instead of world UVs: a screen, a label, a lens, a whole crate face.
FITTED = {"terminal_screen", "mersec_label", "led_red", "led_amber", "crate", "crate_stencil"}


def _fmt(c):
    return "Color(%s, 1.0)" % ", ".join(f"{v:.4g}" for v in c)


def tres_text(name, spec):
    """The Godot material resource for one MATERIALS entry."""
    res = []

    def ext(path):
        res.append(path)
        return f'ExtResource("{len(res)}")'

    base = spec.get("base")
    body = [f'resource_name = "{name}"', "texture_filter = 5",
            f"albedo_color = {_fmt(spec.get('color', (1.0, 1.0, 1.0)))}"]
    if spec.get("albedo") or base:
        path = f"res://textures/props/{spec['albedo']}.png" if spec.get("albedo") else f"res://textures/{base}.png"
        body.append(f"albedo_texture = {ext(path)}")
    if base:
        # ORM: R ambient occlusion, G roughness, B metallic; the scalars multiply it.
        body += ["roughness = 1.0", "metallic = 1.0", "metallic_specular = 0.5",
                 f"orm_texture = {ext(f'res://textures/{base}_orm.png')}", "ao_light_affect = 0.2"]
    else:
        body += [f"metallic = {spec.get('metallic', 0.0)}", f"roughness = {spec.get('roughness', 1.0)}"]
    normal = spec.get("normal", base)
    if normal:
        scale = spec.get("normal_scale", MANIFEST[normal].get("normal_scale", 1.0))
        body += ["normal_enabled = true", f"normal_scale = {scale}",
                 f"normal_texture = {ext(f'res://textures/{normal}_normal.png')}"]
    if "emission" in spec:
        # Multiply: emission = colour * texture * energy (CLAUDE.md 11). The texture is the mask.
        mask = "res://textures/props/%s.png" % spec["emission_tex"]
        body += ["emission_enabled = true", f"emission = {_fmt(spec['emission'])}", "emission_operator = 1",
                 f"emission_energy_multiplier = {spec['energy']}", f"emission_texture = {ext(mask)}"]
    kind = "ORMMaterial3D" if base else "StandardMaterial3D"
    head = [f'[gd_resource type="{kind}" format=3]', ""]
    head += [f'[ext_resource type="Texture2D" path="{p}" id="{i}"]' for i, p in enumerate(res, 1)]
    return "\n".join(head + ([""] if res else []) + ["[resource]"] + body) + "\n"


def write_materials():
    """Write every MATERIALS entry to game/materials/props/<name>.tres."""
    os.makedirs(MAT_DIR, exist_ok=True)
    for name, spec in MATERIALS.items():
        with open(os.path.join(MAT_DIR, name + ".tres"), "w") as f:
            f.write(tres_text(name, spec))


def _srgb_to_linear(c):
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def read_tres(path):
    """(properties, {ext id: res path}) of a Godot material resource."""
    text = open(path).read()
    ext = {i: p for p, i in re.findall(r'\[ext_resource [^\]]*?path="([^"]+)"[^\]]*?id="([^"]+)"', text)}
    props = dict(re.findall(r"^(\w+) = (.+)$", text.split("[resource]", 1)[1], re.M))
    return props, ext


def _color(v):
    return tuple(float(x) for x in re.search(r"Color\(([^)]*)\)", v).group(1).split(","))[:3]


def _tex(props, ext, key):
    m = re.search(r'ExtResource\("([^"]+)"\)', props.get(key, ""))
    return os.path.join(GAME, ext[m.group(1)][len("res://"):]) if m else None


def material_from_tres(name, path):
    """A Blender preview of a Godot material file: albedo (texture x colour), ORM or scalar
    roughness and metallic, normal map, emission (colour x texture x energy)."""
    props, ext = read_tres(path)
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    def image(p, color=True):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(p, check_existing=True)
        if not color:
            n.image.colorspace_settings.name = "Non-Color"
        return n

    def times(node, rgb):
        mul = nt.nodes.new("ShaderNodeVectorMath")
        mul.operation = "MULTIPLY"
        nt.links.new(node.outputs["Color"], mul.inputs[0])
        mul.inputs[1].default_value = rgb
        return mul.outputs[0]

    tint = _srgb_to_linear(_color(props.get("albedo_color", "Color(1, 1, 1, 1)")))
    albedo = _tex(props, ext, "albedo_texture")
    if albedo:
        nt.links.new(times(image(albedo), tint), bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*tint, 1.0)
    orm = _tex(props, ext, "orm_texture")
    if orm:
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(image(orm, False).outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    else:
        bsdf.inputs["Roughness"].default_value = float(props.get("roughness", 1.0))
        bsdf.inputs["Metallic"].default_value = float(props.get("metallic", 0.0))
    normal = _tex(props, ext, "normal_texture")
    if normal and props.get("normal_enabled") == "true":
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(image(normal, False).outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    if props.get("emission_enabled") == "true":
        col = _srgb_to_linear(_color(props.get("emission", "Color(0, 0, 0, 1)")))
        etex = _tex(props, ext, "emission_texture")
        if etex:
            nt.links.new(times(image(etex), col), bsdf.inputs["Emission Color"])
        else:
            bsdf.inputs["Emission Color"].default_value = (*col, 1.0)
        bsdf.inputs["Emission Strength"].default_value = float(props.get("emission_energy_multiplier", 1.0))
    return m


def preview_material(name):
    """The Blender material for a game material name: built from game/materials/props/<name>.tres
    when the name is a prop material, else blendkit's preview of the Material Maker set."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    tres = os.path.join(MAT_DIR, name + ".tres")
    if os.path.exists(tres):
        return material_from_tres(name, tres)
    if os.path.exists(os.path.join(GAME, "textures", name + ".png")):
        return material(name)
    raise SystemExit(f"[undercity_props] unknown material {name!r}: no game/materials/props/{name}.tres "
                     f"and no game/textures/{name}.png")


# ----------------------------------------------------------------------------- textures

# A 5 x 7 pixel font for the generated textures and the contact sheet's labels.
FONT = {
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    "C": [" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "],
    "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    "G": [" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ####"],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "I": [" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "J": ["  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    "N": ["#   #", "#   #", "##  #", "# # #", "#  ##", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "# # #", " # # "],
    "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "Y": ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    "0": [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": ["#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": ["  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "],
    " ": ["     "] * 7,
    "-": ["     ", "     ", "     ", " ### ", "     ", "     ", "     "],
    "_": ["     ", "     ", "     ", "     ", "     ", "     ", "#####"],
    ".": ["     ", "     ", "     ", "     ", "     ", "     ", "  #  "],
    ":": ["     ", "     ", "  #  ", "     ", "     ", "  #  ", "     "],
    "/": ["    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "],
    ">": ["#    ", " #   ", "  #  ", "   # ", "  #  ", " #   ", "#    "],
}


def text_mask(text, cell, bridge=0):
    """`text` in the pixel font as a boolean image (row 0 at the top), `cell` pixels per font
    pixel. `bridge` > 0 cuts that many pixel rows through the strokes at font rows 2 and 5, the
    ties of a stencil."""
    m = np.zeros((7 * cell, (len(text) * 6 - 1) * cell), bool)
    for i, ch in enumerate(text.upper()):
        for r, row in enumerate(FONT[ch]):
            for c, px in enumerate(row):
                if px == "#":
                    m[r * cell:(r + 1) * cell, (i * 6 + c) * cell:(i * 6 + c + 1) * cell] = True
    for r in (2, 5) if bridge else ():
        m[r * cell:r * cell + bridge, :] = False
    return m


def stamp(img, mask, top, left, rgb, alpha=1.0):
    """Paint `rgb` into img (H x W x 3, row 0 at the top) where mask is set, alpha-blended."""
    h, w = mask.shape
    a = (mask * alpha)[..., None] if np.ndim(alpha) == 0 else (mask * alpha[:h, :w])[..., None]
    region = img[top:top + h, left:left + w]
    region[:] = region * (1 - a) + np.array(rgb, np.float32) * a


def save_png(path, rgb):
    """Write an H x W x 3 float image (row 0 at the top, sRGB values 0..1) as a PNG."""
    h, w, _ = rgb.shape
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(rgb, 0.0, 1.0)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def load_png(path):
    """A PNG as an H x W x 3 float array, row 0 at the top."""
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1, :, :3].copy()


def _wear(rng, h, w, block, keep):
    """Blocky paint-wear mask: 1 where the paint holds, fading at the blocks' edges."""
    g = rng.random((h // block + 2, w // block + 2))
    up = np.kron(g, np.ones((block, block)))[:h, :w]
    for axis in (0, 1):                                     # soften the block edges a little
        up = (up + np.roll(up, block // 2, axis) + np.roll(up, -block // 2, axis)) / 3.0
    return np.clip((up - (1.0 - keep)) * 6.0, 0.0, 1.0)


def _blur(a, k):
    """Box blur of a 2D array, radius k pixels, wrapping (the textures tile)."""
    for axis in (0, 1):
        a = sum(np.roll(a, d, axis) for d in range(-k, k + 1)) / (2 * k + 1)
    return a


# The terminal's screen: its size sets the screen texture's aspect.
SCREEN_W, SCREEN_H = 0.5, 0.235
SCREEN_LINES = ["> LOGIN: GUEST", "> MAIL ....... 2 NEW", "> TIDE 3.1 M  RISING", "> CURFEW 02:00-05:00",
                "> HARBOR AUTH NOTICE", "> _"]


def write_textures():
    """The kit's generated textures, derived from the Material Maker sets where they can be (the
    sets have no clean paint, screen, lens or lettering)."""
    os.makedirs(TEX_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)

    # LED lens: bright centre, dimmer rim, a small hot spot. Multiplied by each LED's colour.
    yy, xx = (np.mgrid[0:64, 0:64] / 63.0) * 2 - 1
    lens = np.clip(1.0 - 0.45 * (xx ** 2 + yy ** 2), 0.4, 1.0)
    lens = np.clip(lens + 0.25 * np.exp(-((xx + 0.35) ** 2 + (yy + 0.35) ** 2) / 0.04), 0, 1)
    save_png(os.path.join(TEX_DIR, "led_lens_emission.png"), np.repeat(lens[..., None], 3, 2))

    # Terminal screen: a header bar, lines of text, scanlines and a dim glow. Grey levels only:
    # the material's cyan emission colour tints it.
    w = 512
    h = int(round(w * SCREEN_H / SCREEN_W / 4.0)) * 4
    scr = np.full((h, w, 3), 0.1, np.float32)
    scr *= (0.8 + 0.2 * np.linspace(1, 0, h))[:, None, None]
    scr[10:40, 12:w - 12] = 0.85
    stamp(scr, text_mask("MERINET // PUBLIC NODE", 3), 15, 20, (0.12, 0.12, 0.12))
    for i, line in enumerate(SCREEN_LINES):
        stamp(scr, text_mask(line, 3), 52 + i * 30, 20, (0.8, 0.8, 0.8))
    scr[52 + 5 * 30:52 + 5 * 30 + 21, 20 + 2 * 18:20 + 2 * 18 + 15] = 0.95      # the cursor block
    scr[1::2] *= 0.82                                                           # scanlines
    scr += rng.random((h, w, 1)).astype(np.float32) * 0.03
    save_png(os.path.join(TEX_DIR, "terminal_screen_emission.png"), scr)

    # Painted metal: the rust set's heaviest rust kept, the rest painted over, with its rust
    # clouds softened into grime. No plate seams: world UVs would drop them at arbitrary places
    # (down the middle of a safe). Light grey: each paint material tints it.
    rust = load_png(os.path.join(GAME, "textures", "rust_metal.png"))
    sat = rust[..., 0] - rust[..., 2]                       # rust is orange: red high, blue low
    cloud = _blur(np.clip((sat - np.percentile(sat, 20)) / (np.percentile(sat, 95) - np.percentile(sat, 20)), 0, 1), 6)
    spots = np.clip((sat - 0.445) * 14.0, 0.0, 1.0)[..., None]
    painted = (0.9 - 0.16 * cloud)[..., None] * np.ones(3, np.float32)
    save_png(os.path.join(TEX_DIR, "painted_metal.png"), painted * (1 - spots) + np.array((0.36, 0.2, 0.12)) * spots)

    # Crate: the crate texture with stencilled freight marks, worn where the paint flaked.
    crate = load_png(os.path.join(GAME, "textures", "crate.png"))
    ch, cw, _ = crate.shape
    wear = _wear(rng, ch, cw, 12, 0.8)
    for text, cell, top in (("MERIDIAN", 13, 250), ("FREIGHT", 13, 400), ("UC-7713", 9, 560)):
        m = text_mask(text, cell, bridge=max(2, cell // 4))
        stamp(crate, m, top, (cw - m.shape[1]) // 2, (0.05, 0.045, 0.04), 0.85 * wear[top:, (cw - m.shape[1]) // 2:])
    save_png(os.path.join(TEX_DIR, "crate_stencil.png"), crate)

    # MerSec label: white letters on navy, a thin white border and a red rule.
    lab = np.zeros((64, 256, 3), np.float32) + np.array((0.07, 0.1, 0.26), np.float32)
    lab[3:5, 3:-3] = lab[-5:-3, 3:-3] = 0.85
    lab[3:-3, 3:5] = lab[3:-3, -5:-3] = 0.85
    lab[48:52, 30:-30] = (0.8, 0.08, 0.06)
    m = text_mask("MERSEC", 5)
    stamp(lab, m, 10, (256 - m.shape[1]) // 2, (0.9, 0.92, 0.95))
    save_png(os.path.join(TEX_DIR, "mersec_label.png"), lab)


# ----------------------------------------------------------------------------- modelling kit

def G(p):
    """Blender (x right, y front, z up) -> the Godot coordinates Kit takes."""
    return (p[0], p[2], -p[1])


class PropKit(Kit):
    """build_props.Kit in Blender coordinates, registering every box for the z-fighting check.

    reg is the prop's list of (lo, hi, label) boxes, or None for a collision kit (not drawn,
    so not checked)."""

    AXES = {"x": "x", "y": "z", "z": "y"}   # Blender axis -> the Godot axis cylinder_bm takes

    def __init__(self, name, coll, reg):
        super().__init__(name, coll)
        self.reg = reg

    def box(self, lo, hi, mat, bevel=0.01, skip=()):
        lo, hi = tuple(map(min, lo, hi)), tuple(map(max, lo, hi))
        if min(b - a for a, b in zip(lo, hi)) < 1e-4:
            raise SystemExit(f"[undercity_props] {self.name}: zero-thickness box {lo} {hi}")
        preview_material(mat)
        if self.reg is not None:
            self.reg.append((lo, hi, f"{self.name}#{len(self.reg)}"))
        super().box(G(lo), G(hi), mat, bevel=bevel, skip=skip)

    def cyl(self, center, r, length, axis, mat, bevel=0.0, segments=8, caps=True):
        preview_material(mat)
        super().cyl(G(center), r, length, self.AXES[axis], mat, bevel=bevel, segments=segments, caps=caps)

    def hull(self, pts, mat, bevel=0.0):
        """Convex hull of Blender-space points, coplanar triangles merged into flat faces."""
        preview_material(mat)
        bm = bmesh.new()
        for p in pts:
            bm.verts.new(Vector(p))
        bmesh.ops.convex_hull(bm, input=bm.verts)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:])
        bm.normal_update()
        self._add(bm, mat, bevel)

    def obox(self, c, u, v, n, hu, hv, n0, n1, mat, bevel=0.0):
        """A box on a sloped face: centre c, half sizes hu along u and hv along v, n0..n1 along n."""
        c, u, v, n = Vector(c), Vector(u), Vector(v), Vector(n)
        self.hull([c + u * su * hu + v * sv * hv + n * t for su in (-1, 1) for sv in (-1, 1) for t in (n0, n1)],
                  mat, bevel)

    def finish(self, name=None, pivot=None):
        """Join the parts, world UVs, fitted UVs on FITTED faces; `pivot` becomes the origin."""
        ob = super().finish(name)
        fit_uvs(ob)
        if pivot is not None:
            ob.data.transform(Matrix.Translation(-Vector(pivot)))
            ob.location = pivot
        return ob


def fit_uvs(ob):
    """UVs 0..1 across each flat region of a FITTED material, upright as seen from outside:
    v runs up the face (away from the viewer on a top face), u to the viewer's right."""
    me = ob.data
    names = [m.name.split(".")[0] for m in me.materials]
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    bm.normal_update()
    regions = {}
    for f in bm.faces:
        if names[f.material_index] in FITTED:
            n = f.normal
            key = (f.material_index, round(n.x, 3), round(n.y, 3), round(n.z, 3), round(n.dot(f.verts[0].co), 4))
            regions.setdefault(key, []).append(f)
    for faces in regions.values():
        n = faces[0].normal
        if abs(n.z) > 0.9:
            v_dir = Vector((0.0, -1.0 if n.z > 0 else 1.0, 0.0))
        else:
            v_dir = (Vector((0.0, 0.0, 1.0)) - n * n.z).normalized()
        u_dir = v_dir.cross(n)
        loops = [lp for f in faces for lp in f.loops]
        us = [lp.vert.co.dot(u_dir) for lp in loops]
        vs = [lp.vert.co.dot(v_dir) for lp in loops]
        u0, du = min(us), max(max(us) - min(us), 1e-6)
        v0, dv = min(vs), max(max(vs) - min(vs), 1e-6)
        for lp, a, b in zip(loops, us, vs):
            lp[uv].uv = ((a - u0) / du, (b - v0) / dv)
    bm.to_mesh(me)
    bm.free()


def attach(child, parent):
    """Parent `child` (built in prop space) to `parent`, keeping it where it is, so it moves
    with the parent. Parents here carry only a translation."""
    child.data.transform(Matrix.Translation(-parent.location))
    child.parent = parent
    child.location = (0.0, 0.0, 0.0)


def collision(coll, name, boxes, parent=None):
    """The prop's "-colonly" collision: plain boxes, which Godot turns into a StaticBody3D."""
    c = PropKit(name + "Collision", coll, None)
    for lo, hi in boxes:
        c.box(lo, hi, "rubber", bevel=0.0)
    ob = c.finish(name + "Collision-colonly")
    if parent is not None:
        attach(ob, parent)
    return ob


# Shared hardware: one implementation each, used by every prop that has one.

def keypad(k, cx, cz, y0, cols, rows, key, pitch, depth=0.012, mat="white_plastic"):
    """A grid of keys standing on a face at y = y0 (front +Y), centred on (cx, cz)."""
    for r in range(rows):
        for c in range(cols):
            x = cx + (c - (cols - 1) / 2) * pitch[0]
            z = cz + ((rows - 1) / 2 - r) * pitch[1]
            k.box((x - key[0] / 2, y0, z - key[1] / 2), (x + key[0] / 2, y0 + depth, z + key[1] / 2), mat, bevel=0.0)


def padlock(k, x, yc, zt):
    """A padlock hanging from a hasp: shackle top at zt, centred on (x, yc)."""
    b = 0.008                                             # shackle bar
    for s in (-1, 1):
        k.box((x + s * 0.021, yc - b / 2, zt - 0.036), (x + s * 0.013, yc + b / 2, zt - b), "gunmetal_light", bevel=0.0)
    k.box((x - 0.021, yc - b / 2, zt - b), (x + 0.021, yc + b / 2, zt), "gunmetal_light", bevel=0.0)
    k.box((x - 0.026, yc - 0.011, zt - 0.08), (x + 0.026, yc + 0.011, zt - 0.03), "brass", bevel=0.005)


# ----------------------------------------------------------------------------- the props
# Each builder takes its collection and z-fighting registry and returns the objects to export.

def door_leaf(coll, reg):
    """Swinging interior door for a 1.4 x 2.4 m opening. Origin: the hinge, at the bottom of the
    leaf's left edge; the leaf runs along +X and is centred on y = 0."""
    W, H, t = 1.36, 2.37, 0.03
    k = PropKit("Leaf", coll, reg)
    k.box((0, -t, 0), (W, t, H), "paint_grimy", bevel=0.01)
    for z in (0.3, 1.2, 2.05):                                          # hinge knuckles
        k.cyl((0.0, 0.0, z), 0.018, 0.14, "z", "gunmetal")
    st = PropKit("Status", coll, reg)
    for s in (1, -1):                                                   # front (+Y) and back faces

        def Y(a, b):
            return (s * (t + a), s * (t + b))
        for z0, z1 in ((0.42, 1.0), (1.28, 2.2)):                       # raised panels
            y0, y1 = Y(0, 0.014)
            k.box((0.14, y0, z0), (1.0, y1, z1), "paint_grimy", bevel=0.01)
        for i in range(4):                                              # louvred vent
            y0, y1 = Y(0.014, 0.028)
            k.box((0.3, y0, 0.55 + i * 0.09), (0.84, y1, 0.59 + i * 0.09), "gunmetal", bevel=0.0)
        y0, y1 = Y(0, 0.01)
        k.box((0.05, y0, 0.03), (1.31, y1, 0.3), "diamond_plate", bevel=0.003)       # kick plate
        y0, y1 = Y(0, 0.012)
        k.box((1.16, y0, 0.86), (1.26, y1, 1.12), "gunmetal", bevel=0.004)            # handle rose plate
        k.cyl((1.21, s * (t + 0.027), 1.0), 0.022, 0.03, "y", "gunmetal_light")
        y0, y1 = Y(0.027, 0.047)
        k.box((1.05, y0, 0.985), (1.225, y1, 1.015), "gunmetal_light", bevel=0.004)   # lever, toward the hinge
        y0, y1 = Y(0, 0.012)
        k.box((1.17, y0, 1.2), (1.25, y1, 1.38), "gunmetal", bevel=0.004)             # lock plate
        y0, y1 = Y(0.012, 0.024)
        k.box((1.19, y0, 1.23), (1.23, y1, 1.29), "rubber", bevel=0.0)               # card slot
        st.box((1.195, y0, 1.32), (1.225, y1, 1.35), "led_red", bevel=0.0)           # status light
    leaf = k.finish("Leaf")
    status = st.finish("Status")
    attach(status, leaf)
    col = collision(coll, "Leaf", [((0, -t, 0), (W, t, H))], parent=leaf)
    return [leaf, status, col]


BARRIER_PIVOT = (-4.3, -0.26, 1.0)     # the arm's hinge: top of the left post, behind it


def barrier(coll, reg):
    """Checkpoint boom barrier, 9 m between post centres. The arm hangs behind the posts (-Y) so
    it clears them as it lifts; rotating "arm" +80 degrees about its local Z (Godot) lifts it."""
    k = PropKit("Posts", coll, reg)
    for cx in (-4.5, 4.5):
        k.box((cx - 0.205, -0.205, 0), (cx + 0.205, 0.205, 0.12), "concrete", bevel=0.02, skip=("bottom",))
        k.box((cx - 0.175, -0.175, 0.12), (cx + 0.175, 0.175, 1.04), "tech_panel", bevel=0.02)
        k.box((cx - 0.185, -0.185, 0.78), (cx + 0.185, 0.185, 0.93), "hazard_stripes", bevel=0.005)
        k.box((cx - 0.195, -0.195, 1.04), (cx + 0.195, 0.195, 1.1), "gunmetal", bevel=0.015)
    # left post: the gearbox plate the arm turns on
    k.box((-4.64, -0.212, 0.84), (-4.21, -0.175, 1.08), "gunmetal", bevel=0.01)
    # right post: the rest the arm drops into, a fork on a bracket
    k.box((4.36, -0.212, 0.8), (4.64, -0.175, 0.98), "gunmetal", bevel=0.01)
    k.box((4.14, -0.33, 0.86), (4.4, -0.19, 0.91), "rubber", bevel=0.008)
    for y0, y1 in ((-0.33, -0.315), (-0.205, -0.19)):
        k.box((4.16, y0, 0.91), (4.3, y1, 1.02), "gunmetal", bevel=0.004)
    # MerSec control box on the left post's front: keypad, label, rain hood, status light
    k.box((-4.64, 0.175, 0.5), (-4.36, 0.3, 0.76), "paint_navy", bevel=0.012)
    k.box((-4.65, 0.175, 0.76), (-4.35, 0.32, 0.775), "gunmetal", bevel=0.004)
    k.box((-4.6, 0.3, 0.7), (-4.4, 0.312, 0.745), "mersec_label", bevel=0.0)
    keypad(k, -4.54, 0.6, 0.3, 3, 2, (0.026, 0.024), (0.036, 0.034))
    st = PropKit("Status", coll, reg)
    st.box((-4.44, 0.3, 0.6), (-4.4, 0.312, 0.64), "led_red", bevel=0.0)
    posts = k.finish("Posts")
    status = st.finish("Status")

    a = PropKit("arm", coll, reg)
    a.box((-4.3, -0.3, 0.93), (4.24, -0.22, 1.07), "hazard_stripes", bevel=0.015)
    a.box((4.22, -0.31, 0.92), (4.3, -0.21, 1.08), "rubber", bevel=0.01)             # tip cap
    a.box((-4.6, -0.305, 0.9), (-4.33, -0.215, 1.1), "gunmetal", bevel=0.015)         # counterweight
    a.cyl((-4.3, -0.263, 1.0), 0.11, 0.094, "y", "gunmetal_light", segments=12)      # hub
    arm = a.finish("arm", pivot=BARRIER_PIVOT)
    arm_col = collision(coll, "Arm", [((-4.3, -0.31, 0.92), (4.3, -0.21, 1.08))], parent=arm)
    col = collision(coll, "Barrier", [((cx - 0.205, -0.205, 0), (cx + 0.205, 0.205, 1.1)) for cx in (-4.5, 4.5)])
    return [posts, status, arm, arm_col, col]


def locker(coll, reg):
    """Steel locker: louvred door on the front, a padlocked hasp, a plinth and a cap."""
    k = PropKit("Locker", coll, reg)
    k.box((-0.3, -0.25, 0), (0.3, 0.235, 0.1), "gunmetal", bevel=0.01, skip=("bottom",))
    k.box((-0.29, -0.24, 0.1), (0.29, 0.22, 1.86), "door_metal", bevel=0.015)
    k.box((-0.3, -0.25, 1.86), (0.3, 0.235, 1.9), "gunmetal", bevel=0.01)
    k.box((-0.27, 0.22, 0.13), (0.27, 0.245, 1.83), "door_metal", bevel=0.008)
    for z0 in (0.25, 1.55):                                             # vents, top and bottom
        for i in range(5):
            k.box((-0.17, 0.245, z0 + i * 0.04), (0.17, 0.257, z0 + i * 0.04 + 0.02), "gunmetal", bevel=0.0)
    k.box((0.19, 0.245, 1.0), (0.23, 0.27, 1.16), "gunmetal_light", bevel=0.006)    # pull handle
    k.box((0.17, 0.245, 0.88), (0.25, 0.257, 0.96), "gunmetal", bevel=0.003)        # hasp plate
    k.box((0.2, 0.257, 0.93), (0.22, 0.285, 0.95), "gunmetal_light", bevel=0.0)     # staple
    padlock(k, 0.21, 0.272, 0.945)
    k.box((-0.05, 0.245, 1.77), (-0.05 + 0.1, 0.257, 1.8), "brass", bevel=0.003)    # number plate
    for z in (0.4, 1.55):
        k.cyl((-0.275, 0.24, z), 0.012, 0.1, "z", "gunmetal")
    body = k.finish("Locker")
    return [body, collision(coll, "Locker", [((-0.3, -0.25, 0), (0.3, 0.25, 1.9))])]


def safe(coll, reg):
    """Heavy office safe: combination dial, three-spoke handle, hinges and a brass name plate."""
    k = PropKit("Safe", coll, reg)
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box((sx * 0.26, sy * 0.2, 0), (sx * 0.34, sy * 0.28, 0.06), "gunmetal", bevel=0.01, skip=("bottom",))
    k.box((-0.35, -0.3, 0.06), (0.35, 0.26, 0.9), "paint_safe", bevel=0.035)
    k.box((-0.29, 0.26, 0.14), (0.29, 0.29, 0.8), "paint_safe", bevel=0.015)
    k.box((-0.1, 0.26, 0.818), (0.1, 0.272, 0.852), "brass", bevel=0.004)
    k.cyl((0.0, 0.296, 0.6), 0.075, 0.012, "y", "gunmetal_light", segments=16)    # dial ring
    k.cyl((0.0, 0.316, 0.6), 0.055, 0.028, "y", "brass", segments=16)             # dial
    k.cyl((0.0, 0.34, 0.6), 0.02, 0.02, "y", "brass", segments=8)                 # dial knob
    hub = (0.0, 0.31, 0.36)
    k.cyl(hub, 0.035, 0.04, "y", "gunmetal_light", segments=12)
    for deg in (90, 210, 330):
        a = math.radians(deg)
        u = Vector((math.cos(a), 0.0, math.sin(a)))
        v = Vector((-u.z, 0.0, u.x))
        k.obox(Vector(hub) + u * 0.075 + Vector((0, 0.012, 0)), u, v, Vector((0, 1, 0)), 0.06, 0.009, -0.009, 0.009,
               "gunmetal_light")
        k.cyl(tuple(Vector(hub) + u * 0.14 + Vector((0, 0.012, 0))), 0.016, 0.03, "y", "rubber")
    for z in (0.25, 0.69):
        k.cyl((-0.295, 0.275, z), 0.022, 0.12, "z", "gunmetal", segments=10)
    body = k.finish("Safe")
    return [body, collision(coll, "Safe", [((-0.35, -0.3, 0), (0.35, 0.3, 0.9))])]


def crate(coll, reg):
    """Shipping crate: stencilled sides, steel corner angles, skids and a lid with straps."""
    k = PropKit("Crate", coll, reg)
    for sy in (-1, 1):
        k.box((-0.45, sy * 0.25, 0), (0.45, sy * 0.33, 0.05), "rust_metal", bevel=0.008, skip=("bottom",))
    k.box((-0.49, -0.39, 0.05), (0.49, 0.39, 0.62), "crate_stencil", bevel=0.01, skip=("bottom", "top"))
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box((sx * 0.44, sy * 0.34, 0.07), (sx * 0.5, sy * 0.4, 0.6), "rust_metal", bevel=0.008)
    k.box((-0.5, -0.4, 0.62), (0.5, 0.4, 0.68), "crate", bevel=0.012)
    for sx in (-1, 1):
        k.box((sx * 0.28, -0.37, 0.68), (sx * 0.36, 0.37, 0.7), "rust_metal", bevel=0.005)
    body = k.finish("Crate")
    return [body, collision(coll, "Crate", [((-0.5, -0.4, 0), (0.5, 0.4, 0.7))])]


def tool_box(coll, reg):
    """Red steel tool box: tray, lid with a ridge, two front latches and a rubber grip."""
    k = PropKit("ToolBox", coll, reg)
    k.box((-0.34, -0.165, 0), (0.34, 0.165, 0.22), "paint_red", bevel=0.012, skip=("bottom",))
    k.box((-0.35, -0.175, 0.22), (0.35, 0.175, 0.27), "paint_red", bevel=0.012)
    k.box((-0.3, -0.1, 0.27), (0.3, 0.1, 0.29), "paint_red", bevel=0.008)
    for sx in (-1, 1):
        k.box((sx * 0.175, -0.02, 0.29), (sx * 0.205, 0.02, 0.345), "gunmetal", bevel=0.004)
        k.box((sx * 0.22 - 0.025, 0.165, 0.18), (sx * 0.22 + 0.025, 0.185, 0.25), "gunmetal_light", bevel=0.004)
    k.cyl((0.0, 0.0, 0.325), 0.014, 0.4, "x", "rubber")
    body = k.finish("ToolBox")
    return [body, collision(coll, "ToolBox", [((-0.35, -0.175, 0), (0.35, 0.175, 0.35))])]


SHELF_BOARDS = (0.12, 0.7, 1.28)       # top of each stocked shelf board, metres
# Stock per board: ("box", x0, x1, depth, height, material) with its back against the back
# panel, or ("bottle", x, radius, height, material, cap material) standing at y = 0.
SHELF_STOCK = (
    (("box", -0.74, -0.46, 0.3, 0.26, "cardboard"), ("box", -0.44, -0.2, 0.28, 0.2, "cardboard"),
     ("box", -0.18, 0.1, 0.32, 0.3, "cardboard"), ("box", 0.12, 0.4, 0.25, 0.18, "box_blue"),
     ("box", 0.44, 0.74, 0.3, 0.24, "cardboard")),
    (("box", -0.74, -0.62, 0.14, 0.18, "white_plastic"), ("box", -0.6, -0.48, 0.15, 0.2, "box_blue"),
     ("box", -0.46, -0.34, 0.13, 0.15, "white_plastic"), ("bottle", -0.27, 0.035, 0.14, "bottle_amber", "white_plastic"),
     ("bottle", -0.18, 0.035, 0.14, "bottle_amber", "white_plastic"), ("box", -0.1, 0.16, 0.16, 0.12, "box_green"),
     ("box", 0.18, 0.36, 0.2, 0.22, "white_plastic"), ("bottle", 0.46, 0.04, 0.18, "white_plastic", "shell_red"),
     ("bottle", 0.56, 0.04, 0.18, "white_plastic", "shell_red"), ("bottle", 0.66, 0.04, 0.18, "white_plastic", "shell_red")),
    (("bottle", -0.7, 0.03, 0.12, "bottle_amber", "white_plastic"), ("bottle", -0.62, 0.03, 0.12, "bottle_amber", "white_plastic"),
     ("bottle", -0.54, 0.03, 0.12, "bottle_amber", "white_plastic"), ("box", -0.46, -0.2, 0.18, 0.16, "box_green"),
     ("box", -0.16, 0.08, 0.16, 0.24, "white_plastic"), ("box", 0.12, 0.3, 0.14, 0.14, "box_blue"),
     ("bottle", 0.42, 0.06, 0.2, "white_plastic", "box_blue"), ("box", 0.52, 0.74, 0.2, 0.18, "cardboard")),
)


def shelf(coll, reg):
    """Pharmacy shelving: steel sides and back, three stocked boards with price rails, a toe kick
    and a header with a green cross."""
    k = PropKit("Shelf", coll, reg)
    for sx in (-1, 1):
        k.box((sx * 0.8, -0.225, 0), (sx * 0.775, 0.225, 1.9), "door_metal", bevel=0.006)
    k.box((-0.775, -0.225, 0.02), (0.775, -0.21, 1.88), "door_metal", bevel=0.0)
    k.box((-0.775, -0.21, 0), (0.775, 0.19, 0.095), "gunmetal", bevel=0.006, skip=("bottom",))
    k.box((-0.775, -0.21, 1.86), (0.775, 0.215, 1.88), "door_metal", bevel=0.004)
    k.box((-0.775, 0.19, 1.72), (0.775, 0.225, 1.86), "white_plastic", bevel=0.006)          # header
    k.box((-0.02, 0.225, 1.735), (0.02, 0.237, 1.845), "box_green", bevel=0.0)              # cross
    for sx in (-1, 1):
        k.box((sx * 0.02, 0.225, 1.77), (sx * 0.055, 0.237, 1.81), "box_green", bevel=0.0)
    for top, stock in zip(SHELF_BOARDS, SHELF_STOCK):
        k.box((-0.775, -0.21, top - 0.025), (0.775, 0.215, top), "door_metal", bevel=0.004)
        k.box((-0.775, 0.215, top - 0.05), (0.775, 0.24, top + 0.015), "white_plastic", bevel=0.0)
        for item in stock:
            if item[0] == "box":
                _, x0, x1, d, h, mat = item
                k.box((x0, -0.2, top), (x1, -0.2 + d, top + h), mat, bevel=0.0, skip=("bottom",))
            else:
                _, x, r, h, mat, cap = item
                k.cyl((x, 0.0, top + h * 0.4), r, h * 0.8, "z", mat, segments=6)
                k.cyl((x, 0.0, top + h * 0.9), r * 0.6, h * 0.2, "z", cap, segments=6)
    body = k.finish("Shelf")
    return [body, collision(coll, "Shelf", [((-0.8, -0.225, 0), (0.8, 0.225, 1.9))])]


def offering_box(coll, reg):
    """Red-lacquered shrine offering box on black legs: a coin slot in the top, a brass lock
    plate and corner fittings on the front."""
    k = PropKit("OfferingBox", coll, reg)
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box((sx * 0.2, sy * 0.15, 0), (sx * 0.155, sy * 0.105, 0.5), "lacquer_black", bevel=0.006,
                  skip=("bottom",))
    k.box((-0.19, -0.14, 0.42), (0.19, 0.14, 0.49), "lacquer_black", bevel=0.006)          # apron
    k.box((-0.24, -0.19, 0.5), (0.24, 0.19, 0.84), "lacquer_red", bevel=0.01)
    k.box((-0.25, 0.0125, 0.84), (0.25, 0.2, 0.9), "lacquer_red", bevel=0.01)              # lid, front half
    k.box((-0.25, -0.2, 0.84), (0.25, -0.0125, 0.9), "lacquer_red", bevel=0.01)            # lid, back half
    for sx in (-1, 1):
        k.box((sx * 0.14, -0.0125, 0.84), (sx * 0.25, 0.0125, 0.9), "lacquer_red", bevel=0.0)  # slot ends
    k.box((-0.14, -0.0125, 0.84), (0.14, 0.0125, 0.852), "rubber", bevel=0.0)             # slot, dark inside
    k.box((-0.05, 0.19, 0.6), (0.05, 0.202, 0.74), "brass", bevel=0.004)                  # lock plate
    k.box((-0.009, 0.202, 0.64), (0.009, 0.212, 0.69), "rubber", bevel=0.0)               # keyhole
    for sx in (-1, 1):
        for z0 in (0.51, 0.79):
            k.box((sx * 0.19, 0.19, z0), (sx * 0.23, 0.202, z0 + 0.04), "brass", bevel=0.003)
    body = k.finish("OfferingBox")
    return [body, collision(coll, "OfferingBox", [((-0.25, -0.2, 0), (0.25, 0.2, 0.9))])]


def stash_box(coll, reg):
    """Small battered metal box: ribbed lid, end handles, a carry handle and a front latch."""
    k = PropKit("StashBox", coll, reg)
    k.box((-0.27, -0.18, 0), (0.27, 0.18, 0.27), "rust_metal", bevel=0.015, skip=("bottom",))
    k.box((-0.28, -0.19, 0.27), (0.28, 0.19, 0.315), "paint_grimy", bevel=0.012)
    for x in (-0.16, 0.16):
        k.box((x - 0.02, -0.17, 0.315), (x + 0.02, 0.17, 0.325), "paint_grimy", bevel=0.004)
    for sx in (-1, 1):
        k.box((sx * 0.27, -0.07, 0.15), (sx * 0.285, 0.07, 0.23), "gunmetal", bevel=0.003)
        k.cyl((sx * 0.292, 0.0, 0.2), 0.009, 0.12, "y", "gunmetal_light")
        k.box((sx * 0.07, -0.015, 0.315), (sx * 0.1, 0.015, 0.345), "gunmetal", bevel=0.003)
    k.cyl((0.0, 0.0, 0.338), 0.009, 0.2, "x", "rubber")
    k.box((-0.03, 0.18, 0.22), (0.03, 0.2, 0.3), "gunmetal_light", bevel=0.004)
    body = k.finish("StashBox")
    return [body, collision(coll, "StashBox", [((-0.3, -0.2, 0), (0.3, 0.2, 0.35))])]


TERM_C = Vector((0.0, 0.0, 0.92))        # foot of the terminal's sloped face (y, z)
TERM_D = Vector((0.0, -0.16, 1.19))      # its top


def terminal(coll, reg):
    """Standing console: plinth, pedestal with a vented access panel, keyboard ledge, and a head
    whose screen slopes back to face +Y and up, under a visor. The screen is its own object."""
    k = PropKit("Terminal", coll, reg)
    k.box((-0.35, -0.25, 0), (0.35, 0.2, 0.07), "gunmetal", bevel=0.015, skip=("bottom",))
    k.box((-0.28, -0.22, 0.07), (0.28, 0.1, 0.84), "tech_panel", bevel=0.02)
    k.box((-0.18, 0.1, 0.2), (0.18, 0.112, 0.66), "gunmetal", bevel=0.004)
    for i in range(4):
        k.box((-0.13, 0.112, 0.46 + i * 0.04), (0.13, 0.124, 0.48 + i * 0.04), "gunmetal_light", bevel=0.0)
    k.box((-0.33, -0.2, 0.84), (0.33, 0.25, 0.88), "gunmetal", bevel=0.01)                 # ledge
    k.box((-0.25, 0.04, 0.88), (0.25, 0.22, 0.9), "gunmetal", bevel=0.004)                 # keyboard
    for r in range(4):
        for c in range(3):
            x0 = -0.225 + c * 0.15
            k.box((x0, 0.055 + r * 0.04, 0.9), (x0 + 0.14, 0.08 + r * 0.04, 0.912), "white_plastic", bevel=0.0)
    head = [(x, y, z) for x in (-0.32, 0.32) for y, z in ((-0.25, 0.88), (0.0, 0.88), (TERM_C.y, TERM_C.z),
                                                          (TERM_D.y, TERM_D.z), (-0.25, 1.19))]
    k.hull(head, "tech_panel", bevel=0.012)
    k.box((-0.335, -0.25, 1.19), (0.335, -0.1, 1.25), "tech_panel", bevel=0.012)            # visor
    k.cyl((0.18, -0.235, 0.475), 0.014, 0.81, "z", "rubber")                               # conduit
    # the screen bezel: four bars standing 2 cm off the slope around a recessed screen
    d = (TERM_D - TERM_C).normalized()            # up the slope
    n = Vector((0.0, d.z, -d.y))                   # out of it: toward +Y and up
    x_ax = Vector((1.0, 0.0, 0.0))
    t0, t1 = 0.04, 0.04 + SCREEN_H
    hw = SCREEN_W / 2

    def on_slope(t, x=0.0):
        return Vector((x, TERM_C.y, TERM_C.z)) + d * t

    k.obox(on_slope((0.012 + t0) / 2), x_ax, d, n, hw + 0.04, (t0 - 0.012) / 2, 0.0, 0.02, "gunmetal")
    k.obox(on_slope((t1 + 0.3) / 2), x_ax, d, n, hw + 0.04, (0.3 - t1) / 2, 0.0, 0.02, "gunmetal")
    for s in (-1, 1):
        k.obox(on_slope((t0 + t1) / 2, s * (hw + 0.02)), x_ax, d, n, 0.02, SCREEN_H / 2, 0.0, 0.02, "gunmetal")
    sc = PropKit("Screen", coll, reg)
    sc.obox(on_slope((t0 + t1) / 2), x_ax, d, n, hw, SCREEN_H / 2, 0.0, 0.008, "terminal_screen")
    body = k.finish("Terminal")
    screen = sc.finish("Screen")
    return [body, screen, collision(coll, "Terminal", [((-0.35, -0.25, 0), (0.35, 0.25, 1.25))])]


def wall_panel(coll, reg):
    """Wall-mounted access panel (lift call, gate control). Origin: the centre of its back face,
    which mounts flush on the wall; the front faces +Y."""
    k = PropKit("Panel", coll, reg)
    k.box((-0.16, 0, -0.225), (0.16, 0.02, 0.225), "gunmetal", bevel=0.006)
    k.box((-0.15, 0.02, -0.21), (0.15, 0.1, 0.21), "tech_panel", bevel=0.015)
    k.box((-0.05, 0.1, 0.125), (0.05, 0.11, 0.18), "gunmetal", bevel=0.003)              # light bezel
    k.box((-0.085, 0.1, -0.16), (0.085, 0.11, 0.08), "gunmetal", bevel=0.003)            # keypad plate
    keypad(k, 0.0, -0.045, 0.11, 3, 4, (0.038, 0.034), (0.05, 0.048))
    k.box((-0.14, 0.1, -0.2), (0.14, 0.11, -0.175), "hazard_stripes", bevel=0.0)
    st = PropKit("Status", coll, reg)
    st.box((-0.03, 0.11, 0.14), (0.03, 0.122, 0.165), "led_amber", bevel=0.0)
    body = k.finish("Panel")
    status = st.finish("Status")
    return [body, status, collision(coll, "Panel", [((-0.16, 0, -0.225), (0.16, 0.1, 0.225))])]


def gate(coll, reg):
    """Barred storm-drain gate: posts, rails, flat straps and round bars, with a keypad lock box
    on its right side as the player faces it (-X)."""
    k = PropKit("Gate", coll, reg)
    for sx in (-1, 1):
        k.box((sx * 1.08, -0.06, 0), (sx * 1.2, 0.06, 2.2), "rust_metal", bevel=0.015)
    for z0, z1 in ((0.03, 0.15), (2.05, 2.17)):
        k.box((-1.08, -0.05, z0), (1.08, 0.05, z1), "rust_metal", bevel=0.012)
    for z0 in (0.7, 1.4):
        k.box((-1.08, -0.035, z0), (1.08, 0.035, z0 + 0.06), "rust_metal", bevel=0.006)
    for i in range(13):
        k.cyl((-0.9 + i * 0.15, 0.0, 1.1), 0.018, 1.9, "z", "rust_metal", caps=False)
    k.box((-1.17, 0.06, 0.95), (-0.93, 0.15, 1.3), "tech_panel", bevel=0.012)             # lock box
    k.box((-1.11, 0.15, 1.0), (-0.99, 0.16, 1.2), "gunmetal", bevel=0.003)
    keypad(k, -1.05, 1.1, 0.16, 3, 4, (0.026, 0.026), (0.035, 0.035))
    k.box((-0.93, 0.03, 1.08), (-0.85, 0.1, 1.14), "gunmetal_light", bevel=0.004)         # bolt
    st = PropKit("Status", coll, reg)
    st.box((-1.07, 0.15, 1.23), (-1.03, 0.162, 1.26), "led_red", bevel=0.0)
    body = k.finish("Gate")
    status = st.finish("Status")
    return [body, status, collision(coll, "Gate", [((-1.2, -0.06, 0), (1.2, 0.06, 2.2))])]


def grate(coll, reg):
    """Rusty outfall grate set into a canal wall, padlocked on its right side (-X). Origin: the
    bottom centre of its back face."""
    k = PropKit("Grate", coll, reg)
    for sx in (-1, 1):
        k.box((sx * 0.55, 0, 0), (sx * 0.65, 0.1, 1.3), "rust_metal", bevel=0.012)
    for z0, z1 in ((0.0, 0.1), (1.2, 1.3)):
        k.box((-0.55, 0.01, z0), (0.55, 0.09, z1), "rust_metal", bevel=0.012)
    for z0 in (0.42, 0.82):
        k.box((-0.55, 0.03, z0), (0.55, 0.07, z0 + 0.06), "rust_metal", bevel=0.006)
    for i in range(7):
        k.cyl((-0.45 + i * 0.15, 0.05, 0.65), 0.022, 1.1, "z", "rust_metal", caps=False)
    k.box((-0.63, 0.1, 0.6), (-0.47, 0.112, 0.68), "gunmetal", bevel=0.003)              # hasp over the stile
    k.box((-0.612, 0.107, 0.62), (-0.588, 0.14, 0.66), "gunmetal_light", bevel=0.0)      # staple through it
    padlock(k, -0.6, 0.125, 0.645)
    body = k.finish("Grate")
    return [body, collision(coll, "Grate", [((-0.65, 0, 0), (0.65, 0.1, 1.3))])]


def item_pouch(coll, reg):
    """Small olive canvas pouch marking a pickup: a bag that bulges at the middle, a flap over
    the top and upper front, and a leather strap down the front with a brass buckle."""
    k = PropKit("Pouch", coll, reg)
    rings = ((0.15, 0.1, 0.0), (0.17, 0.12, 0.05), (0.13, 0.08, 0.12))      # half width, half depth, height
    k.hull([(sx * hx, sy * hy, z) for hx, hy, z in rings for sx in (-1, 1) for sy in (-1, 1)], "canvas", bevel=0.02)

    def front(z):                        # the bag's front surface, y at height z (two slopes)
        if z <= 0.05:
            return 0.1 + 0.02 * z / 0.05
        return 0.12 - 0.04 * (z - 0.05) / 0.07
    k.hull([(sx * 0.14, y, z) for sx in (-1, 1) for y in (-0.09, 0.085) for z in (0.12, 0.134)], "canvas",
           bevel=0.005)                                                     # flap over the top
    k.hull([(sx * 0.15, front(z) + dy, z) for sx in (-1, 1) for z in (0.06, 0.134) for dy in (0.0, 0.012)],
           "canvas", bevel=0.004)                                           # and down the front
    for z0, z1, dy0 in ((0.0, 0.05, 0.0), (0.05, 0.1, 0.012)):             # strap, on the bag then the flap
        k.hull([(sx * 0.02, front(z) + dy, z) for sx in (-1, 1) for z in (z0, z1) for dy in (dy0, dy0 + 0.01)],
               "gun_wood")
    k.hull([(sx * 0.028, front(z) + dy, z) for sx in (-1, 1) for z in (0.052, 0.078) for dy in (0.02, 0.032)],
           "brass")                                                          # buckle
    body = k.finish("Pouch")
    return [body, collision(coll, "Pouch", [((-0.17, -0.12, 0), (0.17, 0.12, 0.14))])]


STATIC, DYNAMIC = 2, 3   # Godot's meshes/light_baking: static lightmaps, or lit by probes
# name -> (builder, light baking). Moving and vanishing props are dynamic, so no stale bake.
PROPS = {
    "door_leaf": (door_leaf, DYNAMIC),
    "barrier": (barrier, DYNAMIC),
    "locker": (locker, STATIC),
    "safe": (safe, STATIC),
    "crate": (crate, STATIC),
    "tool_box": (tool_box, STATIC),
    "shelf": (shelf, STATIC),
    "offering_box": (offering_box, STATIC),
    "stash_box": (stash_box, STATIC),
    "terminal": (terminal, STATIC),
    "wall_panel": (wall_panel, STATIC),
    "gate": (gate, STATIC),
    "grate": (grate, STATIC),
    "item_pouch": (item_pouch, DYNAMIC),
}


def triangles(objs):
    """Triangles in the drawn meshes (collision excluded)."""
    return sum(len(p.vertices) - 2 for o in objs if "-colonly" not in o.name for p in o.data.polygons)


def build(name, fn, light_baking):
    """Model one prop, check it (z-fighting, triangle budget), export its .glb and import preset."""
    coll = collection(name)
    reg = []
    objs = fn(coll, reg)
    assert_no_zfighting(name, [], props=reg)
    tris = triangles(objs)
    if tris >= MAX_TRIS:
        raise SystemExit(f"[undercity_props] {name}: {tris} triangles, over the {MAX_TRIS} budget")
    rel = f"models/undercity/props/{name}.glb"
    export(objs, os.path.join(GAME, rel))
    import_presets.write(rel, light_baking, 0.05, "res://addons/brushfire_tools/prop_import.gd")
    print(f"[undercity_props] {name}: {tris} triangles; origins "
          + ", ".join(f"{o.name} {tuple(round(v, 4) for v in o.matrix_world.translation)}" for o in objs))
    # Blender names are global: prefix this prop's objects so the next prop's "Status" or
    # "Screen" keeps its plain name in its own .glb.
    for o in objs:
        o.name = o.data.name = f"{name}:{o.name}"
    return tris


def main():
    """Textures and materials first (the previews read them), then every prop, then the .blend."""
    reset()
    bpy.context.scene.name = "UndercityProps"
    write_textures()
    write_materials()
    counts = {name: build(name, fn, gi) for name, (fn, gi) in PROPS.items()}
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True, compress=True)
    print("[undercity_props] saved", BLEND)
    print("[undercity_props] triangles:", ", ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
