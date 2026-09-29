"""Original chill/lo-fi instrumental bed, synthesized (royalty-free by construction)."""
import numpy as np, wave
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
BPM = 84
BEAT = 60 / BPM
BAR = 4 * BEAT
DUR = 320.0
N = int(SR * DUR)
rng = np.random.default_rng(7)

L = np.zeros(N); R = np.zeros(N)


def mtof(m): return 440 * 2 ** ((m - 69) / 12)


def add(sig, t, pan=0.0, g=1.0):
    i = int(t * SR)
    if i >= N: return
    s = sig[: N - i] * g
    L[i:i + len(s)] += s * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(s)] += s * np.sqrt(0.5 * (1 + pan))


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def ep(m, dur, vel=1.0):
    """Rhodes-ish FM electric piano note."""
    f = mtof(m)
    n = int(SR * (dur + 1.6))
    t = np.arange(n) / SR
    idx = (1.6 * vel) * np.exp(-t / 0.35) + 0.15
    mod = np.sin(2 * np.pi * f * t) * idx
    car = np.sin(2 * np.pi * f * t + mod)
    tine = np.sin(2 * np.pi * f * 7.02 * t) * np.exp(-t / 0.05) * 0.10 * vel
    amp = np.minimum(t / 0.004, 1) * np.exp(-t / 1.25)
    rel = np.clip(1 - (t - dur) / 0.35, 0, 1)
    trem = 1 + 0.05 * np.sin(2 * np.pi * 4.6 * t)
    return (car + tine) * amp * rel * trem * vel


def pad(ms, dur):
    n = int(SR * (dur + 1.0))
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in ms:
        f = mtof(m)
        for det in (-0.09, 0.0, 0.08):
            ph = rng.uniform(0, 1)
            out += 2 * ((f * (1 + det / 100) * t + ph) % 1) - 1
    out = lp(out, 950, 2)
    a = np.minimum(t / 0.9, 1) * np.clip(1 - (t - dur) / 1.0, 0, 1)
    return out * a / (len(ms) * 3)


def bass(m, dur):
    f = mtof(m)
    n = int(SR * (dur + .2))
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    a = np.minimum(t / 0.01, 1) * np.exp(-t / 1.4) * np.clip(1 - (t - dur) / 0.12, 0, 1)
    return lp(s * a, 400)


def kick():
    n = int(SR * .45); t = np.arange(n) / SR
    f = 48 + 70 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.16) * np.minimum(t / 0.002, 1)


def snap():
    n = int(SR * .25); t = np.arange(n) / SR
    nz = hp(lp(rng.standard_normal(n), 5200), 900) * np.exp(-t / 0.045)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.03) * 0.5
    return (nz * 0.8 + tone)


def hat(open_=False):
    n = int(SR * (.18 if open_ else .06)); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7500, 3) * np.exp(-t / (0.06 if open_ else 0.018))


def pluck(m, vel=1.0):
    f = mtof(m); n = int(SR * 1.2); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t / 0.08)
    return s * np.exp(-t / 0.35) * np.minimum(t / 0.002, 1) * vel


# D major: Gmaj9 | F#m7 | Em9 | A7sus4 -> A
CH = [
    ([55, 59, 62, 66, 69], 43),
    ([54, 57, 61, 64, 69], 42),
    ([52, 55, 59, 62, 66], 40),
    ([57, 62, 64, 67, 71], 45),
]
MEL = [74, 78, 81, 83, 81, 78, 76, 74]      # soft motif

KICK, SNAP = kick(), snap()
nbars = int(DUR / BAR) + 1
for b in range(nbars):
    t0 = b * BAR
    notes, root = CH[b % 4]
    sec = (b // 8) % 4                    # small arrangement variation
    groove = b >= 2
    # pad
    add(pad(notes[:4], BAR), t0, 0, 0.55)
    # EP comping: beat 1 + "and" of 2 (+ light anticipation)
    for k, m in enumerate(notes):
        add(ep(m, BEAT * 1.4, 0.55 + 0.1 * (k == 0)), t0 + 0.012 * k, (k - 2) * 0.18, 0.16)
    for k, m in enumerate(notes[2:]):
        add(ep(m, BEAT * 0.8, 0.4), t0 + BEAT * 1.5 + 0.01 * k, (k - 1) * 0.25, 0.11)
    if b % 4 == 3:  # sus -> resolve (C#)
        add(ep(61 + 12, BEAT, 0.45), t0 + BEAT * 3, 0.2, 0.12)
    # bass
    add(bass(root, BEAT * 1.6), t0, 0, 0.42)
    add(bass(root, BEAT * 0.7), t0 + BEAT * 2.5, 0, 0.30)
    add(bass(root + 7 if b % 2 else root + 12, BEAT * 0.6), t0 + BEAT * 3.5, 0, 0.20)
    if groove:
        for q in (0, 2):
            add(KICK, t0 + q * BEAT, 0, 0.50)
        add(KICK, t0 + 2.75 * BEAT, 0, 0.22)
        for q in (1, 3):
            add(SNAP, t0 + q * BEAT + 0.012, 0.05, 0.16)
        for e in range(8):
            sw = 0.06 * BEAT if e % 2 else 0
            add(hat(e == 7), t0 + e * BEAT / 2 + sw, 0.3, 0.05 if e % 2 else 0.075)
    # motif every other 4-bar phrase
    if sec in (1, 3) and b % 4 in (0, 2):
        for k, m in enumerate(MEL[(b % 4) * 2:(b % 4) * 2 + 4]):
            add(pluck(m, .5), t0 + BEAT * (0.5 + k * 0.75), -0.35 + 0.2 * k, 0.07)

# sidechain-ish breathing on the whole bed (subtle)
t = np.arange(N) / SR
ph = (t % BEAT) / BEAT
duck = 1 - 0.10 * np.exp(-ph / 0.18)
L *= duck; R *= duck

# reverb (generated IR)
irn = int(SR * 2.4); ti = np.arange(irn) / SR
irL = rng.standard_normal(irn) * np.exp(-ti / 0.55); irR = rng.standard_normal(irn) * np.exp(-ti / 0.55)
irL, irR = lp(irL, 4500), lp(irR, 4500)
irL /= np.sqrt((irL ** 2).sum()); irR /= np.sqrt((irR ** 2).sum())
wetL = fftconvolve(L, irL)[:N]; wetR = fftconvolve(R, irR)[:N]
L = L + 0.32 * wetL; R = R + 0.32 * wetR

# warm master: gentle lowpass, soft saturation, normalize
L, R = lp(L, 10500), lp(R, 10500)
L, R = hp(L, 35), hp(R, 35)
g = 0.9 / max(np.abs(L).max(), np.abs(R).max())
L, R = np.tanh(L * g * 1.2) / 1.2, np.tanh(R * g * 1.2) / 1.2
st = np.stack([L, R], 1)
st /= np.abs(st).max() / 0.89
w = wave.open("aud/music.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
print("music ok", DUR)
