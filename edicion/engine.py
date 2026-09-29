"""Timeline engine: clips, overlays, cards, transitions."""
from lib import *


class Clip:
    """Maps source segment s0->s1 onto timeline T0->T1 (s0==s1 => freeze)."""

    def __init__(self, src, T0, T1, s0, s1=None, keys=None, xin=None, xin_d=0.0, fx=None, rings=None, tag=""):
        self.src, self.T0, self.T1 = src, T0, T1
        self.s0 = s0
        self.s1 = s0 + (T1 - T0) if s1 is None else s1
        self.keys = keys or [(0, .5, .5, 1.0)]
        self.xin, self.xin_d = xin, xin_d
        self.fx = fx or []          # callables fx(img_rgba, T, clip)
        self.rings = rings or []    # (box_n, t0, t1, color)
        self.tag = tag

    def src_time(self, T):
        if self.s1 == self.s0: return self.s0
        u = (T - self.T0) / (self.T1 - self.T0)
        u = min(max(u, 0.0), 1.0)
        return self.s0 + (self.s1 - self.s0) * u

    def cam(self, T):
        return interp_keys(self.keys, T - self.T0)

    def cambox(self, T):
        cx, cy, z = self.cam(T)
        return cam_box(self.src.w, self.src.h, cx, cy, z)

    def draw(self, T):
        img = self.src.frame(self.src_time(T))
        box = self.cambox(T)
        out = render_cam(img, box).convert("RGBA")
        for (bn, t0, t1, col) in self.rings:
            if t0 <= T <= t1:
                ring(out, box_to_out(bn, box, self.src.w, self.src.h), T, t0, t1, col)
        for f in self.fx:
            f(out, T, self)
        return out


class Custom:
    """A timeline segment drawn by a function (cards, inserts)."""

    def __init__(self, T0, T1, fn, xin=None, xin_d=0.0, tag=""):
        self.T0, self.T1, self.fn = T0, T1, fn
        self.xin, self.xin_d, self.tag = xin, xin_d, tag

    def draw(self, T):
        return self.fn(T)


class Timeline:
    def __init__(self):
        self.segs = []
        self.overlays = []   # (t0, t1, fn(base, T))
        self.audio = []      # dicts

    def add(self, seg):
        self.segs.append(seg); return seg

    def ov(self, t0, t1, fn):
        self.overlays.append((t0, t1, fn))

    def duration(self):
        return max(s.T1 for s in self.segs)

    def seg_at(self, T):
        for i, s in enumerate(self.segs):
            if s.T0 <= T < s.T1: return i
        return len(self.segs) - 1

    def frame(self, T):
        i = self.seg_at(T)
        s = self.segs[i]
        img = s.draw(T)
        if s.xin and i > 0 and T < s.T0 + s.xin_d:
            p = e_io((T - s.T0) / s.xin_d)
            prev = self.segs[i - 1].draw(T)
            img = blend(prev, img, p, s.xin)
        for (t0, t1, fn) in self.overlays:
            if t0 <= T <= t1:
                fn(img, T)
        return img.convert("RGB")


def blend(a, b, p, kind):
    if kind == "fade":
        return Image.blend(a, b, p)
    if kind == "push":   # outgoing grows + fades, incoming settles from slight zoom
        sa = 1 + .10 * p
        a2 = a.resize((round(W * sa), round(H * sa)), Image.BILINEAR).crop(
            (round((W * sa - W) / 2), round((H * sa - H) / 2), round((W * sa - W) / 2) + W, round((H * sa - H) / 2) + H))
        sb = 1.06 - .06 * e_out(p)
        b2 = b.resize((round(W * sb), round(H * sb)), Image.BICUBIC).crop(
            (round((W * sb - W) / 2), round((H * sb - H) / 2), round((W * sb - W) / 2) + W, round((H * sb - H) / 2) + H))
        return Image.blend(a2, b2, min(1, p * 1.25))
    if kind == "flash":
        m = Image.blend(a, b, p)
        k = max(0, 1 - abs(p - .5) * 2.4)
        return Image.blend(m, Image.new("RGBA", (W, H), (255, 255, 255, 255)), k * .55)
    return b
