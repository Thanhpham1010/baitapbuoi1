"""Soft romantic piano + strings bed, 75 BPM, 22.4s (7 bars of 4/4).
Usage: python3 make_music.py out.wav
"""
import sys
import wave
import numpy as np

SR = 44100
BPM = 75
BEAT = 60 / BPM          # 0.8s
BAR = BEAT * 4           # 3.2s
DUR = 22.4
N = int(SR * DUR)
rng = np.random.default_rng(3)

def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)

def add(buf, sig, start):
    i = int(start * SR)
    j = min(len(buf), i + len(sig))
    if i < j:
        buf[i:j] += sig[: j - i]

def lp(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for k in range(len(x)):
        acc = (1 - a) * x[k] + a * acc
        y[k] = acc
    return y

def piano(m, vel=1.0, d=3.0):
    t = np.arange(int(SR * d)) / SR
    f = hz(m)
    s = np.zeros_like(t)
    for h, amp in enumerate([1.0, 0.45, 0.22, 0.12, 0.06, 0.03], start=1):
        fh = f * h * np.sqrt(1 + 0.0004 * h * h)      # slight inharmonicity
        s += amp * np.sin(2 * np.pi * fh * t) * np.exp(-t * (1.1 + 0.9 * h))
    att = np.minimum(1, t / 0.004)
    rel = np.minimum(1, (d - t) / 0.3)
    return s * att * rel * vel * 0.16

def strings(ms, d):
    t = np.arange(int(SR * d)) / SR
    s = np.zeros_like(t)
    for m in ms:
        for det in (-0.07, 0.0, 0.07):
            f = hz(m + det)
            vib = 1 + 0.003 * np.sin(2 * np.pi * 5 * t)
            s += 2 * ((f * vib * t) % 1.0) - 1
    s = lp(s / (len(ms) * 3), 900)
    env = np.minimum(1, t / 1.2) * np.minimum(1, (d - t) / 1.0)
    return s * env * 0.18

# C - G - Am - F | C - G/B - Am - F ... resolve F - G - C
prog = [
    ([48, 55, 60, 64, 67], [60, 64, 67]),   # C
    ([43, 50, 55, 59, 62], [59, 62, 67]),   # G
    ([45, 52, 57, 60, 64], [57, 60, 64]),   # Am
    ([41, 48, 53, 57, 60], [57, 60, 65]),   # F
    ([48, 55, 60, 64, 67], [60, 64, 67]),   # C
    ([41, 48, 53, 57, 60], [57, 60, 65]),   # F
    ([48, 55, 60, 64, 72], [60, 64, 67]),   # C (final, rings out)
]
melody = [  # (bar, beat, midi, len_beats)
    (1, 0, 76, 1.5), (1, 1.5, 74, 0.5), (1, 2, 74, 2),
    (2, 0, 72, 1.5), (2, 1.5, 71, 0.5), (2, 2, 72, 2),
    (3, 0, 69, 1), (3, 1, 72, 1), (3, 2, 77, 2),
    (4, 0, 76, 1.5), (4, 1.5, 74, 0.5), (4, 2, 72, 2),
    (5, 0, 77, 1), (5, 1, 76, 1), (5, 2, 74, 1), (5, 3, 72, 1),
    (6, 0, 72, 4),
]

music = np.zeros(N)
for b, (arp, pad) in enumerate(prog):
    b0 = b * BAR
    last = b == len(prog) - 1
    add(music, piano(arp[0] - 12, 0.9, 4.0), b0)                # bass note
    pattern = [0, 1, 2, 3, 4, 3, 2, 1]
    for k, idx in enumerate(pattern):
        if last and k > 3:
            break
        add(music, piano(arp[idx], 0.55 + 0.1 * (k == 0), 2.5), b0 + k * BEAT / 2)
    if b >= 1:
        add(music, strings(pad, BAR + 0.8), b0 - 0.2)
for bar, beat, m, ln in melody:
    add(music, piano(m, 1.05, max(1.5, ln * BEAT + 1.0)), bar * BAR + beat * BEAT)

# reverb
ir_t = np.arange(int(SR * 2.8)) / SR
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 2.0)
ir = lp(ir, 5000)
ir /= np.sqrt(np.sum(ir ** 2))
L = len(music) + len(ir)
nfft = 1 << (L - 1).bit_length()
wet = np.fft.irfft(np.fft.rfft(music, nfft) * np.fft.rfft(ir, nfft), nfft)[:N]

left = music + wet * 0.45
d = int(SR * 0.017)
right = music + np.concatenate([np.zeros(d), wet[:-d]]) * 0.45
st = np.stack([left, right], 1)
fi, fo = int(SR * 0.6), int(SR * 2.5)
st[:fi] *= np.linspace(0, 1, fi)[:, None]
st[-fo:] *= (np.linspace(1, 0, fo) ** 2)[:, None]
st = np.tanh(st * 1.1)
st /= np.max(np.abs(st)) / 0.89
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
print("wrote", sys.argv[1])
