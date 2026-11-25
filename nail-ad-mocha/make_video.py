"""15s 9:16 "Mocha nails" ad for Gloss Nail Bar built from two still photos.

Usage: python3 make_video.py OUT_silent.mp4
Shots cut every 2.5s on the 96 BPM music: hearts push-in, pan to the rings,
swirl set on a floating card, "1 or 2?" split screen, branded end card.
"""
import math
import os
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SEG, END = 2.5, 5.0

IMG1 = Image.open(os.path.join(HERE, "photo_hearts.jpg")).convert("RGB")   # 703x960
IMG2 = Image.open(os.path.join(HERE, "photo_swirl.jpg")).convert("RGB")    # 450x411

INTER = "/usr/share/fonts/opentype/inter/"
SERIF = "/usr/share/fonts/truetype/crosextra/"
SCRIPT = os.path.join(HERE, "..", "love-video", "fonts", "DancingScript.ttf")

def f(path, size, var=None):
    ft = ImageFont.truetype(path, size)
    if var:
        ft.set_variation_by_name(var)
    return ft

F_SCRIPT = f(SCRIPT, 128, "Bold")
F_SCRIPT_M = f(SCRIPT, 96, "Bold")
F_CAP = f(INTER + "Inter-ExtraBold.otf", 76)
F_TRACK = f(INTER + "Inter-Bold.otf", 64)
F_LOGO_S = f(SERIF + "Caladea-Bold.ttf", 50)
F_LOGO_SUB = f(INTER + "Inter-SemiBold.otf", 17)
F_LOGO_L = f(SERIF + "Caladea-Bold.ttf", 170)
F_SUB_L = f(INTER + "Inter-SemiBold.otf", 34)
F_ITAL = f(SCRIPT, 84, "SemiBold")
F_SMALL = f(INTER + "Inter-SemiBold.otf", 30)
F_PHONE = f(INTER + "Inter-Bold.otf", 92)
F_NUM = f(INTER + "Inter-ExtraBold.otf", 64)

CREAM = (252, 244, 236)
GOLD = (232, 184, 109)
BLUSH = (246, 196, 190)
MOCHA = (58, 38, 32)

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3

def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)

def clamp01(x):
    return min(max(x, 0.0), 1.0)

def view(img, cx, cy, vh, size=(W, H)):
    """Render a window of height vh (image px) centred at cx,cy into `size`."""
    ow, oh = size
    vw = vh * ow / oh
    cx = min(max(cx, vw / 2), img.width - vw / 2)
    cy = min(max(cy, vh / 2), img.height - vh / 2)
    s = oh / vh
    return img.transform(size, Image.AFFINE, (1 / s, 0, cx - vw / 2, 0, 1 / s, cy - vh / 2),
                         resample=Image.BICUBIC)

def sharpen(img):
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))

def warm(img):
    a = np.asarray(img, dtype=np.float32)
    a = a * np.array([1.03, 1.0, 0.96]) + np.array([4, 1, 0])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def blurred_bg(img, dim=0.55, tint=MOCHA):
    b = img.resize((54, 96), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4))
    b = b.resize((W, H), Image.BICUBIC)
    return Image.blend(b, Image.new("RGB", (W, H), tint), 1 - dim)

# bottom/top gradient for legible captions
grad = Image.new("L", (1, H))
for y in range(H):
    v = 0
    if y > H * 0.58:
        v = int(225 * ((y - H * 0.58) / (H * 0.42)) ** 1.3)
    if y < 220:
        v = max(v, int(150 * (1 - y / 220)))
    grad.putpixel((0, y), v)
GRAD = grad.resize((W, H))
SHADE = Image.new("RGB", (W, H), (25, 14, 10))

def spaced(d, xy, text, ft, fill, sp):
    ws = [d.textlength(c, font=ft) for c in text]
    x = xy[0] - (sum(ws) + sp * (len(text) - 1)) / 2
    for c, w in zip(text, ws):
        d.text((x, xy[1]), c, font=ft, fill=fill)
        x += w + sp

BRAND = Image.new("RGBA", (W, H), (0, 0, 0, 0))
bd = ImageDraw.Draw(BRAND)
spaced(bd, (W / 2, 70), "GLOSS", F_LOGO_S, CREAM + (255,), 9)
spaced(bd, (W / 2, 132), "NAIL BAR", F_LOGO_SUB, CREAM + (210,), 8)

# twinkling sparkles (echo the rhinestones on the nails)
def star_sprite(sz):
    S = sz * 4
    im = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(im)
    c = S / 2
    d.polygon([(c, 0), (c + S * 0.07, c - S * 0.07), (S, c), (c + S * 0.07, c + S * 0.07),
               (c, S), (c - S * 0.07, c + S * 0.07), (0, c), (c - S * 0.07, c - S * 0.07)], fill=255)
    im = im.resize((sz, sz), Image.LANCZOS)
    glow = im.filter(ImageFilter.GaussianBlur(sz / 5))
    a = Image.fromarray(np.maximum(np.asarray(im), (np.asarray(glow) * 0.8).astype(np.uint8)))
    out = Image.new("RGBA", (sz, sz), (255, 240, 215, 0))
    out.putalpha(a)
    return out

rng = np.random.default_rng(4)
SPARKS = [dict(x=rng.uniform(60, W - 60), y=rng.uniform(250, H * 0.72), sz=int(rng.uniform(22, 54)),
               ph=rng.uniform(0, 6.28), sp=rng.uniform(2.0, 4.0)) for _ in range(14)]
for s in SPARKS:
    s["spr"] = star_sprite(s["sz"])

def sparkles(fr, t, amount=1.0):
    for s in SPARKS:
        a = max(0.0, math.sin(t * s["sp"] + s["ph"])) ** 3 * 0.85 * amount
        if a < 0.03:
            continue
        spr = s["spr"].copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * a)))
        fr.alpha_composite(spr, (int(s["x"] - s["sz"] / 2), int(s["y"] - s["sz"] / 2)))

def text_in(fr, t, t0, fn, rise=34, fade=0.4):
    k = ease((t - t0) / fade)
    if k <= 0:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fn(ImageDraw.Draw(layer), (1 - k) * rise)
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * k)))
    fr.alpha_composite(layer)

def shadow_text(d, xy, txt, ft, fill, anchor="mm", sh=130):
    d.text((xy[0] + 3, xy[1] + 5), txt, font=ft, fill=(20, 8, 4, sh), anchor=anchor)
    d.text(xy, txt, font=ft, fill=fill + (255,), anchor=anchor)

def mixed_line(d, y, parts, ft, sh=130):
    total = sum(d.textlength(p, font=ft) for p, _ in parts)
    x = (W - total) / 2
    for p, col in parts:
        d.text((x + 3, y + 5), p, font=ft, fill=(20, 8, 4, sh), anchor="lm")
        d.text((x, y), p, font=ft, fill=col + (255,), anchor="lm")
        x += d.textlength(p, font=ft)

def finish(fr_rgb, t_in_shot, cut=True):
    fr = Image.composite(SHADE, fr_rgb, GRAD)
    if cut and t_in_shot < 0.12:
        fr = Image.blend(fr, Image.new("RGB", (W, H), (255, 244, 236)), 0.45 * (1 - t_in_shot / 0.12))
    return fr.convert("RGBA")

enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
     "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
     "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)

def emit(fr):
    enc.stdin.write(fr.convert("RGB").tobytes())

I1 = warm(IMG1)
I2 = warm(IMG2)
I2_BIG = sharpen(I2.resize((I2.width * 3, I2.height * 3), Image.LANCZOS))
I1_BIG = sharpen(I1.resize((I1.width * 2, I1.height * 2), Image.LANCZOS))
n = int(SEG * FPS)
T = 0.0

# ---- shot 1: push in on the heart nails ----
for i in range(n):
    t = i / FPS
    e = smooth(t / SEG)
    fr = finish(sharpen(view(I1_BIG, 2 * (352 - 70 * e), 2 * (480 - 10 * e), 2 * (960 - 220 * e))),
                t, cut=False)
    sparkles(fr, T + t, 0.8)
    fr.alpha_composite(BRAND)
    text_in(fr, t, 0.1, lambda d, dy: shadow_text(d, (W / 2, 1500 + dy), "Fall in love", F_SCRIPT, CREAM))
    text_in(fr, t, 0.45, lambda d, dy: spaced(d, (W / 2, 1600 + dy), "WITH MOCHA NAILS", F_TRACK,
                                                GOLD + (255,), 6))
    emit(fr)
T += SEG

# ---- shot 2: pan from the hearts to the gold rings ----
for i in range(n):
    t = i / FPS
    e = smooth(t / SEG)
    fr = finish(view(I1_BIG, 2 * (270 + 215 * e), 2 * (520 - 150 * e), 2 * (620 - 50 * e)), t)
    sparkles(fr, T + t, 1.0)
    fr.alpha_composite(BRAND)
    text_in(fr, t, 0.15, lambda d, dy: mixed_line(d, 1545 + dy, [("Heart ", CREAM), ("line art.", BLUSH)], F_CAP))
    text_in(fr, t, 0.4, lambda d, dy: mixed_line(d, 1645 + dy, [("Tiny ", CREAM), ("sparkles.", GOLD)], F_CAP))
    emit(fr)
T += SEG

# ---- shot 3: swirl set on a floating card ----
BG2 = blurred_bg(I2, 0.6)
CARD_W = 960
CARD_H = int(CARD_W * I2.height / I2.width)        # ~877
cmask = Image.new("L", (CARD_W, CARD_H), 0)
ImageDraw.Draw(cmask).rounded_rectangle((0, 0, CARD_W - 1, CARD_H - 1), radius=44, fill=255)
cshadow = Image.new("RGBA", (CARD_W + 120, CARD_H + 120), (0, 0, 0, 0))
ImageDraw.Draw(cshadow).rounded_rectangle((60, 75, CARD_W + 60, CARD_H + 75), radius=44, fill=(0, 0, 0, 160))
cshadow = cshadow.filter(ImageFilter.GaussianBlur(26))
for i in range(n):
    t = i / FPS
    e = smooth(t / SEG)
    fr = finish(BG2, t)
    k = ease(t / 0.5)
    vh = I2_BIG.height / (1.0 + 0.08 * e)
    card = view(I2_BIG, I2_BIG.width / 2 + 40 * e, I2_BIG.height / 2, vh, (CARD_W, CARD_H))
    cy = 300 + int((1 - k) * 80)
    fr.alpha_composite(cshadow, ((W - CARD_W) // 2 - 60, cy - 60))
    fr.paste(card, ((W - CARD_W) // 2, cy), cmask)
    sparkles(fr, T + t, 0.7)
    fr.alpha_composite(BRAND)
    text_in(fr, t, 0.2, lambda d, dy: shadow_text(d, (W / 2, 1400 + dy), "Chocolate swirls", F_SCRIPT_M, CREAM))
    text_in(fr, t, 0.5, lambda d, dy: spaced(d, (W / 2, 1490 + dy), "ON SOFT BLUSH", F_TRACK, BLUSH + (255,), 6))
    emit(fr)
T += SEG

# ---- shot 4: "1 or 2?" split screen ----
HALF = 900
top_src = view(I1_BIG, 2 * 330, 2 * 480, 2 * (703 * HALF / W), (W, HALF))
bot_src = view(I2_BIG, I2_BIG.width / 2, I2_BIG.height / 2, I2_BIG.width * HALF / W, (W, HALF))
BAND_Y = HALF - 60
def badge(d, cx, cy, txt):
    d.ellipse((cx - 50, cy - 50, cx + 50, cy + 50), fill=GOLD + (255,))
    d.text((cx, cy - 2), txt, font=F_NUM, fill=MOCHA + (255,), anchor="mm")
for i in range(n):
    t = i / FPS
    fr = Image.new("RGBA", (W, H), MOCHA + (255,))
    kt, kb = ease(t / 0.45), ease((t - 0.12) / 0.45)
    fr.paste(top_src, (int(-(1 - kt) * W), 0))
    fr.paste(bot_src, (int((1 - kb) * W), H - HALF))
    if t < 0.12:
        fr = Image.alpha_composite(fr, Image.new("RGBA", (W, H), (255, 244, 236, int(115 * (1 - t / 0.12)))))
    # centre band
    bk = ease((t - 0.3) / 0.4)
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bdd = ImageDraw.Draw(band)
    bdd.rectangle((0, BAND_Y, W, H - HALF + 60), fill=MOCHA + (int(240 * bk),))
    fr.alpha_composite(band)
    text_in(fr, t, 0.4, lambda d, dy: shadow_text(d, (W / 2, 925 + dy), "Which set is you?", F_SCRIPT_M, CREAM))
    text_in(fr, t, 0.7, lambda d, dy: spaced(d, (W / 2, 1000 + dy), "COMMENT 1 OR 2", F_SMALL, GOLD + (255,), 7))
    text_in(fr, t, 0.55, lambda d, dy: badge(d, 110, 110 + dy, "1"), rise=0)
    text_in(fr, t, 0.75, lambda d, dy: badge(d, W - 110, H - 110 - dy, "2"), rise=0)
    emit(fr)
T += SEG

# ---- end card ----
BGE = blurred_bg(I2, 0.35)
WIN_W, WIN_H = 520, 660
oval = Image.new("L", (WIN_W, WIN_H), 0)
ImageDraw.Draw(oval).ellipse((0, 0, WIN_W - 1, WIN_H - 1), fill=255)
oval = oval.filter(ImageFilter.GaussianBlur(1.2))
ring = Image.new("RGBA", (WIN_W + 28, WIN_H + 28), (0, 0, 0, 0))
ImageDraw.Draw(ring).ellipse((2, 2, WIN_W + 25, WIN_H + 25), outline=GOLD + (235,), width=4)
for i in range(int(END * FPS)):
    t = i / FPS
    fr = BGE.convert("RGBA")
    if t < 0.2:
        fr = Image.alpha_composite(fr, Image.new("RGBA", (W, H), (255, 244, 236, int(170 * (1 - t / 0.2)))))
    k = ease(t / 0.6)
    sc = 0.85 + 0.15 * k
    ww, wh = int(WIN_W * sc), int(WIN_H * sc)
    win = view(I1_BIG, 2 * 300, 2 * 470, 2 * (560 - 40 * t / END), (ww, wh))
    m = oval.resize((ww, wh)).point(lambda v: int(v * k))
    wy = 230 + (WIN_H - wh) // 2
    fr.paste(win, ((W - ww) // 2, wy), m)
    r = ring.resize((ww + 28, wh + 28))
    r.putalpha(r.getchannel("A").point(lambda v: int(v * k)))
    fr.alpha_composite(r, ((W - ww) // 2 - 14, wy - 14))
    sparkles(fr, T + t, 0.6)
    text_in(fr, t, 0.35, lambda d, dy: spaced(d, (W / 2, 950 + dy), "GLOSS", F_LOGO_L, CREAM + (255,), 20))
    text_in(fr, t, 0.55, lambda d, dy: spaced(d, (W / 2, 1140 + dy), "NAIL BAR", F_SUB_L, GOLD + (255,), 16))
    text_in(fr, t, 0.85, lambda d, dy: d.text((W / 2, 1250 + dy), "Mocha Collection", font=F_ITAL,
                                                fill=CREAM + (255,), anchor="mm"))
    text_in(fr, t, 1.2, lambda d, dy: spaced(d, (W / 2, 1400 + dy), "CALL TO BOOK", F_SMALL, CREAM + (200,), 9))
    def phone(d, dy):
        txt = "(929) 888-8288"
        tw = d.textlength(txt, font=F_PHONE)
        x0, y0 = (W - tw) / 2 - 48, 1460 + dy
        d.rounded_rectangle((x0, y0, x0 + tw + 96, y0 + 140), radius=70, outline=GOLD + (255,), width=4)
        d.text((W / 2, y0 + 70), txt, font=F_PHONE, fill=GOLD + (255,), anchor="mm")
    text_in(fr, t, 1.4, phone)
    emit(fr)

enc.stdin.close()
enc.wait()
print("wrote", OUT)
