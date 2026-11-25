"""Synthesize a 15s, 96 BPM dark-pop/trap background track for the nail ad.

6 bars of 4/4 (2.5s each). Bars 1-4 = footage (cuts on every downbeat),
bars 5-6 = end card (drums drop out, pad + bass ring out).
Usage: python3 make_music.py out.wav
"""
import sys
import wave
import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM            # 0.625 s
BAR = BEAT * 4             # 2.5 s
DUR = 15.0
N = int(SR * DUR)
rng = np.random.default_rng(7)

def t_arr(d):
    return np.arange(int(SR * d)) / SR

def add(buf, sig, start):
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]

def onepole_lp(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for k in range(len(x)):
        acc = (1 - a) * x[k] + a * acc
        y[k] = acc
    return y

def note_hz(n):  # MIDI -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)

# ---------- instruments ----------
def kick():
    t = t_arr(0.45)
    f = 45 + 95 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 7)
    click = rng.standard_normal(len(t)) * np.exp(-t * 400) * 0.25
    return np.tanh((s + click) * 1.6) * 0.9

def clap():
    t = t_arr(0.35)
    n = rng.standard_normal(len(t))
    n = n - onepole_lp(n, 900)               # high-pass-ish
    env = np.exp(-t * 18)
    for off in (0.0, 0.011, 0.022):          # clap flams
        env += np.where(t >= off, np.exp(-(t - off) * 120), 0) * 0.6
    return n * env * 0.32

def hat(open_=False):
    t = t_arr(0.25 if open_ else 0.06)
    n = rng.standard_normal(len(t))
    n = np.diff(np.concatenate([[0], np.diff(np.concatenate([[0], n]))]))
    return n * np.exp(-t * (14 if open_ else 70)) * 0.05

def bass808(midi, d):
    t = t_arr(d)
    f = note_hz(midi)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    env = np.minimum(1, t / 0.005) * np.exp(-t * 1.4)
    return np.tanh(s * env * 1.8) * 0.42

def pad(midis, d):
    t = t_arr(d)
    s = np.zeros_like(t)
    for m in midis:
        for det in (-0.08, 0.0, 0.08):     # detuned saws
            f = note_hz(m + det)
            s += 2 * ((f * t) % 1.0) - 1
    s /= len(midis) * 3
    s = onepole_lp(s, 1400)
    env = np.minimum(1, t / 0.25) * np.minimum(1, (d - t) / 0.3)
    return s * env * 0.22

def pluck(midi, d=0.4):
    t = t_arr(d)
    f = note_hz(midi)
    tri = 2 * np.abs(2 * ((f * t) % 1.0) - 1) - 1
    sq = np.sign(np.sin(2 * np.pi * f * t)) * 0.3
    return (tri + sq) * np.exp(-t * 9) * 0.11

def riser(d=0.5):
    t = t_arr(d)
    n = rng.standard_normal(len(t))
    n = n - onepole_lp(n, 2500)
    return n * (t / d) ** 3 * 0.12

def impact():
    t = t_arr(1.8)
    n = rng.standard_normal(len(t))
    n = onepole_lp(n, 3000)
    boom = np.sin(2 * np.pi * (38 + 40 * np.exp(-t * 10)) * t)
    return (n * 0.25 + boom * 0.7) * np.exp(-t * 2.5) * 0.6

# ---------- arrangement (A minor: Am - F - C - G) ----------
chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
roots = [33, 29, 36, 31]
drums = np.zeros(N)
music = np.zeros(N)
fx = np.zeros(N)

K, C = kick(), clap()
for bar in range(6):
    b0 = bar * BAR
    ch = chords[bar % 4]
    music_pad = pad([m + 12 for m in ch], BAR + 0.3)
    add(music, music_pad, b0)
    end_card = bar >= 4
    # bass
    if not end_card:
        add(music, bass808(roots[bar % 4], BEAT * 1.5), b0)
        add(music, bass808(roots[bar % 4], BEAT), b0 + BEAT * 2.5)
    elif bar == 4:
        add(music, bass808(roots[0], BAR * 2), b0)
    # pluck arp (8ths)
    arp = [ch[0] + 24, ch[1] + 24, ch[2] + 24, ch[1] + 24]
    for k in range(8):
        if end_card and k % 2:
            continue
        add(music, pluck(arp[k % 4]), b0 + k * BEAT / 2)
    if end_card:
        continue
    # drums
    add(drums, K, b0)
    add(drums, K, b0 + BEAT * 2.5)
    if bar % 2:
        add(drums, K, b0 + BEAT * 3.5)
    add(drums, C, b0 + BEAT)
    add(drums, C, b0 + BEAT * 3)
    for k in range(16):  # 16th hats with rolls at bar ends
        if bar >= 1 or k % 2 == 0:
            add(drums, hat() * (1.0 if k % 2 == 0 else 0.6), b0 + k * BEAT / 4)
    if bar in (1, 3):
        for k in range(6):
            add(drums, hat() * 0.7, b0 + BEAT * 3.5 + k * BEAT / 12)
    add(drums, hat(True), b0 + BEAT * 1.5)

# transition FX: riser into each cut + impact on end card
for cut in (BAR, 2 * BAR, 3 * BAR):
    add(fx, riser(0.4), cut - 0.4)
add(fx, riser(1.0) * 1.4, 4 * BAR - 1.0)
add(fx, impact(), 4 * BAR)

# simple reverb on music bus
ir_t = t_arr(1.6)
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2)
ir /= np.sqrt(np.sum(ir ** 2))
L = len(music) + len(ir) - 1
nfft = 1 << (L - 1).bit_length()
wet = np.fft.irfft(np.fft.rfft(music, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(music)]
music = music + wet * 0.35

mix = drums + music + fx
fade = np.ones(N)
fl = int(SR * 1.2)
fade[-fl:] = np.linspace(1, 0, fl) ** 2
mix *= fade
mix = np.tanh(mix * 1.3)
mix /= np.max(np.abs(mix)) / 0.89

# stereo: slight width via delayed copy of music
d = int(SR * 0.012)
right = mix.copy()
right[d:] = 0.85 * mix[d:] + 0.15 * mix[:-d]
stereo = np.stack([mix, right], axis=1)
stereo /= np.max(np.abs(stereo)) / 0.89
pcm = (stereo * 32767).astype("<i2")

with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1])
