"""Elegant 'luxury' bed: piano + strings + soft deep pulse, 80 BPM, 18s (6 bars of 3s).
Usage: python3 make_music.py out.wav
"""
import sys
import wave
import numpy as np

SR = 44100
BEAT = 60 / 80          # 0.75s
BAR = BEAT * 4          # 3.0s
DUR = 18.0
N = int(SR * DUR)
rng = np.random.default_rng(8)

def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)

def tt(d):
    return np.arange(int(SR * d)) / SR

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
    t = tt(d)
    f = hz(m)
    s = np.zeros_like(t)
    for h, amp in enumerate([1.0, 0.42, 0.2, 0.1, 0.05], start=1):
        s += amp * np.sin(2 * np.pi * f * h * np.sqrt(1 + 0.0004 * h * h) * t) * np.exp(-t * (0.9 + 0.8 * h))
    return s * np.minimum(1, t / 0.004) * np.minimum(1, (d - t) / 0.3) * vel * 0.15

def strings(ms, d):
    t = tt(d)
    s = np.zeros_like(t)
    for m in ms:
        for det in (-0.06, 0.0, 0.06):
            s += 2 * ((hz(m + det) * (1 + 0.003 * np.sin(2 * np.pi * 5.2 * t)) * t) % 1.0) - 1
    s = lp(s / (len(ms) * 3), 1100)
    return s * np.minimum(1, t / 0.9) * np.minimum(1, (d - t) / 0.8) * 0.17

def pulse():
    t = tt(0.6)
    f = 42 + 40 * np.exp(-t * 22)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * 0.55

def shaker(v=1.0):
    t = tt(0.08)
    n = np.diff(rng.standard_normal(len(t) + 1))
    return n * np.exp(-t * 45) * 0.025 * v

def swell(d):
    t = tt(d)
    n = lp(rng.standard_normal(len(t)), 3000)
    return n * (t / d) ** 2.5 * 0.06

# D minor, cinematic & sophisticated: Dm9 - Bbmaj7 - Gm9 - A7sus -> Dm9 - Bbmaj7(end)
chords = [[50, 57, 60, 64, 65], [46, 53, 57, 62, 65], [43, 50, 53, 57, 58], [45, 52, 55, 57, 62],
          [50, 57, 60, 64, 65], [46, 53, 57, 62, 69]]
pads = [[62, 65, 69, 72], [62, 65, 69, 70], [58, 62, 65, 69], [57, 62, 64, 67], [62, 65, 69, 72],
        [62, 65, 69, 70]]
melody = [(1, 0, 81, 2), (1, 2, 79, 1), (1, 3, 77, 1), (2, 0, 77, 2.5), (2, 3, 76, 1),
          (3, 0, 76, 1.5), (3, 1.5, 74, 0.5), (3, 2, 73, 2), (4, 0, 74, 4)]

music, drums = np.zeros(N), np.zeros(N)
for b, (ch, pd) in enumerate(zip(chords, pads)):
    b0 = b * BAR
    last = b == len(chords) - 1
    add(music, piano(ch[0] - 12, 0.85, 4.5), b0)
    for k, idx in enumerate([1, 2, 3, 4, 3, 2]):
        if last and k > 3:
            break
        add(music, piano(ch[idx] + 12, 0.42, 2.5), b0 + BEAT * (0.5 + k * 0.5))
    add(music, strings(pd, BAR + 1.0 if not last else BAR + 0.1), b0 - 0.3 if b else 0)
    if 1 <= b <= 3 or b == 4:
        add(drums, pulse(), b0)
        add(drums, pulse() * 0.6, b0 + BEAT * 2)
        for k in range(8):
            add(drums, shaker(1.0 if k % 2 else 0.5), b0 + k * BEAT / 2)
for bar, beat, m, ln in melody:
    add(music, piano(m, 1.0, ln * BEAT + 1.5), bar * BAR + beat * BEAT)
for cut in (3.0, 6.0, 9.0, 12.0):
    add(music, swell(1.2), cut - 1.2)

ir_t = tt(3.0)
ir = lp(rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 1.8), 5000)
ir /= np.sqrt(np.sum(ir ** 2))
nfft = 1 << (N + len(ir)).bit_length()
wet = np.fft.irfft(np.fft.rfft(music, nfft) * np.fft.rfft(ir, nfft), nfft)[:N]
d = int(SR * 0.019)
L = music + wet * 0.5 + drums
R = music + np.concatenate([np.zeros(d), wet[:-d]]) * 0.5 + drums
st = np.stack([L, R], 1)
fi, fo = int(SR * 0.4), int(SR * 2.0)
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
