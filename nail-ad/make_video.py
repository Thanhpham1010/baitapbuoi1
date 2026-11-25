"""Re-cut the Gloss Nail Bar footage into a 15s 4:5 (1080x1350) feed ad.

Usage: python3 make_video.py SOURCE.mp4 OUT_silent.mp4
Only the caption-free stretch of the source (2.6s-12.6s) is used, cropped to
the clean middle band (no burned-in logo/captions). Four 2.5s shots cut on the
music downbeats (96 BPM), then a 5s branded end card.
"""
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1350, 30
CW, CH = 960, 1200            # clean crop from source (x=60, y=230)
CROP = f"crop={CW}:{CH}:60:230"
SEG = 2.5
END = 5.0
TOTAL = SEG * 4 + END

FONT = "/usr/share/fonts/opentype/inter/"
SERIF = "/usr/share/fonts/truetype/crosextra/"
GOLD = (232, 184, 109)
CREAM = (250, 242, 232)
BG = (38, 24, 22)

def font(name, size):
    return ImageFont.truetype(name, size)

F_CAP = font(FONT + "Inter-ExtraBold.otf", 78)
F_LOGO_S = font(SERIF + "Caladea-Bold.ttf", 44)
F_LOGO_SUB = font(FONT + "Inter-SemiBold.otf", 15)
F_LOGO_L = font(SERIF + "Caladea-Bold.ttf", 150)
F_SUB_L = font(FONT + "Inter-SemiBold.otf", 30)
F_ITAL = font(SERIF + "Caladea-Italic.ttf", 50)
F_SMALL = font(FONT + "Inter-SemiBold.otf", 26)
F_PHONE = font(FONT + "Inter-Bold.otf", 86)

def reader(start, dur, extra=""):
    vf = CROP + ("," + extra if extra else "")
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", SRC,
           "-vf", vf + f",fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = CW * CH * 3
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield Image.frombuffer("RGB", (CW, CH), b, "raw", "RGB", 0, 1)

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3

def spaced(draw, xy, text, f, fill, spacing, anchor_center=True):
    widths = [draw.textlength(c, font=f) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=f, fill=fill)
        x += w + spacing

def tracked_width(draw, text, f, spacing):
    return sum(draw.textlength(c, font=f) for c in text) + spacing * (len(text) - 1)

# ---------- shot framing: (src_start, zoom_from, zoom_to, center_from, center_to)
SHOTS = [
    (2.6, 1.00, 1.12, (480, 600), (480, 560)),   # slow push-in
    (5.1, 1.45, 1.55, (470, 700), (500, 660)),   # punch-in on the patterns
    (7.6, 1.18, 1.04, (480, 560), (480, 600)),   # pull back
    (10.1, 1.02, 1.16, (480, 600), (520, 520)),  # push toward the tips
]
CAPTIONS = [
    [("Basic nails?", CREAM)], [("Not at ", CREAM), ("Gloss.", GOLD)],
    [("Leopard. ", GOLD), ("Zebra.", CREAM)], [("Glossy ", CREAM), ("black.", GOLD)],
    [("Hand-painted", CREAM)], [("by ", CREAM), ("Brian.", GOLD)],
    [("Sharp ", CREAM), ("stilettos.", GOLD)], [("Pure attitude.", CREAM)],
]

def framed(img, z, c):
    base = max(W / CW, H / CH)              # fill 1080x1350 from 960x1200
    s = base * z
    vw, vh = W / s, H / s
    cx = min(max(c[0], vw / 2), CW - vw / 2)
    cy = min(max(c[1], vh / 2), CH - vh / 2)
    data = (1 / s, 0, cx - vw / 2, 0, 1 / s, cy - vh / 2)
    return img.transform((W, H), Image.AFFINE, data, resample=Image.BICUBIC)

# static layers
grad = Image.new("L", (1, H))
for y in range(H):
    v = 0
    if y > H * 0.55:
        v = int(215 * ((y - H * 0.55) / (H * 0.45)) ** 1.4)
    if y < 170:
        v = max(v, int(140 * (1 - y / 170)))
    grad.putpixel((0, y), v)
grad = grad.resize((W, H))
shade = Image.new("RGB", (W, H), (12, 6, 5))

brand = Image.new("RGBA", (W, H), (0, 0, 0, 0))
bd = ImageDraw.Draw(brand)
spaced(bd, (W / 2, 38), "GLOSS", F_LOGO_S, CREAM + (255,), 8)
spaced(bd, (W / 2, 92), "NAIL BAR", F_LOGO_SUB, CREAM + (200,), 7)

def caption_layer(lines, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y0 = H - 330
    for i, parts in enumerate(lines):
        k = ease((t - 0.12 - i * 0.18) / 0.35)
        if k <= 0:
            continue
        a = int(255 * k)
        total = sum(d.textlength(p, font=F_CAP) for p, _ in parts)
        x = (W - total) / 2
        y = y0 + i * 96 + (1 - k) * 40
        for p, col in parts:
            d.text((x + 3, y + 4), p, font=F_CAP, fill=(0, 0, 0, int(a * 0.45)))
            d.text((x, y), p, font=F_CAP, fill=col + (a,))
            x += d.textlength(p, font=F_CAP)
    return layer

proc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
     "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
     "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
    stdin=subprocess.PIPE)

def emit(img):
    proc.stdin.write(img.convert("RGB").tobytes())

nseg = int(SEG * FPS)
for si, (start, z0, z1, c0, c1) in enumerate(SHOTS):
    for fi, img in enumerate(reader(start, SEG + 0.2)):
        if fi >= nseg:
            break
        u = fi / (nseg - 1)
        e = u * u * (3 - 2 * u)
        z = z0 + (z1 - z0) * e
        c = (c0[0] + (c1[0] - c0[0]) * e, c0[1] + (c1[1] - c0[1]) * e)
        frame = framed(img, z, c)
        frame = Image.composite(shade, frame, grad)
        t = fi / FPS
        if si > 0 and t < 0.12:                      # flash on the cut
            frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 245, 235)),
                                0.55 * (1 - t / 0.12))
        frame = frame.convert("RGBA")
        frame.alpha_composite(brand)
        frame.alpha_composite(caption_layer(CAPTIONS[si * 2: si * 2 + 2], t))
        emit(frame)

# ---------- end card ----------
nend = int(END * FPS)
bg_src = reader(2.6, END + 0.5)
win_src = reader(5.1, END + 0.5)
WIN_W, WIN_H = 460, 560
mask = Image.new("L", (WIN_W, WIN_H), 0)
ImageDraw.Draw(mask).ellipse((0, 0, WIN_W - 1, WIN_H - 1), fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(1.2))
ring = Image.new("RGBA", (WIN_W + 24, WIN_H + 24), (0, 0, 0, 0))
ImageDraw.Draw(ring).ellipse((2, 2, WIN_W + 21, WIN_H + 21), outline=GOLD + (230,), width=3)

for fi in range(nend):
    t = fi / FPS
    bgi = next(bg_src)
    wi = next(win_src)
    bgf = framed(bgi, 1.1 + 0.03 * t / END, (480, 600)).resize((W // 6, H // 6))
    bgf = bgf.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BICUBIC)
    frame = Image.blend(Image.new("RGB", (W, H), BG), bgf, 0.28).convert("RGBA")
    if t < 0.25:                                     # impact flash
        frame = Image.alpha_composite(
            frame, Image.new("RGBA", (W, H), (255, 245, 235, int(200 * (1 - t / 0.25)))))
    d = ImageDraw.Draw(frame)

    # oval window with live footage
    k = ease(t / 0.6)
    sc = 0.85 + 0.15 * k
    ww, wh = int(WIN_W * sc), int(WIN_H * sc)
    s = max(ww / CW, wh / CH) * 1.25
    vw, vh = ww / s, wh / s
    win = wi.transform((ww, wh), Image.AFFINE,
                       (1 / s, 0, 470 - vw / 2, 0, 1 / s, 650 - vh / 2), resample=Image.BICUBIC)
    m = mask.resize((ww, wh)).point(lambda v: int(v * k))
    wy = 120 + (WIN_H - wh) // 2
    frame.paste(win, ((W - ww) // 2, wy), m)
    r = ring.resize((ww + 24, wh + 24))
    r.putalpha(r.getchannel("A").point(lambda v: int(v * k)))
    frame.alpha_composite(r, ((W - ww) // 2 - 12, wy - 12))

    def fade_text(t0, draw_fn):
        kk = ease((t - t0) / 0.5)
        if kk <= 0:
            return
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(layer), (1 - kk) * 30)
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * kk)))
        frame.alpha_composite(layer)

    fade_text(0.35, lambda dd, dy: spaced(dd, (W / 2, 720 + dy), "GLOSS", F_LOGO_L, CREAM, 18))
    fade_text(0.55, lambda dd, dy: spaced(dd, (W / 2, 885 + dy), "NAIL BAR", F_SUB_L, GOLD, 14))
    fade_text(0.85, lambda dd, dy: dd.text((W / 2, 975 + dy), "Nails by Brian", font=F_ITAL,
                                           fill=CREAM, anchor="mt"))
    fade_text(1.25, lambda dd, dy: spaced(dd, (W / 2, 1085 + dy), "CALL TO BOOK", F_SMALL,
                                          CREAM + (190,), 8))

    def phone(dd, dy):
        txt = "(929) 888-8288"
        tw = dd.textlength(txt, font=F_PHONE)
        x0, y0 = (W - tw) / 2 - 44, 1130 + dy
        dd.rounded_rectangle((x0, y0, x0 + tw + 88, y0 + 128), radius=64, outline=GOLD, width=3)
        dd.text((W / 2, y0 + 64), txt, font=F_PHONE, fill=GOLD, anchor="mm")
    fade_text(1.45, phone)
    emit(frame)

proc.stdin.close()
proc.wait()
print("wrote", OUT)
