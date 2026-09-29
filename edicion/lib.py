import math, os, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

SP = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 30

# ---------------------------------------------------------------- palette
BG = (246, 246, 244)
INK = (17, 19, 28)
RED = (227, 6, 19)          # BeCode red
KODU = (64, 50, 232)
TESTRA = (14, 45, 118)
ECHO = (92, 76, 222)
ECHO_DARK = (11, 14, 23)
GREY = (110, 114, 128)
GREEN = (16, 150, 96)
AMBER = (214, 128, 0)
PRODUCT = {"kodu": KODU, "testra": TESTRA, "echo": ECHO}


# ---------------------------------------------------------------- easing
def c01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def e_io(x):
    x = c01(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def e_out(x): x = c01(x); return 1 - (1 - x) ** 3
def e_in(x): x = c01(x); return x ** 3
def e_back(x, s=1.9):
    x = c01(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2
def ramp(t, a, b): return c01((t - a) / (b - a)) if b > a else float(t >= a)
def env(t, t0, t1, fin=.25, fout=.2):
    """0..1 in/out envelope."""
    return min(ramp(t, t0, t0 + fin), 1 - ramp(t, t1 - fout, t1))


# ---------------------------------------------------------------- fonts
@functools.lru_cache(None)
def font(weight, size):
    return ImageFont.truetype(f"{SP}/fonts/Poppins-{weight}.ttf", int(size))


# ---------------------------------------------------------------- sources
@functools.lru_cache(maxsize=10)
def _load(path):
    return Image.open(path).convert("RGB")


class Source:
    def __init__(self, name, fps, t0=0.0):
        self.dir = f"{SP}/fr/{name}"
        self.fps, self.t0 = fps, t0
        self.n = len(os.listdir(self.dir))
        im = _load(self.path(0))
        self.w, self.h = im.size

    def path(self, i): return f"{self.dir}/{i + 1:05d}.jpg"

    def frame(self, t):
        i = int(round((t - self.t0) * self.fps))
        return _load(self.path(max(0, min(self.n - 1, i))))


@functools.lru_cache(None)
def asset(name, height=None):
    im = Image.open(f"{SP}/assets/{name}.png").convert("RGBA")
    if height:
        im = im.resize((max(1, round(im.width * height / im.height)), int(height)), Image.LANCZOS)
    return im


# ---------------------------------------------------------------- camera
def cam_box(src_w, src_h, cx, cy, z):
    """normalized center + zoom -> crop box in source px (kept inside frame)."""
    bw, bh = src_w / z, src_h / z
    x0 = min(max(cx * src_w - bw / 2, 0), src_w - bw)
    y0 = min(max(cy * src_h - bh / 2, 0), src_h - bh)
    return (x0, y0, x0 + bw, y0 + bh)


def interp_keys(keys, v):
    """keys: [(v, cx, cy, z), ...] eased between consecutive keys."""
    if v <= keys[0][0]: return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if v <= b[0]:
            e = e_io((v - a[0]) / (b[0] - a[0]))
            return tuple(lerp(a[i], b[i], e) for i in (1, 2, 3))
    return keys[-1][1:]


def render_cam(img, box, sharpen=True):
    if box[0] == 0 and box[1] == 0 and abs(box[2] - W) < .5 and abs(box[3] - H) < .5 and img.size == (W, H):
        return img.copy()
    out = img.resize((W, H), Image.BICUBIC, box=box)
    z = (box[2] - box[0])
    if sharpen and img.width / z * (W / img.width) > 1.15 and img.width <= W:
        out = out.filter(ImageFilter.UnsharpMask(radius=1.4, percent=45, threshold=2))
    return out


# ---------------------------------------------------------------- drawing helpers
def shadow_of(layer, radius=18, offset=(0, 10), opacity=0.28):
    a = layer.getchannel("A").point(lambda p: int(p * opacity))
    pad = radius * 3
    sh = Image.new("RGBA", (layer.width + pad * 2, layer.height + pad * 2), (0, 0, 0, 0))
    blk = Image.new("RGBA", layer.size, (8, 10, 20, 255)); blk.putalpha(a)
    sh.alpha_composite(blk, (pad, pad))
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    return sh, pad - offset[0], pad - offset[1]


def with_shadow(layer, radius=18, offset=(0, 10), opacity=0.28):
    sh, px, py = shadow_of(layer, radius, offset, opacity)
    sh.alpha_composite(layer, (px, py))
    return sh, px, py


def paste(base, layer, x, y, alpha=1.0, scale=1.0, anchor=(0.5, 0.5)):
    """alpha-composite layer at (x,y) given anchor; supports scale+fade."""
    if alpha <= 0.003 or scale <= 0.01: return
    if abs(scale - 1) > 1e-3:
        layer = layer.resize((max(1, round(layer.width * scale)), max(1, round(layer.height * scale))), Image.BICUBIC)
    if alpha < 0.999:
        layer = layer.copy(); layer.putalpha(layer.getchannel("A").point(lambda p: int(p * alpha)))
    px = int(round(x - layer.width * anchor[0])); py = int(round(y - layer.height * anchor[1]))
    base.alpha_composite(layer, (px, py)) if (px >= 0 and py >= 0 and px + layer.width <= base.width and py + layer.height <= base.height) else _safe_comp(base, layer, px, py)


def _safe_comp(base, layer, px, py):
    x0, y0 = max(px, 0), max(py, 0)
    x1, y1 = min(px + layer.width, base.width), min(py + layer.height, base.height)
    if x1 <= x0 or y1 <= y0: return
    base.alpha_composite(layer.crop((x0 - px, y0 - py, x1 - px, y1 - py)), (x0, y0))


def text_size(txt, f):
    b = f.getbbox(txt)
    return b[2] - b[0], b[3] - b[1], b


@functools.lru_cache(maxsize=256)
def chip_img(text, color, fg=(255, 255, 255), size=34, weight="SemiBold", dot=True, pad=(30, 16), radius=None, outline=None):
    f = font(weight, size)
    tw, th, b = text_size(text, f)
    asc, desc = f.getmetrics()
    hgt = asc + desc * 0 + pad[1] * 2 - 4
    dotw = int(size * .42) + 16 if dot else 0
    wid = tw + pad[0] * 2 + dotw
    r = radius if radius is not None else hgt // 2
    im = Image.new("RGBA", (wid, hgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, wid - 1, hgt - 1), r, fill=color + (255,) if len(color) == 3 else color,
                        outline=outline, width=3 if outline else 0)
    x = pad[0]
    if dot:
        ds = int(size * .42)
        cy = hgt // 2
        d.ellipse((x, cy - ds // 2, x + ds, cy + ds // 2), fill=fg + (255,) if len(fg) == 3 else fg)
        x += dotw
    d.text((x - b[0], (hgt - (asc)) // 2 - 1), text, font=f, fill=fg)
    out, px, py = with_shadow(im, radius=14, offset=(0, 8), opacity=.22)
    out.info["core"] = (px, py, wid, hgt)
    return out


def draw_chip(base, text, t, t0, t1, x, y, color, anchor=(0, .5), fg=(255, 255, 255), size=34, dot=True, weight="SemiBold"):
    if t < t0 or t > t1: return
    img = chip_img(text, color, fg, size, weight, dot)
    px, py, cw, chh = img.info["core"]
    pin = ramp(t, t0, t0 + .32); pout = ramp(t, t1 - .22, t1)
    sc = lerp(.72, 1.0, e_back(pin)) * lerp(1, .96, pout)
    al = min(1, pin * 2.2) * (1 - pout)
    # anchor refers to the pill (not the shadow margin)
    ax = x - (cw * anchor[0] + px) * sc + img.width * sc * .0
    ay = y - (chh * anchor[1] + py) * sc
    paste(base, img, ax, ay - 8 * pout, al, sc, anchor=(0, 0))


def ring(base, box, t, t0, t1, color, width=6, radius=18, pad=10):
    """animated highlight rectangle in output px."""
    if t < t0 or t > t1: return
    pin = e_out(ramp(t, t0, t0 + .35)); al = min(1, ramp(t, t0, t0 + .2)) * (1 - ramp(t, t1 - .2, t1))
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = lerp(1.08, 1.0, pin)
    x0, x1 = cx + (x0 - pad - cx) * s, cx + (x1 + pad - cx) * s
    y0, y1 = cy + (y0 - pad - cy) * s, cy + (y1 + pad - cy) * s
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x0, y0, x1, y1), radius, outline=color + (int(255 * al),), width=width)
    # soft glow
    glow = lay.filter(ImageFilter.GaussianBlur(8))
    base.alpha_composite(glow); base.alpha_composite(lay)


def box_to_out(box_n, cambox, src_w, src_h):
    """normalized source box -> output px under a camera crop box."""
    x0, y0, x1, y1 = box_n
    bx0, by0, bx1, by1 = cambox
    sx = W / (bx1 - bx0); sy = H / (by1 - by0)
    return ((x0 * src_w - bx0) * sx, (y0 * src_h - by0) * sy, (x1 * src_w - bx0) * sx, (y1 * src_h - by0) * sy)


# ---------------------------------------------------------------- slash wipe (BeCode motif)
SLOPE = 0.42   # x shift per y px (the slash of the B/E logo)
BAR = 70


def band_mask(xl, xr):
    """mask of the slanted band between left edge xl and right edge xr (x at vertical center)."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    off = SLOPE * H / 2
    d.polygon([(xl + off, 0), (xr + off, 0), (xr - off, H), (xl - off, H)], fill=255)
    return m


def slash_layer(xl, xr, color):
    lay = Image.new("RGBA", (W, H), color + (255,))
    lay.putalpha(band_mask(xl, xr))
    return lay


def ecosystem_row(active, done=(), size=30):
    """row of three product pills; active highlighted."""
    items = [("KODU", "kodu"), ("TESTRA", "testra"), ("ECHO", "echo")]
    pills = []
    for label, key in items:
        if key == active:
            pills.append(chip_img(label, PRODUCT[key], (255, 255, 255), size, "Bold", True))
        elif key in done:
            pills.append(chip_img(label, (228, 229, 234), (80, 84, 98), size, "SemiBold", True))
        else:
            pills.append(chip_img(label, (236, 237, 241), (150, 154, 166), size, "SemiBold", False))
    return pills


def cursor_img(scale=1.0):
    pts = [(0, 0), (0, 34), (8, 26), (14, 40), (20, 37), (14, 24), (25, 24)]
    s = 1.9 * scale
    im = Image.new("RGBA", (70, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = [(6 + x * s, 6 + y * s) for x, y in pts]
    d.polygon(P, fill=(255, 255, 255, 255), outline=(10, 10, 10, 255))
    d.line(P + [P[0]], fill=(10, 10, 10, 255), width=3, joint="curve")
    out, px, py = with_shadow(im, radius=6, offset=(2, 5), opacity=.35)
    return out, px + 6, py + 6
