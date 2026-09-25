import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdart import (Canvas, B8, bayer, bayer8, tone, hlines, vlines, hatch, hatch_r, cross, dots,
                   wood, brushed, OR, AND, NOT, rivet, screw, dilate, erode, load_font)

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'source', 'images')
PREVIEW_DIR = os.environ.get('PREVIEW_DIR')

W, H = 400, 240
FONT = load_font(8)


def shift(m, dx, dy):
    h, w = m.shape
    out = np.zeros_like(m)
    ys0, ys1 = max(dy, 0), h + min(dy, 0)
    xs0, xs1 = max(dx, 0), w + min(dx, 0)
    out[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def edge_side(m, dx, dy, k=1):
    return m & ~shift(m, -dx * k, -dy * k)


def grow(m, t=1):
    for _ in range(t):
        m = dilate(m)
    return m


def shrink(m, t=1):
    for _ in range(t):
        m = erode(m)
    return m


def rot(pts, cx, cy, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca) for x, y in pts]


def ell_pts(cx, cy, rx, ry, n=48, a0=0.0, a1=math.tau, rot_a=0.0):
    out = []
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * math.cos(rot_a) - y * math.sin(rot_a), cy + x * math.sin(rot_a) + y * math.cos(rot_a)))
    return out


def hsh(*v):
    x = 0
    for k in v:
        x = (x * 1103515245 + int(k) * 2654435761 + 12345) & 0xFFFFFFFF
    x ^= x >> 13
    x = (x * 0x5bd1e995) & 0xFFFFFFFF
    x ^= x >> 15
    return x / 0xFFFFFFFF


def hsh_arr(a, b, seed=0):
    x = (a.astype(np.int64) * 73856093) ^ (b.astype(np.int64) * 19349663) ^ (seed * 83492791)
    x = (x ^ (x >> 13)) * 1274126177
    x = x ^ (x >> 16)
    return (x & 0xFFFF) / 65535.0


def outlined(c, m, pat, t=1):
    c.put(m, pat)
    c.put(grow(m, t) & ~m, True)
    return m


def lit_blob(c, m, base, dark, lx=-1, ly=-1, shade_k=3, hi=True):
    c.put(m, base)
    c.put(edge_side(m, -lx, -ly, shade_k), dark)
    if hi:
        c.put(edge_side(m, lx, ly, 1) & shrink(m, 0), False)
    c.put(grow(m) & ~m, True)


def sphere_field(c, cx, cy, r, lx=-0.6, ly=-0.7, lo=0.05, hi=0.9):
    dx = (c.xs + 0.5 - cx) / r
    dy = (c.ys + 0.5 - cy) / r
    d = dx * lx + dy * ly
    f = 0.5 - 0.5 * d
    return np.clip(lo + (hi - lo) * f, 0, 1)


def layer():
    s = Canvas(W, H, 0)
    s.enable_alpha()
    return s


def comp(c, s, m=None):
    a = s.alpha if m is None else (s.alpha & m)
    c.ink[a] = s.ink[a]


def text(c, s, x, y, ink=True, font=FONT):
    m = c.text_mask(s, x, y, font)
    c.put(m, ink)
    return m


def brick_wall(c, region, bw=22, bh=9, lo=1, hi=5, seed=3, mortar=True):
    xs, ys = c.xs, c.ys
    row = ys // bh
    off = np.where(row % 2 == 1, bw // 2, 0)
    col = (xs + off) // bw
    r = hsh_arr(col, row, seed)
    lvl = lo + np.floor(r * (hi - lo + 1)).astype(int)
    lvl = np.clip(lvl, 0, 16)
    b4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
    ink = b4[ys & 3, xs & 3] < lvl
    ly = ys % bh
    lx = (xs + off) % bw
    ink = ink | ((ly == bh - 2) & (b4[ys & 3, xs & 3] < 12))
    ink = ink & ~((ly == 1) & (lx > 1) & (lx < bw - 2))
    crack = (r > 0.9) & (np.abs((lx - bw * 0.5) - (ly - bh * 0.5) * 1.3) < 0.8) & (ly > 1) & (ly < bh - 1)
    chip = (r < 0.08) & (lx < 4) & (ly < 4) & (ly > 0)
    ink = ink | crack | chip
    if mortar:
        ink = ink | (ly == 0) | (lx == 0)
    c.ink[region] = ink[region]


def perspective_floor(c, region, y_h, vpx, tile=26, cam=900.0, lvl_a=2, lvl_b=6, line=True):
    xs, ys = c.xs.astype(float), c.ys.astype(float)
    dy = np.maximum(ys + 0.5 - y_h, 0.5)
    depth = cam / dy
    wx = (xs + 0.5 - vpx) * depth / cam * 40
    iu = np.floor(wx / tile)
    iv = np.floor(depth / tile * 6)
    iu_r = np.floor((xs + 1.5 - vpx) * depth / cam * 40 / tile)
    dy2 = np.maximum(ys + 1.5 - y_h, 0.5)
    iv_d = np.floor(cam / dy2 / tile * 6)
    checker = ((iu + iv) % 2 == 0)
    b4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
    ix, iy = c.xs & 3, c.ys & 3
    ink = np.where(checker, b4[iy, ix] < lvl_a, b4[iy, ix] < lvl_b)
    if line:
        ink = ink | (iu != iu_r) | (iv != iv_d)
    c.ink[region] = ink[region]


# ---------------------------------------------------------------- robber parts

def ski_head(s, cx, cy, rx, ry, eyes='scared', light=(-1, 0), mouth='O'):
    m = s.ellipse_mask(cx, cy, rx, ry)
    s.put(m, True)
    lx, ly = light
    lit = edge_side(m, lx, ly, 4) & ~edge_side(m, lx, ly, 1)
    rib = lambda x, y: ((x % 3) == 0) & ((y % 2) == 0)
    s.put(lit, rib)
    s.put(edge_side(m, lx, ly, 1), False)
    s.put(grow(m) & ~m, True)
    s.put(s.ellipse_mask(cx, cy - ry + 3, rx * 0.55, 2.2) & m, lambda x, y: ((x + y) % 3 == 0))
    ex = rx * 0.42
    ey = cy - ry * 0.12
    for side in (-1, 1):
        x = cx + side * ex
        if eyes == 'scared':
            s.ellipse(x, ey, 5.2, 5.2, False)
            s.ring(x, ey, 5.2, 6.4, True)
            s.disc(x + 0.5 * side * 0, ey, 1.6, True)
        elif eyes == 'spiral':
            s.ellipse(x, ey, 5.4, 5.0, False)
            s.ring(x, ey, 5.4, 6.4, True)
            pts = []
            for i in range(40):
                t = i / 39 * math.tau * 2.1
                r = 0.3 + i / 39 * 4.6
                pts.append((x + math.cos(t * side) * r, ey + math.sin(t * side) * r * 0.95))
            s.line(pts, 1, True)
        else:
            s.ellipse(x, ey, 4.5, 4, False)
            s.disc(x, ey, 2, True)
            s.disc(x - 0.7, ey - 0.7, 0.8, False)
    my = cy + ry * 0.5
    if mouth == 'O':
        s.ellipse(cx, my, 4.2, 5.2, False)
        s.ellipse(cx, my + 0.3, 2.4, 3.3, True)
    elif mouth == 'wobble':
        s.ellipse(cx, my, 5.5, 3.6, False)
        pts = [(cx - 4 + i, my + (1 if i % 2 else -1) * 0.9) for i in range(9)]
        s.line(pts, 1, True)
    return m


def sweat_drop(s, x, y, size=1.0, ang=0.0):
    pts = [(x, y - 5 * size), (x + 2.6 * size, y + 0.5 * size)] + ell_pts(x, y + 1.2 * size, 2.7 * size, 2.7 * size, 16, 0.0, math.pi) + [(x - 2.6 * size, y + 0.5 * size)]
    pts = rot(pts, x, y, ang)
    m = s.poly_mask(pts)
    s.put(m, False)
    s.put(grow(m) & ~m, True)
    s.put(s.disc_mask(x - 0.8 * size, y + 0.5 * size, 0.9) & m, True)


def glove_hand(s, cx, cy, ang, scale=1.0, open_hand=True, light=(-1, -1)):
    parts = []
    palm = rot([(cx - 5 * scale, cy + 4 * scale), (cx - 5 * scale, cy - 3 * scale), (cx + 5 * scale, cy - 3 * scale), (cx + 5 * scale, cy + 4 * scale)], cx, cy, ang)
    m = s.poly_mask(palm) | s.ellipse_mask(cx, cy, 5.5 * scale, 5 * scale)
    fingers = [(-4, 9, -0.25), (-1.4, 10.5, -0.08), (1.4, 10, 0.08), (4, 8.5, 0.22)] if open_hand else []
    for fx, fl, fa in fingers:
        bx, by = cx + fx * scale, cy - 3 * scale
        tx, ty = bx + math.sin(fa) * fl * scale, by - math.cos(fa) * fl * scale
        p = rot([(bx, by), (tx, ty)], cx, cy, ang)
        fm = s.mask(lambda d, p=p: d.line([tuple(q) for q in p], fill=1, width=max(2, int(3 * scale))))
        fm |= s.disc_mask(p[1][0], p[1][1], 1.5 * scale)
        m |= fm
    th = rot([(cx - 5 * scale, cy + 1), (cx - 10 * scale, cy - 4 * scale)], cx, cy, ang)
    m |= s.mask(lambda d: d.line([tuple(q) for q in th], fill=1, width=max(2, int(3 * scale))))
    m |= s.disc_mask(th[1][0], th[1][1], 1.5 * scale)
    s.put(m, True)
    s.put(edge_side(m, light[0], light[1], 1) & ~edge_side(m, light[0], light[1], 0), False)
    s.put(grow(m) & ~m, True)
    for fx, fl, fa in fingers[1:]:
        bx = cx + (fx - 1.3) * scale
        p = rot([(bx, cy - 1 * scale), (bx, cy - 5 * scale)], cx, cy, ang)
        s.line(p, 1, bayer(6))
    return m


# ---------------------------------------------------------------- scene 1: CAUGHT



def capsule(s, p0, p1, r):
    m = s.mask(lambda d: d.line([tuple(p0), tuple(p1)], fill=1, width=max(1, int(round(r * 2)))))
    return m | s.disc_mask(p0[0], p0[1], r) | s.disc_mask(p1[0], p1[1], r)


def mitt(s, cx, cy, ang, light=(-1, 0), spread=1.0, curl=False):
    m = s.ellipse_mask(cx, cy, 6.5, 6)
    tips = []
    for i, (bx, a, L) in enumerate(((-4.2, -0.42, 8.5), (-1.4, -0.14, 10), (1.4, 0.14, 9.5), (4.2, 0.42, 8))):
        a = a * spread + ang
        b = (cx + bx * math.cos(ang), cy - 3 + bx * math.sin(ang))
        t = (b[0] + math.sin(a) * L, b[1] - math.cos(a) * L)
        if curl:
            t = (b[0] + math.sin(a) * L * 0.5, b[1] - math.cos(a) * L * 0.5)
        m |= capsule(s, b, t, 1.6)
        tips.append(t)
    side = -1 if light[0] < 0 else 1
    ta = ang - 1.1 if cx < 200 else ang + 1.1
    b = (cx - 4 * math.cos(ang), cy + 1)
    m |= capsule(s, b, (b[0] + math.sin(ta) * 7, b[1] - math.cos(ta) * 7), 1.9)
    s.put(grow(m) & ~m, True)
    s.put(m, True)
    s.put(edge_side(m, light[0], light[1], 1), False)
    for t in tips:
        s.put(s.disc_mask(t[0] - 0.6, t[1] - 0.6, 0.7), False)
    return m


def robber_caught(s, cx, feet_y):
    L = (-1, 0)
    hy = feet_y - 106
    torso_top, torso_bot = hy + 17, feet_y - 44
    legs = []
    for side in (-1, 1):
        x_hip = cx + side * 9
        x_knee = cx + side * 5
        x_foot = cx + side * 12
        pts = [(x_hip - 8, torso_bot - 2), (x_hip + 8, torso_bot - 2), (x_knee + 6.5, feet_y - 22), (x_foot + 6, feet_y - 5), (x_foot - 6, feet_y - 5), (x_knee - 6.5, feet_y - 22)]
        legs.append(s.poly_mask(pts))
    legm = legs[0] | legs[1]
    s.put(grow(legm) & ~legm, True)
    s.put(legm, True)
    for lm in legs:
        s.put(edge_side(lm, -1, 0, 1), False)
        s.put(edge_side(lm, -1, 0, 3) & ~edge_side(lm, -1, 0, 1), bayer(12))
    s.line([(cx - 10, feet_y - 28), (cx - 6, feet_y - 22)], 1, bayer(8))
    s.line([(cx + 4, feet_y - 28), (cx + 8, feet_y - 22)], 1, bayer(8))
    for side in (-1, 1):
        fx = cx + side * 13
        sh = (s.ellipse_mask(fx + side * 4, feet_y - 3, 10, 5) & (s.ys < feet_y)) | s.rect_mask(fx - 6, feet_y - 7, fx + 7, feet_y - 3)
        s.put(grow(sh) & ~sh & (s.ys <= feet_y), True)
        s.put(sh, True)
        s.put(s.ellipse_mask(fx + side * 5 - 1, feet_y - 5, 4, 1.2) & sh, False)
        s.put(s.rect_mask(fx - 7, feet_y - 1, fx + 12, feet_y) & sh, bayer(8))

    shL, shR = (cx - 19, torso_top + 6), (cx + 19, torso_top + 6)
    elL, elR = (cx - 33, torso_top - 6), (cx + 33, torso_top - 6)
    hdL, hdR = (cx - 35, torso_top - 34), (cx + 35, torso_top - 34)
    arms = []
    for sh, el, hd in ((shL, elL, hdL), (shR, elR, hdR)):
        am = capsule(s, sh, el, 6.5) | capsule(s, el, (hd[0], hd[1] + 8), 6)
        arms.append(am)
    torso = s.poly_mask([(cx - 21, torso_top + 1), (cx + 21, torso_top + 1), (cx + 23, torso_top + 12), (cx + 18, torso_bot), (cx - 18, torso_bot), (cx - 23, torso_top + 12)])
    body = torso | arms[0] | arms[1]
    stripe = lambda x, y: ((y - torso_top) % 6) < 3
    s.put(grow(body) & ~body, True)
    s.put(body, stripe)
    wh = ~stripe(s.xs, s.ys)
    s.put(edge_side(torso, 1, 0, 8) & wh & ~arms[1], bayer(5))
    s.put(edge_side(torso, 1, 0, 4) & wh & ~arms[1], bayer(10))
    for am in arms:
        s.put(edge_side(am, 1, 0, 3) & wh, bayer(6))
    s.put(edge_side(body, -1, 0, 1), False)
    for am in arms:
        s.put(grow(am) & ~am & torso, True)
    s.put(s.rect_mask(cx - 18, torso_bot - 6, cx + 18, torso_bot), True)
    s.put(s.rect_mask(cx - 17, torso_bot - 5, cx + 17, torso_bot - 4), bayer(8))
    s.rect(cx - 4, torso_bot - 7, cx + 4, torso_bot + 1, True)
    s.rect(cx - 3, torso_bot - 6, cx + 3, torso_bot, False)
    s.rect(cx - 1, torso_bot - 5, cx + 1, torso_bot - 1, True)
    for sh, el, hd in ((shL, elL, hdL), (shR, elR, hdR)):
        side = -1 if hd[0] < cx else 1
        cuff = capsule(s, (hd[0] - 6.5, hd[1] + 7), (hd[0] + 6.5, hd[1] + 7), 2.5)
        s.put(grow(cuff) & ~cuff, True)
        s.put(cuff, False)
        s.put(cuff & (s.xs % 2 == 0), True)
        mitt(s, hd[0], hd[1], side * 0.12, light=L, spread=1.25)

    s.put(s.ellipse_mask(cx, torso_top + 1, 13, 4), True)
    s.put(s.ellipse_mask(cx, torso_top + 1, 12, 3) & (s.ys > torso_top) & ((s.xs % 2) == 0), bayer(8))
    ski_head(s, cx, hy, 18, 21, eyes='scared', light=L, mouth='O')
    return hy
def flash_glare(c, x, y):
    spikes = []
    for k in range(16):
        th = k * math.tau / 16
        rr = 11 if k % 4 == 0 else (7 if k % 2 == 0 else 4)
        spikes.append((x + math.cos(th) * rr, y + math.sin(th) * rr * 0.9))
    m = c.poly_mask(spikes)
    c.put(grow(m) & ~m, True)
    c.put(m, False)
    c.disc(x, y, 2.2, bayer(3))
    for k in range(4):
        th = k * math.tau / 4 + math.pi / 4
        c.line([(x + math.cos(th) * 3, y + math.sin(th) * 3), (x + math.cos(th) * 6, y + math.sin(th) * 6)], 1, bayer(6))


def stethoscope(c, x, y):
    tube = [(x + 2, y + 1), (x + 8, y + 6), (x + 17, y + 7), (x + 25, y + 4), (x + 30, y - 2), (x + 33, y - 8)]
    c.line([(p[0] + 1, p[1] + 3) for p in tube], 4, bayer(10))
    c.line(tube, 5, True)
    c.line([(p[0], p[1] - 1) for p in tube], 1, False)
    for arm in ([(x + 33, y - 8), (x + 28, y - 14), (x + 29, y - 21)], [(x + 33, y - 8), (x + 40, y - 12), (x + 44, y - 18)]):
        c.line(arm, 4, True)
        c.line([(p[0] - 1, p[1]) for p in arm[1:]], 1, False)
        e = arm[-1]
        c.disc(e[0], e[1], 3, True)
        c.disc(e[0] - 0.4, e[1] - 0.4, 1.5, False)
    c.ellipse(x - 1, y + 4, 10, 5, bayer(10))
    c.disc(x - 3, y, 8, True)
    c.disc(x - 3, y, 6, False)
    c.put(c.disc_mask(x - 3, y, 6) & (c.xs + c.ys > x + y), bayer(6))
    c.disc(x - 3, y, 3.2, True)
    c.disc(x - 3.5, y - 0.5, 1.8, bayer(4))

def crowbar(c, x0, y0, x1, y1):
    c.line([(x0 + 1, y0 + 4), (x1 + 1, y1 + 4)], 4, bayer(10))
    hook = [(x1, y1), (x1 + 5, y1 - 2), (x1 + 7, y1 - 7), (x1 + 5, y1 - 12)]
    c.line([(x0, y0), (x1, y1)], 6, True)
    c.line(hook, 6, True)
    c.line([(x0 + 1, y0 - 1), (x1 - 1, y1 - 1)], 1, False)
    c.line([(x1 + 1, y1 - 3), (x1 + 4, y1 - 5), (x1 + 5, y1 - 9)], 1, False)
    c.poly([(x0 - 1, y0 - 3), (x0 - 9, y0 - 1), (x0 - 9, y0 + 2), (x0 - 1, y0 + 3)], True)
    c.line([(x0 - 8, y0 - 1), (x0 - 2, y0 - 2)], 1, False)

def cash_bill(c, x, y, ang, singe=0.0, scale=1.0):
    w, h = 15 * scale, 8 * scale
    pts = rot([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)], x, y, ang)
    m = c.poly_mask(pts)
    c.put(grow(m) & ~m, True)
    c.put(m, False)
    c.put(edge_side(m, 0, 1, 2), bayer(5))
    inner = c.poly_mask(rot([(x - w / 2 + 2, y - h / 2 + 2), (x + w / 2 - 2, y - h / 2 + 2), (x + w / 2 - 2, y + h / 2 - 2), (x - w / 2 + 2, y + h / 2 - 2)], x, y, ang))
    c.put(inner & ~shrink(inner), bayer(10))
    c.put(c.ellipse_mask(x, y, 2.4 * scale, 2.2 * scale) & m, True)
    c.put(c.disc_mask(x - 0.3, y - 0.3, 0.9) & m, False)
    if singe > 0:
        ex = x + math.cos(ang) * w / 2
        ey = y + math.sin(ang) * w / 2
        b = c.disc_mask(ex, ey, w * singe)
        c.put(b & grow(m), True)
        c.put(grow(b, 2) & ~b & m, bayer(10))

DOLLAR = ["..#..", ".####", "#.#..", "#.#..", ".###.", "..#.#", "..#.#", "####.", "..#.."]


def glyph(c, rows, x, y, ink=True):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == '#':
                c.put(c.rect_mask(x + i, y + j, x + i + 1, y + j + 1), ink)


def loot_bag(c, x, y):
    c.ellipse(x + 6, y + 13, 20, 5, bayer(10))
    body = c.ellipse_mask(x, y + 2, 15, 12.5) | c.poly_mask([(x - 6, y - 11), (x + 6, y - 11), (x + 10, y - 3), (x - 10, y - 3)])
    c.put(grow(body, 2) & ~body, True)
    c.put(body, False)
    c.put(edge_side(body, 1, 1, 6), bayer(5))
    c.put(edge_side(body, 1, 1, 3), bayer(10))
    c.line([(x - 9, y - 4), (x - 12, y + 5)], 1, bayer(8))
    c.line([(x + 7, y - 5), (x + 11, y + 2)], 1, bayer(10))
    c.disc(x - 7, y - 1, 1.5, bayer(4))
    neck = c.poly_mask([(x - 4, y - 10), (x + 4, y - 10), (x + 8, y - 18), (x - 8, y - 18)])
    cash_bill(c, x - 4, y - 18, -0.55)
    cash_bill(c, x + 6, y - 19, 0.45)
    c.put(grow(neck, 2) & ~neck & ~body, True)
    c.put(neck, False)
    c.put(neck & (c.xs % 3 == 0) & (c.ys > y - 16), bayer(8))
    c.line([(x - 8, y - 10), (x + 8, y - 10)], 3, True)
    c.line([(x - 7, y - 11), (x + 6, y - 11)], 1, bayer(6))
    c.line([(x + 3, y - 9), (x + 6, y - 4), (x + 9, y - 6)], 2, True)
    glyph(c, DOLLAR, x - 2, y - 2)
    glyph(c, DOLLAR, x - 1, y - 2)

def security_camera(c, x, y, ang=-0.42):
    c.rect(x + 36, y - 6, x + 46, y + 14, True)
    c.rect(x + 37, y - 5, x + 45, y + 13, bayer(3))
    c.put(c.rect_mask(x + 37, y - 5, x + 38, y + 13), False)
    c.put(c.rect_mask(x + 43, y - 5, x + 45, y + 13), bayer(9))
    for yy in (y - 2, y + 10):
        c.disc(x + 41, yy, 1.2, True)
    arm = [(x + 38, y + 4), (x + 30, y + 4), (x + 26, y + 10)]
    c.line(arm, 5, True)
    c.line([(x + 37, y + 3), (x + 30, y + 3)], 1, bayer(4))
    cx0, cy0 = x + 12, y + 12
    body = rot([(x - 2, y + 6), (x + 28, y + 6), (x + 30, y + 9), (x + 30, y + 18), (x - 2, y + 18)], cx0, cy0, ang)
    hood = rot([(x - 8, y + 3), (x + 30, y + 3), (x + 30, y + 7), (x - 8, y + 7)], cx0, cy0, ang)
    bm = c.poly_mask(body)
    hm = c.poly_mask(hood)
    c.put(grow(bm | hm), True)
    c.put(bm, False)
    c.put(edge_side(bm, 0, 1, 4), bayer(6))
    c.put(edge_side(bm, 0, 1, 2), bayer(11))
    c.put(hm, bayer(3))
    c.put(edge_side(hm, 0, -1, 1), False)
    c.put(edge_side(hm, 0, 1, 1), True)
    for k in range(4):
        p = rot([(x + 14 + k * 3, y + 9), (x + 14 + k * 3, y + 15)], cx0, cy0, ang)
        c.line(p, 1, bayer(9))
    lp = rot([(x - 3, y + 12)], cx0, cy0, ang)[0]
    c.disc(lp[0], lp[1], 5, True)
    c.disc(lp[0], lp[1], 3.4, bayer(12))
    c.disc(lp[0] - 1, lp[1] - 1, 1.2, False)
    c.ring(lp[0], lp[1], 3.4, 4, bayer(6))
    led = rot([(x + 6, y + 10)], cx0, cy0, ang)[0]
    c.disc(led[0], led[1], 1.6, True)
    c.disc(led[0], led[1], 0.9, False)
    for k in range(3):
        th = -math.pi / 2 - 0.5 + k * 0.5
        c.line([(led[0] + math.cos(th) * 4, led[1] + math.sin(th) * 4 - 6), (led[0] + math.cos(th) * 7, led[1] + math.sin(th) * 7 - 6)], 1, False)

def doorway(c, x0, y0, x1, y1):
    c.rect(x0 - 5, y0 - 5, x1 + 5, y1, True)
    c.rect(x0 - 3, y0 - 3, x1 + 3, y1, wood)
    c.put(c.rect_mask(x0 - 3, y0 - 3, x1 + 3, y0 - 2), False)
    inner = c.rect_mask(x0, y0, x1, y1)
    vx, vy = (x0 + x1) / 2 + 4, y0 + (y1 - y0) * 0.45
    far = (x0 + 12, y0 + 22, x1 - 8, y1 - 34)
    c.put(inner, bayer(2))
    c.put(inner & (c.ys > far[3]), bayer(5))
    c.put(inner & (c.ys < far[1]), bayer(4))
    c.put(c.rect_mask(*far), bayer(1))
    c.put(c.rect_mask(far[0], far[1], far[2], far[3]) & ~shrink(c.rect_mask(*far)), True)
    for (px, py) in ((far[0], far[1]), (far[2], far[1]), (far[0], far[3]), (far[2], far[3])):
        tx = x0 if px == far[0] else x1
        ty = y0 if py == far[1] else y1
        c.line([(px, py), (tx, ty)], 1, True)
    c.rect(far[0] + 6, far[1] + 4, far[0] + 14, far[3], True)
    c.rect(far[0] + 7, far[1] + 5, far[0] + 13, far[3], bayer(6))
    c.disc((far[0] + far[2]) / 2, y0 + 8, 3, False)
    c.ellipse((far[0] + far[2]) / 2, y0 + 5, 6, 2, True)
    c.put(inner & (c.ys > far[3] + 8) & (((c.ys - far[3]) % 7) == 0), True)
    c.put(inner & ~shrink(inner), True)




def vault_door(c, cx, cy, r, dial_cx, dial_cy, dial_r=18, plaque=True):
    fx0, fy0, fx1, fy1 = cx - r - 13, cy - r - 12, cx + r + 13, cy + r + 10
    c.rect(fx0 + 4, fy0 + 4, fx1 + 4, fy1 + 2, bayer(12))
    c.rect(fx0, fy0, fx1, fy1, True)
    plate = c.rect_mask(fx0 + 2, fy0 + 2, fx1 - 2, fy1 - 2)
    c.put(plate, False)
    rng = np.random.default_rng(9)
    for _ in range(26):
        y = rng.integers(int(fy0) + 4, int(fy1) - 6)
        x = rng.integers(int(fx0) + 4, int(fx1) - 30)
        c.put(c.rect_mask(x, y, x + rng.integers(6, 26), y + 1) & plate, bayer(5))
    c.put(c.rect_mask(fx1 - 6, fy0 + 3, fx1 - 2, fy1 - 2), bayer(7))
    c.put(c.rect_mask(fx0 + 3, fy1 - 6, fx1 - 2, fy1 - 2), bayer(7))
    c.put(c.rect_mask(fx1 - 7, fy0 + 3, fx1 - 6, fy1 - 6), True)
    c.put(c.rect_mask(fx0 + 3, fy1 - 7, fx1 - 6, fy1 - 6), True)
    for x in (fx0 + 7, fx1 - 12):
        for y in range(int(fy0) + 9, int(fy1) - 10, 15):
            rivet(c, x, y, 2)
    for x in range(int(fx0) + 22, int(fx1) - 14, 18):
        rivet(c, x, fy0 + 7, 2)
    c.disc(cx + 3, cy + 4, r + 5, bayer(10))
    c.disc(cx, cy, r + 4, True)
    rim = c.ring_mask(cx, cy, r - 8, r + 2)
    c.put(rim, False)
    dd = (c.xs - cx) + (c.ys - cy)
    c.put(rim & (dd > r * 0.35), bayer(5))
    c.put(rim & (dd > r * 0.95), bayer(10))
    c.put(c.ring_mask(cx, cy, r - 9.5, r - 8), True)
    for k in range(18):
        th = k * math.tau / 18 + 0.1
        bx, by = cx + math.cos(th) * (r - 3), cy + math.sin(th) * (r - 3)
        c.disc(bx + 0.8, by + 1, 2.6, bayer(12))
        c.disc(bx, by, 2.4, True)
        c.disc(bx, by, 1.4, False)
    face = c.disc_mask(cx, cy, r - 9.5)
    c.put(face, False)
    c.put(face & (dd > r * 0.55), bayer(2))
    c.put(face & (dd > r * 0.95), bayer(4))
    c.put(face & (dd < -r * 0.9) & (c.ring_mask(cx, cy, r - 16, r - 13)), bayer(3))
    c.ring(cx, cy, r - 21, r - 19.8, True)
    c.put(c.ring_mask(cx, cy, r - 23, r - 21.5) & (dd > 0), bayer(8))
    for k in range(8):
        th = k * math.tau / 8 + math.pi / 8
        x0, y0 = cx + math.cos(th) * (r - 18), cy + math.sin(th) * (r - 18)
        x1, y1 = cx + math.cos(th) * (r - 12), cy + math.sin(th) * (r - 12)
        c.line([(x0, y0), (x1, y1)], 3, True)
    if plaque:
        plq = (cx - 15, cy + r - 31, cx + 16, cy + r - 21)
        c.rect(plq[0] + 1, plq[1] + 1, plq[2] + 1, plq[3] + 1, bayer(10))
        c.rect(plq[0], plq[1], plq[2], plq[3], True)
        c.rect(plq[0] + 1, plq[1] + 1, plq[2] - 1, plq[3] - 1, False)
        text(c, 'SAFU', plq[0] + 6, plq[1] + 1)
    dr = dial_r
    c.disc(dial_cx + 2, dial_cy + 3, dr + 4, bayer(10))
    c.disc(dial_cx, dial_cy, dr + 3.5, True)
    kn = c.ring_mask(dial_cx, dial_cy, dr + 0.5, dr + 2.6)
    c.put(kn & ((np.floor(np.arctan2(c.ys + 0.5 - dial_cy, c.xs + 0.5 - dial_cx) * 36 / math.tau) % 2) == 0), False)
    c.disc(dial_cx, dial_cy, dr, False)
    for k in range(40):
        th = k * math.tau / 40 - math.pi / 2
        Lk = 5 if k % 5 == 0 else 2.5
        c.line([(dial_cx + math.cos(th) * (dr - 0.5), dial_cy + math.sin(th) * (dr - 0.5)),
                (dial_cx + math.cos(th) * (dr - Lk), dial_cy + math.sin(th) * (dr - Lk))], 1, True)
    c.disc(dial_cx, dial_cy, dr - 7, True)
    knob = c.disc_mask(dial_cx, dial_cy, dr - 8)
    c.put(knob, False)
    kd = (c.xs - dial_cx) + (c.ys - dial_cy)
    c.put(knob & (kd > 0), bayer(5))
    c.put(knob & (kd > dr * 0.6), bayer(10))
    c.line([(dial_cx, dial_cy - dr + 9), (dial_cx, dial_cy + dr - 9)], 3, True)
    c.disc(dial_cx, dial_cy, 2.5, True)
    c.disc(dial_cx - 0.5, dial_cy - 0.5, 1, False)
    c.poly([(dial_cx - 4, dial_cy - dr - 9), (dial_cx + 4, dial_cy - dr - 9), (dial_cx, dial_cy - dr - 3)], True)


def guard(s, fl):
    body = s.poly_mask([(-6, 142), (6, 128), (26, 120), (48, 120), (60, 126), (66, 146), (68, 196), (66, 240), (-6, 240)])
    arm = s.mask(lambda d: d.line([(56, 134), (64, 137), (fl[0] - 28, fl[1] + 3)], fill=1, width=15, joint='curve'))
    arm |= s.disc_mask(56, 136, 10)
    neck = s.poly_mask([(28, 106), (48, 106), (50, 124), (26, 124)])
    face = s.poly_mask([(22, 84), (54, 82), (57, 88), (56, 92), (63, 99), (58, 101), (61, 101), (63, 104), (59, 106), (58, 111), (52, 117), (42, 117), (26, 114), (22, 104), (19, 96)])
    crown = s.poly_mask([(18, 80), (19, 70), (30, 62), (58, 61), (68, 68), (66, 80)])
    brim = s.poly_mask([(52, 79), (66, 78), (83, 84), (79, 88), (54, 87)])
    fist = s.ellipse_mask(fl[0] - 26, fl[1] + 3, 7, 7.5)
    sil = body | arm | neck | face | crown | brim | fist
    s.put(grow(sil) & ~sil, True)
    s.put(sil, True)
    s.put(edge_side(sil, -1, 0, 1), bayer(9))
    rim = edge_side(sil, 1, 0, 1) | (edge_side(sil, 0, -1, 1) & (s.xs > 44))
    s.put(rim, False)
    s.put(edge_side(sil, 1, 0, 2) & ~edge_side(sil, 1, 0, 1) & (s.ys > 84) & (s.ys < 120), bayer(12))

    s.put(edge_side(crown, 0, -1, 1), False)
    s.put(s.ellipse_mask(46, 65, 10, 1.6) & crown, bayer(10))
    band = s.poly_mask([(19, 74), (66, 72), (66, 79), (19, 81)])
    s.put(band, lambda x, y: ((((x - 19) // 3) + (y // 3)) % 2 == 0))
    s.line([(19, 74), (66, 72)], 1, True)
    s.line([(19, 81), (66, 79)], 1, True)
    s.line([(66, 79), (83, 84)], 1, False)
    s.line([(57, 87), (78, 88)], 1, bayer(10))
    bx, by = 59, 66
    sh = s.poly_mask([(bx - 4, by - 4), (bx + 4, by - 4), (bx + 4, by + 2), (bx, by + 6), (bx - 4, by + 2)])
    s.put(grow(sh), True)
    s.put(sh, False)
    s.put(s.disc_mask(bx, by, 1.5), True)
    for k in range(2):
        s.line([(bx - 8 - k * 3, by + 1 - k), (bx - 10 - k * 3, by + 3 - k)], 1, False)

    eye = s.poly_mask([(46, 93), (50, 91.5), (56, 92.5), (54, 95.5), (48, 95.5)])
    s.put(eye, False)
    s.disc(53, 93.8, 1.5, True)
    s.line([(44, 89), (56, 91)], 1, bayer(8))
    s.line([(49, 97.5), (54, 97.5)], 1, bayer(10))
    s.put(s.ring_mask(35, 99, 3.5, 4.5) & (s.xs < 36), bayer(9))
    s.line([(52, 109), (57, 109)], 1, False)
    s.line([(51, 110), (52, 109)], 1, False)
    s.put(face & (s.xs > 40) & (s.ys > 104) & (s.ys < 116) & ((s.xs * 3 + s.ys * 5) % 7 == 0), bayer(12) if False else False)
    s.line([(28, 112), (40, 116), (51, 117)], 1, bayer(11))
    for y in range(90, 110, 3):
        s.line([(21, y), (25, y + 1)], 1, bayer(10))

    s.line([(26, 122), (36, 132), (46, 122)], 1, False)
    s.line([(36, 132), (38, 160)], 1, bayer(8))
    tie = s.poly_mask([(34, 124), (38, 124), (40, 150), (36, 154), (33, 150)])
    s.put(grow(tie) & ~tie, bayer(8))
    ep = s.poly_mask([(40, 121), (56, 124), (58, 129), (42, 127)])
    s.put(grow(ep) & ~ep, False)
    s.put(ep & (s.xs % 3 == 0), False)
    s.line([(56, 124), (62, 140), (65, 196)], 1, bayer(8))
    for y in range(146, 192, 11):
        s.disc(61, y, 1.4, False)
    pk = s.poly_mask([(42, 144), (56, 144), (56, 158), (49, 161), (42, 158)])
    s.put(grow(pk) & ~pk, bayer(9))
    s.line([(42, 149), (56, 149)], 1, bayer(9))
    s.disc(49, 147, 1, False)
    px, py = 24, 152
    star = []
    for k in range(10):
        th = -math.pi / 2 + k * math.pi / 5
        rr = 8 if k % 2 == 0 else 3.6
        star.append((px + math.cos(th) * rr, py + math.sin(th) * rr))
    sm = s.poly_mask(star)
    s.put(sm, False)
    s.put(sm & edge_side(sm, 1, 1, 2), bayer(5))
    s.disc(px, py, 2.2, True)
    s.disc(px, py, 1, False)
    rad = s.rect_mask(4, 130, 14, 152)
    s.put(grow(rad) & ~rad, False)
    s.put(rad, True)
    for y in range(134, 150, 3):
        s.line([(7, y), (11, y)], 1, bayer(8))
    s.line([(9, 128), (7, 104)], 3, True)
    s.line([(8, 104), (9.5, 127)], 1, bayer(8))
    s.disc(7, 102, 2.2, True)
    s.disc(6.5, 101.5, 0.8, False)
    s.line([(14, 140), (20, 136), (26, 128)], 1, bayer(9))

    s.rect(-8, 194, 67, 204, True)
    s.line([(-8, 194), (67, 194)], 1, False)
    s.line([(-8, 204), (67, 204)], 1, bayer(9))
    for x in range(-4, 66, 6):
        s.rect(x, 199, x + 1, 200, bayer(8))
    s.rect(46, 192, 62, 206, False)
    s.rect(47, 193, 61, 205, True)
    s.rect(49, 195, 59, 203, bayer(4))
    s.rect(52, 197, 56, 201, True)
    s.line([(49, 195), (58, 195)], 1, False)
    pouch = s.rect_mask(4, 192, 20, 222)
    s.put(grow(pouch) & ~pouch, bayer(8))
    s.put(pouch, True)
    s.line([(4, 200), (20, 200)], 1, bayer(8))
    s.ring(12, 206, 1.5, 2.6, False)
    s.rect(30, 203, 34, 212, True)
    s.line([(32, 204), (32, 211)], 1, False)
    for (x, y) in ((32, 217), (38, 230)):
        r = 6.2
        s.ring(x, y, r - 2.4, r + 1.3, True)
        rm = s.ring_mask(x, y, r - 1.3, r)
        s.put(rm, False)
        s.put(rm & (s.xs - x + s.ys - y > 3), bayer(6))
    s.line([(35, 222), (36, 224), (37, 226)], 2, True)
    s.disc(36, 224, 1.2, False)
    kr = (22, 213)
    s.ring(kr[0], kr[1], 2.2, 3.4, False)
    for a in (1.25, 1.65, 2.05):
        x1, y1 = kr[0] + math.cos(a) * 12, kr[1] + math.sin(a) * 12
        s.line([(kr[0] + math.cos(a) * 3, kr[1] + math.sin(a) * 3), (x1, y1)], 3, True)
        s.line([(kr[0] + math.cos(a) * 4, kr[1] + math.sin(a) * 4), (x1, y1)], 1, False)
        s.rect(x1 - 1, y1 - 1, x1 + 2, y1 + 1, False)

    s.line([(60, 127), (fl[0] - 34, fl[1] - 4)], 1, False)
    s.line([(58, 143), (fl[0] - 34, fl[1] + 10)], 1, bayer(11))
    s.line([(fl[0] - 36, fl[1] - 5), (fl[0] - 36, fl[1] + 11)], 1, False)
    s.line([(fl[0] - 34, fl[1] - 5), (fl[0] - 34, fl[1] + 11)], 1, bayer(8))

    tube = s.rect_mask(fl[0] - 34, fl[1] - 4, fl[0] - 10, fl[1] + 4)
    headp = s.poly_mask([(fl[0] - 12, fl[1] - 5), (fl[0] - 3, fl[1] - 10), (fl[0] + 1, fl[1] - 10), (fl[0] + 1, fl[1] + 10), (fl[0] - 3, fl[1] + 10), (fl[0] - 12, fl[1] + 5)])
    fm = tube | headp
    s.put(grow(fm), True)
    s.put(fm, False)
    s.put(fm & (s.ys > fl[1] + 1), bayer(5))
    s.put(fm & (s.ys > fl[1] + 3), bayer(10))
    s.put(tube & (s.ys == fl[1] - 3), bayer(4))
    for x in range(int(fl[0]) - 32, int(fl[0]) - 22, 2):
        s.put(tube & (s.xs == x), True)
    s.put(headp & (s.ys > fl[1] + 6), bayer(13))
    s.line([(fl[0] - 11, fl[1] - 5), (fl[0] - 11, fl[1] + 5)], 1, True)
    s.line([(fl[0] - 20, fl[1] - 4), (fl[0] - 20, fl[1] + 4)], 1, True)
    s.rect(fl[0] + 1, fl[1] - 10, fl[0] + 4, fl[1] + 11, False)
    s.line([(fl[0] + 4, fl[1] - 10), (fl[0] + 4, fl[1] + 10)], 1, True)
    s.rect(fl[0] - 17, fl[1] - 6, fl[0] - 13, fl[1] - 4, True)
    s.rect(fl[0] - 16, fl[1] - 6, fl[0] - 14, fl[1] - 5, False)
    fist2 = s.ellipse_mask(fl[0] - 26, fl[1] + 3, 7, 7.5)
    s.put(grow(fist2) & ~fist2, True)
    s.put(fist2, True)
    s.put(edge_side(fist2, 1, 0, 1) | edge_side(fist2, 0, -1, 1), False)
    for k in range(3):
        s.line([(fl[0] - 29 + k * 3.5, fl[1] + 0), (fl[0] - 29 + k * 3.5, fl[1] + 9)], 1, bayer(10))


def room_bg(c, floor_y, dark):
    wall = c.rect_mask(0, 0, W, floor_y)
    bh, bw = 9, 22
    row = c.ys // bh
    off = np.where(row % 2 == 1, bw // 2, 0)
    mort = ((c.ys % bh == 0) | ((c.xs + off) % bw == 0)) & wall
    if dark:
        c.put(wall, True)
        c.put(mort, bayer(12))
    else:
        brick_wall(c, wall, lo=0, hi=2, seed=7)
    D = (lambda lv: bayer(max(lv, 13))) if dark else (lambda lv: bayer(lv))
    HI = bayer(11) if dark else False
    c.put(c.rect_mask(0, 0, W, 12), D(5))
    c.rect(0, 12, W, 14, True)
    c.rect(0, 14, W, 17, D(10))
    for x in range(12, W, 40):
        c.rect(x, 0, x + 3, 12, True)
        c.rect(x + 1, 0, x + 2, 12, HI)
    py0 = 22
    c.rect(0, py0, W, py0 + 9, True)
    c.rect(0, py0 + 1, W, py0 + 3, HI)
    c.rect(0, py0 + 3, W, py0 + 7, D(4))
    c.rect(0, py0 + 7, W, py0 + 9, D(11))
    c.rect(0, py0 + 9, W, py0 + 12, bayer(14) if dark else bayer(10))
    for x in range(34, W, 64):
        c.rect(x, py0 - 3, x + 7, py0 + 12, True)
        c.rect(x + 1, py0 - 2, x + 3, py0 + 11, HI)
        c.disc(x + 3.5, py0 - 5, 1.8, True)
    floor = c.rect_mask(0, floor_y, W, H)
    xs, ys = c.xs.astype(float), c.ys.astype(float)
    if dark:
        c.put(floor, True)
        dy = np.maximum(ys + 0.5 - 140, 0.5)
        depth = 900.0 / dy
        iu = np.floor((xs + 0.5 - 160) * depth / 900 * 40 / 26)
        iu_r = np.floor((xs + 1.5 - 160) * depth / 900 * 40 / 26)
        iv = np.floor(depth / 26 * 6)
        iv_d = np.floor(900.0 / np.maximum(ys + 1.5 - 140, 0.5) / 26 * 6)
        c.put(floor & ((iu != iu_r) | (iv != iv_d)), bayer(12))
    else:
        perspective_floor(c, floor, 140, 160, tile=26, lvl_a=0, lvl_b=1)
    c.rect(0, floor_y - 7, W, floor_y + 1, True)
    c.rect(0, floor_y - 6, W, floor_y - 5, HI)
    c.rect(0, floor_y - 4, W, floor_y - 1, D(6))
    c.rect(0, floor_y + 1, W, floor_y + 3, D(12))


def doorway(c, x0, y0, x1, y1):
    c.rect(x0 - 6, y0 - 6, x1 + 6, y1, True)
    c.rect(x0 - 4, y0 - 4, x1 + 4, y1, bayer(13))
    c.put(c.rect_mask(x0 - 4, y0 - 4, x1 + 4, y0 - 3), bayer(9))
    c.put(c.rect_mask(x1 + 2, y0 - 4, x1 + 3, y1), bayer(9))
    inner = c.rect_mask(x0, y0, x1, y1)
    far = (x0 + 12, y0 + 24, x1 - 8, y1 - 40)
    c.put(inner, False)
    c.put(inner & (c.ys > far[3]), lambda x, y: (y % 2 == 0) & (B8[y & 7, x & 7] < 12))
    c.put(inner & (c.ys < far[1]), bayer(2))
    c.put(c.rect_mask(*far), False)
    c.put(c.rect_mask(*far) & ~shrink(c.rect_mask(*far)), True)
    for (px, py) in ((far[0], far[1]), (far[2], far[1]), (far[0], far[3]), (far[2], far[3])):
        tx = x0 if px == far[0] else x1
        ty = y0 if py == far[1] else y1
        c.line([(px, py), (tx, ty)], 1, True)
    c.rect(far[2] - 16, far[1] + 6, far[2] - 6, far[3], True)
    c.rect(far[2] - 15, far[1] + 7, far[2] - 7, far[3], bayer(4))
    c.disc(far[2] - 14, (far[1] + far[3]) / 2 + 2, 1, True)
    lx = (far[0] + far[2]) / 2
    c.line([(lx, y0), (lx, y0 + 6)], 1, True)
    c.ellipse(lx, y0 + 8, 7, 2.5, True)
    c.put(c.ellipse_mask(lx, y0 + 11, 4, 2) & (c.ys > y0 + 9), False)
    for k in range(4):
        c.line([(x0 + 2, y0 + 30 + k * 6), (x0 + 8, y0 + 32 + k * 5)], 1, bayer(6))


def scene_caught():
    floor_y = 176
    fl = (82, 132)
    GX = 14
    feet_y = 216
    rcx = 154
    vcx, vcy, vr = 208, 106, 54

    lit = Canvas(W, H, 0)
    room_bg(lit, floor_y, False)
    drk = Canvas(W, H, 0)
    room_bg(drk, floor_y, True)

    vl = layer()
    vault_door(vl, vcx, vcy, vr, vcx + 5, vcy - 4, 17)
    comp(lit, vl)
    vd = vl.ink | bayer(13)(vl.xs, vl.ys)
    drk.ink[vl.alpha] = vd[vl.alpha]

    rob = layer()
    robber_caught(rob, rcx, feet_y)

    c = lit
    wall_spot = (rcx + 24, 130, 60, 94)
    pool = (rcx + 14, feet_y - 1, 70, 23)
    pts = ell_pts(*wall_spot, n=160)
    angs = [math.atan2(p[1] - fl[1], p[0] - fl[0]) for p in pts]
    t1 = pts[int(np.argmin(angs))]
    cone = c.poly_mask([fl, t1, (wall_spot[0], wall_spot[1] - 20), (wall_spot[0], floor_y), (pool[0], pool[1])])
    pts2 = ell_pts(*pool, n=160)
    angs2 = [math.atan2(p[1] - fl[1], p[0] - fl[0]) for p in pts2]
    t3 = pts2[int(np.argmax(angs2))]
    cone |= c.poly_mask([fl, (wall_spot[0], wall_spot[1]), (pool[0], pool[1]), t3])
    spot = c.ellipse_mask(wall_spot[0], wall_spot[1], wall_spot[2], wall_spot[3])
    poolm = c.ellipse_mask(*pool)
    litm = cone | spot | poolm | grow(rob.alpha, 2)

    shadow = shift(rob.alpha, 13, 3) & (c.ys < floor_y - 7) & ~grow(rob.alpha, 2)
    lit.put(shadow & (c.ys > 150), bayer(10))
    fshadow = lit.poly_mask([(rcx - 18, feet_y - 2), (rcx + 20, feet_y - 4), (rcx + 70, feet_y - 10), (rcx + 74, feet_y - 4), (rcx + 20, feet_y + 4), (rcx - 16, feet_y + 3)])
    lit.put(fshadow, bayer(8))

    for cv in (lit, drk):
        crowbar(cv, 108, 233, 152, 228)
        cash_bill(cv, 214, 208, 0.3)
        cash_bill(cv, 146, 226, -0.4)
        cash_bill(cv, 222, 230, 0.15)
        cash_bill(cv, 100, 222, 0.6)
        loot_bag(cv, 118, 206)
        stethoscope(cv, 186, 226)
    drk.put(drk.rect_mask(0, floor_y + 3, W, H), OR(lambda x, y: drk.ink[y, x], bayer(13)))

    dist_edge = np.zeros((H, W))
    g = litm.copy()
    for i in range(1, 5):
        ng = dilate(g)
        dist_edge[ng & ~g] = i
        g = ng
    blend = np.where(litm, 0.0, np.where(dist_edge > 0, dist_edge / 5.0, 1.0))
    pick_dark = tone(blend)(c.xs, c.ys)
    cone_only = cone & ~spot & ~poolm
    d = np.hypot(c.xs - fl[0], c.ys - fl[1])
    out = Canvas(W, H, 0)
    out.ink = np.where(pick_dark, drk.ink, lit.ink)
    out.ink &= ~(cone_only & bayer(9)(c.xs, c.ys) & (c.ys < floor_y - 7))
    out.ink |= cone_only & tone(np.clip((d - 30) / 400.0, 0, 0.1))(c.xs, c.ys)
    c = out

    doorway(c, -2, 36, 64, floor_y)
    spill = c.poly_mask([(0, floor_y), (64, floor_y), (78, H), (0, H)])
    c.ink[spill] = (lit.ink | bayer(4)(c.xs, c.ys))[spill]

    comp(c, rob)
    hy = feet_y - 106
    sweat_drop(c, rcx - 22, hy - 22, 1.7, -0.8)
    sweat_drop(c, rcx + 23, hy - 20, 1.5, 0.8)
    sweat_drop(c, rcx + 19, hy + 2, 1.2, 0.3)
    for j, a in enumerate((-0.42, -0.14, 0.14, 0.42)):
        th = -math.pi / 2 + a
        r0, r1 = 26, 34 + (j % 2) * 5
        seg = [(rcx + math.cos(th) * r0, hy + math.sin(th) * r0), (rcx + math.cos(th) * r1, hy + math.sin(th) * r1)]
        c.line(seg, 5, False)
    for j, a in enumerate((-0.42, -0.14, 0.14, 0.42)):
        th = -math.pi / 2 + a
        r0, r1 = 27, 33 + (j % 2) * 5
        seg = [(rcx + math.cos(th) * r0, hy + math.sin(th) * r0), (rcx + math.cos(th) * r1, hy + math.sin(th) * r1)]
        c.line(seg, 2, True)

    rng = np.random.default_rng(4)
    for _ in range(30):
        t = rng.uniform(0.15, 0.9)
        a = rng.uniform(-1, 1)
        px = fl[0] + (wall_spot[0] - fl[0]) * t
        py = fl[1] + a * 60 * t
        ix, iy = int(px), int(py)
        if 0 <= iy < H and cone_only[iy, ix] and not rob.alpha[iy, ix]:
            c.put(c.disc_mask(px, py, 0.6), True)

    grd = layer()
    guard(grd, (fl[0] + GX, fl[1]))
    grd.ink = shift(grd.ink, -GX, 0)
    grd.alpha = shift(grd.alpha, -GX, 0)
    comp(c, grd)
    flash_glare(c, fl[0] + 7, fl[1])

    security_camera(c, 348, 14)
    return c


def burst_mask(c, cx, cy, n, rin, rout, seed=1, squash=1.0):
    rng = np.random.default_rng(seed)
    pts = []
    for k in range(n * 2):
        th = k * math.pi / n + rng.uniform(-0.08, 0.08)
        rr = (rout * rng.uniform(0.8, 1.15)) if k % 2 == 0 else (rin * rng.uniform(0.85, 1.1))
        pts.append((cx + math.cos(th) * rr, cy + math.sin(th) * rr * squash))
    return c.poly_mask(pts)


def ink_line(c, pts, w=2, halo=2):
    c.line(pts, w + halo * 2, False)
    c.line(pts, w, True)


def wisp(c, x, y, h, amp=3, phase=0.0, w=3):
    pts = [(x + math.sin(phase + t * 0.35) * amp * (0.4 + t / h), y - t) for t in range(0, int(h), 2)]
    c.line(pts, w + 2, True)
    c.line(pts, w, False)
    c.put(c.disc_mask(pts[-1][0], pts[-1][1], w * 0.5 + 1), True)
    c.put(c.disc_mask(pts[-1][0], pts[-1][1], w * 0.5), False)


def hex_nut(c, x, y, r, ang):
    pts = [(x + math.cos(ang + k * math.pi / 3) * r, y + math.sin(ang + k * math.pi / 3) * r) for k in range(6)]
    m = c.poly_mask(pts)
    c.put(grow(m) & ~m, True)
    c.put(m, bayer(3))
    c.put(edge_side(m, 1, 1, 2), bayer(10))
    c.put(edge_side(m, -1, -1, 1), False)
    c.disc(x, y, r * 0.45, True)
    c.disc(x - 0.4, y - 0.4, r * 0.2, bayer(8))


def bolt_piece(c, x, y, ang, L=14):
    dx, dy = math.cos(ang), math.sin(ang)
    tip = (x + dx * L, y + dy * L)
    c.line([(x, y), tip], 5, True)
    c.line([(x, y), tip], 3, bayer(4))
    for k in range(3, int(L), 2):
        px, py = x + dx * k, y + dy * k
        c.line([(px - dy * 1.5, py + dx * 1.5), (px + dy * 1.5, py - dx * 1.5)], 1, True)
    hp = [(x - dx * 3 + dy * 5, y - dy * 3 - dx * 5), (x + dx * 1 + dy * 5, y + dy * 1 - dx * 5), (x + dx * 1 - dy * 5, y + dy * 1 + dx * 5), (x - dx * 3 - dy * 5, y - dy * 3 + dx * 5)]
    m = c.poly_mask(hp)
    c.put(grow(m) & ~m, True)
    c.put(m, bayer(2))
    c.put(edge_side(m, 1, 1, 1), bayer(10))


def brick_chunk(c, x, y, ang, w=14, h=8, soot=False):
    pts = rot([(x - w / 2, y - h / 2), (x + w / 2 - 2, y - h / 2), (x + w / 2, y - h / 2 + 3), (x + w / 2 - 1, y + h / 2), (x - w / 2 + 3, y + h / 2), (x - w / 2, y + 1)], x, y, ang)
    m = c.poly_mask(pts)
    c.put(grow(m) & ~m, True)
    c.put(m, bayer(10) if soot else bayer(4))
    c.put(edge_side(m, -1, -1, 1), False)
    c.put(edge_side(m, 1, 1, 2), True)
    c.put(c.disc_mask(x - 1, y, 1.2) & m, True)


def gear_piece(c, x, y, r, ang, n=8):
    pts = []
    for k in range(n * 2):
        th = ang + k * math.pi / n
        rr = r if k % 2 == 0 else r * 0.72
        pts.append((x + math.cos(th - 0.15) * rr, y + math.sin(th - 0.15) * rr))
        pts.append((x + math.cos(th + 0.15) * rr, y + math.sin(th + 0.15) * rr))
    m = c.poly_mask(pts)
    c.put(grow(m) & ~m, True)
    c.put(m, bayer(3))
    c.put(edge_side(m, 1, 1, 2), bayer(10))
    c.disc(x, y, r * 0.4, True)
    c.disc(x, y, r * 0.22, False)


def spring_piece(c, x, y, ang, L=18, n=6):
    pts = []
    for i in range(n * 8 + 1):
        t = i / (n * 8)
        a = t * n * math.tau
        px = x + math.cos(ang) * t * L - math.sin(ang) * math.sin(a) * 3.5
        py = y + math.sin(ang) * t * L + math.cos(ang) * math.sin(a) * 3.5
        pts.append((px, py))
    c.line(pts, 3, True)
    c.line([(p[0] - 0.5, p[1] - 0.5) for p in pts], 1, False)


def motion_lines(c, x, y, ang, n=4, L=24, gap=6, w=2, halo=1):
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy, dx
    for k in range(n):
        o = (k - (n - 1) / 2) * gap
        l = L * (0.6 + 0.4 * ((k * 7) % 5) / 4)
        s0 = (x + px * o, y + py * o)
        s1 = (s0[0] + dx * l, s0[1] + dy * l)
        c.line([s0, s1], w + halo * 2, False)
        c.line([s0, s1], w, True)


B4A = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def B4f(x, y):
    return B4A[y & 3, x & 3]


def flying_door(c, cx, cy, rx, ry, ang):
    th = (4, 5)
    for a in (0.15, -0.45):
        e = rot([(cx + rx * math.cos(a) * 0.98, cy + ry * math.sin(a) * 0.98)], cx, cy, ang)[0]
        o = rot([(cx + rx * math.cos(a) * 1.3, cy + ry * math.sin(a) * 1.3)], cx, cy, ang)[0]
        dx, dy = o[0] - e[0], o[1] - e[1]
        n = math.hypot(dx, dy)
        px, py = -dy / n * 4, dx / n * 4
        blk = c.poly_mask([(e[0] + px, e[1] + py), (o[0] + px, o[1] + py), (o[0] + px * 0.2 + dx * 0.15, o[1] + py * 0.2 + dy * 0.15), (o[0] - px * 0.4, o[1] - py * 0.4), (o[0] - px, o[1] - py), (e[0] - px, e[1] - py)])
        c.put(grow(blk) & ~blk, True)
        c.put(blk, bayer(4))
        c.put(edge_side(blk, 1, 1, 2), bayer(11))
        c.line([(e[0] + dx * 0.5 + px, e[1] + dy * 0.5 + py), (e[0] + dx * 0.5 - px, e[1] + dy * 0.5 - py)], 1, True)
    for k in range(18):
        a = k * math.tau / 18
        if k in (3, 4, 11):
            continue
        ex, ey = rx * math.cos(a), ry * math.sin(a)
        p0 = rot([(cx + ex * 0.92, cy + ey * 0.92)], cx, cy, ang)[0]
        p1 = rot([(cx + ex * 1.14 + th[0] * 0.5, cy + ey * 1.14 + th[1] * 0.5)], cx, cy, ang)[0]
        c.line([p0, p1], 5, True)
        c.line([p0, p1], 3, bayer(3) if k % 5 else bayer(8))
    side = c.poly_mask(ell_pts(cx + th[0], cy + th[1], rx, ry, 64, rot_a=ang)) | c.poly_mask(ell_pts(cx, cy, rx, ry, 64, rot_a=ang))
    c.put(grow(side, 2) & ~side, True)
    c.put(side, bayer(12))
    c.put(side & (c.xs % 3 == 0), True)
    face = c.poly_mask(ell_pts(cx, cy, rx, ry, 64, rot_a=ang))
    c.put(face, False)
    ca, sa = math.cos(ang), math.sin(ang)
    u = ((c.xs + 0.5 - cx) * ca + (c.ys + 0.5 - cy) * sa) / rx
    v = (-(c.xs + 0.5 - cx) * sa + (c.ys + 0.5 - cy) * ca) / ry
    crease = u * 0.8 + v * 0.6
    c.put(face & (crease > 0.12), bayer(4))
    c.put(face & (crease > 0.12) & (crease < 0.3), bayer(9))
    c.put(face & (np.abs(crease - 0.12) < 0.035), True)
    c.put(face & (np.abs(crease - 0.07) < 0.03), False)
    c.put(face & (u * u + v * v > 0.62) & (u * u + v * v < 0.7), True)
    c.put(face & (u * u + v * v > 0.7) & (crease < 0.12) & (u + v < -0.6), bayer(3))
    for k in range(8):
        a = k * math.tau / 8 + 0.3
        p0 = rot([(cx + rx * 0.3 * math.cos(a), cy + ry * 0.3 * math.sin(a))], cx, cy, ang)[0]
        p1 = rot([(cx + rx * 0.62 * math.cos(a), cy + ry * 0.62 * math.sin(a))], cx, cy, ang)[0]
        c.line([p0, p1], 2, True)
    hcx, hcy = rot([(cx - rx * 0.05, cy - ry * 0.05)], cx, cy, ang)[0]
    for k in range(3):
        a = k * math.tau / 3 + 0.5
        tip = (hcx + math.cos(a) * rx * 0.42, hcy + math.sin(a) * ry * 0.42)
        if k == 2:
            tip = (hcx + math.cos(a) * rx * 0.25, hcy + math.sin(a) * ry * 0.25 + 3)
        c.line([(hcx, hcy), tip], 4, True)
        c.line([(hcx - 1, hcy - 1), (tip[0] - 1, tip[1] - 1)], 1, False)
        c.disc(tip[0], tip[1], 3.4, True)
        c.disc(tip[0] - 0.6, tip[1] - 0.6, 1.5, False)
    c.disc(hcx, hcy, 5, True)
    c.disc(hcx, hcy, 3.2, bayer(5))
    c.disc(hcx - 1, hcy - 1, 1.2, False)


def vault_hole(c, cx, cy, r):
    fx0, fy0, fx1, fy1 = cx - r - 13, cy - r - 12, cx + r + 13, cy + r + 10
    c.rect(fx0 + 4, fy0 + 4, fx1 + 4, fy1 + 2, bayer(12))
    frame = c.poly_mask([(fx0, fy0 + 3), (fx1, fy0), (fx1, fy1), (fx0 + 2, fy1 + 1)])
    c.put(frame, True)
    plate = shrink(frame, 2)
    c.put(plate, False)
    dd = np.hypot(c.xs - cx, c.ys - cy)
    c.put(plate & (dd < r + 14), tone(np.clip(1.0 - (dd - r) / 16.0, 0, 0.85)))
    for x in (fx0 + 7, fx1 - 10):
        for y in range(int(fy0) + 10, int(fy1) - 8, 15):
            rivet(c, x, y, 2)
    for x in range(int(fx0) + 22, int(fx1) - 14, 18):
        rivet(c, x, fy0 + 8, 2)
    c.put(c.rect_mask(fx1 - 6, fy0 + 3, fx1 - 2, fy1 - 2), bayer(8))
    rng = np.random.default_rng(3)
    pts = []
    for k in range(40):
        a = k * math.tau / 40
        rr = r + (5 if k % 2 == 0 else -2) + rng.uniform(-2, 3)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    teeth = c.poly_mask(pts)
    c.put(grow(teeth, 2) & ~teeth, True)
    c.put(teeth, bayer(4))
    c.put(edge_side(teeth, -1, -1, 2), False)
    hole = c.disc_mask(cx, cy, r - 4)
    c.put(grow(hole) & ~hole, True)
    c.put(hole, True)
    for y in range(int(cy - r * 0.5), int(cy + r * 0.8), 12):
        c.put(hole & (c.ys == y) & (c.xs > cx - r * 0.7), bayer(10))
    for k in range(5):
        x = cx - r * 0.5 + k * 11
        c.put(hole & c.rect_mask(x, cy + r * 0.3, x + 9, cy + r * 0.3 + 7), bayer(11))


def flask(c, x, y, ang=0.0, cracked=True):
    neck = [(x - 3, y - 20), (x + 3, y - 20), (x + 3, y - 12), (x + 10, y + 3), (x + 10, y + 6), (x - 10, y + 6), (x - 10, y + 3), (x - 3, y - 12)]
    neck = rot(neck, x, y, ang)
    m = c.poly_mask(neck)
    lip = c.poly_mask(rot([(x - 5, y - 23), (x + 5, y - 23), (x + 5, y - 20), (x - 5, y - 20)], x, y, ang))
    c.put(grow(m | lip, 2) & ~(m | lip), True)
    c.put(m | lip, False)
    liq = m & (c.ys > y - 5)
    c.put(liq, bayer(9))
    c.put(liq & edge_side(m, 1, 0, 3), bayer(13))
    c.put(m & (c.ys == y - 5), True)
    for bx, by, br in ((x - 3, y + 1, 1.4), (x + 3, y - 2, 1), (x + 1, y + 3, 0.8)):
        c.ring(bx, by, br, br + 0.8, False)
    c.put(edge_side(m, -1, 0, 1) & (c.ys < y), bayer(4))
    c.line(rot([(x - 6, y - 2), (x - 2, y - 13)], x, y, ang), 1, bayer(6))
    if cracked:
        cr = rot([(x + 9, y - 1), (x + 5, y - 3), (x + 6, y - 7), (x + 1, y - 9), (x + 2, y - 13)], x, y, ang)
        c.line(cr, 1, True)
        c.line(rot([(x + 5, y - 3), (x + 1, y + 1)], x, y, ang), 1, True)
        c.line(rot([(x - 4, y + 6), (x - 2, y + 2), (x - 5, y - 1)], x, y, ang), 1, True)
        chip = c.poly_mask(rot([(x + 1, y - 24), (x + 5, y - 24), (x + 5, y - 20)], x, y, ang))
        c.put(chip, False)


def alarm_bell(c, x, y):
    c.rect(x - 3, y - 14, x + 3, y - 6, True)
    c.rect(x - 2, y - 13, x + 2, y - 7, bayer(6))
    bell = c.disc_mask(x, y + 4, 12) & (c.ys < y + 10)
    bell |= c.rect_mask(x - 13, y + 8, x + 14, y + 11)
    c.put(grow(bell) & ~bell, True)
    c.put(bell, False)
    c.put(bell & ~c.disc_mask(x - 4, y, 12), bayer(6))
    c.put(bell & ~c.disc_mask(x - 2, y + 2, 12), bayer(11))
    c.put(c.rect_mask(x - 12, y + 8, x + 13, y + 9), True)
    c.disc(x + 6, y + 14, 2.5, True)
    c.disc(x + 5.5, y + 13.5, 1, False)
    c.line([(x, y + 4), (x + 6, y + 13)], 1, True)
    for side in (-1, 1):
        for k, r0 in enumerate((17, 22)):
            for a in (-0.5, 0.0, 0.5):
                th = (math.pi if side < 0 else 0) + side * a
                c.line([(x + math.cos(th) * r0, y + 4 + math.sin(th) * r0), (x + math.cos(th) * (r0 + 3), y + 4 + math.sin(th) * (r0 + 3))], 1, True)


def tiny_star(c, x, y, r=4.5):
    pts = []
    for k in range(10):
        th = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((x + math.cos(th) * rr, y + math.sin(th) * rr))
    m = c.poly_mask(pts)
    c.put(grow(m) & ~m, True)
    c.put(m, False)


def robber_charred(s, cx, feet_y):
    L = (-1, -1)
    hy = feet_y - 104
    torso_top, torso_bot = hy + 17, feet_y - 44
    legs = []
    for side, kn in ((-1, 4), (1, -2)):
        x_hip = cx + side * 9
        x_knee = cx + side * 6 + kn
        x_foot = cx + side * 14
        pts = [(x_hip - 8, torso_bot - 2), (x_hip + 8, torso_bot - 2), (x_knee + 6.5, feet_y - 22), (x_foot + 6, feet_y - 5), (x_foot - 6, feet_y - 5), (x_knee - 6.5, feet_y - 22)]
        legs.append(s.poly_mask(pts))
    legm = legs[0] | legs[1]
    s.put(grow(legm) & ~legm, True)
    s.put(legm, True)
    for lm in legs:
        s.put(edge_side(lm, -1, 0, 1), bayer(6))
    s.put(s.ellipse_mask(cx - 12, feet_y - 30, 3, 2), bayer(4))
    s.put(s.ellipse_mask(cx + 10, feet_y - 16, 2, 2), bayer(5))
    for side in (-1, 1):
        fx = cx + side * 15
        sh = (s.ellipse_mask(fx + side * 4, feet_y - 3, 10, 5) & (s.ys < feet_y)) | s.rect_mask(fx - 6, feet_y - 7, fx + 7, feet_y - 3)
        s.put(grow(sh) & ~sh & (s.ys <= feet_y), True)
        s.put(sh, True)
        s.put(s.ellipse_mask(fx + side * 5 - 1, feet_y - 5, 4, 1.2) & sh, bayer(6))

    shL, shR = (cx - 19, torso_top + 6), (cx + 19, torso_top + 6)
    armL = capsule(s, shL, (cx - 27, torso_top + 22), 6.5) | capsule(s, (cx - 27, torso_top + 22), (cx - 28, torso_top + 38), 6)
    armR = capsule(s, shR, (cx + 31, torso_top + 16), 6.5) | capsule(s, (cx + 31, torso_top + 16), (cx + 37, torso_top), 6)
    torso = s.poly_mask([(cx - 21, torso_top + 1), (cx + 21, torso_top + 1), (cx + 23, torso_top + 12), (cx + 20, torso_bot - 2), (cx - 20, torso_bot - 2), (cx - 23, torso_top + 12)])
    hem = []
    for i in range(9):
        x = cx - 20 + i * 5
        hem += [(x, torso_bot - 3), (x + 2.5, torso_bot + (3 if i % 2 else 5))]
    hem += [(cx + 20, torso_bot - 3)]
    torso |= s.poly_mask(hem + [(cx + 20, torso_bot - 6), (cx - 20, torso_bot - 6)])
    body = torso | armL | armR
    stripe = lambda x, y: ((y - torso_top) % 6) < 3
    s.put(grow(body) & ~body, True)
    s.put(body, True)
    s.put(body & ~stripe(s.xs, s.ys), bayer(7))
    for (sx, sy, sr) in ((cx - 10, torso_top + 8, 7), (cx + 12, torso_top + 22, 8), (cx - 14, torso_top + 30, 6), (cx + 26, torso_top + 6, 5)):
        s.put(body & s.ellipse_mask(sx, sy, sr, sr * 0.7), bayer(13))
    s.put(edge_side(body, -1, -1, 2) & ~stripe(s.xs, s.ys), bayer(7))
    s.put(edge_side(body, -1, 0, 1), bayer(5))
    for am in (armL, armR):
        s.put(grow(am) & ~am & torso, True)
    for hx, hyy, hr in ((cx - 8, torso_top + 14, 2.6), (cx + 10, torso_top + 26, 2.2), (cx - 12, torso_top + 30, 1.8), (cx + 26, torso_top + 16, 1.8)):
        hm = s.ellipse_mask(hx, hyy, hr, hr * 0.8)
        s.put(grow(hm) & ~hm, True)
        s.put(hm, bayer(3))
    s.put(s.rect_mask(cx - 20, torso_bot - 8, cx + 20, torso_bot - 3), True)
    s.put(s.rect_mask(cx - 19, torso_bot - 7, cx + 19, torso_bot - 6), bayer(10))
    s.rect(cx - 4, torso_bot - 9, cx + 4, torso_bot - 2, True)
    s.rect(cx - 3, torso_bot - 8, cx + 3, torso_bot - 3, bayer(8))

    hl = (cx - 28, torso_top + 44)
    cuff = capsule(s, (hl[0] - 6, hl[1] - 6), (hl[0] + 6, hl[1] - 6), 2.3)
    s.put(grow(cuff) & ~cuff, True)
    s.put(cuff, bayer(10))
    hm = s.ellipse_mask(hl[0], hl[1], 6, 6.5)
    for bx in (-4, -1.3, 1.3, 4):
        hm |= capsule(s, (hl[0] + bx, hl[1] + 2), (hl[0] + bx * 1.1, hl[1] + 9), 1.6)
    s.put(grow(hm) & ~hm, True)
    s.put(hm, True)
    s.put(edge_side(hm, -1, 0, 1), bayer(5))

    fx, fy = cx + 39, torso_top - 10
    flask(s, fx, fy, 0.12)
    grip = s.ellipse_mask(fx - 1, fy + 5, 7.5, 6)
    s.put(grow(grip) & ~grip, True)
    s.put(grip, True)
    s.put(edge_side(grip, -1, -1, 1), bayer(5))
    for k in range(3):
        s.line([(fx - 6 + k * 3.5, fy + 2), (fx - 5 + k * 3.5, fy + 9)], 1, bayer(9))
    s.line([(fx + 6, fy + 1), (fx + 8, fy + 5)], 2, True)
    s.put(s.ellipse_mask(cx, torso_top + 1, 13, 4), True)
    ski_head(s, cx + 2, hy, 18, 21, eyes='spiral', light=L, mouth='O')
    strands = ((-15, -0.95), (-11, -0.6), (-6, -0.3), (-1, -0.05), (4, 0.2), (9, 0.5), (13, 0.8), (16, 1.1))
    paths = []
    for k, (dx, a) in enumerate(strands):
        bx = cx + 2 + dx
        by = hy - math.sqrt(max(0, 1 - (dx / 18.5) ** 2)) * 21 + 3
        L0 = 8 + (k % 3) * 3
        pts = [(bx, by)]
        for i in range(1, 5):
            t = i / 4
            pts.append((bx + math.sin(a) * L0 * t + (1.8 if i % 2 else -1.8) * math.cos(a), by - math.cos(a) * L0 * t + (1.8 if i % 2 else -1.8) * math.sin(a)))
        paths.append(pts)
    for pts in paths:
        s.line(pts, 4, False)
    for pts in paths:
        s.line(pts, 2, True)
    return hy


def greedy_points(ys, xs, spacing, rng):
    idx = rng.permutation(len(ys))
    pts = []
    for i in idx:
        y, x = ys[i], xs[i]
        ok = True
        for (py, px) in pts:
            if (py - y) ** 2 + (px - x) ** 2 < spacing * spacing:
                ok = False
                break
        if ok:
            pts.append((y, x))
    return pts


def cumulus2(c, shape, seed=1, bump=(7, 12), spacing=13, billow=(9, 16), bspacing=24, base=False, dark=False):
    rng = np.random.default_rng(seed)
    edge = shape & ~erode(shape)
    ys, xs = np.nonzero(edge)
    bumps = []
    for (y, x) in greedy_points(ys, xs, spacing, rng):
        bumps.append((x, y, rng.uniform(*bump)))
    union = shape.copy()
    for x, y, r in bumps:
        union |= c.disc_mask(x, y, r)
    c.put(grow(union, 2) & ~union, True)
    c.put(union, base)
    for x, y, r in sorted(bumps, key=lambda b: b[1]):
        m = c.disc_mask(x, y, r) & union
        c.put(m & ~c.disc_mask(x - r * 0.3, y - r * 0.35, r) & ~shape, bayer(9 if dark else 4))
    c.put(edge_side(union, 1, 1, 12) & ~edge_side(union, 1, 1, 6), bayer(6 if dark else 2))
    c.put(edge_side(union, 1, 1, 6) & ~edge_side(union, 1, 1, 3), bayer(10 if dark else 5))
    c.put(edge_side(union, 1, 1, 3), bayer(13 if dark else 9))
    inner = shrink(union, 14)
    ys, xs = np.nonzero(inner)
    for (y, x) in greedy_points(ys, xs, bspacing, rng):
        r = rng.uniform(*billow)
        y = y + rng.uniform(-6, 6)
        x = x + rng.uniform(-6, 6)
        a0 = rng.uniform(-0.7, -0.1)
        a1 = a0 - rng.uniform(1.6, 2.6)
        ang = np.arctan2(c.ys + 0.5 - y, c.xs + 0.5 - x)
        sector = (ang < a0) & (ang > a1)
        c.put(c.ring_mask(x, y, r + 1.3, r + 4.5) & sector & union, bayer(6 if dark else 3))
        c.put(c.ring_mask(x, y, r, r + 1.3) & sector & union, True)
    return union


def scene_boom():
    floor_y = 196
    bx, by = 196, 102
    c = Canvas(W, H, 0)
    wall = c.rect_mask(0, 0, W, floor_y)
    brick_wall(c, wall, lo=0, hi=2, seed=11)
    d = np.hypot(c.xs - bx, (c.ys - by) * 1.1)
    c.put(wall & (d > 200), OR(lambda x, y: c.ink[y, x], bayer(5)))
    c.put(wall & (d > 250), OR(lambda x, y: c.ink[y, x], bayer(8)))
    rng = np.random.default_rng(21)
    floor = c.rect_mask(0, floor_y, W, H)
    c.put(floor, False)
    fy = c.ys - floor_y
    row = fy // 9
    board_ln = (fy % 9 == 0)
    seam = ((c.xs + (row * 37) % 60) % 60 == 0)
    grain = ((fy % 9 == 4) & ((c.xs + row * 13) % 23 < 6)) | ((fy % 9 == 6) & ((c.xs + row * 7) % 31 == 3))
    c.put(floor, lambda x, y: board_ln | seam | grain | (B4f(x, y) < 2))
    fd = np.hypot((c.xs - bx) * 0.55, (c.ys - floor_y) * 2.2) + np.clip(160 - c.xs, 0, None) * 0.8
    c.put(floor, OR(lambda x, y: c.ink[y, x], tone(np.clip(1.0 - fd / 44.0, 0, 0.92))))
    c.rect(0, floor_y - 7, W, floor_y + 1, True)
    c.rect(0, floor_y - 6, W, floor_y - 5, False)
    c.rect(0, floor_y - 4, W, floor_y - 1, bayer(6))
    c.rect(0, floor_y + 1, W, floor_y + 3, bayer(12))
    c.put(c.rect_mask(0, floor_y - 7, W, floor_y + 1) & (np.abs(c.xs - bx) < 60), OR(lambda x, y: c.ink[y, x], bayer(12)))

    vault_hole(c, bx, by, 50)
    sp = burst_mask(c, 40, 170, 11, 12, 26, seed=13, squash=0.8)
    for k in range(7):
        a = k * 0.9 + 0.3
        sp |= c.disc_mask(40 + math.cos(a) * 30, 170 + math.sin(a) * 22, 2 + (k % 3))
    sp &= wall
    c.put(sp, OR(lambda x, y: c.ink[y, x], bayer(13)))
    c.put(sp & shrink(sp, 4), True)

    bm = burst_mask(c, bx - 8, by - 6, 12, 74, 132, seed=5, squash=0.82)
    for k in range(30):
        a = k * math.tau / 30 + rng.uniform(-0.05, 0.05)
        r0, r1 = rng.uniform(118, 140), rng.uniform(175, 250)
        p0 = (bx + math.cos(a) * r0, by + math.sin(a) * r0 * 0.82)
        p1 = (bx + math.cos(a) * r1, by + math.sin(a) * r1 * 0.82)
        wdt = 2 if k % 3 else 3
        m = c.mask(lambda dr, p0=p0, p1=p1, wdt=wdt: dr.line([p0, p1], fill=1, width=wdt + 2))
        c.put(m & ~bm & wall, False)
        m = c.mask(lambda dr, p0=p0, p1=p1, wdt=wdt: dr.line([p0, p1], fill=1, width=wdt))
        c.put(m & ~bm & wall, True)
    soot = burst_mask(c, bx - 8, by - 6, 12, 90, 150, seed=5, squash=0.82) & ~bm & wall
    c.put(soot, OR(lambda x, y: c.ink[y, x], bayer(9)))
    c.put(grow(bm, 2) & ~bm, True)
    c.put(bm, False)
    bm2 = burst_mask(c, bx - 8, by - 6, 12, 60, 108, seed=6, squash=0.82)
    c.put(bm & ~bm2, lambda x, y: (B8[y & 7, x & 7] < 6))
    c.put(bm2 & ~shrink(bm2, 1), bayer(10))

    bshape = (c.ellipse_mask(140, 44, 26, 20) | c.ellipse_mask(288, 76, 24, 30) | c.ellipse_mask(270, 20, 24, 16) | c.ellipse_mask(84, 104, 18, 14) | c.ellipse_mask(296, 140, 18, 22))
    cumulus2(c, bshape, seed=7, bump=(5, 9), spacing=10, billow=(6, 9), bspacing=18, base=bayer(5), dark=True)
    shape = (c.ellipse_mask(204, 44, 58, 34) | c.ellipse_mask(196, 104, 68, 48) | c.ellipse_mask(150, 138, 60, 40)
             | c.ellipse_mask(228, 150, 44, 34) | c.ellipse_mask(106, 132, 26, 30) | c.ellipse_mask(250, 90, 26, 34))
    shape &= c.rect_mask(0, 0, W, 186)
    cumulus2(c, shape, seed=3, bump=(8, 15), spacing=15, billow=(8, 20), bspacing=24)
    for (x, y, r) in ((118, 186, 8), (108, 192, 6), (134, 190, 7)):
        c.disc(x, y, r + 1.4, True)
        c.disc(x, y, r, False)
        c.put(c.disc_mask(x, y, r) & ~c.disc_mask(x - r * 0.3, y - r * 0.4, r), bayer(6))

    brick_chunk(c, 156, 214, 0.3, soot=True)
    brick_chunk(c, 242, 206, -0.2)
    brick_chunk(c, 174, 232, 0.1, 16, 9)
    hex_nut(c, 196, 224, 4.5, 0.3)
    bolt_piece(c, 146, 234, -0.3, 12)
    dk = (216, 218)
    c.ellipse(dk[0] + 3, dk[1] + 8, 12, 3, bayer(10))
    c.disc(dk[0], dk[1], 10, True)
    c.disc(dk[0], dk[1], 8.5, False)
    c.put(c.disc_mask(dk[0], dk[1], 8.5) & (c.xs + c.ys > dk[0] + dk[1] + 2), bayer(5))
    for k in range(24):
        th = k * math.tau / 24 + 0.4
        c.line([(dk[0] + math.cos(th) * 8, dk[1] + math.sin(th) * 8), (dk[0] + math.cos(th) * (6 if k % 3 else 4.5), dk[1] + math.sin(th) * (6 if k % 3 else 4.5))], 1, True)
    c.disc(dk[0], dk[1], 3, True)
    c.line([(dk[0] - 1, dk[1] - 1), (dk[0] + 2, dk[1] + 2)], 1, False)
    for k, (x, y, a) in enumerate(((58, 232, -0.3), (232, 236, 0.4), (20, 214, 0.1), (190, 206, -0.6))):
        cash_bill(c, x, y, a, singe=0.35 if k % 2 == 0 else 0.0)

    rob = layer()
    rcx, feet_y = 124, 228
    hy = robber_charred(rob, rcx, feet_y)
    c.put(grow(rob.alpha, 1) & ~rob.alpha, False)
    c.put(c.ellipse_mask(rcx + 4, feet_y, 34, 5), bayer(12))
    comp(c, rob)
    wisp(c, rcx - 20, hy - 20, 20, 3, 0.0, 2)
    wisp(c, rcx + 22, hy - 18, 16, 3, 2.0, 2)
    for (x, y) in ((rcx - 26, hy - 34), (rcx + 2, hy - 44), (rcx + 28, hy - 34)):
        tiny_star(c, x, y, 5.5)
    for (x0, y0, x1, y1) in ((rcx - 18, hy - 40, rcx - 10, hy - 44), (rcx + 12, hy - 44, rcx + 20, hy - 40)):
        c.line([(x0, y0), (x1, y1)], 3, False)
        c.line([(x0, y0), (x1, y1)], 1, True)
    for i, (x, y, r) in enumerate(((rcx - 22, hy + 14, 3), (rcx - 29, hy + 9, 4), (rcx - 38, hy + 3, 5.5))):
        c.disc(x, y, r + 1.4, True)
        c.disc(x, y, r, False)
        c.put(c.disc_mask(x, y, r) & ~c.disc_mask(x - r * 0.3, y - r * 0.3, r), bayer(6))

    dcx, dcy = 34, 88
    motion_lines(c, dcx + 30, dcy + 6, 0.12, 4, 16, 6, 2, 1)
    flying_door(c, dcx, dcy, 27, 21, -0.55)
    for a0, n in ((-1.9, 9), (1.0, 8)):
        pts = [(dcx + math.cos(a0 + t * 0.1) * 38, dcy + math.sin(a0 + t * 0.1) * 31) for t in range(n)]
        ink_line(c, pts, 2, 1)
        e, f = pts[-1], pts[-2]
        ang = math.atan2(e[1] - f[1], e[0] - f[0])
        c.poly([(e[0] + math.cos(ang) * 4, e[1] + math.sin(ang) * 4), (e[0] + math.cos(ang + 2.2) * 4, e[1] + math.sin(ang + 2.2) * 4), (e[0] + math.cos(ang - 2.2) * 4, e[1] + math.sin(ang - 2.2) * 4)], True)

    brick_chunk(c, 112, 60, 0.6, 16, 9)
    motion_lines(c, 124, 67, 0.3, 3, 14, 5, 1, 1)
    brick_chunk(c, 16, 150, -0.4, 14, 8, soot=True)
    motion_lines(c, 27, 154, 0.15, 3, 14, 5, 1, 1)
    bolt_piece(c, 80, 40, -0.4, 14)
    motion_lines(c, 98, 36, 0.15, 2, 14, 5, 1, 1)
    hex_nut(c, 140, 30, 5, 0.2)
    gear_piece(c, 22, 30, 9, 0.3)
    motion_lines(c, 35, 36, 0.35, 3, 14, 6, 1, 1)
    spring_piece(c, 6, 124, 0.25, 20, 5)
    hex_nut(c, 56, 156, 4, 0.8)
    for k, (x, y, a, sg) in enumerate(((150, 12, 0.5, 0.0), (64, 128, -0.4, 0.4), (60, 20, 0.9, 0.0), (22, 182, 0.3, 0.0), (44, 56, -0.8, 0.5), (106, 12, -0.2, 0.45), (290, 18, 0.7, 0.0), (322, 50, -0.3, 0.4), (138, 196, 1.1, 0.0))):
        cash_bill(c, x, y, a, singe=sg)
    alarm_bell(c, 364, 30)
    return c


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, fn in (('end-caught', scene_caught), ('end-boom', scene_boom)):
        c = fn()
        c.save(os.path.join(OUT_DIR, name + '.png'))
        if PREVIEW_DIR:
            c.preview(os.path.join(PREVIEW_DIR, name + '@3x.png'), 3)


if __name__ == '__main__':
    main()
