import math
import numpy as np
from PIL import Image, ImageDraw

B4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
B8 = np.array([
    [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]])


class Canvas:
    def __init__(self, w=400, h=240, fill=0):
        self.w, self.h = w, h
        self.ink = np.full((h, w), bool(fill))
        self.alpha = None
        ys, xs = np.mgrid[0:h, 0:w]
        self.xs, self.ys = xs, ys

    def enable_alpha(self, opaque=False):
        self.alpha = np.full((self.h, self.w), bool(opaque))

    def mask(self, fn):
        img = Image.new('1', (self.w, self.h), 0)
        fn(ImageDraw.Draw(img))
        return np.array(img, dtype=bool)

    def put(self, m, pat):
        if isinstance(pat, (bool, int, np.bool_)):
            self.ink[m] = bool(pat)
        else:
            p = pat(self.xs, self.ys)
            self.ink[m] = p[m]
        if self.alpha is not None:
            self.alpha[m] = True

    def clear(self, m):
        if self.alpha is not None:
            self.alpha[m] = False
        self.ink[m] = False

    def rect(self, x0, y0, x1, y1, pat):
        m = np.zeros((self.h, self.w), bool)
        m[max(0, int(y0)):max(0, int(y1)), max(0, int(x0)):max(0, int(x1))] = True
        self.put(m, pat)
        return m

    def frame(self, x0, y0, x1, y1, t, pat=True):
        outer = self.rect_mask(x0, y0, x1, y1)
        inner = self.rect_mask(x0 + t, y0 + t, x1 - t, y1 - t)
        self.put(outer & ~inner, pat)

    def rect_mask(self, x0, y0, x1, y1):
        m = np.zeros((self.h, self.w), bool)
        m[max(0, int(y0)):max(0, int(y1)), max(0, int(x0)):max(0, int(x1))] = True
        return m

    def disc_mask(self, cx, cy, r):
        return (self.xs + 0.5 - cx) ** 2 + (self.ys + 0.5 - cy) ** 2 <= r * r

    def ellipse_mask(self, cx, cy, rx, ry):
        return ((self.xs + 0.5 - cx) / max(rx, .01)) ** 2 + ((self.ys + 0.5 - cy) / max(ry, .01)) ** 2 <= 1

    def ring_mask(self, cx, cy, r0, r1):
        d = np.hypot(self.xs + 0.5 - cx, self.ys + 0.5 - cy)
        return (d >= r0) & (d <= r1)

    def disc(self, cx, cy, r, pat):
        m = self.disc_mask(cx, cy, r)
        self.put(m, pat)
        return m

    def ellipse(self, cx, cy, rx, ry, pat):
        m = self.ellipse_mask(cx, cy, rx, ry)
        self.put(m, pat)
        return m

    def ring(self, cx, cy, r0, r1, pat):
        m = self.ring_mask(cx, cy, r0, r1)
        self.put(m, pat)
        return m

    def poly_mask(self, pts):
        return self.mask(lambda d: d.polygon([tuple(p) for p in pts], fill=1, outline=1))

    def poly(self, pts, pat):
        m = self.poly_mask(pts)
        self.put(m, pat)
        return m

    def outline_poly(self, pts, pat=True, width=1):
        pts = [tuple(p) for p in pts]
        m = self.mask(lambda d: d.line(pts + [pts[0]], fill=1, width=width, joint='curve'))
        self.put(m, pat)
        return m

    def line(self, pts, width=1, pat=True):
        pts = [tuple(p) for p in pts]
        m = self.mask(lambda d: d.line(pts, fill=1, width=width, joint='curve'))
        self.put(m, pat)
        return m

    def text_mask(self, s, x, y, font):
        return self.mask(lambda d: d.text((x, y), s, fill=1, font=font))

    def outline_of(self, m, t=1):
        g = m.copy()
        for _ in range(t):
            g = dilate(g)
        return g & ~m

    def stamp(self, path, x, y, threshold=128, invert=False):
        im = Image.open(path).convert('LA')
        a = np.array(im)
        lum, al = a[..., 0], a[..., 1]
        h, w = lum.shape
        ink = lum < threshold
        if invert:
            ink = ~ink
        vis = al > 127
        for j in range(h):
            yy = y + j
            if not 0 <= yy < self.h:
                continue
            for i in range(w):
                xx = x + i
                if 0 <= xx < self.w and vis[j, i]:
                    self.ink[yy, xx] = ink[j, i]
                    if self.alpha is not None:
                        self.alpha[yy, xx] = True

    def save(self, path):
        a = np.where(self.ink, 0, 255).astype(np.uint8)
        if self.alpha is None:
            Image.fromarray(a, 'L').convert('1').save(path)
        else:
            rgba = np.zeros((self.h, self.w, 4), np.uint8)
            rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = a
            rgba[..., 3] = np.where(self.alpha, 255, 0)
            Image.fromarray(rgba, 'RGBA').save(path)

    def preview(self, path, scale=3):
        a = np.where(self.ink, 0x31, 0xB1).astype(np.uint8)
        rgb = np.stack([np.where(self.ink, 0x31, 0xB1), np.where(self.ink, 0x2F, 0xAF),
                        np.where(self.ink, 0x28, 0xA8)], -1).astype(np.uint8)
        if self.alpha is not None:
            rgb[~self.alpha] = (255, 0, 255)
        Image.fromarray(rgb, 'RGB').resize((self.w * scale, self.h * scale), Image.NEAREST).save(path)


def dilate(m):
    g = m.copy()
    g[1:, :] |= m[:-1, :]
    g[:-1, :] |= m[1:, :]
    g[:, 1:] |= m[:, :-1]
    g[:, :-1] |= m[:, 1:]
    return g


def erode(m):
    return ~dilate(~m)


# ---- patterns: fn(xs, ys) -> bool ink array.  level 0 = white, 16 = black ----

def bayer(level):
    level = max(0, min(16, level))
    return lambda x, y: B4[y & 3, x & 3] < level


def bayer8(level64):
    return lambda x, y: B8[y & 7, x & 7] < level64


def tone(field):
    """field: float array 0..1 (1 = black), dithered with Bayer 8x8."""
    return lambda x, y: (B8[y & 7, x & 7] + 0.5) / 64.0 < field


def hlines(period=2, phase=0):
    return lambda x, y: (y + phase) % period == 0


def vlines(period=2, phase=0):
    return lambda x, y: (x + phase) % period == 0


def hatch(period=4):
    return lambda x, y: (x + y) % period == 0


def hatch_r(period=4):
    return lambda x, y: (x - y) % period == 0


def cross(period=4):
    return lambda x, y: ((x + y) % period == 0) | ((x - y) % period == 0)


def dots(period=4):
    return lambda x, y: (x % period == 0) & (y % period == 0)


def brick(bw=24, bh=10):
    def f(x, y):
        row = y // bh
        off = np.where(row % 2 == 1, bw // 2, 0)
        return (y % bh == 0) | ((x + off) % bw == 0)
    return f


def wood(x, y):
    return (y % 8 == 7) | ((y % 8 == 3) & (x % 16 < 3)) | ((y % 8 == 2) & (x % 16 == 12))


def brushed(base_level=3, seed=1):
    rng = np.random.default_rng(seed)
    streak = rng.random(4096)
    def f(x, y):
        s = streak[(y * 131 + (x // 23) * 7) % 4096]
        return (B4[y & 3, x & 3] < base_level) | ((s > 0.93) & (x % 3 != 0))
    return f


def OR(*pats):
    def f(x, y):
        out = np.zeros(x.shape, bool)
        for p in pats:
            out |= p(x, y)
        return out
    return f


def AND(*pats):
    def f(x, y):
        out = np.ones(x.shape, bool)
        for p in pats:
            out &= p(x, y)
        return out
    return f


def NOT(p):
    return lambda x, y: ~p(x, y)


# ---- composite helpers in the reference-mockup style ----

def rivet(c, cx, cy, r=3):
    c.disc(cx + 1, cy + 1, r + 0.5, bayer(12))
    c.disc(cx, cy, r + 0.5, True)
    c.disc(cx, cy, r - 0.5, bayer(5))
    c.disc(cx - r * 0.35, cy - r * 0.35, max(1.0, r * 0.45), False)


def screw(c, cx, cy, r=3, ang=0.6):
    c.disc(cx + 1, cy + 1, r + 0.5, bayer(12))
    c.disc(cx, cy, r + 0.5, True)
    c.disc(cx, cy, r - 0.5, bayer(3))
    dx, dy = math.cos(ang) * (r - 0.5), math.sin(ang) * (r - 0.5)
    c.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], 1, True)


def panel(c, x, y, w, h, fill=False, shadow=True, shadow_level=8):
    if shadow:
        c.rect(x + 3, y + 3, x + w + 3, y + h + 3, bayer(shadow_level))
    c.rect(x + 1, y, x + w - 1, y + h, True)
    c.rect(x, y + 1, x + w, y + h - 1, True)
    c.rect(x + 2, y + 2, x + w - 2, y + h - 2, fill)


def load_font(size=8):
    from PIL import ImageFont
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    for p in [os.path.join(here, 'Silkscreen-Regular.ttf')]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()
