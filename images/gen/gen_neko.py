import math
import os
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdart import B4, dilate, erode, load_font

SCRATCH = os.environ.get('NEKO_SCRATCH', '')

BODY = 2
SHADE = 8
INNER = 10
BLUSH = 10


def pat(level):
    return lambda x, y: B4[y & 3, x & 3] < level


STAMP_PAT = {':': 8, '=': 12, '+': 4, '*': 10}


class Spr:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ink = np.zeros((h, w), bool)
        self.alpha = np.zeros((h, w), bool)
        ys, xs = np.mgrid[0:h, 0:w]
        self.xs, self.ys = xs, ys

    def fill(self, v=False):
        self.ink[:] = v
        self.alpha[:] = True

    def put(self, m, p):
        if isinstance(p, (bool, np.bool_, int)):
            self.ink[m] = bool(p)
        else:
            self.ink[m] = p(self.xs, self.ys)[m]
        self.alpha[m] = True

    def erase(self, m):
        self.ink[m] = False
        self.alpha[m] = False

    def ss(self, fn, k=4):
        img = Image.new('L', (self.w * k, self.h * k), 0)
        d = ImageDraw.Draw(img)
        fn(d, k)
        a = np.asarray(img.resize((self.w, self.h), Image.BOX), dtype=np.float32)
        return a >= 128

    def poly(self, pts, k=4):
        return self.ss(lambda d, k: d.polygon([(x * k, y * k) for x, y in pts], fill=255), k)

    def ell(self, cx, cy, rx, ry, k=4):
        return self.ss(lambda d, k: d.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], fill=255), k)

    def rect(self, x0, y0, x1, y1):
        m = np.zeros((self.h, self.w), bool)
        m[max(0, int(y0)):max(0, int(y1)), max(0, int(x0)):max(0, int(x1))] = True
        return m

    def rrect(self, x0, y0, x1, y1, r, k=4):
        return self.ss(lambda d, k: d.rounded_rectangle([x0 * k, y0 * k, x1 * k - 1, y1 * k - 1], r * k, fill=255), k)

    def lines(self, pts, w, k=4, caps=True):
        def f(d, k):
            pp = [(x * k, y * k) for x, y in pts]
            d.line(pp, fill=255, width=max(1, int(round(w * k))), joint='curve')
            if caps:
                r = w * k / 2
                for x, y in (pp[0], pp[-1]):
                    d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return self.ss(f, k)

    def arc(self, cx, cy, rx, ry, a0, a1, w, n=24):
        pts = [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
        return self.lines(pts, w)

    def pline(self, pts):
        img = Image.new('1', (self.w, self.h), 0)
        ImageDraw.Draw(img).line([(int(x), int(y)) for x, y in pts], fill=1, width=1)
        return np.array(img, dtype=bool)

    def text(self, s, x, y, font, v=True):
        img = Image.new('L', (self.w, self.h), 0)
        ImageDraw.Draw(img).text((x, y), s, fill=255, font=font)
        m = np.asarray(img) >= 128
        self.put(m, v)
        return m

    def px(self, x, y, v=True):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.ink[y, x] = v
            self.alpha[y, x] = True

    def stamp(self, rows, x, y, center=True, flip=False):
        if isinstance(rows, str):
            rows = [r for r in rows.strip('\n').split('\n')]
        if flip:
            w = max(len(r) for r in rows)
            rows = [r.ljust(w, '.')[::-1] for r in rows]
        h = len(rows)
        w = max(len(r) for r in rows)
        x, y = int(math.floor(x)), int(math.floor(y))
        if center:
            x -= w // 2
            y -= h // 2
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                xx, yy = x + i, y + j
                if not (0 <= xx < self.w and 0 <= yy < self.h):
                    continue
                if ch == '#':
                    self.px(xx, yy, True)
                elif ch == 'o':
                    self.px(xx, yy, False)
                elif ch in STAMP_PAT:
                    self.px(xx, yy, B4[yy & 3, xx & 3] < STAMP_PAT[ch])
                elif ch == 'b':
                    self.px(xx, yy, B4[yy & 3, xx & 3] < BODY)
                elif ch == 'x':
                    self.ink[yy, xx] = False
                    self.alpha[yy, xx] = False

    def blit(self, other, x, y, flip=False):
        ink, al = other.ink, other.alpha
        if flip:
            ink, al = ink[:, ::-1], al[:, ::-1]
        h, w = ink.shape
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        si = ink[y0 - y:y1 - y, x0 - x:x1 - x]
        sa = al[y0 - y:y1 - y, x0 - x:x1 - x]
        self.ink[y0:y1, x0:x1][sa] = si[sa]
        self.alpha[y0:y1, x0:x1] |= sa

    def save(self, path):
        a = np.where(self.ink, 0, 255).astype(np.uint8)
        rgba = np.zeros((self.h, self.w, 4), np.uint8)
        rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = a
        rgba[..., 3] = np.where(self.alpha, 255, 0)
        Image.fromarray(rgba, 'RGBA').save(path)

    def save_opaque(self, path):
        a = np.where(self.ink & self.alpha, 0, 255).astype(np.uint8)
        Image.fromarray(a, 'L').convert('1').save(path)

    def crop(self, pad=0):
        ys, xs = np.nonzero(self.alpha)
        x0, x1 = max(0, xs.min() - pad), min(self.w, xs.max() + 1 + pad)
        y0, y1 = max(0, ys.min() - pad), min(self.h, ys.max() + 1 + pad)
        s = Spr(x1 - x0, y1 - y0)
        s.ink = self.ink[y0:y1, x0:x1].copy()
        s.alpha = self.alpha[y0:y1, x0:x1].copy()
        return s

    def preview(self, path, scale=3, magenta=False):
        rgb = np.stack([np.where(self.ink, 0x31, 0xB1), np.where(self.ink, 0x2F, 0xAF),
                        np.where(self.ink, 0x28, 0xA8)], -1).astype(np.uint8)
        if magenta:
            rgb[~self.alpha] = (255, 0, 255)
        Image.fromarray(rgb, 'RGB').resize((self.w * scale, self.h * scale), Image.NEAREST).save(path)


def shift(m, dx, dy):
    out = np.zeros_like(m)
    h, w = m.shape
    xs0, xs1 = max(0, dx), min(w, w + dx)
    ys0, ys1 = max(0, dy), min(h, h + dy)
    if xs1 > xs0 and ys1 > ys0:
        out[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def grow(m, t):
    for _ in range(t):
        m = dilate(m)
    return m


def disc_grow(m, r):
    out = m.copy()
    ri = int(math.ceil(r))
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            if (dx or dy) and dx * dx + dy * dy <= r * r + 0.5:
                out |= shift(m, dx, dy)
    return out


def smooth(m):
    return grow(erode(m), 1) | (erode(grow(m, 1)) & m)


def outline(sp, m, t, v=True):
    sp.put(disc_grow(m, t) & ~m, v)


def head_pts(cx, cy, u, n=3.0, bulge=0.10, squash=0.80):
    pts = []
    for i in range(120):
        t = 2 * math.pi * i / 120
        c, s_ = math.cos(t), math.sin(t)
        x = math.copysign(abs(c) ** (2 / n), c)
        y = math.copysign(abs(s_) ** (2 / n), s_)
        x *= 1 + bulge * y
        pts.append((cx + x * u, cy + y * u * squash))
    return pts


def ear_pts(cx, cy, u, side, lift=0.0, inner=False, lean=0.0):
    base_out = (-0.96, -0.30)
    base_in = (-0.26, -0.72)
    tip = (-0.76 + lean, -1.10 - lift)
    if inner:
        base_out = (-0.80, -0.44)
        base_in = (-0.40, -0.66)
        tip = (-0.72 + lean * 0.9, -0.96 - lift * 0.9)
    a, t, b = base_out, tip, base_in
    res = []
    for i in range(13):
        k = i / 12
        res.append((a[0] + (t[0] - a[0]) * k, a[1] + (t[1] - a[1]) * k))
    for i in range(1, 13):
        k = i / 12
        res.append((t[0] + (b[0] - t[0]) * k, t[1] + (b[1] - t[1]) * k))
    res.append((b[0] + 0.2, b[1] + 0.3))
    res.append((a[0] + 0.2, a[1] + 0.3))
    return [(cx + side * x * u, cy + y * u) for x, y in res]


def base_head(sp, cx, cy, W, ears=((0, 0), (0, 0)), char=False, gloss=True, shade=True):
    u = W / 2.0
    t = 2 if W < 70 else 3
    head = sp.poly(head_pts(cx, cy, u))
    (l0, n0), (l1, n1) = ears
    eL = sp.poly(ear_pts(cx, cy, u, -1, lift=l0, lean=n0))
    eR = sp.poly(ear_pts(cx, cy, u, 1, lift=l1, lean=n1))
    sil = smooth(head | eL | eR)
    outline(sp, sil, t)
    sp.put(sil, pat(BODY))
    if char:
        sp.put(sil, pat(3))
    if shade:
        d = max(2, int(round(W * 0.07)))
        sh = sil & ~shift(sil, -d, -max(1, d // 2))
        sh &= sp.xs > cx - u * 0.2
        sp.put(sh, pat(SHADE))
    iL = sp.poly(ear_pts(cx, cy, u, -1, lift=l0, lean=n0, inner=True)) & eL
    iR = sp.poly(ear_pts(cx, cy, u, 1, lift=l1, lean=n1, inner=True)) & eR
    sp.put((iL | iR) & ~head, pat(INNER if not char else 14))
    if gloss:
        ang = np.degrees(np.arctan2(sp.ys + 0.5 - cy, sp.xs + 0.5 - cx))
        sector = (ang > -150) & (ang < -112)
        if W >= 70:
            g = head & ~shift(head, 3, 3) & shift(head, 1, 1) & sector
            sp.put(g, False)
            spot = sp.ell(cx - u * 0.62, cy - u * 0.36, u * 0.05, u * 0.05)
            sp.put(spot, False)
        else:
            g = head & ~shift(head, 2, 2) & shift(head, 1, 1) & sector
            sp.put(g, False)
    return dict(sp=sp, cx=cx, cy=cy, u=u, W=W, t=t, sil=sil, head=head)


def whiskers(ctx, droop=0.0, n=3, frazzle=False):
    sp, cx, cy, u, W = ctx['sp'], ctx['cx'], ctx['cy'], ctx['u'], ctx['W']
    lw = 1 if W < 70 else 2
    for side in (-1, 1):
        for i in range(n):
            yy = cy + u * (0.16 + 0.16 * i)
            x0 = cx + side * u * 0.80
            x1 = cx + side * u * 1.20
            dy = (i - (n - 1) / 2) * u * 0.08 + droop * u * 0.12
            if frazzle:
                xm = (x0 + x1) / 2
                pts = [(x0, yy), (xm, yy + dy / 2 - u * 0.08), (x1, yy + dy + u * 0.06)]
            else:
                pts = [(x0, yy), (x1, yy + dy)]
            if lw == 1:
                sp.put(sp.pline(pts), True)
            else:
                sp.put(sp.lines(pts, lw), True)


# ---------------- large (vector) face: hero / title / turnaround ----------------

def big_eyes(ctx, kind='dot', look=0.0, dy=0.0):
    sp, cx, cy, u, W = ctx['sp'], ctx['cx'], ctx['cy'], ctx['u'], ctx['W']
    ey = cy + u * (0.04 + dy)
    lw = 2 if W < 90 else 3
    for side in (-1, 1):
        ex = cx + side * u * 0.44
        if kind == 'masked':
            r = u * 0.135
            px = ex + look * u * 0.07 - side * u * 0.02
            py = ey + u * 0.03
            sp.put(sp.ell(px, py, r, r * 1.12), True)
            sp.put(sp.ell(px - r * 0.34, py - r * 0.42, r * 0.36, r * 0.36), False)
            sp.put(sp.ell(px + r * 0.38, py + r * 0.45, r * 0.15, r * 0.15), False)
        elif kind == 'dot':
            r = u * 0.15
            px = ex + look * u * 0.07
            sp.put(sp.ell(px, ey, r, r * 1.15), True)
            sp.put(sp.ell(px - r * 0.34, ey - r * 0.42, r * 0.34, r * 0.34), False)
            sp.put(sp.ell(px + r * 0.38, ey + r * 0.45, r * 0.15, r * 0.15), False)
        elif kind == 'happy':
            sp.put(sp.arc(ex, ey + u * 0.08, u * 0.15, u * 0.14, 200, 340, lw), True)
        elif kind == 'half':
            r = u * 0.15
            px = ex + look * u * 0.07
            e = sp.ell(px, ey, r, r * 1.15)
            e &= sp.ys > ey - r * 0.1
            sp.put(e, True)
            sp.put(sp.ell(px - r * 0.3, ey + r * 0.25, r * 0.28, r * 0.28), False)
            sp.put(sp.lines([(ex - u * 0.2, ey - r * 0.15), (ex + u * 0.2, ey - r * 0.15)], lw), True)
        elif kind == 'squint':
            sp.put(sp.lines([(ex - u * 0.16, ey), (ex + u * 0.16, ey)], lw), True)
            sp.put(sp.lines([(ex - u * 0.1, ey + u * 0.06), (ex + u * 0.1, ey + u * 0.06)], lw), True)


def big_mouth(ctx, kind='w', dy=0.0):
    sp, cx, cy, u, W = ctx['sp'], ctx['cx'], ctx['cy'], ctx['u'], ctx['W']
    lw = 2 if W < 110 else 3
    ny = cy + u * (0.15 + dy)
    rw = u * 0.075
    nm = sp.ell(cx, ny, rw * 1.35, rw * 0.85)
    sp.put(grow(nm, 1), True)
    sp.put(nm, pat(INNER))
    my = ny + u * 0.07
    a = u * 0.11
    if kind == 'open':
        m = sp.ell(cx, my + a * 1.3, a * 1.1, a * 1.25)
        m &= sp.ys > my + a * 0.2
        sp.put(grow(m, lw - 1) | m, True)
        inner = m & ~grow(~m, 1)
        sp.put(inner, False)
        sp.put(inner & (sp.ys > my + a * 1.6), pat(INNER))
    if kind == 'flat':
        sp.put(sp.lines([(cx - a * 1.4, my + a * 0.6), (cx + a * 1.4, my + a * 0.5)], lw), True)
        return
    pts = [(cx - a * 1.9, my - a * 0.1), (cx - a * 1.45, my + a * 0.65), (cx - a * 0.8, my + a * 0.75), (cx - a * 0.25, my + a * 0.35), (cx, my - a * 0.1),
           (cx + a * 0.25, my + a * 0.35), (cx + a * 0.8, my + a * 0.75), (cx + a * 1.45, my + a * 0.65), (cx + a * 1.9, my - a * 0.1)]
    sp.put(sp.lines(pts[1:-1], lw), True)


def big_blush(ctx):
    sp, cx, cy, u = ctx['sp'], ctx['cx'], ctx['cy'], ctx['u']
    for side in (-1, 1):
        bx = cx + side * u * 0.66
        m = sp.ell(bx, cy + u * 0.30, u * 0.14, u * 0.075)
        sp.put(m, pat(BLUSH))


def big_mask(ctx, up=False, knot=True):
    sp, cx, cy, u, W = ctx['sp'], ctx['cx'], ctx['cy'], ctx['u'], ctx['W']
    sil = ctx['sil']
    lift = u * 0.56 if up else u * 0.05
    ey = cy + u * 0.04 - lift
    sc = 0.8 if up else 1.0
    m = np.zeros_like(sil)
    for side in (-1, 1):
        ex = cx + side * u * 0.44
        m |= sp.ell(ex + side * u * 0.03, ey + u * 0.01, u * 0.37, u * 0.36 * sc)
        m |= sp.poly([(ex - side * u * 0.02, ey - u * 0.22 * sc), (ex + side * u * 0.56, ey - u * 0.40 * sc),
                      (ex + side * u * 0.40, ey + u * 0.06), (ex, ey + u * 0.06)])
    m |= sp.poly([(cx - u * 0.3, ey - u * 0.25 * sc), (cx + u * 0.3, ey - u * 0.25 * sc), (cx + u * 0.16, ey + u * 0.06),
                  (cx, ey + u * 0.03), (cx - u * 0.16, ey + u * 0.06)])
    m = smooth(m)
    band = sp.rect(0, ey - u * 0.16, sp.w, ey - u * 0.04) & sil
    sp.put((m | band) & grow(sil, 1), True)
    hl = m & ~shift(m, 0, 2) & shift(m, 0, 1) & (sp.xs < cx - u * 0.12) & (sp.xs > cx - u * 0.72)
    sp.put(hl, False)
    for side in (-1, 1):
        ex = cx + side * u * 0.44
        if up:
            sp.put(sp.ell(ex, ey + u * 0.02, u * 0.2, u * 0.11), pat(BODY))
        else:
            sp.put(sp.ell(ex, ey + u * 0.0, u * 0.215, u * 0.26), False)
    if knot:
        kx, ky = cx + u * 1.02, ey - u * 0.10
        lw = max(2, u * 0.1)
        sp.put(sp.ell(kx, ky, u * 0.09, u * 0.09), True)
        sp.put(sp.lines([(kx, ky), (kx + u * 0.22, ky - u * 0.18), (kx + u * 0.38, ky - u * 0.12)], lw), True)
        sp.put(sp.lines([(kx, ky), (kx + u * 0.26, ky + u * 0.06), (kx + u * 0.4, ky + u * 0.2)], lw), True)
    ctx['mask'] = m


def big_face(ctx, eyes='dot', mouth='w', mask='up', look=0.0, blush=True):
    if mask == 'down':
        big_mask(ctx)
    elif mask == 'up':
        big_mask(ctx, up=True)
    whiskers(ctx)
    if blush:
        big_blush(ctx)
    big_eyes(ctx, 'masked' if (mask == 'down' and eyes == 'dot') else eyes, look)
    big_mouth(ctx, mouth)


def big_head(W, **kw):
    ears = kw.pop('ears', ((0, 0), (0, 0)))
    sp = Spr(int(W * 1.9) + 10, int(W * 1.5) + 10)
    cx = sp.w // 2 + 0.5
    cy = int(sp.h * 0.6) + 0.5
    ctx = base_head(sp, cx, cy, W, ears=ears)
    big_face(ctx, **kw)
    return sp.crop()


# ---------------- body parts ----------------

def part(sp, m, fill, t=2, shade=SHADE, d=3, cx=None):
    outline(sp, m, t)
    sp.put(m, fill)
    if shade is not None:
        sh = m & ~shift(m, -d, -max(1, d - 1))
        if cx is not None:
            sh &= sp.xs > cx
        sp.put(sh, pat(shade))


def stripes(period=6, black=3):
    return lambda x, y: (y % period) < black


def paw(sp, x, y, r, t=2, pads=False, fill=None):
    m = sp.ell(x, y, r * 1.1, r)
    part(sp, m, pat(BODY) if fill is None else fill, t=t, shade=None)
    if pads and r >= 4:
        for k in (-1, 1):
            sp.put(sp.lines([(x + k * r * 0.4, y - r * 0.1), (x + k * r * 0.4, y + r * 0.5)], 1), True)
    return m


DOLLAR = '''
..##..
.####.
##.#..
.###..
..###.
..#.##
####..
..##..
'''
DOLLAR_BIG = '''
...##...
.######.
###.##..
###.##..
.######.
...##.##
...##.##
.######.
...##...
'''


def loot_sack(sp, sx, sy, r=22, t=2):
    sack = sp.ell(sx, sy, r * 1.05, r) | sp.poly([(sx - r * 0.45, sy - r * 0.7), (sx - r * 0.3, sy - r * 1.25),
                                                    (sx + r * 0.3, sy - r * 1.25), (sx + r * 0.45, sy - r * 0.7)])
    sack = smooth(sack)
    part(sp, sack, pat(4), t=t, cx=sx - r * 0.2, shade=10, d=max(3, int(r * 0.2)))
    hl = sack & ~shift(sack, 2, 2) & shift(sack, 1, 1) & (sp.xs < sx) & (sp.ys < sy + 2) & (sp.ys > sy - r * 0.8)
    sp.put(hl, False)
    tie = sp.lines([(sx - r * 0.42, sy - r * 0.8), (sx + r * 0.42, sy - r * 0.8)], max(2, r * 0.12))
    sp.put(tie, True)
    for k in (-1, 0, 1):
        sp.put(sp.lines([(sx + k * r * 0.18, sy - r * 1.15), (sx + k * r * 0.2, sy - r * 0.95)], 1), True)
    if r >= 18:
        f = load_font(24 if r >= 20 else 16)
        img = Image.new('L', (60, 60), 0)
        ImageDraw.Draw(img).text((0, 0), '$', fill=255, font=f)
        g = np.asarray(img) >= 128
        ys, xs = np.nonzero(g)
        g = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        h, w = g.shape
        x0, y0 = int(sx - w / 2 + 1), int(sy + r * 0.15 - h / 2)
        m = np.zeros_like(sack)
        m[y0:y0 + h, x0:x0 + w] = g
        sp.put(grow(m, 1) & sack, False)
        sp.put(m, True)
    else:
        sp.stamp(DOLLAR, sx + 1, sy + r * 0.12)
    return sack


def neko_hero(W=66, mask='down', look=1.2, eyes='dot', mouth='w', wave=True):
    sp = Spr(170, 130)
    hx, hy = 70.5, 44.5
    t = 2
    by = hy + 46
    tail = sp.lines([(hx - 16, by + 16), (hx - 30, by + 18), (hx - 40, by + 12), (hx - 44, by + 2), (hx - 40, by - 5)], 7)
    part(sp, tail, pat(BODY), t=t, shade=None)
    sp.put(sp.lines([(hx - 45, by + 5), (hx - 40, by + 4)], 3) & tail, pat(10))
    sp.put(sp.lines([(hx - 41, by + 14), (hx - 38, by + 10)], 3) & tail, pat(10))
    loot_sack(sp, hx + 44, by - 2, 23, t)
    body = sp.ell(hx, by + 2, 25, 20) | sp.rrect(hx - 23, by - 18, hx + 23, by + 16, 10)
    feetm = sp.ell(hx - 12, by + 20, 10, 6) | sp.ell(hx + 12, by + 20, 10, 6)
    part(sp, feetm, pat(BODY), t=t, shade=None)
    part(sp, body, stripes(), t=t, shade=None)
    shade_side = body & ~shift(body, -6, 0) & (sp.xs > hx)
    sp.put(shade_side & ~stripes()(sp.xs, sp.ys), pat(8))
    belly = body & (sp.ys >= by + 9)
    sp.put(belly, pat(BODY))
    sp.put(belly & ~shift(body, -4, -2), pat(8))
    sp.put(body & (sp.ys >= by + 8) & (sp.ys < by + 9), True)
    for fx in (hx - 12, hx + 12):
        sp.put(sp.lines([(fx - 3, by + 22), (fx - 3, by + 24)], 1) | sp.lines([(fx + 3, by + 22), (fx + 3, by + 24)], 1), True)
    armR = sp.lines([(hx + 17, by - 10), (hx + 26, by - 18), (hx + 36, by - 20)], 8)
    part(sp, armR, pat(BODY), t=t, shade=None)
    if wave:
        armL = sp.lines([(hx - 17, by - 10), (hx - 32, by - 16), (hx - 42, by - 28)], 8)
    else:
        armL = sp.lines([(hx - 17, by - 10), (hx - 26, by - 2), (hx - 22, by + 6)], 8)
    part(sp, armL, pat(BODY), t=t, shade=None)
    ctx = base_head(sp, hx, hy, W)
    big_face(ctx, mask=mask, look=look, eyes=eyes, mouth=mouth)
    paw(sp, hx + 37, by - 21, 6, pads=True)
    if wave:
        paw(sp, hx - 44, by - 31, 6, pads=True)
        for r in (10, 14):
            sp.put(sp.arc(hx - 44, by - 31, r, r, 195, 250, 1), True)
    return sp.crop()


# ---------------- small (40px) pixel faces ----------------

SW = 42


def S(txt):
    return [r for r in txt.strip('\n').split('\n')]


EYE = S('''
.###.
#oo##
#oo##
#####
#####
#####
.###.
''')
EYE_HAPPY = S('''
..###..
.#####.
##...##
#.....#
''')
EYE_SLEEP = S('''
#.....#
##...##
.#####.
''')
EYE_FOCUS = S('''
#######
.##o##.
..###..
''')
EYE_SHOCK = S('''
..###..
.#ooo#.
#ooooo#
#oo#oo#
#oo#oo#
#ooooo#
#ooooo#
.#ooo#.
..###..
''')
EYE_X = S('''
##...##
###.###
.#####.
..###..
.#####.
###.###
##...##
''')
EYE_DOLLAR = S('''
..#..
.####
##.#.
##.#.
.###.
..#.#
..#.#
####.
..#..
''')
PUPIL = S('''
.##.
#o##
####
.##.
''')
PUPIL_S = S('''
##
##
''')
MOUTH_W = S('''
..###..
...#...
#..#..#
.##.##.
''')
MOUTH_OPEN = S('''
..###..
...#...
#######
#ooooo#
.#o*o#.
..###..
''')
MOUTH_O = S('''
..###..
...#...
..###..
.#ooo#.
#o***o#
#o***o#
.#ooo#.
..###..
''')
MOUTH_SMALL_O = S('''
..###..
...#...
...#...
..#o#..
..###..
''')
MOUTH_WAVY = S('''
..###..
...#...
.......
.#.#.#.
#.#.#.#
''')
MOUTH_GRIN = S('''
..###..
...#...
#######
.#ooo#.
..#o#..
...#...
''')
MOUTH_SMIRK = S('''
..###..
...#...
......#
.#..##.
..##...
''')
MOUTH_KO = S('''
..###..
...#...
.......
.#####.
.#o*o#.
....##.
''')
MOUTH_SLEEP = S('''
..###..
...#...
.......
..###..
..#o#..
..###..
''')
BLUSH_S = S('''
.#.#.#
#.#.#.
''')
DROP = S('''
..#..
..#..
.#o#.
#ooo#
#ooo#
.###.
''')
DROP_BIG = S('''
...#...
...#...
..#o#..
.#ooo#.
#ooooo#
#oo:oo#
.#o::#.
..###..
''')
BANG = S('''
##
##
##
##
..
##
''')
Z_BIG = S('''
#####
...#.
..#..
.#...
#####
''')
Z_SMALL = S('''
###
.#.
###
''')
SPARK = S('''
...#...
...#...
..###..
#######
..###..
...#...
...#...
''')
SPARK_S = S('''
.#.
###
.#.
''')
STAR = S('''
..#..
.###.
#####
.#.#.
''')
COIN = S('''
.####.
#oooo#
#o##o#
#o##o#
#oooo#
.####.
''')
BUBBLE = S('''
.###.
#oo.#
#o..#
#...#
.###.
''')
PAW_UP = S('''
.##.##.##.
#bb#bb#bb#
#bbbbbbbb#
#bbbbbbbb#
#bb****bb#
#b******b#
#bb****bb#
.#bbbbbb#.
..#bbbb#..
..#bbbb#..
''')
MASK_UP = S('''
#.........................#
##.......................##
.#########.......#########.
###########################
###::::::#########::::::###
.###::::###########::::###.
..#########.....#########..
....#####...........#####..
''')
KNOT = S('''
......##
..#.###.
.####...
####....
.####...
..#.###.
......##
''')


def small_mask_down(sp, ci, cj, angry=False):
    ey = cj + 1
    m = np.zeros((sp.h, sp.w), bool)
    for side in (-1, 1):
        ex = ci + 0.5 + side * 10
        m |= sp.ell(ex + side * 0.5, ey + 0.5, 8.2, 6.4)
        tip_y = ey - 7 if not angry else ey - 8
        m |= sp.poly([(ex - side * 2, ey - 4), (ex + side * 10.5, tip_y), (ex + side * 8, ey + 1), (ex, ey + 2)])
    m |= sp.rect(ci - 8, ey - 5, ci + 9, ey + 1)
    if angry:
        m |= sp.poly([(ci - 16, ey - 6), (ci + 0.5, ey - 2), (ci + 17, ey - 6), (ci + 17, ey), (ci - 16, ey)])
    sp.put(m & grow(sp.alpha, 0), True)
    holes = []
    for side in (-1, 1):
        ex = ci + 0.5 + side * 10
        h = sp.ell(ex, ey + 0.5, 3.6, 4.2)
        if angry:
            h &= ~sp.poly([(ex - side * 5, ey - 5), (ex + side * 5, ey - 5), (ex + side * 5, ey - 3.5), (ex - side * 5, ey - 0.5)])
        sp.put(h, False)
        holes.append(h)
    sp.stamp(KNOT, ci + 22, cj - 3)
    return holes


def small_head(expr, pad=18, mask=None, body=None):
    global BODY
    W = SW
    sp = Spr(W + 2 * pad + 12, W + 2 * pad + 12)
    cx = sp.w // 2 + 0.5
    cy = sp.h // 2 + 5.5
    ears = ((0, 0), (0, 0))
    char = False
    if expr == 'listening':
        ears = ((-0.06, 0.08), (0.26, 0.14))
    if expr == 'shocked':
        ears = ((0.12, -0.06), (0.12, 0.06))
    if expr in ('caught', 'sleeping', 'sweating'):
        ears = ((-0.08, 0.12), (-0.08, -0.12))
    if expr == 'dizzy':
        char = True
    keep = BODY
    BODY = 1 if body is None else body
    ctx = base_head(sp, cx, cy, W, ears=ears, char=char)
    ci, cj = int(cx), int(cy)
    EL, ER = ci - 10, ci + 10
    EY = cj + 1
    MY = cj + 7
    if mask is None:
        mask = 'down' if expr in ('neutral', 'listening', 'shifty', 'caught', 'determined') else 'up'
    if expr == 'dizzy':
        sp.put(sp.ell(ci - 11, cj - 7, 5, 2.5) | sp.ell(ci + 13, cj + 11, 4, 2) | sp.ell(ci - 15, cj + 12, 3, 1.5), pat(12))
    whisk = dict(droop=0.0, frazzle=False)
    if expr in ('sweating', 'caught', 'sleeping'):
        whisk['droop'] = 0.7
    if expr == 'dizzy':
        whisk['frazzle'] = True
    whiskers(ctx, **whisk)
    if mask == 'up':
        sp.stamp(MASK_UP, ci, cj - 12)
        sp.stamp(KNOT, ci + 22, cj - 13)
    holes = None
    if mask == 'down':
        holes = small_mask_down(sp, ci, cj, angry=(expr == 'determined'))
    if mask != 'down' and expr not in ('dizzy',):
        sp.stamp(BLUSH_S, ci - 15, cj + 7)
        sp.stamp(BLUSH_S, ci + 16, cj + 7)

    def eyes(st, dy=0, flip_r=False):
        sp.stamp(st, EL, EY + dy)
        sp.stamp(st, ER + (1 if flip_r else 0), EY + dy, flip=flip_r)

    def pupils(dx=0, dy=1, st=PUPIL):
        for x in (EL, ER):
            sp.stamp(st, x + 1 + dx, EY + dy)

    if expr == 'neutral':
        if mask == 'down':
            pupils(0, 1)
        else:
            eyes(EYE)
        sp.stamp(MOUTH_W, ci, MY)
    elif expr == 'happy':
        if mask == 'down':
            for x in (EL, ER):
                sp.stamp(S('''
.###.
#...#
#...#
'''), x + 1, EY + 1)
        else:
            eyes(EYE_HAPPY, 0)
        sp.stamp(MOUTH_OPEN, ci, MY + 1)
        sp.stamp(SPARK_S, ci - 25, cj - 10); sp.stamp(SPARK, ci + 27, cj - 18)
    elif expr == 'listening':
        for x in (EL, ER):
            sp.put(sp.rect(x - 4, EY - 4, x + 5, EY - 1), True)
            sp.stamp(PUPIL, x + 2, EY + 1)
        sp.stamp(MOUTH_SMALL_O, ci, MY)
        for r in (4, 7, 10):
            sp.put(sp.arc(ci + 19, cj - 22, r, r, -80, 10, 1), True)
    elif expr == 'shocked':
        if mask == 'down':
            for x in (EL, ER):
                sp.stamp(PUPIL_S, x + 1, EY + 1)
        else:
            eyes(EYE_SHOCK)
        sp.stamp(MOUTH_O, ci, MY + 1)
        sp.stamp(BANG, ci + 27, cj - 20); sp.stamp(BANG, ci + 31, cj - 18)
        for k in range(3):
            sp.put(sp.pline([(ci - 16 + k * 3, cj - 13), (ci - 16 + k * 3, cj - 10)]), True)
    elif expr == 'sweating':
        if mask == 'down':
            pupils(-1, 0)
        else:
            eyes(EYE)
        sp.stamp(MOUTH_WAVY, ci, MY)
        sp.stamp(DROP_BIG, ci + 20, cj - 12); sp.stamp(DROP, ci - 23, cj - 9)
        sp.put(sp.pline([(ci - 14, cj - 4), (ci - 6, cj - 6)]), True)
        sp.put(sp.pline([(ci + 14, cj - 4), (ci + 6, cj - 6)]), True)
    elif expr == 'shifty':
        for x, h in zip((EL, ER), holes):
            sp.stamp(PUPIL, x + 3, EY + 2)
            sp.put(h & (sp.ys <= EY - 1), True)
        sp.stamp(MOUTH_SMIRK, ci, MY)
        for k in range(3):
            sp.put(sp.pline([(ci - 27, cj + 1 + k * 4), (ci - 33, cj + 1 + k * 4)]), True)
    elif expr == 'rich':
        eyes(EYE_DOLLAR)
        sp.stamp(MOUTH_OPEN, ci, MY + 2)
        sp.stamp(COIN, ci - 27, cj - 12); sp.stamp(COIN, ci + 28, cj - 6); sp.stamp(SPARK_S, ci + 23, cj - 20); sp.stamp(SPARK_S, ci - 20, cj - 22)
    elif expr == 'caught':
        for x in (EL, ER):
            sp.stamp(PUPIL_S, x + 1, EY + 1)
        sp.stamp(MOUTH_WAVY, ci, MY + 1)
        sp.stamp(PAW_UP, ci - 29, cj - 12); sp.stamp(PAW_UP, ci + 30, cj - 12, flip=True)
        sp.stamp(DROP, ci + 17, cj - 16)
    elif expr == 'dizzy':
        eyes(EYE_X)
        sp.stamp(MOUTH_KO, ci, MY + 1)
        orbit = sp.ell(ci, cj - 25, 17, 4.5) & ~sp.ell(ci, cj - 25, 16, 3.5)
        sp.put(orbit & ((sp.xs // 2) % 2 == 0), True)
        sp.stamp(STAR, ci - 14, cj - 27); sp.stamp(STAR, ci + 11, cj - 24); sp.stamp(SPARK_S, ci - 1, cj - 30)
        for k, (x0, y0) in enumerate([(ci - 30, cj - 2), (ci + 28, cj + 8)]):
            sp.put(sp.ell(x0, y0, 4, 3) | sp.ell(x0 + 3, y0 - 3, 3, 3), pat(6))
    elif expr == 'sleeping':
        eyes(EYE_SLEEP, 1)
        sp.stamp(MOUTH_SLEEP, ci, MY)
        sp.stamp(BUBBLE, ci + 7, cj + 5)
        sp.stamp(Z_BIG, ci + 25, cj - 20); sp.stamp(Z_SMALL, ci + 31, cj - 27)
    elif expr == 'determined':
        pupils(0, 1)
        sp.stamp(MOUTH_GRIN, ci, MY + 1)
        sp.stamp(SPARK, ci + 27, cj - 16)
    BODY = keep
    return sp.crop()


EXPRS = ['neutral', 'happy', 'listening', 'shocked', 'sweating', 'shifty', 'rich', 'caught', 'dizzy', 'sleeping', 'determined']

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'prototypes', 'neko')


def tiny_head(W=24):
    sp = Spr(W * 2 + 8, W * 2 + 8)
    cx, cy = sp.w // 2 + 0.5, sp.h // 2 + 3.5
    global BODY
    keep = BODY
    BODY = 1
    ctx = base_head(sp, cx, cy, W, gloss=False)
    ci, cj = int(cx), int(cy)
    sp.stamp(S('''
#.........#
##########.
.##::#::##.
'''), ci, cj - 6)
    for x in (ci - 6, ci + 6):
        sp.stamp(S('''
##
##
##
'''), x + 1, cj + 1)
    sp.stamp(S('''
.#.
#.#
'''), ci, cj + 4)
    for side in (-1, 1):
        sp.put(sp.pline([(ci + side * 10, cj + 3), (ci + side * 14, cj + 2)]), True)
        sp.put(sp.pline([(ci + side * 10, cj + 5), (ci + side * 14, cj + 6)]), True)
    BODY = keep
    return sp.crop()


def font_mask(text, path, size, k=4):
    from PIL import ImageFont
    f = ImageFont.truetype(path, size * k)
    l, t, r, b = f.getbbox(text)
    img = Image.new('L', (r - l + 8 * k, b - t + 8 * k), 0)
    ImageDraw.Draw(img).text((4 * k - l, 4 * k - t), text, fill=255, font=f)
    img = img.resize((img.width // k, img.height // k), Image.BOX)
    return np.asarray(img) >= 128


def place(sp, m, x, y):
    out = np.zeros((sp.h, sp.w), bool)
    h, w = m.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(sp.w, x + w), min(sp.h, y + h)
    out[y0:y1, x0:x1] = m[y0 - y:y1 - y, x0 - x:x1 - x]
    return out


def brick_wall(sp, rays=True, spot=(140, 122, 98, 100)):
    bw, bh = 26, 11
    ys, xs = sp.ys, sp.xs
    row = ys // bh
    off = np.where(row % 2 == 1, bw // 2, 0)
    mortar = (ys % bh == 0) | ((xs + off) % bw == 0)
    lower = (ys % bh >= bh - 3)
    top = (ys % bh == 1) & ((xs + off) % bw > 1)
    sx, sy, rx, ry = spot
    d = np.sqrt(((xs + 0.5 - sx) / rx) ** 2 + ((ys + 0.5 - sy) / ry) ** 2)
    inside = d <= 1.0
    edge = (d > 1.0) & (d <= 1.04)
    dark_face = pat(11)(xs, ys)
    dark_face = np.where(lower, pat(14)(xs, ys), dark_face)
    dark_face = np.where(top, pat(7)(xs, ys), dark_face)
    lit_face = pat(1)(xs, ys)
    lit_face = np.where(lower, pat(6)(xs, ys), lit_face)
    lit_face = np.where(top, False, lit_face)
    ink = np.where(inside, lit_face, dark_face)
    ink = np.where(edge, pat(8)(xs, ys) | mortar, ink)
    ink = np.where(mortar & ~edge, True, ink)
    if rays:
        lx, ly = -40, -60
        ang = np.degrees(np.arctan2(ys + 0.5 - ly, xs + 0.5 - lx))
        beam = (ang > 41) & (ang < 53) & ~inside & ~edge & (ys < 206)
        bf = np.where(lower, pat(10)(xs, ys), pat(6)(xs, ys))
        bf = np.where(top, pat(2)(xs, ys), bf)
        ink = np.where(beam & ~mortar, bf, ink)
    sp.ink[:] = ink
    sp.alpha[:] = True


def rim_composite(dst, src, x, y, rim=1):
    tmp = Spr(dst.w, dst.h)
    tmp.blit(src, x, y)
    halo = disc_grow(tmp.alpha, rim) & ~tmp.alpha
    dst.put(halo, False)
    dst.blit(tmp, 0, 0)


def neko_title_spr(W=100):
    sp = Spr(260, 200)
    neko_title(sp, 100.5, 70.5, W)
    return sp


def wordmark(sp, text, x, y, size=44, spacing=-2):
    path = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Silkscreen-Regular.ttf')
    m = np.zeros((sp.h, sp.w), bool)
    cx = x
    for ch in text:
        g = font_mask(ch, path, size)
        ys, xs = np.nonzero(g)
        g = g[:, xs.min():xs.max() + 1]
        m |= place(sp, g, cx, y)
        cx += g.shape[1] + spacing
    ext = np.zeros_like(m)
    for d in range(1, 6):
        ext |= shift(m, 0, d)
    solid = disc_grow(m | ext, 3)
    sp.put(shift(solid, 4, 3) & ~solid, pat(12))
    sp.put(disc_grow(solid, 1) & ~solid, False)
    sp.put(solid, True)
    sp.put(m, False)
    sp.put(m & ~shift(m, 0, -3), pat(6))
    inner = m & ~erode(erode(m))
    hl = m & shift(m, 2, 2) & ~shift(m, 3, 3) & (sp.ys < y + size * 0.5)
    return m


def vault_door(sp, cx, cy, R, font):
    sp.put(sp.ell(cx + 6, cy + 8, R + 3, R + 3), pat(13))
    sp.put(sp.ell(cx, cy, R + 2, R + 2), True)
    frame = sp.ell(cx, cy, R, R)
    sp.put(frame, pat(3))
    sp.put(frame & ~sp.ell(cx + 3, cy + 3, R - 1, R - 1), False)
    sp.put(frame & ~sp.ell(cx - 3, cy - 3, R - 1, R - 1), pat(12))
    Rd = R - 16
    sp.put(sp.ell(cx, cy, Rd + 3, Rd + 3), True)
    door = sp.ell(cx, cy, Rd, Rd)
    sp.put(door, pat(9))
    sp.put(door & ~sp.ell(cx - 3, cy - 3, Rd - 1, Rd - 1), pat(13))
    sp.put(door & ~sp.ell(cx + 2, cy + 2, Rd - 1, Rd - 1), False)
    for i in range(18):
        a = 2 * math.pi * i / 18 + 0.1
        bx, by = cx + math.cos(a) * (R - 8), cy + math.sin(a) * (R - 8)
        sp.put(sp.ell(bx + 1, by + 1, 3.6, 3.6), pat(13))
        sp.put(sp.ell(bx, by, 3.6, 3.6), True)
        sp.put(sp.ell(bx, by, 2.3, 2.3), pat(4))
        sp.px(bx - 1, by - 1, False)
    hx0 = cx - Rd + 4
    for yy in (cy - 36, cy + 30):
        m = sp.rrect(cx - R - 6, yy, cx - R + 16, yy + 14, 3)
        sp.put(grow(m, 1), True)
        sp.put(m, pat(4))
        sp.put(m & ~shift(m, 0, 1), False)
    dr = 46
    sp.put(sp.ell(cx + 4, cy + 5, dr + 4, dr + 4), pat(13))
    sp.put(sp.ell(cx, cy, dr + 4, dr + 4), True)
    for i in range(60):
        a = 2 * math.pi * i / 60
        if i % 2 == 0:
            sp.put(sp.pline([(cx + math.cos(a) * (dr + 1), cy + math.sin(a) * (dr + 1)), (cx + math.cos(a) * (dr + 3), cy + math.sin(a) * (dr + 3))]), False)
    face = sp.ell(cx, cy, dr, dr)
    sp.put(face, False)
    sp.put(face & ~sp.ell(cx - 4, cy - 4, dr, dr), pat(6))
    for i in range(50):
        a = 2 * math.pi * i / 50 - math.pi / 2
        r0 = dr - (7 if i % 5 == 0 else 4)
        sp.put(sp.pline([(cx + math.cos(a) * r0, cy + math.sin(a) * r0), (cx + math.cos(a) * (dr - 1), cy + math.sin(a) * (dr - 1))]), True)
    for k in range(10):
        a = 2 * math.pi * k / 10 - math.pi / 2
        s = str(k * 10)
        w = font.getlength(s)
        tx, ty = cx + math.cos(a) * (dr - 15), cy + math.sin(a) * (dr - 15)
        sp.text(s, int(tx - w / 2 + 0.5), int(ty - 4), font, True)
    kr = 15
    sp.put(sp.ell(cx + 2, cy + 3, kr + 2, kr + 2), pat(12))
    sp.put(sp.ell(cx, cy, kr + 2, kr + 2), True)
    sp.put(sp.ell(cx, cy, kr, kr), pat(9))
    sp.put(sp.ell(cx, cy, kr, kr) & ~sp.ell(cx + 2, cy + 2, kr, kr), False)
    sp.put(sp.ell(cx, cy, 5, 5), True)
    sp.put(sp.ell(cx - 5, cy - 6, 2.5, 2), False)
    sp.put(sp.poly([(cx - 5, cy - dr - 12), (cx + 5, cy - dr - 12), (cx, cy - dr - 3)]), True)


def cash_stack(sp, x, y, n=3, w=26):
    for i in range(n):
        yy = y - i * 7 + (i % 2)
        xx = x + (i % 2) * 2
        m = sp.rect(xx, yy, xx + w, yy + 7)
        outline(sp, m, 1)
        sp.put(m, False)
        sp.put(m & ~shift(m, -2, -1), pat(8))
        sp.put(sp.rect(xx + w // 2 - 4, yy, xx + w // 2 + 4, yy + 7), pat(12))
        sp.put(sp.rect(xx + 3, yy + 3, xx + 7, yy + 4), True)


def coin(sp, x, y, r=4):
    sp.put(sp.ell(x, y, r + 1, r * 0.7 + 1), True)
    sp.put(sp.ell(x, y, r, r * 0.7), pat(4))
    sp.put(sp.ell(x - r * 0.3, y - r * 0.2, r * 0.3, r * 0.2), False)


def neko_title(sp, hx, hy, W=100):
    t = 3
    u = W / 2
    by = hy + u + 24
    sp.put(sp.ell(hx + 6, by + 32, 58, 8), pat(14))
    tail = sp.lines([(hx - 20, by + 18), (hx - 44, by + 20), (hx - 60, by + 8), (hx - 62, by - 8), (hx - 54, by - 18)], 10)
    part(sp, tail, pat(BODY), t=t, shade=None)
    sp.put(sp.lines([(hx - 64, by - 2), (hx - 56, by - 4)], 4) & tail, pat(10))
    loot_sack(sp, hx - 66, by + 14, 21, t)
    body = sp.ell(hx, by + 2, 38, 28) | sp.rrect(hx - 35, by - 26, hx + 35, by + 22, 14)
    feetm = sp.ell(hx - 18, by + 27, 13, 7) | sp.ell(hx + 18, by + 27, 13, 7)
    part(sp, feetm, pat(BODY), t=t, shade=None)
    st = stripes(8, 4)
    part(sp, body, st, t=t, shade=None)
    shade_side = body & ~shift(body, -9, 0) & (sp.xs > hx)
    sp.put(shade_side & ~st(sp.xs, sp.ys), pat(8))
    for fx in (hx - 18, hx + 18):
        for dx in (-4, 0, 4):
            sp.put(sp.pline([(fx + dx, by + 29), (fx + dx, by + 32)]), True)
    armL = sp.lines([(hx - 28, by - 14), (hx - 40, by - 2), (hx - 36, by + 8)], 12)
    part(sp, armL, pat(BODY), t=t, shade=None)
    ctx = base_head(sp, hx, hy, W, ears=((-0.04, 0.06), (0.24, 0.12)))
    big_face(ctx, mask='down', look=1.7, mouth='w')
    yb = by - 8
    u_pts = [(hx - u * 0.62, hy + u * 0.78), (hx - u * 0.5, yb - 4), (hx - 10, yb + 4), (hx + 10, yb + 4), (hx + u * 0.5, yb - 4), (hx + u * 0.62, hy + u * 0.78)]
    sp.put(sp.lines(u_pts, 6), True)
    sp.put(sp.lines(u_pts, 2), False)
    for side in (-1, 1):
        sp.put(sp.ell(hx + side * u * 0.62, hy + u * 0.78, 3.5, 3.5), True)
        sp.px(hx + side * u * 0.62 - 1, hy + u * 0.78 - 1, False)
    px, py = hx + 76, by - 30
    tube = [(hx, yb + 5), (hx + 16, yb + 14), (hx + 44, yb + 8), (px - 8, py + 8), (px, py)]
    sp.put(sp.lines(tube, 6), True)
    sp.put(sp.lines(tube, 2), False)
    armR = sp.lines([(hx + 28, by - 14), (hx + 48, by - 16), (px - 6, py + 4)], 12)
    part(sp, armR, pat(BODY), t=t, shade=None)
    sp.put(sp.ell(px + 5, py, 10, 10), True)
    sp.put(sp.ell(px + 5, py, 7, 7), pat(5))
    sp.put(sp.ell(px + 3, py - 2, 2.5, 2.5), False)
    paw(sp, px - 3, py + 3, 8, pads=True)
    ex, ey = hx + u * 0.9, hy - u * 1.05
    for r in (7, 12, 17):
        sp.put(sp.arc(ex, ey, r, r, -60, 20, 2), True)


def title_mockup():
    sp = Spr(400, 240)
    brick_wall(sp)
    floor = sp.rect(0, 206, 400, 240)
    sp.put(floor, pat(11))
    sp.put(floor & (sp.ys % 5 == 0), True)
    sp.put(sp.rect(0, 205, 400, 208), True)
    sp.put(sp.rect(0, 208, 400, 209), pat(8))
    font = load_font(8)
    vault_door(sp, 306, 98, 104, font)
    cash_stack(sp, 6, 226, 4, 26)
    cash_stack(sp, 36, 230, 2, 22)
    for (x, y) in ((64, 230), (70, 234), (58, 236)):
        coin(sp, x, y)
    rim_composite(sp, neko_title_spr(100), 46, 52)
    wordmark(sp, 'SAFU', 10, 3, 62, 0)
    sp.stamp(SPARK, 226, 22); sp.stamp(SPARK_S, 214, 40); sp.stamp(SPARK_S, 20, 78)
    f = load_font(8)
    w1 = int(f.getlength('CRACK IT')) + 26
    w2 = int(f.getlength('TUTORIAL')) + 26
    x = 400 - 8 - w1 - 8 - w2
    chip(sp, x, 216, 'A', 'CRACK IT', f)
    chip(sp, x + w1 + 8, 216, 'B', 'TUTORIAL', f)
    return sp


def chip(sp, x, y, letter, label, font):
    tw = int(font.getlength(label))
    w = tw + 28
    h = 18
    l, t, r, b = font.getbbox(label)
    ty = int(y + h / 2 - (t + b) / 2)
    sp.put(sp.rrect(x + 2, y + 2, x + w + 2, y + h + 2, 6), pat(12))
    sp.put(sp.rrect(x - 1, y - 1, x + w + 1, y + h + 1, 7), False)
    sp.put(sp.rrect(x, y, x + w, y + h, 6), True)
    l2, t2, r2, b2 = font.getbbox(letter)
    ccx, ccy = x + 11, y + h / 2
    sp.put(sp.ell(ccx, ccy, 6.5, 6.5), False)
    sp.text(letter, int(ccx - (l2 + r2) / 2 + 0.5), int(ccy - (t2 + b2) / 2 + 0.5), font, True)
    sp.text(label, x + 21, ty, font, False)
    return w


def label(sp, text, x, y, font, center=True):
    w = int(font.getlength(text))
    if center:
        x = int(x - w / 2)
    sp.text(text, x, y, font, True)


def ground(sp, cx, y, rx):
    sp.put(sp.ell(cx, y, rx, 3), pat(10))


def sheet():
    font = load_font(8)
    sp = Spr(480, 360)
    sp.fill(False)
    sp.put(sp.rect(0, 0, 480, 14), True)
    sp.text('NEKO  -  SAFU MASCOT  -  1-BIT CHARACTER SHEET', 6, 3, font, False)
    hero = neko_hero(W=66, mask='down', look=1.2)
    ground(sp, 92, 136, 58)
    sp.blit(hero, 92 - hero.w // 2 + 8, 134 - hero.h + 3)
    label(sp, 'HERO - ON THE JOB', 92, 144, font)
    x = 190
    for m, name in (('none', 'NO MASK'), ('up', 'MASK UP'), ('down', 'MASK DOWN')):
        h = big_head(56, mask=m, look=(1.2 if m == 'down' else 0.0))
        sp.blit(h, x + (96 - h.w) // 2 + 6, 20 + (56 - h.h))
        label(sp, name, x + 48, 80, font)
        x += 96
    label(sp, '(OFF DUTY)', 190 + 96 + 48, 90, font)
    label(sp, '(ON THE JOB)', 190 + 192 + 48, 90, font)
    sp.put(sp.rect(186, 104, 476, 105), pat(8))
    sp.text('SCALE TEST', 192, 112, font, True)
    sp.text('HEAD WIDTH', 192, 124, font, True)
    sp.text('24 / 42 PX', 192, 136, font, True)
    xs = 306
    for hh in (tiny_head(24), small_head('neutral', mask='none'), small_head('neutral')):
        sp.blit(hh, xs, 156 - hh.h)
        xs += hh.w + 4
    sp.put(sp.rect(0, 164, 480, 166), True)
    for i, e in enumerate(EXPRS):
        h = small_head(e)
        cellw = 80
        cx = (i % 6) * cellw + cellw // 2
        cy = 172 + (i // 6) * 94
        sp.blit(h, cx - h.w // 2, cy + 70 - h.h)
        label(sp, e.upper(), cx, cy + 76, font)
    cx = 5 * 80 + 40
    cy = 172 + 94
    ic = tiny_head(24)
    sp.text('BODY  B2', cx - 30, cy + 12, font, True)
    sp.text('EARS  B10', cx - 30, cy + 24, font, True)
    sp.text('SHADE B8', cx - 30, cy + 36, font, True)
    sp.text('LINE  2-3', cx - 30, cy + 48, font, True)
    sp.text('SMALL B1', cx - 30, cy + 60, font, True)
    return sp


def main():
    os.makedirs(os.path.join(OUT, 'sprites'), exist_ok=True)
    sh = sheet()
    sh.save_opaque(os.path.join(OUT, 'neko-sheet.png'))
    sh.preview(os.path.join(OUT, 'neko-sheet@3x.png'), 3)
    neko_hero(W=66, mask='down', look=1.2).save(os.path.join(OUT, 'sprites', 'neko-hero.png'))
    neko_hero(W=66, mask='up', look=0.0).save(os.path.join(OUT, 'sprites', 'neko-hero-offduty.png'))
    for e in EXPRS:
        small_head(e).save(os.path.join(OUT, 'sprites', 'neko-%s.png' % e))
    small_head('neutral', mask='up').save(os.path.join(OUT, 'sprites', 'neko-neutral-offduty.png'))
    small_head('neutral', mask='none').save(os.path.join(OUT, 'sprites', 'neko-neutral-nomask.png'))
    tiny_head(24).save(os.path.join(OUT, 'sprites', 'neko-icon-24.png'))
    t = title_mockup()
    t.save_opaque(os.path.join(OUT, 'title-neko-mockup.png'))
    t.preview(os.path.join(OUT, 'title-neko-mockup@3x.png'), 3)


if __name__ == '__main__':
    main()
