"""Romantic 9:16 edit: polaroid title -> graded footage with Vietnamese subtitles
and floating hearts -> polaroid memory collage.

Usage: python3 make_video.py SOURCE.mp4 OUT_silent.mp4
"""
import math
import os
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SW, SH = 720, 1280
INTRO, FOOT, OUTRO = 3.2, 9.8, 9.4
TOTAL = INTRO + FOOT + OUTRO

def fnt(name, size, var=None):
    f = ImageFont.truetype(os.path.join(HERE, "fonts", name), size)
    if var:
        f.set_variation_by_name(var)
    return f

F_SCRIPT_XL = fnt("DancingScript.ttf", 132, "Bold")
F_SCRIPT_L = fnt("DancingScript.ttf", 104, "SemiBold")
F_SCRIPT_S = fnt("DancingScript.ttf", 46, "Bold")
F_SUB = fnt("PlayfairDisplay-Italic.ttf", 68, "SemiBold Italic")
F_SMALL = fnt("PlayfairDisplay.ttf", 30, "Regular")

CREAM = (255, 246, 240)
ROSE = (255, 170, 190)

def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3

def ease_back(x):
    x = min(max(x, 0.0), 1.0)
    c = 1.4
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def clamp01(x):
    return min(max(x, 0.0), 1.0)

def still(t):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", SRC, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombuffer("RGB", (SW, SH), b, "raw", "RGB", 0, 1)

def frames(start, dur):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", SRC,
                          "-vf", f"fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = SW * SH * 3
    last = None
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        last = Image.frombuffer("RGB", (SW, SH), b, "raw", "RGB", 0, 1)
        yield last
    while last is not None:   # pad if the source runs short
        yield last

def fill(img, z=1.0, cx=SW / 2, cy=SH / 2):
    s = W / SW * z
    data = (1 / s, 0, cx - W / s / 2, 0, 1 / s, cy - H / s / 2)
    return img.transform((W, H), Image.AFFINE, data, resample=Image.BICUBIC)

# ---------- color grade ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.62)) ** 2)
VIG = np.clip(1.08 - 0.55 * r ** 2.2, 0.35, 1.0)[..., None]

def grade(img, glow=0.32):
    a = np.asarray(img, dtype=np.float32) / 255
    g = img.resize((W // 10, H // 10), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4))
    g = np.asarray(g.resize((W, H), Image.BILINEAR), dtype=np.float32) / 255
    a = 1 - (1 - a) * (1 - g * glow)                       # screen bloom
    a = a * np.array([1.06, 0.99, 0.93]) + np.array([0.02, 0.0, 0.025])  # warm, rosy shadows
    a = a ** 1.05
    a *= VIG
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

def dreamy_bg(img, z, dim=0.55):
    small = fill(img, z).resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
    b = np.asarray(small.resize((W, H), Image.BICUBIC), dtype=np.float32)
    b = b * dim * np.array([1.05, 0.92, 1.0]) * VIG
    return Image.fromarray(np.clip(b, 0, 255).astype(np.uint8))

# ---------- hearts ----------
def heart_sprite(size, color, alpha):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    pts = []
    for k in range(120):
        t = 2 * math.pi * k / 120
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((S / 2 + x * S / 40, S / 2 - y * S / 40 - S * 0.04))
    ImageDraw.Draw(im).polygon(pts, fill=color + (alpha,))
    im = im.resize((size, size), Image.LANCZOS)
    glow = im.filter(ImageFilter.GaussianBlur(size / 6))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(im)
    return out

rng = np.random.default_rng(11)
HCOL = [(255, 150, 175), (255, 205, 215), (255, 120, 150), (255, 230, 235)]
HEARTS = []
for i in range(34):
    size = int(rng.uniform(22, 60))
    HEARTS.append(dict(
        spr=heart_sprite(size, HCOL[i % 4], 255), size=size,
        x=rng.uniform(40, W - 40), t0=rng.uniform(-6, TOTAL), speed=rng.uniform(110, 230),
        sway=rng.uniform(15, 45), ph=rng.uniform(0, 6.28), a=rng.uniform(0.35, 0.8),
        rot=rng.uniform(-20, 20)))

def draw_hearts(frame, t, density=1.0):
    for k, h in enumerate(HEARTS):
        if k / len(HEARTS) > density:
            continue
        age = t - h["t0"]
        if age < 0:
            continue
        y = H + 60 - h["speed"] * age
        if y < -80:
            continue
        x = h["x"] + h["sway"] * math.sin(age * 1.3 + h["ph"])
        life = clamp01((H + 60 - y) / 300) * clamp01(y / 500)
        a = h["a"] * life
        if a <= 0.01:
            continue
        spr = h["spr"]
        al = spr.getchannel("A").point(lambda v: int(v * a))
        s2 = spr.copy()
        s2.putalpha(al)
        frame.alpha_composite(s2, (int(x - h["size"] / 2), int(y - h["size"] / 2)))

# ---------- polaroids ----------
def polaroid(t, box, caption, photo_w=400):
    img = still(t).crop(box)
    ph = int(photo_w * img.height / img.width)
    img = grade_small(img.resize((photo_w, ph), Image.LANCZOS))
    pad, bottom = 26, 110
    pw, phh = photo_w + 2 * pad, ph + pad + bottom
    card = Image.new("RGBA", (pw, phh), (252, 248, 242, 255))
    card.paste(img, (pad, pad))
    d = ImageDraw.Draw(card)
    d.text((pw / 2, ph + pad + bottom / 2), caption, font=F_SCRIPT_S, fill=(70, 45, 55), anchor="mm")
    m = 40
    out = Image.new("RGBA", (pw + 2 * m, phh + 2 * m), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((m + 6, m + 14, m + pw + 6, m + phh + 14), fill=(0, 0, 0, 150))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    out.alpha_composite(card, (m, m))
    return out

def grade_small(img):
    a = np.asarray(img, dtype=np.float32) / 255
    a = a * np.array([1.06, 0.99, 0.93]) + np.array([0.02, 0.0, 0.025])
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

def place(frame, spr, cx, cy, angle, scale, alpha):
    if alpha <= 0:
        return
    s = spr.rotate(angle, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 1e-3:
        s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BICUBIC)
    if alpha < 1:
        s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))

def drop_in(frame, spr, cx, cy, rot, t, t0, dur=0.7):
    k = (t - t0) / dur
    if k <= 0:
        return
    e = ease_back(k)
    place(frame, spr, cx, cy - (1 - ease_out(k)) * 60, rot + (1 - e) * 12,
          1.35 - 0.35 * e, clamp01(k * 2.2))

# ---------- text ----------
def text_layer(t, t0, draw_fn, fade=0.6, rise=26, t_out=None, fade_out=0.4):
    k = ease_out((t - t0) / fade)
    if t_out is not None:
        k *= 1 - clamp01((t - t_out) / fade_out)
    if k <= 0:
        return None
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), (1 - k) * rise)
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * k)))
    return layer

def soft_text(d, xy, txt, f, fill, anchor="mm", shadow=150):
    x, y = xy
    d.text((x + 2, y + 4), txt, font=f, fill=(20, 5, 15, shadow), anchor=anchor)
    d.text((x, y), txt, font=f, fill=fill + (255,), anchor=anchor)

def comp(frame, layer):
    if layer is not None:
        frame.alpha_composite(layer)

def light_leak(t, center_t, width=0.7):
    k = 1 - abs(t - center_t) / width
    if k <= 0:
        return None
    k = k * k
    leak = np.zeros((H // 8, W // 8, 4), np.float32)
    yy2, xx2 = np.mgrid[0:H // 8, 0:W // 8].astype(np.float32)
    cx = W // 8 * (0.15 + 0.7 * (t - center_t + width) / (2 * width))
    d = np.sqrt((xx2 - cx) ** 2 + (yy2 - H // 8 * 0.35) ** 2) / (W // 8 * 0.7)
    a = np.clip(1 - d, 0, 1) ** 1.5 * k
    leak[..., 0], leak[..., 1], leak[..., 2] = 255, 150, 120
    leak[..., 3] = a * 200
    return Image.fromarray(leak.astype(np.uint8), "RGBA").resize((W, H), Image.BICUBIC)

# ---------- assets ----------
P_INTRO = polaroid(3.3, (75, 450, 675, 1200), "New York, đêm ấy", 520)
P1 = polaroid(0.8, (60, 420, 660, 1170), "Tay trong tay")
P2 = polaroid(5.7, (30, 330, 630, 1080), "Phố lên đèn")
P3 = polaroid(9.6, (120, 300, 720, 1050), "Mãi về sau")
BG_INTRO_SRC = still(1.6)
BG_OUTRO_SRC = still(9.6)
BIG_HEART = heart_sprite(64, (255, 120, 150), 255)

SUBS = [  # (start, end) in footage time
    (0.25, 2.35, "Giữa ngàn ánh đèn rực rỡ…"),
    (2.55, 4.85, "anh chỉ nhìn thấy mỗi em."),
    (5.05, 7.35, "Phố có đông người đến mấy,"),
    (7.55, 9.6, "chỉ cần nắm tay em là đủ."),
]

enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
     "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
     "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)

def emit(fr):
    enc.stdin.write(fr.convert("RGB").tobytes())

foot = frames(0, FOOT + 0.3)
first_foot = None
nI, nF, nO = round(INTRO * FPS), round(FOOT * FPS), round(OUTRO * FPS)

# ---- intro ----
for i in range(nI):
    t = i / FPS
    fr = dreamy_bg(BG_INTRO_SRC, 1.15 + 0.05 * t / INTRO).convert("RGBA")
    draw_hearts(fr, t, 0.6)
    drop_in(fr, P_INTRO, W / 2, 800, -4, t, 0.15, 0.9)
    comp(fr, text_layer(t, 0.95, lambda d, dy: soft_text(d, (W / 2, 1390 + dy), "Giữa phố đông,",
                                                           F_SCRIPT_XL, CREAM)))
    comp(fr, text_layer(t, 1.3, lambda d, dy: soft_text(d, (W / 2, 1540 + dy), "mình có nhau",
                                                          F_SCRIPT_XL, ROSE)))
    comp(fr, text_layer(t, 1.7, lambda d, dy: soft_text(d, (W / 2, 1680 + dy),
                                                          "— TIMES SQUARE · NEW YORK —", F_SMALL,
                                                          (235, 215, 210), shadow=110)))
    if t > INTRO - 0.5:                         # crossfade into footage
        if first_foot is None:
            first_foot = next(foot)
        k = (t - (INTRO - 0.5)) / 0.5
        ff = grade(fill(first_foot, 1.0)).convert("RGBA")
        fr = Image.blend(fr, ff, ease_out(k))
    comp(fr, light_leak(t, INTRO, 0.7))
    emit(fr)

# ---- footage ----
for i in range(nF):
    t = i / FPS
    src = first_foot if (i == 0 and first_foot is not None) else next(foot)
    z = 1.0 + 0.07 * (t / FOOT)
    fr = grade(fill(src, z, SW / 2, SH / 2 + 40 * t / FOOT)).convert("RGBA")
    draw_hearts(fr, INTRO + t, 0.45)
    for s0, s1, txt in SUBS:
        if s0 - 0.1 <= t <= s1 + 0.5:
            comp(fr, text_layer(t, s0, lambda d, dy, txt=txt: soft_text(
                d, (W / 2, 1620 + dy * 0.5), txt, F_SUB, CREAM, shadow=190),
                fade=0.45, rise=20, t_out=s1, fade_out=0.35))
    comp(fr, light_leak(INTRO + t, INTRO, 0.7))
    last_foot = fr
    emit(fr)

# ---- outro ----
T0 = INTRO + FOOT
for i in range(nO):
    t = i / FPS
    fr = dreamy_bg(BG_OUTRO_SRC, 1.2 + 0.06 * t / OUTRO, 0.5).convert("RGBA")
    if t < 0.6:                                  # dissolve from last footage frame
        fr = Image.blend(last_foot, fr, ease_out(t / 0.6))
    if t < 0.35:
        fr = Image.alpha_composite(fr, Image.new("RGBA", (W, H), (255, 235, 235,
                                                               int(170 * (1 - t / 0.35)))))
    draw_hearts(fr, T0 + t, 1.0)
    drop_in(fr, P1, 310, 470, -7, t, 0.4)
    drop_in(fr, P2, 770, 730, 7, t, 1.0)
    drop_in(fr, P3, 420, 1175, -3, t, 1.6)
    comp(fr, text_layer(t, 2.6, lambda d, dy: soft_text(d, (W / 2, 1590 + dy), "Yêu là cùng nhau",
                                                          F_SCRIPT_L, CREAM)))
    comp(fr, text_layer(t, 3.1, lambda d, dy: soft_text(d, (W / 2, 1715 + dy),
                                                          "đi qua mọi con phố.", F_SCRIPT_L, ROSE)))
    hk = ease_back((t - 3.9) / 0.7)
    if t > 3.9:
        beat = 1 + 0.06 * max(0, math.sin((t - 4.6) * 2 * math.pi / 0.8)) if t > 4.6 else 1
        place(fr, BIG_HEART, W / 2, 1830, 0, max(0.01, hk * beat), clamp01((t - 3.9) * 3))
    if t > OUTRO - 1.2:                          # fade to black
        k = (t - (OUTRO - 1.2)) / 1.2
        fr = Image.alpha_composite(fr, Image.new("RGBA", (W, H), (0, 0, 0, int(255 * k * k))))
    emit(fr)

enc.stdin.close()
enc.wait()
print("wrote", OUT)
