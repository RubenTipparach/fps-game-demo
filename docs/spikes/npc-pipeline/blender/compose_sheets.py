"""Composes contact sheets from the Godot captures (system python3 + Pillow).
usage: python3 compose_sheets.py <npc_dir>"""
import os, sys, glob
from PIL import Image, ImageDraw

NPC = sys.argv[1]
ST = os.path.join(NPC, "stills")


def sheet(paths, labels, cols, out, w=320):
    ims = [Image.open(p).convert("RGB") for p in paths]
    h = int(ims[0].height * w / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    s = Image.new("RGB", (cols * w, rows * (h + 18)), (20, 20, 24))
    d = ImageDraw.Draw(s)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * w, (i // cols) * (h + 18)
        s.paste(im.resize((w, h)), (x, y))
        d.text((x + 4, y + h + 3), lab, fill=(230, 230, 230))
    s.save(out)
    print("wrote", out)


anim = sorted(glob.glob(os.path.join(ST, "anim", "bouncer_*.png")))
if anim:
    sheet(anim, [os.path.basename(p)[8:-4] for p in anim], 4, os.path.join(ST, "04_godot_ual_clips_on_mpfb_bouncer.png"))
for eng in ("jolt60", "godot60", "jolt120", "godot120"):
    rd = sorted(glob.glob(os.path.join(ST, "ragdoll", f"{eng}_*_*.png")))
    if rd:
        sheet(rd, [os.path.basename(p)[:-4] for p in rd], 3, os.path.join(ST, f"06_ragdoll_{eng}.png"), w=480)
