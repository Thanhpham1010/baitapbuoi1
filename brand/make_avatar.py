"""Instagram profile picture (1080x1080) for the nail bar, black & gold luxury style
matching the luxury video ads. Instagram crops it to a circle, so everything
important sits inside the central circle.

Usage: python3 make_avatar.py NAME OUT.png      e.g. python3 make_avatar.py GLOSS avatar.png
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

NAME, OUT = sys.argv[1].upper(), sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "love-video", "fonts")
S = 2160                      # draw at 2x, downsample for clean edges
C = S / 2

def font(path, size, var=None):
    f = ImageFont.truetype(path, size)
    if var:
        f.set_variation_by_name(var)
    return f

F_MONO = font(os.path.join(FONTS, "PlayfairDisplay.ttf"), 1000, "Regular")
F_NAME = font("/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf", 210)
F_SUB = font("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 64)

# background: deep warm black with a soft centre glow
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
r = np.sqrt((xx - C) ** 2 + (yy - C * 0.92) ** 2) / (S * 0.6)
bg = np.stack([np.clip(30 - 22 * r, 8, 30), np.clip(24 - 18 * r, 6, 24), np.clip(18 - 13 * r, 5, 18)], -1)
img = Image.fromarray(bg.astype(np.uint8)).convert("RGBA")

# gold gradient fill (diagonal, with a bright "gloss" band)
t = (xx * 0.35 + yy) / (S * 1.35)
stops_p = [0.0, 0.32, 0.46, 0.58, 0.8, 1.0]
stops_c = np.array([[176, 132, 66], [232, 196, 128], [255, 241, 204], [222, 182, 110],
                    [188, 144, 74], [236, 204, 140]], np.float32)
gold = np.stack([np.interp(t, stops_p, stops_c[:, c]) for c in range(3)], -1)
GOLD = Image.fromarray(gold.astype(np.uint8)).convert("RGBA")

def gold_draw(fn, glow=0):
    m = Image.new("L", (S, S), 0)
    fn(ImageDraw.Draw(m))
    if glow:
        g = Image.new("RGBA", (S, S), (230, 180, 100, 255))
        g.putalpha(m.filter(ImageFilter.GaussianBlur(glow)).point(lambda v: int(v * 0.35)))
        img.alpha_composite(g)
    layer = GOLD.copy()
    layer.putalpha(m)
    img.alpha_composite(layer)

def tracked(d, cx, cy, text, f, sp):
    ws = [d.textlength(ch, font=f) for ch in text]
    x = cx - (sum(ws) + sp * (len(text) - 1)) / 2
    for ch, w in zip(text, ws):
        d.text((x, cy), ch, font=f, fill=255, anchor="lm")
        x += w + sp

# double ring inside the circular crop
def rings(d):
    for rad, w in ((C * 0.90, 7), (C * 0.865, 3)):
        d.ellipse((C - rad, C - rad, C + rad, C + rad), outline=255, width=w)
gold_draw(rings)

# monogram G
gold_draw(lambda d: d.text((C, C * 0.80), NAME[0], font=F_MONO, fill=255, anchor="mm"), glow=40)

# sparkle on the monogram ("gloss" highlight)
def sparkle(d, cx, cy, s):
    k = 0.12 * s
    d.polygon([(cx, cy - s), (cx + k, cy - k), (cx + s, cy), (cx + k, cy + k),
               (cx, cy + s), (cx - k, cy + k), (cx - s, cy), (cx - k, cy - k)], fill=255)
gold_draw(lambda d: (sparkle(d, C + 300, C * 0.80 - 330, 70), sparkle(d, C + 395, C * 0.80 - 250, 30)), glow=20)

# name + descriptor
gold_draw(lambda d: tracked(d, C, C * 1.33, NAME, F_NAME, 40))
def sub(d):
    tracked(d, C, C * 1.53, "NAIL BAR", F_SUB, 26)
    d.rectangle((C - 70, C * 1.615, C + 70, C * 1.615 + 3), fill=255)
gold_draw(sub)

out = img.convert("RGB").resize((1080, 1080), Image.LANCZOS)
out.save(OUT, quality=95)
print("wrote", OUT)
