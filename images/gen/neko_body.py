import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdart import B4, B8, dilate, erode, load_font
import gen_neko_v2 as NV
import gen_neko_v2_expr as EX

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'prototypes', 'neko', 'v2', 'body')
PREVIEW = os.environ.get('PREVIEW_DIR')

N = 8
SIL48 = (6, 10, 48)
_CACHE = {}


def checker(h, w, ox=0, oy=0):
    ys, xs = np.mgrid[0:h, 0:w]
    return (xs + ox + ys + oy) % 2 == 0


def shift(m, dx, dy):
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(0, dy):min(h, h + dy), max(0, dx):min(w, w + dx)] = m[max(0, -dy):min(h, h - dy), max(0, -dx):min(w, w - dx)]
    return out


def dgrow(m, r):
    return NV.disc_grow(m, r)


def shrink(m, r):
    return ~dgrow(~m, r)


def scale_into(src, k, ox, oy, H, W, thr=0.5):
    big = np.zeros((H * N, W * N), np.float32)
    ys, xs = np.nonzero(src)
    for y, x in zip(ys, xs):
        x0 = int(round((ox + x * k) * N))
        x1 = int(round((ox + (x + 1) * k) * N))
        y0 = int(round((oy + y * k) * N))
        y1 = int(round((oy + (y + 1) * k) * N))
        big[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = 1
    return big.reshape(H, N, W, N).mean((1, 3)) >= thr


def head_base(width, back=False):
    key = ('head', width, back)
    if key in _CACHE:
        return _CACHE[key]
    L, reg, sil = NV.head_ref()
    ys, xs = np.nonzero(sil)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    sc = width / float(x1 - x0)
    tw, th = width, int(round((y1 - y0) * sc))
    pad = int(math.ceil(width * 0.3))
    w, h = tw + 2 * pad, th + 2 * pad
    big = Image.fromarray((sil[y0:y1, x0:x1] * 255).astype(np.uint8))
    o = np.asarray(big.resize((tw, th), Image.BOX), np.float32) / 255.0 >= 0.5
    outer = np.zeros((h, w), bool)
    outer[pad:pad + th, pad:pad + tw] = o
    outer = erode(dilate(outer))
    rows = np.nonzero(outer.any(1))[0]
    for y in range(rows.min() + int(len(rows) * 0.45), rows.max() + 1):
        xs_ = np.nonzero(outer[y])[0]
        outer[y, xs_.min():xs_.max() + 1] = True
    yy_ = np.mgrid[0:h, 0:w][0]
    lower = yy_ > pad + int(0.3 * th)
    sm = shrink(dgrow(outer, 4.5), 4.5)
    outer = np.where(lower, sm, outer)
    inner = ~dgrow(~outer, 2.0)
    ink = outer & ~inner
    yyr = np.mgrid[0:reg.shape[0], 0:reg.shape[1]][0]
    greyr = (L['grey'] & reg & ~NV.grow(L['ink'], 2) & (yyr < 75))[y0:y1, x0:x1]
    gs = np.asarray(Image.fromarray((greyr * 255).astype(np.uint8)).resize((tw, th), Image.BOX), np.float32) / 255.0 >= 0.4
    grey = np.zeros((h, w), bool)
    grey[pad:pad + th, pad:pad + tw] = gs
    k = width / 48.0
    ox, oy = pad - SIL48[0] * k, pad - SIL48[1] * k
    if back:
        yy = np.mgrid[0:h, 0:w][0]
        cxh = pad + tw // 2
        y_ear = pad + int(0.32 * th)
        for y in range(y_ear, h):
            xs_ = np.nonzero(outer[y, cxh:])[0]
            if len(xs_):
                r = xs_.max()
                outer[y, :] = False
                outer[y, max(0, cxh - r - (tw % 2)):cxh + r + 1] = True
        cl = shrink(dgrow(outer, 4.0), 4.0)
        outer = np.where(yy < y_ear + 4, cl, outer)
        inner = ~dgrow(~outer, 2.0)
        ink = outer & ~inner
        d = dict(ink=ink, outer=outer | ink, w=w, h=h, pad=pad, k=k, ox=ox, oy=oy, width=width, jaw=pad + th)
        _CACHE[key] = d
        return d
    ink |= grey & inner & checker(h, w)
    hgrey = grey & inner
    base = EX.Face(48)
    tb = np.zeros_like(base.ink)
    tb[16:23, 19:36] = True
    tuft = base.ink & tb
    tr = scale_into(tb, k, ox, oy, h, w, 0.99)
    tr &= ~dgrow(~outer, 1.0) | (np.mgrid[0:h, 0:w][0] < pad + 13 * k)
    ink[tr] = False
    outer[tr] = False
    tink = scale_into(tuft, k, ox, oy, h, w, 0.45)
    ink |= tink
    outer |= tink
    xs_t = np.nonzero(tink.any(0))[0]
    for x in xs_t:
        top = np.nonzero(tink[:, x])[0].min()
        col = tr[:, x].copy()
        col[:top + 1] = False
        outer[col, x] = True
    d = dict(ink=ink, outer=outer | ink, w=w, h=h, pad=pad, k=k, ox=ox, oy=oy, width=width,
             jaw=pad + th, grey=hgrey)
    _CACHE[key] = d
    return d


def whisker_mask():
    base = EX.Face(48)
    m = np.zeros_like(base.ink)
    for y in range(40, 56):
        row = base.ink[y]
        x = 0
        while x < len(row):
            if row[x]:
                e = x
                while e < len(row) and row[e]:
                    e += 1
                if e - x >= 6:
                    m[y, x:e] = True
                x = e
            else:
                x += 1
    return m


SOOT_RECTS48 = [(7, 19, 8, 4), (33, 21, 6, 3), (31, 41, 8, 4), (9, 42, 6, 3)]
SOOT_BLOTCH48 = [(15.5, 30.0, 4.2, 3.0, True), (37.0, 50.5, 4.4, 3.0, True), (41.0, 27.5, 2.8, 2.0, False)]


def face_layers(name):
    base = EX.Face(48)
    f = EX.build(name, 48)
    if name == 'charred':
        for x, y, w_, h_ in SOOT_RECTS48:
            f.ink[f.oy + y:f.oy + y + h_, f.ox + x:f.ox + x + w_] = False
    feat = f.ink & ~base.ink
    white = f.alpha & ~f.ink & base.ink
    props = (f.ink | f.alpha) & ~dilate(base.head)
    return feat, white, props, whisker_mask()


def head(name, width, face_props=True):
    key = ('face', name, width, face_props)
    if key in _CACHE:
        return _CACHE[key]
    if name == 'back':
        hb = dict(head_base(width, True))
        hb.update(extra_alpha=np.zeros_like(hb['ink']), name=name)
        _CACHE[key] = hb
        return hb
    hb = head_base(width)
    h, w, k, ox, oy = hb['h'], hb['w'], hb['k'], hb['ox'], hb['oy']
    ink = hb['ink'].copy()
    outer = hb['outer'].copy()
    feat, white, props, wh = face_layers(name)
    fi = scale_into(feat | wh, k, ox, oy, h, w, 0.5)
    fw = scale_into(white, k, ox, oy, h, w, 0.5)
    pr = scale_into(props, k, ox, oy, h, w, 0.5)
    if not face_props:
        near = dgrow(outer, 4.0)
        fi &= near
        pr &= near
    ink &= ~fw
    ink |= fi
    extra = (fi | pr) & ~outer
    halo = dgrow(extra, 1.0) & ~outer
    if name == 'charred':
        for bx, by, rx, ry, speck in SOOT_BLOTCH48:
            soot_blotch(ink, outer & ~dgrow(fi, 1.0) & ~dgrow(hb['ink'], 1.0), ox + (bx + 0.5) * k, oy + (by + 0.5) * k, rx * k, ry * k, speck, seed=int(bx * 7 + by))
    d = dict(hb)
    d.update(ink=ink, outer=outer, extra_alpha=halo | extra, name=name)
    _CACHE[key] = d
    return d


def to_rgb(ink, alpha=None, bg=(255, 0, 255)):
    rgb = np.stack([np.where(ink, 0x31, 0xB1), np.where(ink, 0x2F, 0xAF), np.where(ink, 0x28, 0xA8)], -1).astype(np.uint8)
    if alpha is not None:
        rgb[~alpha & ~ink] = bg
    return rgb


def save_preview(ink, alpha, path, scale=3):
    Image.fromarray(to_rgb(ink, alpha), 'RGB').resize((ink.shape[1] * scale, ink.shape[0] * scale), Image.NEAREST).save(path)


SSN = 4


class Fig:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ink = np.zeros((h, w), bool)
        self.alpha = np.zeros((h, w), bool)
        self.ys, self.xs = np.mgrid[0:h, 0:w]
        self.chk = (self.xs + self.ys) % 2 == 0

    def ss(self, fn):
        img = Image.new('L', (self.w * SSN, self.h * SSN), 0)
        fn(ImageDraw.Draw(img), SSN)
        return np.asarray(img.resize((self.w, self.h), Image.BOX), np.float32) / 255.0 >= 0.5

    def ell(self, cx, cy, rx, ry):
        return self.ss(lambda d, k: d.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], fill=255))

    def poly(self, pts):
        return self.ss(lambda d, k: d.polygon([(x * k, y * k) for x, y in pts], fill=255))

    def tube(self, pts, r0, r1=None, n=60):
        r1 = r0 if r1 is None else r1
        path = spline(pts, n)
        def fn(d, k):
            m = len(path)
            for i, (x, y) in enumerate(path):
                r = r0 + (r1 - r0) * i / max(1, m - 1)
                d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=255)
        return self.ss(fn)

    def line(self, pts, wd):
        return self.ss(lambda d, k: d.line([(x * k, y * k) for x, y in pts], fill=255, width=int(wd * k), joint='curve'))

    def part(self, m, shade=None, clip=None, lw=2.0):
        ring = dgrow(m, lw) & ~m
        if clip is not None:
            ring &= clip
            m = m & clip
        self.ink[ring] = True
        self.ink[m] = False
        self.alpha |= ring | m
        if shade:
            band = np.zeros_like(m)
            for dx, dy, t in shade:
                band |= m & ~shift(m, -dx * t, -dy * t) if False else m & ~shift(m, -int(dx * t), -int(dy * t))
            self.ink[band & self.chk] = True
        return m


def spline(pts, n=60):
    if len(pts) == 2:
        (x0, y0), (x1, y1) = pts
        return [(x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n) for t in range(n + 1)]
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    seg = len(pts) - 1
    per = max(8, n // seg)
    for i in range(seg):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        for j in range(per + (1 if i == seg - 1 else 0)):
            t = j / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in range(2)))
    return out


def soot_blotch(ink, allowed, X, Y, rx, ry, speck=True, seed=1):
    h, w = ink.shape
    ys, xs = np.mgrid[0:h, 0:w]
    rng = np.random.default_rng(seed)
    ang = np.arctan2(ys + 0.5 - Y, xs + 0.5 - X)
    wob = 1 + 0.18 * np.sin(ang * 3 + rng.uniform(0, 6)) + 0.1 * np.sin(ang * 5 + rng.uniform(0, 6))
    d = np.hypot((xs + 0.5 - X) / rx, (ys + 0.5 - Y) / ry) / wob
    core = (d < 0.6) & allowed
    rim = (d >= 0.6) & (d < 1.0) & allowed
    ink[core & ((xs + ys) % 2 == 0)] = True
    ink[rim & (xs % 2 == 0) & (ys % 2 == 0)] = True
    if speck:
        sx, sy = int(round(X + rx * 0.15)), int(round(Y - ry * 0.1))
        sp = np.zeros_like(ink)
        sp[sy - 1:sy + 1, sx - 1:sx + 2] = True
        sp[sy + 1, sx:sx + 1] = True
        ink[sp & allowed] = True


def paste_head(F, hd, hx0, hy0):
    hm = np.zeros((F.h, F.w), bool)
    hi = np.zeros((F.h, F.w), bool)
    he = np.zeros((F.h, F.w), bool)
    hm[hy0:hy0 + hd['h'], hx0:hx0 + hd['w']] = hd['outer']
    hi[hy0:hy0 + hd['h'], hx0:hx0 + hd['w']] = hd['ink']
    he[hy0:hy0 + hd['h'], hx0:hx0 + hd['w']] = hd['extra_alpha']
    ex = he & ~hm
    F.ink[ex] = hi[ex]
    F.ink[hm] = hi[hm]
    if 'grey' in hd:
        hg = np.zeros((F.h, F.w), bool)
        hg[hy0:hy0 + hd['h'], hx0:hx0 + hd['w']] = hd['grey']
        F.ink[hg] = F.chk[hg]
    F.alpha |= hm | he
    return hm


def jaw_band(hm, body, cx, halfw, depth):
    h, w = hm.shape
    band = np.zeros_like(hm)
    for x in range(w):
        col = np.nonzero(hm[:, x])[0]
        if not len(col):
            continue
        q = (x + 0.5 - cx) / halfw
        if abs(q) >= 1:
            continue
        t = depth * (1 - q * q) ** 0.7
        jb = col.max()
        n = int(round(t))
        if n > 0:
            band[jb + 1:jb + 1 + n, x] = True
    return band & body & ~hm


def runs_ok(m, axis, n):
    out = np.zeros_like(m)
    a = m if axis == 1 else m.T
    o = out if axis == 1 else out.T
    for i in range(a.shape[0]):
        row = a[i]
        x = 0
        L = len(row)
        while x < L:
            if row[x]:
                e = x
                while e < L and row[e]:
                    e += 1
                if e - x >= n:
                    o[i, x:e] = True
                x = e
            else:
                x += 1
    return out


def components(m):
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    sizes = [0]
    cur = 0
    ys, xs = np.nonzero(m)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        stack = [(y0, x0)]
        lab[y0, x0] = cur
        n = 0
        while stack:
            y, x = stack.pop()
            n += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = cur
                        stack.append((yy, xx))
        sizes.append(n)
    return lab, np.array(sizes)


def clean_grey(g, min_px=8, min_run=3):
    g = g & runs_ok(g, 1, min_run) & runs_ok(g, 0, min_run)
    lab, sizes = components(g)
    keep = sizes >= min_px
    keep[0] = False
    return keep[lab]


def pixel_cleanup(F, zone):
    ink = F.ink
    for _ in range(2):
        n8i = np.zeros(ink.shape, np.int32)
        n8w = np.zeros(ink.shape, np.int32)
        wa = ~ink & F.alpha
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx or dy:
                    n8i += shift(ink, dx, dy)
                    n8w += shift(wa, dx, dy)
        orphan = ink & (n8i == 0) & zone
        hole = wa & (n8w == 0) & zone
        ink[orphan] = False
        ink[hole] = True


def jaw_shadow(F, hm, depth, under):
    sh = np.zeros_like(hm)
    for d in range(1, depth + 1):
        sh |= shift(hm, 0, d)
    band = sh & ~hm & under & ~F.ink
    xs = np.nonzero(hm.any(0))[0]
    F.ink[band & F.chk] = True


def coin(F, cx, cy, r):
    m = F.ell(cx, cy, r, r)
    F.part(m, shade=[(1, 1, max(2, r * 0.25))])
    inner = F.ell(cx, cy, r - 3, r - 3)
    F.ink[m & ~inner & ~F.chk] = False
    font_rows = ["..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."]
    x0, y0 = int(round(cx - 2)), int(round(cy - 3))
    for j, row in enumerate(font_rows):
        for i, ch in enumerate(row):
            if ch == '#':
                F.ink[y0 + j, x0 + i] = True
    return m


def bill(F, cx, cy, w, h, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = [(cx + ca * x - sa * y, cy + sa * x + ca * y) for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
    m = F.poly(pts)
    F.part(m)
    inner = F.poly([(cx + ca * x * 0.62 - sa * y * 0.45, cy + sa * x * 0.62 + ca * y * 0.45) for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))])
    F.ink[inner & F.chk & m] = True
    F.ink[F.ell(cx, cy, h * 0.22, h * 0.22) & m] = False
    return m


def flask(F, cx, cy, r, ang=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    def R(x, y):
        return (cx + ca * x - sa * y, cy + sa * x + ca * y)
    nw = r * 0.36
    neck = F.poly([R(-nw, -r * 0.6), R(nw, -r * 0.6), R(nw, -r * 1.7), R(-nw, -r * 1.7)])
    lip = F.poly([R(-nw - 1.5, -r * 1.7), R(nw + 1.5, -r * 1.7), R(nw + 1.5, -r * 1.95), R(-nw - 1.5, -r * 1.95)])
    bulb = F.ell(cx, cy, r, r)
    m = neck | lip | bulb
    F.part(m)
    lvl = F.poly([R(-2 * r, r * 0.15), R(2 * r, r * 0.15), R(2 * r, 2 * r), R(-2 * r, 2 * r)])
    liq = shrink(bulb, 1.0) & lvl
    F.ink[liq & F.chk] = True
    F.ink[F.line([R(-r * 0.9, r * 0.15), R(r * 0.9, r * 0.15)], 1.0) & bulb] = True
    F.ink[F.ell(*R(-r * 0.42, -r * 0.35), r * 0.16, r * 0.24) & bulb] = False
    crack = [R(r * 0.2, -r * 1.0), R(r * 0.42, -r * 0.55), R(r * 0.18, -r * 0.2), R(r * 0.52, r * 0.2)]
    F.ink[F.line(crack, 1.0) & bulb] = True
    return m


POSES = ('stand', 'cheer', 'panic', 'hands_up', 'sit', 'dazed', 'rich')
DEFAULT_FACE = dict(stand='smiling', cheer='happy', panic='panicked', hands_up='caught', sit='neutral',
                    dazed='charred', rich='rich')

COLLAR_W = 0.54
COLLAR_T = 0.1
BELL_R = 0.065
TORSO_W = 0.5
TORSO_H = 0.45
ARM_T = 0.2
ARM_L = 0.25
LEG_T = 0.21
LEG_L = 0.2
PAW_R = 0.11
FILLET = 0.035
CREASE_L = 0.16
KOBAN = (0.3, 0.38)


def rrect(F, x0, y0, x1, y1, r, belly=0.0):
    def fn(d, k):
        d.rounded_rectangle([x0 * k, y0 * k, x1 * k, y1 * k], radius=r * k, fill=255)
        if belly:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + (y1 - y0) * 0.08
            d.ellipse([(x0 - belly) * k, (cy - (y1 - y0) * 0.36) * k, (x1 + belly) * k, (cy + (y1 - y0) * 0.36) * k], fill=255)
    return F.ss(fn)


def pads(F, x, y, r, ang=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    def R(dx, dy):
        return x + ca * dx - sa * dy, y + sa * dx + ca * dy
    m = F.ell(*R(0, r * 0.28), r * 0.42, r * 0.34)
    for dx, dy in ((-0.5, -0.32), (0.0, -0.5), (0.5, -0.32)):
        m |= F.ell(*R(dx * r, dy * r), r * 0.19, r * 0.22)
    F.ink[m] = True


def sole(F, x, y, u, rx=1.0, ry=1.1, ang=0.0):
    r = PAW_R * u * 1.08
    m = F.ell(x, y, r * rx, r * ry)
    F.part(m)
    pads(F, x, y + r * 0.05, r * 0.95, ang)
    return m


def bell(F, x, y, u):
    r = BELL_R * u
    m = F.ell(x, y, r, r)
    F.part(m, shade=[(1, 1, 2)])
    F.ink[F.line([(x - r * 0.75, y + r * 0.1), (x + r * 0.75, y + r * 0.1)], 1.2) & m] = True
    F.ink[F.line([(x, y + r * 0.1), (x, y + r * 0.8)], 1.2) & m] = True
    F.ink[F.ell(x, y + r * 0.35, r * 0.2, r * 0.2)] = True
    F.ink[F.ell(x - r * 0.4, y - r * 0.42, r * 0.22, r * 0.18) & m] = False


def collar(F, cx, J, u, w=COLLAR_W):
    m = rrect(F, cx - w * u / 2, J - 0.04 * u, cx + w * u / 2, J + (COLLAR_T - 0.02) * u, COLLAR_T * u * 0.5)
    F.ink[dgrow(m, 2.0) & ~m] = True
    F.ink[m] = True
    F.alpha |= dgrow(m, 2.0)
    hl = rrect(F, cx - w * u / 2 + 3, J + 0.005 * u, cx + w * u / 2 - 3, J + 0.005 * u + 1, 0.5)
    F.ink[hl & (F.xs % 2 == 0)] = False
    return m


GLYPH_DOLLAR = [
    "...##...",
    ".######.",
    "##.##.##",
    "##.##...",
    ".######.",
    "...##.##",
    "##.##.##",
    ".######.",
    "...##...",
]
GLYPH_BARS = [
    "########",
    "........",
    ".######.",
    "........",
    "########",
    "...##...",
    "...##...",
]


def koban(F, cx, cy, u, mark='dollar'):
    rx, ry = KOBAN[0] * u / 2, KOBAN[1] * u / 2
    m = F.ell(cx, cy, rx, ry)
    F.part(m)
    inner = F.ell(cx, cy, rx - 3, ry - 3)
    F.ink[m & ~inner & F.chk] = True
    F.ink[inner & ~F.ell(cx, cy, rx - 4, ry - 4)] = True
    g = GLYPH_DOLLAR if mark == 'dollar' else GLYPH_BARS
    gh, gw = len(g), len(g[0])
    sc = max(1, int(round(ry * 1.1 / gh)))
    x0, y0 = int(round(cx - gw * sc / 2)), int(round(cy - gh * sc / 2))
    for j, row in enumerate(g):
        for i, ch in enumerate(row):
            if ch == '#':
                F.ink[y0 + j * sc:y0 + (j + 1) * sc, x0 + i * sc:x0 + (i + 1) * sc] = True
    return m


def redraw_tip(F, a, t):
    tx, ty = a['tip']
    ex, ey = a['pts'][-1]
    L = math.hypot(tx - ex, ty - ey) or 1.0
    dx, dy = (tx - ex) / L, (ty - ey) / L
    r = t / 2
    fwd = ((F.xs + 0.5 - tx) * dx + (F.ys + 0.5 - ty) * dy) >= -r * 0.5
    reg = F.ell(tx, ty, r + 2.5, r + 2.5) & fwd
    F.part(a['m'], clip=reg)


def tip_cap(F, a, t, U, hm):
    tx, ty = a['tip']
    ex, ey = a['pts'][-1]
    L = math.hypot(tx - ex, ty - ey)
    if L < 0.5:
        return
    dx, dy = (tx - ex) / L, (ty - ey) / L
    r = t / 2
    fwd = ((F.xs + 0.5 - tx) * dx + (F.ys + 0.5 - ty) * dy) >= -r * 0.35
    ring = dgrow(a['m'], 2.0) & ~a['m'] & F.ell(tx, ty, r + 2.5, r + 2.5) & fwd
    ring &= shrink(U, 1.0) & ~dgrow(hm, 1.0)
    if ring.sum() >= 6:
        F.ink[ring] = True


def toes(F, base, tip, t, ext):
    tx, ty = tip
    ex, ey = base
    r = t / 2
    L = math.hypot(tx - ex, ty - ey)
    if L < 0.5:
        return
    dx, dy = (tx - ex) / L, (ty - ey) / L
    nx, ny = -dy, dx
    for off in (-0.3, 0.3):
        ox, oy = tx + nx * off * r, ty + ny * off * r
        edge = r * math.sqrt(1 - off * off) + 0.4
        p0 = (ox + dx * edge, oy + dy * edge)
        p1 = (ox + dx * (edge - 5.0), oy + dy * (edge - 5.0))
        F.ink[F.line([p0, p1], 1.5) & dgrow(ext, 1.0)] = True


def stick_tip(F, arms, tip, t):
    tx, ty = tip
    best = min(arms, key=lambda a: math.hypot(a[0][-1][0] - tx, a[0][-1][1] - ty))
    pts, am = best
    ex, ey = pts[-1]
    if math.hypot(tx - ex, ty - ey) < 0.5:
        ex, ey = pts[-2]
    ext = F.tube([pts[-1], (tx, ty)], t / 2) if math.hypot(tx - pts[-1][0], ty - pts[-1][1]) >= 0.5 else F.ell(tx, ty, t / 2, t / 2)
    F.part(am | ext, [(1, 1, 2)], clip=dgrow(ext, 3.0))
    r = t / 2
    L = math.hypot(tx - ex, ty - ey) or 1.0
    dx, dy = (tx - ex) / L, (ty - ey) / L
    nx, ny = -dy, dx
    for off in (-0.3, 0.3):
        ox, oy = tx + nx * off * r, ty + ny * off * r
        edge = r * math.sqrt(1 - off * off) + 0.4
        p0 = (ox + dx * edge, oy + dy * edge)
        p1 = (ox + dx * (edge - 5.0), oy + dy * (edge - 5.0))
        F.ink[F.line([p0, p1], 1.5) & dgrow(ext, 1.0)] = True


def limb(F, pts, t):
    return F.tube(pts, t / 2)


def render(pose, face=None, width=96, flip=False, props=True, soot=None, face_props=True, mark='dollar'):
    face = face or DEFAULT_FACE[pose]
    hd = head(face, width, face_props)
    u = float(width)
    FW = int(2.0 * u) + 2 * hd['pad']
    FH = hd['h'] + int(1.0 * u)
    F = Fig(FW, FH)
    hx0 = FW // 2 - hd['pad'] - width // 2
    hy0 = int(0.1 * u)
    cx = hx0 + hd['pad'] + width / 2.0
    J = hy0 + hd['jaw']
    sh = [(1, 0, max(3, u * 0.05))]
    shb = [(1, 0, max(3, u * 0.05)), (0, 1, max(2, u * 0.03))]
    at, lt = ARM_T * u, LEG_T * u
    tw = TORSO_W * u / 2
    sitting = pose in ('sit', 'dazed', 'rich')
    top = J - 0.08 * u
    bot = J + (TORSO_H + COLLAR_T - 0.02) * u
    A = {}
    back_arms, front_arms, paws_front, soles, after = [], [], [], [], []
    if sitting:
        bot = J + (TORSO_H + COLLAR_T - 0.1) * u
        G = bot + 0.1 * u
    else:
        G = bot + LEG_L * u
    A['G'] = G
    tail = limb(F, [(cx + tw * 0.6, bot - 0.08 * u), (cx + tw + 0.14 * u, bot - 0.14 * u), (cx + tw + 0.2 * u, bot - 0.26 * u)], 0.12 * u)
    legs_ms = []
    if not sitting:
        if pose == 'panic':
            legs = [[(cx - 0.13 * u, bot - 0.06 * u), (cx - 0.06 * u, bot + 0.1 * u), (cx - 0.15 * u, G - lt / 2)],
                    [(cx + 0.13 * u, bot - 0.06 * u), (cx + 0.06 * u, bot + 0.1 * u), (cx + 0.15 * u, G - lt / 2)]]
        elif pose == 'cheer':
            legs = [[(cx - 0.13 * u, bot - 0.06 * u), (cx - 0.15 * u, G - lt / 2)],
                    [(cx + 0.13 * u, bot - 0.06 * u), (cx + 0.24 * u, G - lt / 2 - 0.08 * u)]]
        else:
            legs = [[(cx - 0.13 * u, bot - 0.06 * u), (cx - 0.14 * u, G - lt / 2)],
                    [(cx + 0.13 * u, bot - 0.06 * u), (cx + 0.14 * u, G - lt / 2)]]
        for lg in legs:
            legs_ms.append(limb(F, lg, lt))
    torso = rrect(F, cx - tw, top, cx + tw, bot, 0.2 * u, belly=0.02 * u)
    if sitting:
        for sd in (-1, 1):
            legs_ms.append(limb(F, [(cx + sd * 0.12 * u, bot - 0.1 * u), (cx + sd * 0.17 * u, G - 0.1 * u)], lt))
        soles += [(cx - 0.17 * u, G - 0.11 * u, -0.2), (cx + 0.17 * u, G - 0.11 * u, 0.2)]
    sx = tw + at * 0.2
    shoulder_y = J + 0.07 * u
    if pose == 'stand':
        front_arms.append(([(cx - sx, shoulder_y), (cx - sx - 0.02 * u, J + 0.16 * u)], None))
        paws_front.append((cx - sx - 0.03 * u, J + 0.21 * u, False))
        back_arms.append([(cx + sx, shoulder_y), (cx + sx + 0.07 * u, J + 0.02 * u)])
        paws_front.append((cx + sx + 0.1 * u, J - 0.03 * u, True))
    elif pose in ('cheer', 'hands_up'):
        spread = 0.1 if pose == 'cheer' else 0.07
        for sd in (-1, 1):
            back_arms.append([(cx + sd * sx, shoulder_y), (cx + sd * (sx + spread * u), J + 0.0 * u)])
            paws_front.append((cx + sd * (sx + (spread + 0.03) * u), J - 0.05 * u, True))
    elif pose == 'panic':
        for sd in (-1, 1):
            front_arms.append(([(cx + sd * sx, shoulder_y), (cx + sd * (sx + 0.01 * u), J + 0.0 * u)], 'clip'))
            paws_front.append((cx + sd * (sx + 0.0 * u), J - 0.04 * u, False))
    elif pose == 'sit':
        for sd in (-1, 1):
            front_arms.append(([(cx + sd * sx, shoulder_y), (cx + sd * (sx + 0.02 * u), J + 0.16 * u)], None))
            paws_front.append((cx + sd * (sx + 0.03 * u), J + 0.21 * u, False))
    elif pose == 'dazed':
        front_arms.append(([(cx - sx, shoulder_y), (cx - sx - 0.04 * u, J + 0.17 * u)], None))
        paws_front.append((cx - sx - 0.06 * u, J + 0.22 * u, False))
        front_arms.append(([(cx + sx, shoulder_y), (cx + sx + 0.06 * u, J + 0.14 * u)], None))
        A['flask'] = (cx + sx + 0.27 * u, J + 0.22 * u)
        A['flask_paw'] = (cx + sx + 0.1 * u, J + 0.18 * u)
    elif pose == 'rich':
        for sd in (-1, 1):
            front_arms.append(([(cx + sd * sx, shoulder_y), (cx + sd * (sx - 0.02 * u), J + 0.16 * u)], None))
        A['coin'] = (cx, J + 0.17 * u)
        A['coin_paws'] = [(cx - 0.235 * u, J + 0.22 * u), (cx + 0.235 * u, J + 0.2 * u)]
    arms = []
    for pts in back_arms:
        arms.append(dict(pts=pts, m=limb(F, pts, at), front=False, mode=None, tip=None, ext=None))
    for pts, mode in front_arms:
        arms.append(dict(pts=pts, m=limb(F, pts, at), front=True, mode=mode, tip=None, ext=None))
    tips = [(x, y, 'plain') for x, y, _ in paws_front]
    if pose == 'rich':
        tips += [(x, y, 'prop') for x, y in A['coin_paws']]
    if pose == 'dazed':
        tips += [(A['flask_paw'][0], A['flask_paw'][1], 'prop')]
    for tx, ty, kind in tips:
        a = min(arms, key=lambda a: math.hypot(a['pts'][-1][0] - tx, a['pts'][-1][1] - ty))
        e = a['pts'][-1]
        ext = F.tube([e, (tx, ty)], at / 2) if math.hypot(tx - e[0], ty - e[1]) >= 0.5 else F.ell(tx, ty, at / 2, at / 2)
        a['m'] = a['m'] | ext
        a['tip'], a['ext'], a['kind'] = (tx, ty), ext, kind
    U = torso | tail
    for m in legs_ms:
        U |= m
    for a in arms:
        U |= a['m']
    raw = U.copy()
    U = shrink(dgrow(U, FILLET * u), FILLET * u)
    if not sitting:
        U &= raw | (F.ys < bot - 0.02 * u)
    else:
        U &= ~F.ell(cx, G + 0.03 * u, 0.06 * u, 0.15 * u)
    if pose == 'panic':
        U &= ~F.ell(cx, G + 0.01 * u, 0.028 * u, 0.1 * u)
    U = dgrow(shrink(U, 1.0), 1.0)
    U = shrink(dgrow(U, 1.0), 1.0)
    ring = dgrow(U, 2.0) & ~U
    F.ink[ring] = True
    F.ink[U] = False
    F.alpha |= ring | U
    if pose == 'dazed':
        hy0 += int(0.04 * u)
    hm = np.zeros_like(U)
    hm[hy0:hy0 + hd['h'], hx0:hx0 + hd['w']] = hd['outer']
    front_m = np.zeros_like(U)
    for a in arms:
        if a['mode'] == 'clip':
            front_m |= a['m']
    sole_ms = [F.ell(x, y, PAW_R * u * 1.08, PAW_R * u * 1.08 * 1.1) for x, y, _ in soles]
    sole_zone = np.zeros_like(U)
    for m in sole_ms:
        sole_zone |= dgrow(m, 3.0)
    k1, k2 = max(4, int(round(u * 0.05))), max(3, int(round(u * 0.032)))
    shade = U & ~shift(U, -k1, -k2)
    jaw = jaw_band(hm, U & ~front_m, cx, tw + 0.1 * u, max(4, int(round(u * 0.055))))
    grey = ((shade & ~dgrow(hm, 1.0)) | jaw) & ~sole_zone & ~hm
    grey = clean_grey(grey)
    F.ink[grey] = F.chk[grey]
    for (x, y, a_), m in zip(soles, sole_ms):
        if pose != 'rich':
            sole(F, x, y, u, 1.0, 1.1, a_)
    hm = paste_head(F, hd, hx0, hy0)
    clip = dgrow(hm, 2.5)
    for a in arms:
        if a['mode'] == 'clip':
            reg = (dgrow(hm, 2.0) | dgrow(jaw, 1.0)) & (F.ys < J + 0.1 * u)
            F.part(a['m'], clip=reg)
        elif a['ext'] is not None and a.get('kind') == 'plain':
            reg = dgrow(a['ext'], 3.0) & clip & (F.ys <= J)
            if reg.any():
                F.part(a['m'], clip=reg)
            tip_cap(F, a, at, U, hm)
    for a in arms:
        if a['ext'] is not None and a.get('kind') == 'plain':
            toes(F, a['pts'][-1], a['tip'], at, a['ext'])
    if props and pose == 'rich':
        x, y = A['coin']
        r = 0.17 * u
        m = F.ell(x, y, r, r * 0.94)
        m_coin = m
        F.part(m)
        F.ink[F.ell(x, y, r - 3, r * 0.94 - 3) & ~F.ell(x, y, r - 4, r * 0.94 - 4)] = True
        csh = clean_grey(m & ~F.ell(x, y, r - 3, r * 0.94 - 3) & ~shift(m, -4, -4), 4, 2)
        F.ink[csh] = F.chk[csh]
        g = GLYPH_DOLLAR
        sc = 2
        x0, y0 = int(round(x - len(g[0]) * sc / 2)), int(round(y - len(g) * sc / 2))
        for j, row in enumerate(g):
            for i, ch in enumerate(row):
                if ch == '#':
                    F.ink[y0 + j * sc:y0 + (j + 1) * sc, x0 + i * sc:x0 + (i + 1) * sc] = True
        for a in arms:
            if a.get('kind') == 'prop':
                redraw_tip(F, a, at)
                toes(F, a['pts'][-1], a['tip'], at, a['ext'])
        for x, y, a_ in soles:
            sole(F, x, y, u, 1.0, 1.1, a_)
    if props and pose == 'dazed':
        x, y = A['flask']
        fm = flask(F, x, y, u * 0.13, 0.35)
        for a in arms:
            if a.get('kind') == 'prop':
                redraw_tip(F, a, at)
                toes(F, a['pts'][-1], a['tip'], at, a['ext'])
    body_zone = (F.alpha | F.ink) & ~dgrow(hm, 1.0)
    pixel_cleanup(F, body_zone & ~grey)
    s_all = ring | U | hm
    for m in sole_ms:
        s_all |= dgrow(m, 2.0)
    outline = s_all & ~shrink(s_all, 2.0)
    outline &= ~(hm & (F.ys < hy0 + hd['pad'] + int(0.28 * u)))
    if props and pose == 'rich':
        outline &= ~dgrow(m_coin, 2.0)
    if props and pose == 'dazed':
        outline &= ~dgrow(fm, 2.0)
    if soot:
        fur = F.alpha & ~F.ink & ~dgrow(hm, 1.0) & ~dgrow(F.ink, 1.0)
        for i, (bx, by, rx, ry) in enumerate(soot):
            soot_blotch(F.ink, fur, cx + bx * u, J + by * u, rx * u, ry * u, i < 2, seed=11 + i)
    if flip:
        F.ink = F.ink[:, ::-1]
        F.alpha = F.alpha[:, ::-1]
        hm = hm[:, ::-1]
        grey = grey[:, ::-1]
        outline = outline[:, ::-1]
        cx = FW - cx
    F.alpha |= F.ink
    ys, xs = np.nonzero(F.alpha)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    hys = np.nonzero(hm.any(1))[0]
    out = dict(ink=F.ink[y0:y1, x0:x1], alpha=F.alpha[y0:y1, x0:x1], head=hm[y0:y1, x0:x1],
               cx=cx - x0, G=int(round(A['G'])) - y0, J=J - y0, u=u, pose=pose, face=face,
               lift=0, head_top=hys.min() - y0, phase=(x0 + y0) % 2, grey=grey[y0:y1, x0:x1], outline=outline[y0:y1, x0:x1])
    out['w'], out['h'] = out['ink'].shape[1], out['ink'].shape[0]
    return out


def origin(fig, cx, ground):
    x0 = int(round(cx - fig['cx']))
    y0 = int(round(ground - fig['G']))
    if (x0 + y0) % 2 != fig.get('phase', 0):
        x0 += 1
    return x0, y0


def mask_at(fig, cx, ground, H=240, W=400, key='alpha'):
    x0, y0 = origin(fig, cx, ground)
    out = np.zeros((H, W), bool)
    hh, ww = fig['h'], fig['w']
    sy0, sx0 = max(0, -y0), max(0, -x0)
    sy1, sx1 = min(hh, H - y0), min(ww, W - x0)
    out[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1] = fig[key][sy0:sy1, sx0:sx1]
    return out


def dist_map(m, rmax):
    d = np.full(m.shape, rmax + 1, np.float32)
    d[m] = 0
    cur = m.copy()
    for i in range(1, rmax + 1):
        nxt = dilate(cur)
        if i % 2 == 0:
            g = nxt.copy()
            g[1:, 1:] |= cur[:-1, :-1]
            g[:-1, :-1] |= cur[1:, 1:]
            g[1:, :-1] |= cur[:-1, 1:]
            g[:-1, 1:] |= cur[1:, :-1]
            nxt = g
        d[nxt & ~cur] = i
        cur = nxt
    return d


PLACED = []


def halo_rim(c, a, halo=2.0, rim=3.0):
    outer = dgrow(a, halo + rim)
    inner = dgrow(a, halo)
    c.ink[outer & ~inner] = True
    c.ink[inner & ~a] = False


def backdrop(c, fig, cx, ground, *args, **kw):
    return mask_at(fig, cx, ground, c.h, c.w)


def place(c, fig, cx, ground, halo=2.0, rim=3.0):
    x0, y0 = origin(fig, cx, ground)
    H, W = c.ink.shape
    a = np.zeros((H, W), bool)
    k = np.zeros((H, W), bool)
    hh, ww = fig['h'], fig['w']
    sy0, sx0 = max(0, -y0), max(0, -x0)
    sy1, sx1 = min(hh, H - y0), min(ww, W - x0)
    a[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1] = fig['alpha'][sy0:sy1, sx0:sx1]
    k[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1] = fig['ink'][sy0:sy1, sx0:sx1]
    if halo:
        halo_rim(c, a, halo, rim)
    c.ink[a] = k[a]
    if getattr(c, 'alpha', None) is not None:
        c.alpha |= a
    PLACED.append((fig, x0, y0))
    return a


def repaste(c):
    fig, x0, y0 = PLACED[-1]
    H, W = c.ink.shape
    hh, ww = fig['h'], fig['w']
    sy0, sx0 = max(0, -y0), max(0, -x0)
    sy1, sx1 = min(hh, H - y0), min(ww, W - x0)
    al = fig['alpha'][sy0:sy1, sx0:sx1]
    reg = c.ink[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1]
    reg[al] = fig['ink'][sy0:sy1, sx0:sx1][al]


def outline_errors(ink, fig, x0, y0):
    H, W = ink.shape
    ys, xs = np.nonzero(fig['outline'])
    Y, X = ys + y0, xs + x0
    ok = (Y >= 0) & (Y < H) & (X >= 0) & (X < W)
    bad = ~ink[Y[ok], X[ok]]
    return int(bad.sum()), int(ok.sum()), list(zip(X[ok][bad][:10], Y[ok][bad][:10]))


def sheet(width=96, path=None, scale=1):
    figs = [render(p, width=width) for p in POSES]
    gap = 14
    font = load_font(8)
    W = sum(f['w'] for f in figs) + gap * (len(figs) + 1)
    top = max(f['G'] for f in figs)
    below = max(f['h'] - f['G'] for f in figs)
    H = top + below + 30
    ink = np.zeros((H, W), bool)
    x = gap
    for f in figs:
        y = 8 + top - f['G']
        ink[y:y + f['h'], x:x + f['w']] |= f['ink'] & f['alpha']
        ink[8 + top + 2, x:x + f['w']] |= np.arange(f['w']) % 2 == 0
        img = Image.new('1', (W, H), 0)
        ImageDraw.Draw(img).text((x + f['w'] // 2 - len(f['pose']) * 3, 8 + top + 8), f['pose'].upper(), fill=1, font=font)
        ink |= np.array(img, bool)
        x += f['w'] + gap
    return ink, figs


REF_V3 = [
    ('neko-body2-figure-front.png', 'stand', (5, 5, 430), 'FIGURE: HEAD H/W 1.05, HEAD/TOTAL 0.56, COLLAR W 0.42 T 0.09, BELL D 0.12, TORSO W 0.45 (0.86 W/ ARMS) H 0.47, KOBAN 0.36X0.41, ARM T 0.19 L 0.42, LEG T 0.20 L 0.24'),
    ('neko-body2-manga-front.png', 'hands_up', (38, 15, 300), 'MANGA FRONT: HEAD H/W 1.01, COLLAR T 0.15, BELL D 0.11, KOBAN 0.38X0.38, TORSO+ARMS W 0.73, SOLE PADS 3 TOES + HEEL'),
    ('neko-body2-manga-sitting.png', 'sit', (125, 85, 380), 'MANGA SITTING: SOLE 0.22 W X 0.27 H, 3 TOE BEANS + HEEL PAD, LEGS OUT FRONT'),
    ('neko-body2-manga-action.png', 'cheer', (300, 60, 640), 'MANGA ACTION: TAIL SHORT THICK T 0.12, LEG T 0.2'),
]


def compare_sheet(width=96):
    font = load_font(8)
    cells = []
    for fn, pose, (hx0, hy0, hx1), txt in REF_V3:
        f = render(pose, width=width)
        im = Image.open(os.path.join(ROOT, 'art-references', fn)).convert('L')
        sc = width / float(hx1 - hx0)
        g = np.asarray(im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS))
        cells.append((g, f, txt))
    gap = 10
    W = sum(g.shape[1] + f['w'] + gap * 3 for g, f, _ in cells)
    body_h = max(max(g.shape[0], f['h']) for g, f, _ in cells)
    H = body_h + 2 * gap + 11 * 9
    out = np.full((H, W), 255, np.uint8)
    x = 0
    for g, f, _ in cells:
        out[gap:gap + g.shape[0], x + gap:x + gap + g.shape[1]] = g
        x += g.shape[1] + gap * 2
        out[gap:gap + f['h'], x:x + f['w']] = np.where(f['ink'], 0, 255)
        x += f['w'] + gap
    img = Image.fromarray(out)
    d = ImageDraw.Draw(img)
    y = body_h + 2 * gap
    st = cells[0][1]
    mine = 'MINE (HEAD 96PX = 2X): HEAD H/W 1.06, HEAD/TOTAL %.2f, NO COLLAR/BELL/KOBAN, TORSO W %.2f H %.2f, ARM T %.2f VIS LEN (SHOULDER TO PAW TIP) %.2f, PAW D %.2f, HANG PAW BTM AT MID-TORSO, RAISED PAW TOP AT JAW-0.15, LEG T %.2f L %.2f' % (
        (st['J'] - st['head_top']) / float(st['G'] - st['head_top']), TORSO_W, TORSO_H, ARM_T, ARM_L, PAW_R * 2, LEG_T, LEG_L)
    lines = ['REF RATIOS (X HEAD WIDTH, MEASURED IN PX) VS MINE. EACH REF SCALED TO 96PX HEAD WIDTH.'] + ['REF ' + c[2] for c in cells] + [mine]
    for ln in lines:
        d.text((4, y), ln, fill=0, font=font)
        y += 11
    return np.asarray(img)


def main():
    os.makedirs(OUT, exist_ok=True)
    ink, _ = sheet(96)
    im = Image.fromarray(np.where(ink, 0, 255).astype(np.uint8), 'L').convert('1')
    im.save(os.path.join(OUT, 'neko-v5-poses.png'))
    Image.fromarray(to_rgb(ink), 'RGB').resize((ink.shape[1] * 3, ink.shape[0] * 3), Image.NEAREST).save(os.path.join(OUT, 'neko-v5-poses@3x.png'))
    old_p = os.path.join(OUT, 'rejected', 'v4', 'neko-v4-poses.png')
    if os.path.exists(old_p):
        old = np.asarray(Image.open(old_p).convert('L')) < 128
        W = max(old.shape[1], ink.shape[1])
        both = np.zeros((old.shape[0] + ink.shape[0] + 6, W), bool)
        both[:old.shape[0], :old.shape[1]] = old
        both[old.shape[0] + 2:old.shape[0] + 4, :] = np.arange(W) % 2 == 0
        both[old.shape[0] + 6:, :ink.shape[1]] = ink
        Image.fromarray(to_rgb(both), 'RGB').resize((W * 3, both.shape[0] * 3), Image.NEAREST).save(os.path.join(OUT, 'neko-v4-vs-v5@3x.png'))


if __name__ == '__main__':
    main()
