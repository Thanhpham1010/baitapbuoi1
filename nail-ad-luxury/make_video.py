"""18s 9:16 luxury ad for Gloss Nail Bar (Brooklyn) from three nail photos.

Usage: python3 make_video.py OUT_silent.mp4
Black & gold editorial look: gold-gradient serif type, thin gold frame,
slow camera moves, soft dissolves on the 80 BPM bar lines (every 3s).
"""
import math
import os
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "love-video", "fonts")
W, H, FPS = 1080, 1920, 30
TOTAL = 18.0
XF = 0.7                       # dissolve length

def load(name):
    return Image.open(os.path.join(HERE, name)).convert("RGB")

def grade(img):
    a = np.asarray(img, dtype=np.float32) / 255
    lum = (a @ np.array([0.299, 0.587, 0.114]))[..., None]
    a = lum + (a - lum) * 0.9                       # slightly muted, editorial
    a = np.clip((a - 0.5) * 1.08 + 0.5, 0, 1)        # gentle contrast
    a = a * np.array([1.02, 1.0, 0.97])             # warm highlights
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

def big(img, k=2):
    return grade(img).resize((img.width * k, img.height * k), Image.LANCZOS).filter(
        ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))

EMERALD = big(load("photo_emerald.jpg"))   # 736x920 -> x2
DAISY = big(load("photo_daisy.jpg"))       # 859x1145 -> x2
BOWS = big(load("photo_bows.jpg"))         # 960x959 -> x2

def ft(path, size, var=None):
    f = ImageFont.truetype(path, size)
    if var:
        f.set_variation_by_name(var)
    return f

SERIF = "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf"
F_LOGO_XL = ft(SERIF, 190)
F_LOGO_L = ft(SERIF, 150)
F_ITAL = ft(os.path.join(FONTS, "PlayfairDisplay-Italic.ttf"), 76, "Italic")
F_ITAL_S = ft(os.path.join(FONTS, "PlayfairDisplay-Italic.ttf"), 64, "Italic")
F_PHONE = ft(os.path.join(FONTS, "PlayfairDisplay.ttf"), 78, "Regular")
F_TRACK = ft("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 30)
F_TRACK_S = ft("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 27)
F_ADDR = ft("/usr/share/fonts/opentype/inter/Inter-Regular.otf", 34)

CREAM = (247, 240, 228)
GOLD = (214, 178, 112)

# vertical gold gradient used to fill type and lines
gy = np.linspace(0, 1, H)[:, None]
stops = np.array([[250, 232, 186], [205, 160, 88], [244, 214, 150], [170, 128, 62]], np.float32)
pos = np.array([0.0, 0.45, 0.7, 1.0])
gcol = np.stack([np.interp(gy[:, 0], pos, stops[:, c]) for c in range(3)], 1)
GOLD_FILL = Image.fromarray(np.repeat(gcol[:, None, :], W, 1).astype(np.uint8))

def clamp01(x):
    return min(max(x, 0.0), 1.0)

def ease(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3

def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)

def view(img, cx, cy, vh, size=(W, H)):
    ow, oh = size
    vw = vh * ow / oh
    cx = min(max(cx, vw / 2), img.width - vw / 2)
    cy = min(max(cy, vh / 2), img.height - vh / 2)
    s = oh / vh
    return img.transform(size, Image.AFFINE, (1 / s, 0, cx - vw / 2, 0, 1 / s, cy - vh / 2),
                         resample=Image.BICUBIC)

def tracked(d, x, y, text, f, fill, sp, anchor_mid=True):
    ws = [d.textlength(c, font=f) for c in text]
    total = sum(ws) + sp * (len(text) - 1)
    x0 = x - total / 2 if anchor_mid else x
    for c, w in zip(text, ws):
        d.text((x0, y), c, font=f, fill=fill, anchor="lm")
        x0 += w + sp
    return total

def gold_layer(draw_fn, alpha=1.0):
    """draw_fn draws white shapes on an L mask; returns gold-filled RGBA layer."""
    m = Image.new("L", (W, H), 0)
    draw_fn(ImageDraw.Draw(m))
    if alpha < 1:
        m = m.point(lambda v: int(v * alpha))
    layer = GOLD_FILL.convert("RGBA")
    layer.putalpha(m)
    return layer

def cream_layer(draw_fn, alpha=1.0, color=CREAM, shadow=True):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = Image.new("L", (W, H), 0)
    draw_fn(ImageDraw.Draw(m))
    if shadow:
        sh = m.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.6 * alpha))
        s_layer = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        s_layer.putalpha(sh)
        layer.alpha_composite(s_layer, (0, 4))
    c = Image.new("RGBA", (W, H), color + (255,))
    c.putalpha(m.point(lambda v: int(v * alpha)))
    layer.alpha_composite(c)
    return layer

# ---- static overlays ----
grad = np.zeros((H, 1), np.float32)
yy = np.arange(H)
grad[:, 0] = np.clip((yy - H * 0.55) / (H * 0.45), 0, 1) ** 1.2 * 235
grad[:, 0] = np.maximum(grad[:, 0], np.clip(1 - yy / 260, 0, 1) * 120)
SHADE = Image.new("RGBA", (W, H), (8, 6, 5, 255))
SHADE.putalpha(Image.fromarray(np.repeat(grad, W, 1).astype(np.uint8)))

def frame_lines(d):
    m = 40
    d.rectangle((m, m, W - m, H - m), outline=255, width=2)
    for cx, cy in ((m, m), (W - m, m), (m, H - m), (W - m, H - m)):
        d.polygon([(cx, cy - 9), (cx + 9, cy), (cx, cy + 9), (cx - 9, cy)], fill=255)
FRAME = gold_layer(frame_lines, 0.75)

rng = np.random.default_rng(2)
GRAIN = []
for _ in range(6):
    g = rng.normal(0, 7, (H // 2, W // 2)).astype(np.float32)
    g = Image.fromarray(np.clip(g + 128, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    GRAIN.append(np.asarray(g, dtype=np.int16) - 128)

def add_grain(img, i):
    a = np.asarray(img.convert("RGB"), dtype=np.int16) + GRAIN[i % len(GRAIN)][..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def caption(fr, t, t0, small, big_lines):
    k = ease((t - t0) / 0.8)
    if k <= 0:
        return
    fr.alpha_composite(gold_layer(lambda d: tracked(d, W / 2, 1545 + (1 - k) * 20, small, F_TRACK, 255, 9), k))
    for i, line in enumerate(big_lines):
        kk = ease((t - t0 - 0.25 - 0.2 * i) / 0.8)
        if kk <= 0:
            continue
        fr.alpha_composite(cream_layer(
            lambda d, line=line, i=i: d.text((W / 2, 1640 + i * 92 + (1 - kk) * 24), line,
                                             font=F_ITAL, fill=255, anchor="mm"), kk))

# ---- shots (each returns RGBA frame for local time u in seconds) ----
def shot_intro(u):
    fr = Image.new("RGBA", (W, H), (6, 5, 4, 255))
    bg = view(EMERALD, 2 * 330, 2 * 470, 2 * (900 - 60 * u / 3)).convert("RGBA")
    bg.putalpha(int(255 * 0.28 * ease(u / 1.5)))
    fr.alpha_composite(bg)
    lk = ease((u - 0.2) / 0.9)
    if lk > 0:
        fr.alpha_composite(gold_layer(lambda d: d.rectangle(
            (W / 2 - 260 * lk, 905, W / 2 + 260 * lk, 906), fill=255)))
    k = ease((u - 0.55) / 1.1)
    if k > 0:
        sp = 22 + 30 * (1 - k)
        fr.alpha_composite(gold_layer(lambda d: tracked(d, W / 2, 790, "GLOSS", F_LOGO_XL, 255, sp), k))
    k2 = ease((u - 1.1) / 0.8)
    if k2 > 0:
        fr.alpha_composite(gold_layer(lambda d: tracked(d, W / 2, 965, "NAIL BAR", F_TRACK, 255, 16), k2))
    k3 = ease((u - 1.5) / 0.8)
    if k3 > 0:
        fr.alpha_composite(cream_layer(lambda d: d.text((W / 2, 1080), "Luxury, at your fingertips.",
                                                        font=F_ITAL_S, fill=255, anchor="mm"), k3))
    return fr

def photo_shot(img, a, b, vh0, vh1):
    def fn(u):
        e = smooth(u / 3.6)
        cx, cy = a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e
        fr = view(img, 2 * cx, 2 * cy, 2 * (vh0 + (vh1 - vh0) * e)).convert("RGBA")
        fr.alpha_composite(SHADE)
        return fr
    return fn

s_emerald = photo_shot(EMERALD, (330, 500), (300, 460), 920, 780)
s_daisy = photo_shot(DAISY, (330, 600), (540, 540), 1060, 980)
s_bows = photo_shot(BOWS, (330, 420), (620, 560), 860, 780)

ARCH_W, ARCH_H = 660, 840
arch = Image.new("L", (ARCH_W, ARCH_H), 0)
ad = ImageDraw.Draw(arch)
ad.ellipse((0, 0, ARCH_W - 1, ARCH_W - 1), fill=255)
ad.rectangle((0, ARCH_W // 2, ARCH_W - 1, ARCH_H - 1), fill=255)
ARCH = arch.filter(ImageFilter.GaussianBlur(1))
AX, AY = (W - ARCH_W) // 2, 150

def arch_outline(d, k):
    pad = 14
    x0, y0, x1, y1 = AX - pad, AY - pad, AX + ARCH_W + pad, AY + ARCH_H + pad
    r = (x1 - x0) / 2
    d.arc((x0, y0, x1, y0 + 2 * r), 180, 360, fill=255, width=3)
    d.line((x0, y0 + r, x0, y1), fill=255, width=3)
    d.line((x1, y0 + r, x1, y1), fill=255, width=3)
    d.line((x0, y1, x1, y1), fill=255, width=3)

END_IMGS = [(EMERALD, (330, 470), 720), (DAISY, (430, 560), 900), (BOWS, (480, 480), 760)]

def shot_end(u):
    fr = Image.new("RGBA", (W, H), (8, 6, 5, 255))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((W / 2 - 520, 120, W / 2 + 520, 1100), fill=60)
    gl = Image.new("RGBA", (W, H), (120, 90, 45, 255))
    gl.putalpha(glow.filter(ImageFilter.GaussianBlur(120)))
    fr.alpha_composite(gl)
    k = ease(u / 0.8)
    seg = 1.6
    idx = int(u // seg) % 3
    nxt = (idx + 1) % 3
    w_local = (u % seg)
    def win(i):
        img, c, vh = END_IMGS[i]
        return view(img, 2 * c[0], 2 * c[1], 2 * vh * (1 - 0.04 * w_local / seg), (ARCH_W, ARCH_H))
    picture = win(idx)
    if w_local > seg - 0.5:
        picture = Image.blend(picture, win(nxt), smooth((w_local - (seg - 0.5)) / 0.5))
    fr.paste(picture, (AX, AY), ARCH.point(lambda v: int(v * k)))
    fr.alpha_composite(gold_layer(lambda d: arch_outline(d, k), k))
    k1 = ease((u - 0.4) / 0.9)
    if k1 > 0:
        fr.alpha_composite(gold_layer(lambda d: tracked(d, W / 2, 1110 + (1 - k1) * 20, "GLOSS",
                                                        F_LOGO_L, 255, 22), k1))
    k2 = ease((u - 0.7) / 0.8)
    if k2 > 0:
        fr.alpha_composite(gold_layer(lambda d: (tracked(d, W / 2, 1235, "NAIL BAR", F_TRACK, 255, 16),
                                                 d.rectangle((W / 2 - 60, 1290, W / 2 + 60, 1291), fill=255)), k2))
    k3 = ease((u - 1.1) / 0.8)
    if k3 > 0:
        fr.alpha_composite(cream_layer(lambda d: tracked(d, W / 2, 1350, "BOOK YOUR APPOINTMENT",
                                                         F_TRACK_S, 255, 7), k3 * 0.85, shadow=False))
        fr.alpha_composite(cream_layer(lambda d: d.text((W / 2, 1440), "(929) 888-8288", font=F_PHONE,
                                                        fill=255, anchor="mm"), k3))
    k4 = ease((u - 1.5) / 0.8)
    if k4 > 0:
        fr.alpha_composite(gold_layer(lambda d: d.text((W / 2, 1545), "3 Flushing Ave  ·  Brooklyn, NY 11205",
                                                       font=F_ADDR, fill=255, anchor="mm"), k4))
    return fr

SHOTS = [  # (start, end, fn, caption)
    (0.0, 3.0, shot_intro, None),
    (3.0, 6.0, s_emerald, ("THE ART OF DETAIL", ["Emerald & gold,", "painted to perfection."])),
    (6.0, 9.0, s_daisy, ("MODERN FRENCH", ["Effortlessly chic."])),
    (9.0, 12.0, s_bows, ("COUTURE DETAILS", ["Pearls, bows", "& a little sparkle."])),
    (12.0, 18.0, shot_end, None),
]

def render_shot(k, t):
    s0, s1, fn, cap = SHOTS[k]
    u = t - s0 + XF / 2
    fr = fn(u)
    if cap:
        caption(fr, u, 0.75, cap[0], cap[1])
        out = 1 - clamp01((t - (s1 - XF / 2 - 0.3)) / 0.4)
        if out < 1:  # fade captions just before the dissolve
            base = fn(u)
            fr = Image.blend(base, fr, out)
    return fr

enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
     "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "26",
     "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)

for i in range(int(TOTAL * FPS)):
    t = i / FPS
    k = max(j for j, s in enumerate(SHOTS) if s[0] <= t)
    fr = render_shot(k, t)
    # dissolve into the next shot around each boundary
    if k + 1 < len(SHOTS) and t > SHOTS[k][1] - XF / 2:
        fr = Image.blend(fr, render_shot(k + 1, t), smooth((t - (SHOTS[k][1] - XF / 2)) / XF))
    elif k > 0 and t < SHOTS[k][0] + XF / 2:
        fr = Image.blend(render_shot(k - 1, t), fr, smooth((t - (SHOTS[k][0] - XF / 2)) / XF))
    fr = fr.copy()
    fr.alpha_composite(FRAME)
    if t > TOTAL - 0.9:
        fr = Image.alpha_composite(fr, Image.new("RGBA", (W, H), (0, 0, 0, int(255 * smooth((t - TOTAL + 0.9) / 0.9)))))
    enc.stdin.write(add_grain(fr, i).tobytes())

enc.stdin.close()
enc.wait()
print("wrote", OUT)
