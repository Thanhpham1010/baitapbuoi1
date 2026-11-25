"""Chill R&B bed for the mocha nail ad: 96 BPM, 15s = 6 bars (cuts every 2.5s).
Usage: python3 make_music.py out.wav
"""
import sys
import wave
import numpy as np

SR = 44100
BEAT = 60 / 96
BAR = BEAT * 4
N = int(SR * 15.0)
rng = np.random.default_rng(5)

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

def tt(d):
    return np.arange(int(SR * d)) / SR

def rhodes(m, d, vel=1.0):
    t = tt(d)
    f = hz(m)
    trem = 1 + 0.15 * np.sin(2 * np.pi * 4.5 * t)
    s = (np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * t) * np.exp(-t * 6))
         + 0.2 * np.sin(4 * np.pi * f * t) * np.exp(-t * 3))
    env = np.minimum(1, t / 0.006) * np.exp(-t * 0.9) * np.minimum(1, (d - t) / 0.15)
    return s * env * trem * vel * 0.07

def kick():
    t = tt(0.4)
    f = 48 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8) * 0.75

def snap():
    t = tt(0.25)
    n = rng.standard_normal(len(t))
    n = n - lp(n, 1500)
    return n * np.exp(-t * 28) * 0.22

def hat(v=1.0):
    t = tt(0.05)
    n = np.diff(rng.standard_normal(len(t) + 1))
    return n * np.exp(-t * 90) * 0.035 * v

def bass(m, d):
    t = tt(d)
    s = np.sin(2 * np.pi * hz(m) * t)
    return np.tanh(s * 1.5) * np.minimum(1, t / 0.01) * np.exp(-t * 1.2) * \
        np.minimum(1, (d - t) / 0.05) * 0.35

# Fmaj9 - Em7 - Dm9 - Cmaj7 (warm, "mocha")
chords = [[65, 69, 72, 76, 79], [64, 67, 71, 74], [62, 65, 69, 72, 76], [60, 64, 67, 71]]
roots = [41, 40, 38, 36]
music, drums = np.zeros(N), np.zeros(N)
K, S = kick(), snap()
for bar in range(6):
    b0 = bar * BAR
    ch = chords[bar % 4]
    end = bar >= 4
    for k, off in enumerate([0, BEAT * 1.5, BEAT * 2.75] if not end else [0]):
        for j, m in enumerate(ch):
            add(music, rhodes(m - 12 * (j == 0), BAR if end else 1.4, 0.9 - 0.15 * k),
                b0 + off + j * 0.012)
    add(music, bass(roots[bar % 4], BEAT * 1.4), b0)
    if not end:
        add(music, bass(roots[bar % 4] + 7, BEAT * 0.4), b0 + BEAT * 2.5)
        add(music, bass(roots[bar % 4], BEAT * 0.9), b0 + BEAT * 3)
    if end and bar == 5:
        continue
    if bar >= 1 and not end:
        add(drums, K, b0)
        add(drums, K, b0 + BEAT * 2.5)
        add(drums, S, b0 + BEAT)
        add(drums, S, b0 + BEAT * 3)
    for k in range(8):
        swing = 0.06 * BEAT if k % 2 else 0
        add(drums, hat(1.0 if k % 2 == 0 else 0.6), b0 + k * BEAT / 2 + swing)

# vinyl crackle for lo-fi warmth
crackle = (rng.random(N) > 0.9993) * rng.standard_normal(N) * 0.08
music += lp(crackle, 4000)

ir_t = tt(1.4)
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.5)
ir /= np.sqrt(np.sum(ir ** 2))
nfft = 1 << (N + len(ir)).bit_length()
wet = np.fft.irfft(np.fft.rfft(music, nfft) * np.fft.rfft(ir, nfft), nfft)[:N]
mix = lp(music + wet * 0.3, 7000) + drums
fo = int(SR * 1.5)
mix[-fo:] *= np.linspace(1, 0, fo) ** 2
mix[: int(SR * 0.05)] *= np.linspace(0, 1, int(SR * 0.05))
mix = np.tanh(mix * 1.2)
d = int(SR * 0.011)
right = np.concatenate([mix[:d], 0.8 * mix[d:] + 0.2 * mix[:-d]])
st = np.stack([mix, right], 1)
st /= np.max(np.abs(st)) / 0.89
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
print("wrote", sys.argv[1])
