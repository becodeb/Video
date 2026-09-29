"""Final audio mix: voices + pitch + ducked demo beds + music + sfx."""
import json, subprocess, functools
import numpy as np

SR = 48000
tl = json.load(open("timeline.json"))
M = tl["marks"]
TOTAL = M["TOTAL"]
N = int(SR * (TOTAL + 0.3))


@functools.lru_cache(None)
def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def db(x): return 10 ** (x / 20)


def loop_extend(x, need):
    """extend a music bed by jumping back one self-similar period, with crossfade."""
    if len(x) >= need: return x
    env = np.sqrt(np.convolve((x ** 2).mean(1), np.ones(480) / 480, "same"))[::480]  # 10ms
    e = (env - env.mean()) / (env.std() + 1e-9)
    best, bl = -1, None
    for L in range(800, 2400):          # 8..24 s
        a = e[:-L]; b = e[L:]
        c = (a * b).mean()
        if c > best: best, bl = c, L
    L = bl * 480
    jump = int(len(x) * 0.88)           # before the outro sting
    xf = int(SR * 1.2)
    out = x[:jump].copy()
    while len(out) < need:
        seg = x[jump - L: jump]
        f = np.linspace(0, 1, xf)[:, None]
        out[-xf:] = out[-xf:] * (1 - f) + seg[:xf] * f
        out = np.concatenate([out, seg[xf:]])
    print("loop period", L / SR, "corr", round(best, 3))
    return out


def place(buf, x, T, src, dur, g, fin=0.0, fout=0.0, loop=False):
    a = int(src * SR)
    n = int(dur * SR) if dur else len(x) - a
    if loop: x = loop_extend(x, a + n)
    seg = x[a:a + n].copy()
    if fin > 0:
        k = min(len(seg), int(fin * SR)); seg[:k] *= np.linspace(0, 1, k)[:, None]
    if fout > 0:
        k = min(len(seg), int(fout * SR)); seg[-k:] *= np.linspace(1, 0, k)[:, None]
    i = int(T * SR)
    if i < 0: seg = seg[-i:]; i = 0
    m = min(len(seg), N - i)
    buf[i:i + m] += seg[:m] * g


voice = np.zeros((N, 2)); pitch = np.zeros((N, 2)); demo = np.zeros((N, 2)); sfx = np.zeros((N, 2))
for ev in tl["audio"]:
    x = load(ev["path"])
    tgt = {"vo": voice, "pitch": pitch, "demo": demo, "sfx": sfx}[ev["role"]]
    g = db(ev.get("gain_db", 0) + (-5 if ev["role"] == "sfx" else 0))
    place(tgt, x, ev["T"], ev["src"], ev["dur"], g, ev.get("fin", .005), ev.get("fout", .02), ev.get("loop", False))

# ---- speech activity envelope (for ducking)
sp = voice + pitch
hop = 480
rms = np.sqrt(np.convolve((sp ** 2).mean(1), np.ones(hop * 2) / (hop * 2), "same"))[::hop]
act = (20 * np.log10(rms + 1e-9) > -42).astype(float)
# lookahead 120ms, attack 80ms, release 450ms
act = np.roll(act, -12)
envd = np.zeros_like(act); v = 0.0
for i, a in enumerate(act):
    k = 1 - np.exp(-1 / (8 if a > v else 45))
    v += (a - v) * k; envd[i] = v
duck = np.repeat(envd, hop)[:N]
if len(duck) < N: duck = np.pad(duck, (0, N - len(duck)))
duck = duck[:, None]

# ---- demo beds: lowered under the voice-over
demo_g = db(-7) * (1 - duck) + db(-15) * duck
demo *= demo_g

# ---- music bed
mus = load("aud/c_music.wav")
music = np.zeros((N, 2))
m = min(len(mus), N); music[:m] = mus[:m]
t = np.arange(N) / SR
gate = np.ones(N)
for (a, b) in tl["music"]["blocks"]:
    fa = np.clip((t - a) / 1.0, 0, 1); fb = np.clip((t - b) / 1.2, 0, 1)
    gate *= 1 - (fa - fb)        # 0 inside block, crossfaded edges
gate = np.clip(gate, 0, 1)
base = np.full(N, -9.0)                       # music level without speech
base[t < 1.5] = -9 - 10 * (1 - t[t < 1.5] / 1.5)   # gentle fade-in at the very start
# pause insert: music a bit more present
ins = (t > M["T_INS0"]) & (t < M["T_INS1"])
base[ins] = -8.0
end = t > M["END0"]
base[end] = -6.0
mgain_db = base[:, None] * (1 - duck) + (base[:, None] - 10.5) * duck
music *= db(mgain_db) * gate[:, None]
# fade out at the end
fo = np.clip((TOTAL - t) / 1.6, 0, 1)[:, None]
music *= fo

mix = voice + pitch + demo + music + sfx
mix *= fo ** 0.5
out = mix.astype(np.float32)
out.tofile("aud/mix_raw.f32")
print("mix peak", 20 * np.log10(np.abs(out).max()), "len", len(out) / SR)

def lvl(x, a, b):
    s = x[int(a * SR):int(b * SR)]
    return 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9)
for name, (a, b) in {"ini": (1, 34), "card1": M["CARD1"], "kodu": (M["KB"] + 3, M["CARD2"][0]), "testra": (M["TB"] + 3, M["CARD3"][0]),
                     "echo": (M["EB"] + 1, M["CARD4"][0]), "card4": M["CARD4"], "final": (M["F0"] + 1, M["TP"]), "insert": (M["T_INS0"], M["T_INS1"]), "end": (M["END0"], M["TOTAL"])}.items():
    print(f"{name:7s} voice {lvl(voice,a,b):6.1f} pitch {lvl(pitch,a,b):6.1f} demo {lvl(demo,a,b):6.1f} music {lvl(music,a,b):6.1f} sfx {lvl(sfx,a,b):6.1f}")
