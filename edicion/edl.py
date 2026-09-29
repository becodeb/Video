"""Edit decision list for the BeCode pitch."""
import json
from engine import *

INI = Source("ini", 24, 4.0)
FIN = Source("fin", 30, 7.0)
KD = Source("kodu", 60)
TS = Source("testra", 60)
EC = Source("echo", 60)

tl = Timeline()
A = tl.audio
BG_RGBA = BG + (255,)


def sfx(name, T, db=0.0):
    A.append(dict(role="sfx", path=f"aud/sfx_{name}.wav", T=T, src=0, dur=None, gain_db=db))


# ---------------------------------------------------------------- overlay builders
def chip(t0, t1, text, color, x=72, y=H - 96, anchor=(0, .5), fg=(255, 255, 255), size=32, dot=True, pop=False):
    tl.ov(t0, t1, lambda b, T: draw_chip(b, text, T, t0, t1, x, y, color, anchor, fg, size, dot))
    if pop: sfx("pop", t0, -9)


def pitch_chip(t0, t1, text, x=80, y=H - 104):
    """white pill with BeCode red dot for the talking-head parts."""
    img = _pitch_pill(text)
    def fn(b, T):
        pin = ramp(T, t0, t0 + .35); pout = ramp(T, t1 - .25, t1)
        sc = lerp(.8, 1, e_back(pin)); al = min(1, pin * 2) * (1 - pout)
        px, py, cw, chh = img.info["core"]
        paste(b, img, x - px * sc, y - (chh / 2 + py) * sc - 10 * pout, al, sc, anchor=(0, 0))
    tl.ov(t0, t1, fn)


@functools.lru_cache(None)
def _pitch_pill(text):
    f = font("SemiBold", 34)
    tw, th, bb = text_size(text, f)
    asc, _ = f.getmetrics()
    hgt = 70; wid = tw + 96
    im = Image.new("RGBA", (wid, hgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, wid - 1, hgt - 1), hgt // 2, fill=(255, 255, 255, 240))
    d.polygon([(30, 50), (40, 50), (50, 20), (40, 20)], fill=RED)      # BeCode slash
    d.text((66 - bb[0], (hgt - asc) // 2 - 1), text, font=f, fill=INK)
    out, px, py = with_shadow(im, radius=16, offset=(0, 8), opacity=.25)
    out.info["core"] = (px, py, wid, hgt)
    return out


def text_block(lines, t0, t1, y=H - 150, bg=True):
    """elegant quote-like lower text (few words)."""
    def fn(b, T):
        a = env(T, t0, t1, .45, .4)
        if a <= 0: return
        if bg:
            g = _grad()
            paste(b, g, 0, H, a, 1, anchor=(0, 1))
        yy = y
        for k, (txt, wgt, sz, col) in enumerate(lines):
            f = font(wgt, sz)
            tw, th, bb = text_size(txt, f)
            ak = e_out(ramp(T, t0 + .12 * k, t0 + .12 * k + .5)) * (1 - ramp(T, t1 - .4, t1))
            lay = Image.new("RGBA", (tw + 20, sz + 30), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((10 - bb[0], 6), txt, font=f, fill=col)
            paste(b, lay, W / 2, yy + 18 * (1 - ak), ak, 1)
            yy += sz * 1.25
    tl.ov(t0, t1, fn)


@functools.lru_cache(None)
def _grad():
    g = np.zeros((380, W, 4), np.uint8)
    a = (np.linspace(0, 1, 380) ** 1.6 * 175).astype(np.uint8)
    g[..., 3] = a[:, None]
    g[..., :3] = (8, 10, 18)
    return Image.fromarray(g, "RGBA")


def qmarks(t0, t1, pts, color):
    """little ? pops (humor)."""
    def fn(b, T):
        for k, (x, y, rot) in enumerate(pts):
            tk = t0 + .16 * k
            if T < tk: continue
            p = e_back(ramp(T, tk, tk + .3), 2.6); a = 1 - ramp(T, t1 - .2, t1)
            lay = _qmark(color)
            lay = lay.rotate(rot + 6 * math.sin((T - tk) * 9), Image.BICUBIC, expand=True)
            paste(b, lay, x, y - 10 * p, a * min(1, p * 2), max(.05, p))
    tl.ov(t0, t1, fn)
    for k in range(len(pts)): sfx("boing", t0 + .16 * k, -10 - 2 * k)


@functools.lru_cache(None)
def _qmark(color):
    f = font("ExtraBold", 96)
    lay = Image.new("RGBA", (110, 130), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((22, -6), "?", font=f, fill=color + (255,), stroke_width=6, stroke_fill=(255, 255, 255))
    return with_shadow(lay, 8, (0, 4), .25)[0]


def pen_circle(clip, box_n, t0, t1, color=RED):
    """hand-drawn ellipse drawn progressively (teacher red pen), in source coords of a freeze clip."""
    rng_ = np.random.default_rng(5)
    jit = rng_.normal(0, 1, 8)
    def fx(img, T, c):
        if T < t0 or T > t1: return
        p = e_out(ramp(T, t0, t0 + .55)); a = 1 - ramp(T, t1 - .15, t1)
        x0, y0, x1, y1 = box_to_out(box_n, c.cambox(T), c.src.w, c.src.h)
        cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 + 26, (y1 - y0) / 2 + 20
        n = 90; ang = np.linspace(-2.2, -2.2 + 2 * np.pi * 1.12 * p, max(2, int(n * p)))
        wob = 1 + 0.03 * np.sin(ang * 3 + jit[0]) + 0.02 * np.sin(ang * 5 + jit[1])
        P = [(cx + rx * wob[i] * math.cos(a_), cy + ry * wob[i] * math.sin(a_)) for i, a_ in enumerate(ang)]
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).line(P, fill=color + (int(235 * a),), width=9, joint="curve")
        img.alpha_composite(lay)
    clip.fx.append(fx)


def marker(clip, box_n, t0, t1, color):
    """translucent highlighter sweep over a text line (source coords)."""
    def fx(img, T, c):
        if T < t0 or T > t1: return
        p = e_io(ramp(T, t0, t0 + .6)); a = 1 - ramp(T, t1 - .2, t1)
        x0, y0, x1, y1 = box_to_out(box_n, c.cambox(T), c.src.w, c.src.h)
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle((x0 - 10, y0 - 6, x0 - 10 + (x1 - x0 + 20) * p, y1 + 6), 10,
                                              fill=color + (int(70 * a),))
        img.alpha_composite(lay, (0, 0)) if True else None
        # draw below text: use multiply-ish by compositing then re-darkening text is not possible; keep light alpha
    clip.fx.insert(0, fx)


# ---------------------------------------------------------------- cards (BeCode slash wipe)
@functools.lru_cache(None)
def card_bg():
    im = Image.new("RGBA", (W, H), BG_RGBA)
    d = ImageDraw.Draw(im)
    for x in range(24, W, 48):
        for y in range(24, H, 48):
            d.ellipse((x - 1.6, y - 1.6, x + 1.6, y + 1.6), fill=(222, 223, 229, 255))
    # soft vignette to white centre
    v = Image.new("L", (W, H), 0)
    ImageDraw.Draw(v).ellipse((W * .18, H * .08, W * .82, H * .92), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(160))
    white = Image.new("RGBA", (W, H), (250, 250, 249, 255)); white.putalpha(v)
    im.alpha_composite(white)
    logo = becode_logo(64)
    im.alpha_composite(logo, (W - logo.width - 56, H - logo.height - 44))
    return im


@functools.lru_cache(None)
def becode_logo(h):
    im = Image.open(f"{SP}/src/Logo becode.png").convert("RGB")
    a = np.asarray(im).astype(np.float32)
    d = 255 - a.min(-1)
    al = np.clip((d - 18) / 60, 0, 1)
    ys, xs = np.where(al > .5)
    rgba = np.dstack([a, al * 255]).astype(np.uint8)[ys.min() - 2:ys.max() + 3, xs.min() - 2:xs.max() + 3]
    lg = Image.fromarray(rgba, "RGBA")
    return lg.resize((round(lg.width * h / lg.height), h), Image.LANCZOS)


def product_block(key, name, tagline):
    """icon + name + tagline, returns RGBA."""
    icon = {"kodu": asset("kodu_icon", 150), "testra": asset("testra_icon", 124), "echo": asset("echo_icon", 132)}[key]
    fN = font("ExtraBold", 136); fT = font("Medium", 46)
    nw, nh, nb = text_size(name, fN); tw, th, tb = text_size(tagline, fT)
    gap = 44
    wid = icon.width + gap + max(nw, tw) + 10
    hgt = max(icon.height, 250)
    im = Image.new("RGBA", (wid, hgt), (0, 0, 0, 0))
    im.alpha_composite(icon, (0, (hgt - icon.height) // 2 - 8))
    d = ImageDraw.Draw(im)
    tx = icon.width + gap
    d.text((tx - nb[0], 10 - nb[1] + 20), name, font=fN, fill=INK)
    d.text((tx - tb[0], 10 + 136 + 36 - tb[1]), tagline, font=fT, fill=PRODUCT[key])
    return im


def card_segment(T0, T1, stages, prev_seg, next_seg, win=.5, wout=.5, kind="product"):
    """stages: list of (t_start_rel, spec); spec = ('product', key, name, tagline, done) or ('closing', ...)."""
    def draw_content(T):
        lay = card_bg().copy()
        rel = T - T0
        cur = max([i for i, (ts, _) in enumerate(stages) if rel >= ts] or [0])
        for i, (ts, spec) in enumerate(stages):
            te = stages[i + 1][0] if i + 1 < len(stages) else 1e9
            if rel < ts - .01 or rel > te + .32: continue
            d0 = .12 if i == 0 else .16
            pin = e_out(ramp(rel, ts + d0, ts + d0 + .42))
            pout = e_in(ramp(rel, te, te + .2))
            dy = 60 * (1 - pin) - 70 * pout
            a = min(pin * 1.4, 1) * (1 - pout)
            draw_spec(lay, spec, rel - ts, a, dy)
        # ecosystem row
        spec = stages[cur][1]
        if spec[0] == "product":
            key, done = spec[1], spec[4]
            pills = ecosystem_row(key, done)
            tot = sum(p.width for p in pills) - 40
            x = (W - tot) / 2
            ar = e_out(ramp(T - T0, 0.05, .5))
            for p in pills:
                paste(lay, p, x, 250 - 20 * (1 - ar), ar, 1, anchor=(0, .5)); x += p.width - 40
        return lay

    def fn(T):
        pin = e_io(ramp(T, T0, T0 + win)); pout = e_io(ramp(T, T1 - wout, T1))
        off = SLOPE * H / 2 + BAR + 10
        xr = lerp(-off, W + off, pin); xl = lerp(-off, W + off, pout)
        under = prev_seg.draw(T) if pout <= 0 else next_seg.draw(T)
        if pin >= 1 and pout <= 0:
            return draw_content(T)
        base = under
        cont = draw_content(T)
        cont.putalpha(band_mask(xl, xr))
        base.alpha_composite(cont)
        if pin < 1: base.alpha_composite(slash_layer(xr - 4, xr + BAR, RED))
        if pout > 0 and pout < 1:
            base.alpha_composite(slash_layer(xl - BAR, xl + 4, RED))
            base.alpha_composite(slash_layer(xl - BAR - 26, xl - BAR - 8, INK))
        if pin < 1:
            base.alpha_composite(slash_layer(xr + BAR + 8, xr + BAR + 26, INK))
        return base

    sfx("whoosh", T0 - .1, -6)
    sfx("whoosh", T1 - wout - .05, -8)
    return Custom(T0, T1, fn, tag="card")


def draw_spec(lay, spec, rel, a, dy):
    if a <= 0: return
    if spec[0] == "product":
        _, key, name, tagline, done = spec
        blk = _pblock(key, name, tagline)
        paste(lay, blk, W / 2, H / 2 + 40 + dy, a, 1)
    elif spec[0] == "closing":
        l1 = _txt("Menos carga administrativa.", "ExtraBold", 86, INK)
        l2 = _txt("Más tiempo para escuchar, conversar y acompañar.", "Medium", 52, ECHO)
        paste(lay, l1, W / 2, H / 2 - 40 + dy, a, 1)
        a2 = a * e_out(ramp(rel, .35, .8))
        paste(lay, l2, W / 2, H / 2 + 60 + dy + 20 * (1 - a2), a2, 1)
    elif spec[0] == "eco":
        l1 = _txt("Un ecosistema para la escuela", "ExtraBold", 74, INK)
        paste(lay, l1, W / 2, H / 2 - 150 + dy, a, 1)
        logos = [asset("kodu_word", 118), asset("testra_word", 82), asset("echo_word", 100)]
        tot = sum(l.width for l in logos) + 2 * 170
        x = (W - tot) / 2
        for k, lg in enumerate(logos):
            ak = a * e_back(ramp(rel, .25 + .18 * k, .6 + .18 * k), 1.4)
            paste(lay, lg, x + lg.width / 2, H / 2 + 60 + dy + 30 * (1 - ak), min(1, ak), max(.2, ak))
            x += lg.width + 170
        sub = _txt("Kodu · Testra · Echo — creadas desde adentro de la escuela", "Medium", 38, GREY)
        a3 = a * e_out(ramp(rel, .9, 1.4))
        paste(lay, sub, W / 2, H / 2 + 220 + dy, a3, 1)


@functools.lru_cache(None)
def _pblock(key, name, tagline): return product_block(key, name, tagline)


@functools.lru_cache(None)
def _txt(txt, wgt, sz, col):
    f = font(wgt, sz); tw, th, bb = text_size(txt, f)
    lay = Image.new("RGBA", (tw + 20, int(sz * 1.45)), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((10 - bb[0], int(sz * .1)), txt, font=f, fill=col)
    return lay


# ================================================================ BUILD
T = 0.0
segs = []

# ---------------------------------------------------------------- 1. PITCH INICIAL
I0 = T
def ini(s0, s1, keys, xin=None, xd=0):
    c = Clip(INI, I0 + (s0 - 4.35), I0 + (s1 - 4.35), s0, s1, keys, xin, xd, tag="ini")
    return tl.add(c)

L_, M_, R_ = (.30, .54), (.50, .50), (.70, .46)
ini(4.35, 8.9, [(0, .5, .5, 1.0), (4.55, .5, .48, 1.09)])
ini(8.9, 16.3, [(0, *L_, 1.38), (7.4, L_[0] + .02, L_[1], 1.5)])
ini(16.3, 19.8, [(0, *M_, 1.42), (3.5, .5, .49, 1.5)])
ini(19.8, 22.1, [(0, .5, .47, 1.78), (2.3, .5, .47, 1.86)])
ini(22.1, 25.85, [(0, .5, .5, 1.1), (3.75, .5, .5, 1.0)])
ini(25.85, 31.8, [(0, *R_, 1.4), (5.95, R_[0], R_[1] - .01, 1.5)])
ini_last = ini(31.8, 38.95, [(0, .5, .52, 1.0), (7.15, .5, .5, 1.07)])
T = I0 + (38.95 - 4.35)
TI_END = T

def iT(s): return I0 + (s - 4.35)
pitch_chip(iT(12.3), iT(14.6), "Profes de programación y robótica")
pitch_chip(iT(14.7), iT(16.25), "Asistentes de tecnología")
pitch_chip(iT(20.0), iT(22.0), "Lo vivimos todos los días")
pitch_chip(iT(23.4), iT(25.8), "Soluciones mano a mano con docentes")


# product badges row (Kodu/Testra/Echo) during the list
def badge_row(ts):
    items = [("kodu", "Recursos didácticos"), ("testra", "Evaluaciones digitales"), ("echo", "Reuniones y actas")]
    imgs = [_badge(k, t) for k, t in items]
    def fn(b, T):
        tot = sum(i.width for i in imgs) + 2 * 6
        x = (W - tot) / 2
        for k, im in enumerate(imgs):
            p = ramp(T, ts[k], ts[k] + .4)
            out = ramp(T, TI_END - .05, TI_END + .25)
            if p > 0:
                paste(b, im, x + im.width / 2, H - 150 + 30 * (1 - e_out(p)), min(1, p * 2) * (1 - out), lerp(.85, 1, e_back(p)))
            x += im.width + 6
    tl.ov(ts[0], TI_END + .3, fn)
    for t_ in ts: sfx("pop", t_, -8)


@functools.lru_cache(None)
def _badge(key, text):
    icon = {"kodu": asset("kodu_icon", 64), "testra": asset("testra_icon", 58), "echo": asset("echo_icon", 60)}[key]
    name = {"kodu": "KODU", "testra": "TESTRA", "echo": "ECHO"}[key]
    fN, fT = font("ExtraBold", 36), font("Medium", 26)
    nw, _, nb = text_size(name, fN); tw, _, tb = text_size(text, fT)
    wid = 36 + icon.width + 22 + max(nw, tw) + 40; hgt = 118
    im = Image.new("RGBA", (wid, hgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, wid - 1, hgt - 1), 26, fill=(255, 255, 255, 245))
    im.alpha_composite(icon, (32, (hgt - icon.height) // 2))
    x = 32 + icon.width + 22
    d.text((x - nb[0], 20 - nb[1] + 4), name, font=fN, fill=PRODUCT[key] if key != "echo" else ECHO_DARK)
    d.text((x - tb[0], 68 - tb[1]), text, font=fT, fill=GREY)
    return with_shadow(im, 18, (0, 10), .28)[0]


badge_row([iT(33.35), iT(35.55), iT(37.85)])

A.append(dict(role="pitch", path="aud/c_ini.wav", T=I0, src=4.35, dur=38.95 - 4.35, gain_db=0, fin=.06, fout=.12))

# ---------------------------------------------------------------- KODU
CARD1 = (T, T + 1.9)
KB = CARD1[1] - 1.3          # VO file t=0 on timeline
def kv(v): return KB + v
def kc(v0, v1, s0, s1, keys=None, xin=None, xd=0, rings=None):
    return tl.add(Clip(KD, kv(v0), kv(v1), s0, s1, keys, xin, xd, rings=rings, tag="kodu"))

card1_idx = len(tl.segs); tl.segs.append(None)
k1 = kc(1.3, 2.87, 1.9, 3.47)
k2 = kc(2.87, 6.23, 5.05, 5.78, [(0, .5, .6, 1.34), (3.36, .5, .61, 1.5)])
# gallery freeze: simulation -> graph -> game
k3 = kc(6.23, 8.28, 45.9, 45.9, [(0, .80, .45, 1.62), (1.0, .80, .45, 1.66), (1.25, .50, .45, 1.62), (2.05, .50, .45, 1.66)], xin="push", xd=.22,
        rings=[((.665, .235, .965, .63), kv(6.35), kv(7.22), KODU), ((.355, .235, .655, .63), kv(7.42), kv(8.28), KODU)])
k3b = kc(8.28, 9.53, 50.2, 50.2, [(0, .79, .46, 1.55), (1.25, .79, .45, 1.64)], xin="fade", xd=.14,
         rings=[((.665, .27, .965, .60), kv(8.36), kv(9.53), KODU)])
chip(kv(6.35), kv(7.25), "Simulación", KODU, x=72, y=H - 90)
chip(kv(7.42), kv(8.28), "Gráfico interactivo", KODU, x=72, y=H - 90)
chip(kv(8.36), kv(9.5), "Juego", KODU, x=72, y=H - 90)
# the problem: "¿Three.js? ¿WebGL?" (humor freeze)
k4 = kc(9.53, 10.95, 5.78, 6.42, [(0, .5, .5, 1.0), (1.42, .5, .55, 1.08)], xin="push", xd=.2)
k4b = kc(10.95, 12.95, 6.42, 6.42, [(0, .47, .72, 1.9), (2.0, .47, .72, 2.0)])
qmarks(kv(11.15), kv(12.95), [(1600, 400, -12), (1660, 660, 10), (300, 470, -8)], KODU)
k5 = kc(12.95, 14.33, 6.55, 7.95, [(0, .5, .52, 1.12), (1.38, .5, .5, 1.0)])
sfx("scribble", kv(12.95), -6)
k6 = kc(14.33, 16.79, 8.25, 10.7, [(0, .5, .5, 1.0), (2.46, .5, .52, 1.06)])
chip(kv(14.9), kv(16.7), "Conversa con la IA", KODU, x=W - 72, y=H - 90, anchor=(1, .5))
k7 = kc(16.79, 20.41, 10.9, 13.95, [(0, .45, .55, 1.04), (3.62, .42, .6, 1.16)])
k8a = kc(20.41, 21.25, 13.95, 14.8)
k8b = kc(21.25, 22.65, 15.0, 16.4)
k8c = kc(22.65, 23.55, 18.75, 19.62, [(0, .5, .5, 1.0), (.9, .5, .45, 1.12)])
sfx("click", kv(22.65 + (19.48 - 18.75) / (19.62 - 18.75) * .9), -4)
chip(kv(22.75), kv(23.55), "Generar", KODU, x=W - 72, y=H - 90, anchor=(1, .5))
k8d = kc(23.55, 26.2, 21.3, 24.45)
t_app = kv(23.55 + (23.55 - 21.3) / (24.45 - 21.3) * 2.65)
sfx("confirm", t_app, -5)
chip(t_app, kv(26.1), "Recurso interactivo listo", KODU, x=W - 72, y=H - 90, anchor=(1, .5), pop=False)
k9a = kc(26.2, 27.35, 26.6, 27.75)
k9b = kc(27.35, 28.45, 31.25, 32.95, [(0, .5, .5, 1.0), (1.1, .42, .62, 1.18)])
sfx("click", kv(28.4), -6)
k9c = kc(28.45, 29.2, 34.5, 35.25)
k9d = kc(29.2, 30.14, 38.6, 39.55)
k10a = kc(30.14, 33.1, 39.6, 42.6, [(0, .5, .5, 1.0), (2.96, .62, .5, 1.1)])
chip(kv(30.5), kv(33.0), "Compartir con un link", KODU, x=W - 72, y=H - 90, anchor=(1, .5))
k10b = kc(33.1, 37.62, 44.9, 49.4, xin="push", xd=.2)
chip(kv(33.5), kv(37.5), "Galería entre colegas", KODU, x=W - 72, y=H - 90, anchor=(1, .5))
k11 = kc(37.62, 39.6, 35.3, 37.3, [(0, .5, .5, 1.0), (1.98, .55, .5, 1.08)])
k12 = kc(39.6, 42.6, 52.4, 54.75, xin="fade", xd=.25)
k12b = kc(42.6, 45.3, 54.75, 54.75, [(0, .5, .5, 1.0), (2.7, .5, .5, 1.04)])
T = kv(45.3)
A.append(dict(role="vo", path="aud/c_vkodu.wav", T=KB, src=0, dur=45.18, gain_db=0))
A.append(dict(role="demo", path="aud/c_dkodu.wav", T=kv(1.2), src=1.0, dur=45.3 - 1.2 + .8, gain_db=0, fin=.4, fout=.8))

# ---------------------------------------------------------------- TESTRA
CARD2 = (T, T + 2.3)
TB = CARD2[1] - 1.3
def tv(v): return TB + v
def tc(v0, v1, s0, s1, keys=None, xin=None, xd=0, rings=None):
    return tl.add(Clip(TS, tv(v0), tv(v1), s0, s1, keys, xin, xd, rings=rings, tag="testra"))

card2_idx = len(tl.segs); tl.segs.append(None)
t1 = tc(1.3, 2.45, 0.35, 1.5)
t1b = tc(2.45, 4.92, 12.95, 13.85, [(0, .5, .5, 1.05), (2.47, .5, .42, 1.22)])
chip(tv(3.3), tv(4.85), "Dos problemas", (60, 64, 80), x=72, y=H - 90)
t2 = tc(4.92, 7.03, 1.6, 2.5, [(0, .5, .5, 1.0), (2.11, .3, .68, 1.3)])
chip(tv(5.0), tv(6.95), "1 · Poca flexibilidad", (60, 64, 80), x=72, y=H - 90, pop=False)
t3 = tc(7.03, 10.04, 9.1, 10.7, [(0, .45, .5, 1.05), (3.0, .62, .45, 1.2)])
chip(tv(7.15), tv(9.95), "2 · Desconfianza", (60, 64, 80), x=W - 72, y=H - 90, anchor=(1, .5))
t4 = tc(10.04, 11.8, 31.15, 32.9, [(0, .5, .47, 1.45), (1.76, .5, .47, 1.6)], xin="flash", xd=.25)
t5 = tc(11.8, 12.9, 2.4, 3.3)
t5b = tc(12.9, 16.02, 3.3, 3.95, [(0, .5, .5, 1.0), (.55, .22, .74, 1.95), (3.12, .22, .75, 2.05)],
         rings=[((.065, .675, .255, .935), tv(13.4), tv(15.95), TESTRA)])
chip(tv(13.5), tv(15.95), "Múltiples formatos de consigna", TESTRA, x=W - 72, y=H - 90, anchor=(1, .5))
t6 = tc(16.02, 19.1, 26.4, 28.05, [(0, .5, .5, 1.0), (3.08, .45, .58, 1.12)], xin="push", xd=.2)
chip(tv(16.2), tv(19.0), "Corrección asistida", TESTRA, x=W - 72, y=H - 90, anchor=(1, .5))
t7 = tc(19.1, 21.78, 6.05, 8.55)
chip(tv(19.4), tv(21.7), "Ingreso con código", TESTRA, x=W - 72, y=H - 90, anchor=(1, .5))
t8 = tc(21.78, 23.28, 11.0, 12.5)
t8b = tc(23.28, 24.12, 13.0, 13.85)
t9a = tc(24.12, 25.35, 16.95, 18.2)
sfx("notify", tv(24.2), -4)
chip(tv(24.2), tv(25.3), "Evento detectado", AMBER, x=72, y=H - 90)
t9b = tc(25.35, 26.84, 22.62, 22.62, [(0, .32, .36, 1.35), (1.49, .32, .36, 1.45)])
chip(tv(25.45), tv(26.8), "Copiar / pegar", AMBER, x=W - 72, y=H - 90, anchor=(1, .5))
t10 = tc(26.84, 28.79, 13.85, 15.8)
sfx("notify", tv(26.84 + (14.8 - 13.85) / (15.8 - 13.85) * 1.95), -3)
chip(tv(27.9), tv(28.75), "Aviso al alumno", TESTRA, x=72, y=H - 90)
t11 = tc(28.79, 31.77, 22.35, 24.4, [(0, .5, .5, 1.0), (2.98, .5, .5, 1.05)], xin="push", xd=.2)
chip(tv(29.0), tv(31.7), "Reporte cronológico", TESTRA, x=W - 72, y=H - 90, anchor=(1, .5))
# change of rhythm: Testra doesn't decide
t12 = tc(31.77, 34.3, 15.6, 15.6, [(0, .47, .5, 1.2), (2.53, .45, .49, 1.55)], xin="fade", xd=.3)
marker(t12, (.205, .478, .64, .508), tv(32.3), tv(34.3), TESTRA)
chip(tv(32.5), tv(34.25), "Sin sanciones automáticas", TESTRA, x=W / 2, y=H - 100, anchor=(.5, .5))
t13 = tc(34.3, 35.6, 19.95, 20.9, xin="fade", xd=.2)
t13b = tc(35.6, 37.4, 29.6, 30.9)
chip(tv(35.7), tv(37.35), "Contexto para el docente", TESTRA, x=W - 72, y=H - 90, anchor=(1, .5))
t14 = tc(37.4, 38.55, 24.8, 25.65)
t14b = tc(38.55, 41.9, 28.75, 29.25, [(0, .5, .5, 1.0), (3.35, .36, .66, 1.3)])
chip(tv(39.0), tv(41.8), "El docente decide", TESTRA, x=W - 72, y=H - 90, anchor=(1, .5))
sfx("confirm", tv(38.6), -9)
T = tv(41.9)
A.append(dict(role="vo", path="aud/c_vtestra.wav", T=TB, src=0, dur=41.47, gain_db=0))
A.append(dict(role="demo", path="aud/c_dtestra.wav", T=tv(1.1), src=0.0, dur=41.9 - 1.1 + .8, gain_db=0, fin=.4, fout=.8, loop=True))

# ---------------------------------------------------------------- ECHO
CARD3 = (T, T + 2.2)
EB = CARD3[1] + 0.05
def ev(v): return EB + v
def ecl(v0, v1, s0, s1, keys=None, xin=None, xd=0, rings=None):
    return tl.add(Clip(EC, ev(v0), ev(v1), s0, s1, keys, xin, xd, rings=rings, tag="echo"))

card3_idx = len(tl.segs); tl.segs.append(None)
e1 = ecl(-0.05, 4.9, 8.8, 9.4, [(0, .5, .53, 1.2), (4.95, .5, .5, 1.32)],
         rings=[((.318, .258, .495, .312), ev(.9), ev(2.4), ECHO), ((.318, .588, .69, .643), ev(2.5), ev(4.8), ECHO)])
e2 = ecl(4.9, 8.9, 5.75, 7.3, [(0, .5, .5, 1.0), (4.0, .5, .5, 1.22)], xin="push", xd=.22)
chip(ev(5.3), ev(11.9), "ANTES", (70, 74, 88), x=72, y=H - 90, dot=False)
e2b = ecl(8.9, 11.25, 7.3, 7.3, [(0, .5, .52, 2.0), (2.35, .5, .53, 2.12)])
pen_circle(e2b, (.40, .565, .585, .60), ev(9.25), ev(11.25))
sfx("scribble", ev(9.25), -9)
e2c = ecl(11.25, 11.93, 7.3, 7.95, [(0, .5, .46, 1.6), (.68, .5, .5, 1.05)])
sfx("scribble", ev(11.25), -6)
e3 = ecl(11.93, 12.6, 7.95, 8.45)
e3b = ecl(12.6, 14.46, 9.4, 11.3)
chip(ev(12.0), ev(14.4), "DESPUÉS", ECHO, x=72, y=H - 90, dot=False)
sfx("click", ev(12.6 + (9.52 - 9.4) / 1.9 * 1.86), -5); sfx("click", ev(12.6 + (10.72 - 9.4) / 1.9 * 1.86), -5)
e4 = ecl(14.46, 17.72, 11.3, 14.6, [(0, .5, .5, 1.0), (3.26, .52, .45, 1.1)])
chip(ev(15.0), ev(17.6), "Transcripción en vivo", ECHO, x=W - 72, y=H - 90, anchor=(1, .5))
e5a = ecl(17.72, 19.4, 15.1, 16.8)
e5b = ecl(19.4, 20.9, 17.2, 18.7)
chip(ev(19.5), ev(20.85), "Identifica participantes", ECHO, x=W - 72, y=H - 90, anchor=(1, .5))
e5c = ecl(20.9, 23.45, 22.0, 24.55, xin="push", xd=.2)
sfx("confirm", ev(21.0), -5)
chip(ev(21.0), ev(23.4), "Acta automática", ECHO, x=W - 72, y=H - 90, anchor=(1, .5), pop=False)
e5d = ecl(23.45, 24.45, 24.55, 25.55)
e5e = ecl(24.45, 25.37, 31.5, 32.4)
chip(ev(24.5), ev(25.35), "Tareas y compromisos", ECHO, x=W - 72, y=H - 90, anchor=(1, .5))
e6a = ecl(25.37, 27.0, 26.1, 27.7, [(0, .6, .5, 1.25), (1.63, .64, .5, 1.3)],
          rings=[((.465, .492, .71, .565), ev(25.5), ev(26.35), ECHO), ((.72, .492, .84, .565), ev(26.35), ev(27.0), ECHO)])
e6b = ecl(27.0, 28.89, 28.2, 30.1)
chip(ev(27.2), ev(28.85), "Exportar a PDF", ECHO, x=W - 72, y=H - 90, anchor=(1, .5))
e7 = ecl(28.89, 32.0, 34.2, 37.3, xin="push", xd=.2)
chip(ev(29.2), ev(31.9), "Consulta con IA", ECHO, x=W - 72, y=H - 90, anchor=(1, .5))
e8 = ecl(32.0, 33.7, 39.15, 40.85)
e8b = ecl(33.7, 35.61, 19.6, 21.5)
chip(ev(32.2), ev(35.5), "Seguimiento por familia", ECHO, x=W - 72, y=H - 90, anchor=(1, .5))
e9 = ecl(35.61, 38.94, 37.4, 38.95, [(0, .5, .5, 1.0), (3.33, .5, .56, 1.12)], xin="fade", xd=.25)
text_block([("Menos notas. Más conversación.", "ExtraBold", 62, (255, 255, 255))], ev(36.0), ev(38.9), y=H - 175)
e10 = ecl(38.94, 41.3, 42.1, 44.3, xin="fade", xd=.2)
T = ev(41.3)
A.append(dict(role="vo", path="aud/c_vecho.wav", T=EB, src=0, dur=40.26, gain_db=0))
A.append(dict(role="demo", path="aud/c_decho.wav", T=ev(-.4), src=1.0, dur=41.3 + .4 + .8, gain_db=0, fin=.4, fout=.8))

# ---------------------------------------------------------------- CLOSING / ECOSYSTEM CARD
CARD4 = (T, T + 4.7)
card4_idx = len(tl.segs); tl.segs.append(None)
T = CARD4[1]

# ---------------------------------------------------------------- PITCH FINAL
F0 = T
S_START, S_PAUSE, S_END = 7.95, 84.4, 90.85
def fT(s): return F0 + (s - S_START)
def fin(s0, s1, keys, xin=None, xd=0, T0=None):
    base = F0 if T0 is None else T0
    ss = S_START if T0 is None else s_ref[0]
    c = Clip(FIN, base + (s0 - ss), base + (s1 - ss), s0, s1, keys, xin, xd, tag="fin")
    return tl.add(c)
s_ref = [S_START]
Lf, Rf = (.36, .45), (.64, .42)
fin(7.95, 13.7, [(0, .5, .5, 1.0), (5.75, .5, .48, 1.07)])
fin(13.7, 18.9, [(0, *Lf, 1.2), (5.2, Lf[0], Lf[1], 1.26)])
fin(18.9, 26.4, [(0, .5, .5, 1.04), (7.5, .5, .48, 1.1)])
fin(26.4, 29.6, [(0, *Lf, 1.24), (3.2, Lf[0] + .01, Lf[1], 1.3)])
fin(29.6, 38.9, [(0, .5, .5, 1.08), (9.3, .5, .5, 1.0)])
fin(38.9, 47.7, [(0, *Rf, 1.2), (8.8, Rf[0], Rf[1], 1.27)])
fin(47.7, 52.3, [(0, .5, .5, 1.0), (4.6, .5, .48, 1.06)])
fin(52.3, 64.0, [(0, *Rf, 1.18), (11.7, Rf[0] - .02, Rf[1] - .02, 1.1)])
fin(64.0, 77.5, [(0, .5, .45, 1.08), (13.5, .52, .44, 1.14)])
pre_pause = fin(77.5, S_PAUSE, [(0, *Lf, 1.2), (6.9, Lf[0], Lf[1], 1.26)])
TP = fT(S_PAUSE)

pitch_chip(fT(9.5), fT(13.5), "Desarrolladas, probadas y validadas con docentes")
pitch_chip(fT(16.4), fT(18.8), "Acompañamiento desde el primer día")
pitch_chip(fT(19.6), fT(22.6), "Capacitaciones para docentes y directivos")
pitch_chip(fT(23.2), fT(26.3), "Soporte directo y continuo")
pitch_chip(fT(27.6), fT(29.5), "Somos los desarrolladores")
pitch_chip(fT(30.6), fT(33.3), "Herramientas adaptadas a cada colegio")
pitch_chip(fT(40.2), fT(43.6), "Licencia institucional por sede")
pitch_chip(fT(43.8), fT(47.5), "Sin costo por docente individual")
pitch_chip(fT(48.4), fT(52.0), "Ciclo lectivo anual")
pitch_chip(fT(78.4), fT(83.9), "Varias sedes: propuesta personalizada")


# pricing strips
def price_strip(t0, t1, title, cells, reveal):
    """cells: [(logo_or_None, label, price)], reveal: times for each cell."""
    def fn(b, T):
        a = env(T, t0, t1, .45, .35)
        if a <= 0: return
        img = _strip(title, tuple((c[0], c[1], c[2]) for c in cells))
        paste(b, img["panel"], W / 2, H - 40 + 40 * (1 - e_out(ramp(T, t0, t0 + .5))), a, 1, anchor=(.5, 1))
        x0 = W / 2 - img["panel"].width / 2
        for k, (cell, cx) in enumerate(zip(img["cells"], img["xs"])):
            p = ramp(T, reveal[k], reveal[k] + .4)
            if p <= 0: continue
            paste(b, cell, x0 + cx, H - 40 - img["cell_y"] + 20 * (1 - e_out(p)) + 40 * (1 - e_out(ramp(T, t0, t0 + .5))),
                  a * min(1, p * 2), lerp(.9, 1, e_back(p)), anchor=(.5, .5))
    tl.ov(t0, t1, fn)
    for r in reveal: sfx("pop", r, -10)


@functools.lru_cache(None)
def _strip(title, cells):
    cw, ch, gap = 430, 150, 26
    pw = len(cells) * cw + (len(cells) - 1) * gap + 60
    ph = ch + 110
    panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(panel)
    d.rounded_rectangle((0, 0, pw - 1, ph - 1), 30, fill=(255, 255, 255, 238))
    d.polygon([(34, 58), (44, 58), (56, 26), (46, 26)], fill=RED)
    f = font("Bold", 32); d.text((70, 22), title, font=f, fill=INK)
    panel = with_shadow(panel, 22, (0, 12), .3)[0]
    pad = (panel.width - pw) // 2
    outs, xs = [], []
    for k, (logo, label, price) in enumerate(cells):
        c = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        dc = ImageDraw.Draw(c)
        dc.rounded_rectangle((0, 0, cw - 1, ch - 1), 22, fill=(244, 245, 248, 255))
        x = 26
        if logo:
            lg = asset(logo, 44 if "testra" in logo else 50)
            c.alpha_composite(lg, (x, 24))
        else:
            dc.text((x, 22), label, font=font("SemiBold", 34), fill=INK)
        dc.text((x, 84), price, font=font("ExtraBold", 40), fill=RED if not logo else INK)
        if logo:
            dc.text((x + 250, 36), label, font=font("Medium", 24), fill=GREY)
        outs.append(c); xs.append(pad + 30 + k * (cw + gap) + cw / 2)
    return {"panel": panel, "cells": outs, "xs": xs, "cell_y": pad + ph - (60 + ch / 2) - 0}


price_strip(fT(56.5), fT(64.0), "Por módulo · licencia mensual",
            [("testra_word", "desde", "US$ 45 / mes"), ("kodu_word", "desde", "US$ 65 / mes"), ("echo_word", "desde", "US$ 75 / mes")],
            [fT(56.85), fT(59.1), fT(61.5)])
price_strip(fT(67.2), fT(77.3), "Ecosistema completo · las 3 herramientas",
            [(None, "Colegio pequeño", "US$ 135 / mes"), (None, "Colegio mediano", "US$ 240 / mes"), (None, "Institución grande", "US$ 380 / mes")],
            [fT(67.8), fT(70.6), fT(73.7)])

A.append(dict(role="pitch", path="aud/c_fin.wav", T=F0, src=S_START, dur=S_PAUSE - S_START, gain_db=0, fin=.05, fout=.08))

# ---------------------------------------------------------------- PAUSE INSERT (mouse) + Límites gratuitos
INS = 14.2
T_INS0, T_INS1 = TP, TP + INS
LIM_T = T_INS0 + 1.35          # limites audio start
PAUSE_FRAME = S_PAUSE


def insert_fn(T):
    r = T - T_INS0
    base_clip = pre_pause
    fr = FIN.frame(PAUSE_FRAME)
    box = base_clip.cambox(base_clip.T1)
    img = render_cam(fr, box).convert("RGBA")
    # dim + blur while paused
    dim = e_io(ramp(r, .95, 1.5)) * (1 - e_io(ramp(r, INS - .75, INS - .25)))
    if dim > 0:
        bl = img.filter(ImageFilter.GaussianBlur(10 * dim))
        img = Image.blend(img, bl, 1.0)
        ov = Image.new("RGBA", (W, H), (12, 14, 22, int(120 * dim)))
        img.alpha_composite(ov)
    # player bar
    bar_a = env(r, .1, INS - .1, .3, .3)
    if bar_a > 0: _player_bar(img, r, bar_a)
    # big pause / play flash
    for tc_, kind in ((1.0, "pause"), (INS - .75, "play")):
        p = ramp(r, tc_, tc_ + .55)
        if 0 < p < 1:
            ic = _bigicon(kind)
            paste(img, ic, W / 2, H / 2, (1 - p) * min(1, p * 5), lerp(.8, 1.25, e_out(p)))
    # panel
    pin = e_out(ramp(r, 1.45, 2.0)); pout = e_in(ramp(r, INS - 1.1, INS - .7))
    if pin > 0 and pout < 1:
        _limits_panel(img, r, pin, pout)
    # cursor path
    _cursor(img, r)
    return img


PLAY_BTN = (118, H - 70)


def _player_bar(img, r, a):
    lay = Image.new("RGBA", (W, 150), (0, 0, 0, 0))
    g = np.zeros((150, W, 4), np.uint8); g[..., 3] = (np.linspace(0, 1, 150) ** 1.5 * 150).astype(np.uint8)[:, None]
    lay = Image.fromarray(g, "RGBA")
    d = ImageDraw.Draw(lay)
    prog = (TP - 0) / (tl_total_estimate)
    d.rounded_rectangle((70, 60, W - 70, 66), 3, fill=(255, 255, 255, 90))
    d.rounded_rectangle((70, 60, 70 + (W - 140) * prog, 66), 3, fill=RED + (255,))
    d.ellipse((70 + (W - 140) * prog - 9, 54, 70 + (W - 140) * prog + 9, 72), fill=(255, 255, 255, 255))
    paused = 1.0 <= r < INS - .75
    x, y = PLAY_BTN[0], 110
    if paused:   # play triangle (video paused)
        d.polygon([(x - 12, y - 16), (x - 12, y + 16), (x + 16, y)], fill=(255, 255, 255, 255))
    else:
        d.rectangle((x - 12, y - 15, x - 4, y + 15), fill=(255, 255, 255, 255)); d.rectangle((x + 4, y - 15, x + 12, y + 15), fill=(255, 255, 255, 255))
    ff = font("Medium", 24)
    d.text((170, 96), "BeCode · Pitch institucional", font=ff, fill=(255, 255, 255, 230))
    if a < 1: lay.putalpha(lay.getchannel("A").point(lambda p: int(p * a)))
    img.alpha_composite(lay, (0, H - 150))


@functools.lru_cache(None)
def _bigicon(kind):
    s = 190
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=(10, 12, 20, 150))
    if kind == "pause":
        d.rounded_rectangle((62, 52, 84, 138), 6, fill=(255, 255, 255, 255)); d.rounded_rectangle((106, 52, 128, 138), 6, fill=(255, 255, 255, 255))
    else:
        d.polygon([(72, 50), (72, 140), (146, 95)], fill=(255, 255, 255, 255))
    return im


def _cursor(img, r):
    cur, ox, oy = cursor_img(1.0)
    start = (W * .78, H * .62)
    p1 = e_io(ramp(r, .2, .95))
    pos = (lerp(start[0], PLAY_BTN[0], p1), lerp(start[1], PLAY_BTN[1] + 40, p1 * p1 ** .2))
    if r > 1.2:   # drift up to panel while listening
        p2 = e_io(ramp(r, 1.3, 2.4))
        pos = (lerp(PLAY_BTN[0], W * .73, p2), lerp(PLAY_BTN[1] + 40, H * .78, p2))
    if r > INS - 1.6:
        p3 = e_io(ramp(r, INS - 1.6, INS - .85))
        pos = (lerp(W * .73, PLAY_BTN[0], p3), lerp(H * .78, PLAY_BTN[1] + 40, p3))
    if r > INS - .5:
        p4 = e_in(ramp(r, INS - .5, INS))
        pos = (lerp(PLAY_BTN[0], -80, p4), lerp(PLAY_BTN[1] + 40, H + 80, p4))
    a = min(1, ramp(r, .15, .35))
    press = any(0 < r - tc_ < .14 for tc_ in (.97, INS - .78))
    sc = .86 if press else 1.0
    paste(img, cur, pos[0] - ox * sc, pos[1] - oy * sc, a, sc, anchor=(0, 0))


def _limits_panel(img, r, pin, pout):
    pw, ph = 1180, 600
    pnl = _lim_base(pw, ph)
    x = W / 2; y = H / 2 - 20 + 50 * (1 - pin) - 40 * pout
    a = min(1, pin * 1.5) * (1 - pout)
    paste(img, pnl, x, y, a, lerp(.96, 1, pin))
    x0 = x - pw / 2; y0 = y - ph / 2
    rows = [("testra", "Gratis por tiempo limitado", GREEN, .70), ("kodu", "Versión freemium", KODU, 3.96), ("echo", "Solo pago · para organizaciones", (70, 74, 88), 6.62)]
    for k, (key, txt, col, at) in enumerate(rows):
        tr = LIM_T + at - T_INS0
        p = ramp(r, tr, tr + .45)
        if p <= 0: continue
        row = _lim_row(key, txt, col)
        ry = y0 + 190 + k * 128
        paste(img, row, x0 + 70 + 30 * (1 - e_out(p)), ry, a * min(1, p * 2), 1, anchor=(0, .5))


@functools.lru_cache(None)
def _lim_base(pw, ph):
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, pw - 1, ph - 1), 36, fill=(255, 255, 255, 250))
    d.polygon([(66, 102), (80, 102), (98, 52), (84, 52)], fill=RED)
    d.text((118, 40), "Límites gratuitos", font=font("ExtraBold", 54), fill=INK)
    f2 = font("Medium", 28); tw2 = text_size("Para empezar a usarlas", f2)[0]
    d.text((pw - 70 - tw2, 62), "Para empezar a usarlas", font=f2, fill=GREY)
    d.line((70, 128, pw - 70, 128), fill=(232, 233, 238), width=2)
    return with_shadow(im, 30, (0, 16), .35)[0]


@functools.lru_cache(None)
def _lim_row(key, txt, col):
    logo = {"kodu": asset("kodu_word", 58), "testra": asset("testra_word", 46), "echo": asset("echo_word", 54)}[key]
    rw, rh = 1040, 104
    im = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, rw - 1, rh - 1), 24, fill=(245, 246, 249, 255))
    im.alpha_composite(logo, (34, (rh - logo.height) // 2))
    pill = chip_img(txt, col, (255, 255, 255), 32, "SemiBold", True)
    px, py, cw, chh = pill.info["core"]
    core = pill.crop((px, py, px + cw, py + chh))
    im.alpha_composite(core, (rw - cw - 30, (rh - chh) // 2))
    return im


tl_total_estimate = 1.0  # set below
ins = tl.add(Custom(T_INS0, T_INS1, insert_fn, tag="insert"))
sfx("click", T_INS0 + .97, -2); sfx("tapestop", T_INS0 + 1.0, -8)
sfx("whoosh", T_INS0 + 1.4, -12)
sfx("click", T_INS1 - .78, -2)
for at in (.70, 3.96, 6.62): sfx("pop", LIM_T + at, -9)
A.append(dict(role="vo", path="aud/c_limites.wav", T=LIM_T, src=0, dur=11.75, gain_db=0))

# resume
F1 = T_INS1
s_ref[0] = S_PAUSE
c_last = fin(S_PAUSE, S_END, [(0, .5, .5, 1.0), (S_END - S_PAUSE, .5, .47, 1.08)], T0=F1)
text_block([("“Una gran propuesta pedagógica nunca debería", "SemiBold", 46, (255, 255, 255)),
            ("estar frenada por barreras técnicas.”", "SemiBold", 46, (255, 255, 255))],
           F1 + (85.2 - S_PAUSE), F1 + (89.9 - S_PAUSE), y=H - 200)
A.append(dict(role="pitch", path="aud/c_fin.wav", T=F1, src=S_PAUSE, dur=91.0 - S_PAUSE, gain_db=0, fin=.05, fout=.12))
T = F1 + (S_END - S_PAUSE)

# end: freeze on us + BeCode logo
END0 = T
END_D = 3.4
def end_fn(Tt):
    r = Tt - END0
    fr = FIN.frame(S_END)
    z = 1.08 + .05 * e_out(r / END_D)
    img = render_cam(fr, cam_box(FIN.w, FIN.h, .5, .47, z)).convert("RGBA")
    w_ = e_io(ramp(r, .9, 1.7))
    if w_ > 0:
        img = Image.blend(img, card_bg(), w_ * .96)
    lg = becode_logo(210)
    la = e_out(ramp(r, 1.2, 1.8))
    paste(img, lg, W / 2, H / 2 - 40 + 30 * (1 - la), la, lerp(.9, 1, la))
    sub = _txt("Kodu · Testra · Echo", "SemiBold", 40, GREY)
    sa = e_out(ramp(r, 1.5, 2.1))
    paste(img, sub, W / 2, H / 2 + 120 + 20 * (1 - sa), sa, 1)
    fo = ramp(r, END_D - .6, END_D)
    if fo > 0:
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * e_io(fo)))))
    return img
tl.add(Custom(END0, END0 + END_D, end_fn, tag="end"))
sfx("riser", END0 + .5, -14)
T = END0 + END_D
TOTAL = T
tl_total_estimate = TOTAL

# ---------------------------------------------------------------- fill the cards (need neighbours)
def nxt(i): return tl.segs[i + 1]
tl.segs[card1_idx] = card_segment(CARD1[0], CARD1[1], [(0, ("product", "kodu", "KODU", "De una idea a una experiencia interactiva", ()))],
                                  ini_last, nxt(card1_idx))
tl.segs[card2_idx] = card_segment(CARD2[0], CARD2[1], [(0, ("product", "kodu", "KODU", "Recursos didácticos interactivos", ())),
                                                       (.95, ("product", "testra", "TESTRA", "Evaluaciones digitales con contexto", ("kodu",)))],
                                  tl.segs[card2_idx - 1], nxt(card2_idx))
tl.segs[card3_idx] = card_segment(CARD3[0], CARD3[1], [(0, ("product", "testra", "TESTRA", "Evaluaciones digitales con contexto", ("kodu",))),
                                                       (.85, ("product", "echo", "ECHO", "Reuniones y seguimiento", ("kodu", "testra")))],
                                  tl.segs[card3_idx - 1], nxt(card3_idx))
tl.segs[card4_idx] = card_segment(CARD4[0], CARD4[1], [(0, ("closing",)), (2.35, ("eco",))],
                                  tl.segs[card4_idx - 1], nxt(card4_idx), win=.55, wout=.55)
sfx("pop", CARD2[0] + .95, -12); sfx("pop", CARD3[0] + .85, -12)

# music plan: (T, gain_db) keys; None regions = muted by blocks
MUSIC = dict(path="aud/music.wav", blocks=[(KB + 1.0, kv(45.3)), (TB + 1.0, tv(41.9)), (EB - .2, ev(41.3))])
MARKS = dict(I0=I0, CARD1=CARD1, KB=KB, CARD2=CARD2, TB=TB, CARD3=CARD3, EB=EB, CARD4=CARD4, F0=F0, TP=TP,
             T_INS0=T_INS0, T_INS1=T_INS1, F1=F1, END0=END0, TOTAL=TOTAL, LIM_T=LIM_T)

if __name__ == "__main__":
    json.dump(dict(audio=A, music=MUSIC, marks=MARKS), open("timeline.json", "w"), indent=1)
    print(json.dumps(MARKS, indent=1))
    print("segments", len(tl.segs), "overlays", len(tl.overlays), "audio", len(A))
