"""Subtle UI sound effects, synthesized."""
import numpy as np, wave
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(3)


def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], "band", fs=SR, output="sos"), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x)


def T(d): return np.arange(int(SR * d)) / SR


def save(name, x, peak=0.5):
    x = x / (np.abs(x).max() + 1e-9) * peak
    fade = np.minimum(1, (len(x) - np.arange(len(x))) / (SR * 0.01))
    x = x * (fade[:, None] if x.ndim == 2 else fade)
    st = np.stack([x, x], 1) if x.ndim == 1 else x
    w = wave.open(f"aud/sfx_{name}.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()


def tone(f, d, tau, h=(1, .3, .1)):
    t = T(d)
    return sum(a * np.sin(2 * np.pi * f * (k + 1) * t) for k, a in enumerate(h)) * np.exp(-t / tau) * np.minimum(t / .003, 1)


# whoosh: filtered noise with swept band, soft
t = T(0.75)
nz = rng.standard_normal(len(t))
out = np.zeros(len(t))
seg = 256
for i in range(0, len(t), seg):
    u = i / len(t)
    fc = 300 + 3200 * np.sin(np.pi * u) ** 1.5
    out[i:i + seg] = nz[i:i + seg]
out = np.concatenate([bp(out[i:i + 2048], 250 + 2800 * np.sin(np.pi * i / len(t)), 700 + 5200 * np.sin(np.pi * i / len(t))) for i in range(0, len(t), 2048)])[:len(t)]
out *= np.sin(np.pi * np.clip(t / 0.75, 0, 1)) ** 2
L = out * np.linspace(1.3, .5, len(t)); R = out * np.linspace(.5, 1.3, len(t))
save("whoosh", np.stack([lp(L, 7000), lp(R, 7000)], 1), 0.5)

# pop (bubble)
t = T(0.14)
f = 520 + 900 * np.exp(-t / 0.02)
pop = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035) * np.minimum(t / .002, 1)
save("pop", pop, 0.45)

# click (mouse)
t = T(0.05)
ck = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.004) + 0.4 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t / 0.006)
save("click", ck, 0.45)

# notification (two soft bell tones)
n1 = tone(1318.5, .5, .18, (1, .25, .08)); n2 = tone(1760, .6, .22, (1, .25, .08))
x = np.zeros(int(SR * .75)); x[:len(n1)] += n1; x[int(SR * .11):int(SR * .11) + len(n2)] += n2
save("notify", x, 0.42)

# confirm (rising three-note chime)
x = np.zeros(int(SR * .8))
for k, fr in enumerate((880, 1108.7, 1318.5)):
    s = tone(fr, .6, .2, (1, .2)); i = int(SR * .075 * k); x[i:i + len(s)] += s * (0.8 + .1 * k)
save("confirm", x, 0.4)

# pen scribble / strike
t = T(0.55)
nz = bp(rng.standard_normal(len(t)), 1800, 6000)
am = 0.6 + 0.4 * np.sin(2 * np.pi * 14 * t) ** 2
save("scribble", nz * am * np.sin(np.pi * t / .55) ** .7, 0.3)

# soft "question" boing (tiny upward bend)
t = T(0.28)
f = 380 + 260 * (t / .28) ** 1.4
q = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .12) * np.minimum(t / .004, 1)
save("boing", q, 0.35)

# riser for freeze/pause
t = T(0.45)
r = bp(rng.standard_normal(len(t)), 500, 4000) * (t / .45) ** 2
save("riser", r, 0.25)

# tape stop-ish (for pause): quick downward sine glide
t = T(0.35)
f = 900 * np.exp(-t / .12) + 80
s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .15)
save("tapestop", s, 0.3)
print("sfx ok")
