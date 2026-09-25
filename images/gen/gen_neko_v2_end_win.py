import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdart import (Canvas, bayer, bayer8, tone, hlines, vlines, hatch, hatch_r, cross, dots, brick,
                   wood, brushed, OR, AND, NOT, rivet, screw, panel, dilate, erode, load_font, B8 as B8f)

import neko_body as NB

W, H = 400, 240
PREVIEW = os.environ.get('PREVIEW_DIR')


def shift(m, dx, dy):
    out = np.zeros_like(m)
    h, w = m.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def rot_rect(cx, cy, w, h, a):
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for dx, dy in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]:
        pts.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    return pts


def sparkle(c, x, y, r, thick=False):
    arm = c.poly_mask([(x - r, y), (x - 1, y - 1), (x, y - r), (x + 1, y - 1), (x + r, y), (x + 1, y + 1),
                       (x, y + r), (x - 1, y + 1)])
    c.put(dilate(arm), True)
    c.put(arm, False)
    if thick:
        d = r * 0.45
        for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            c.put(c.rect_mask(x + sx * d, y + sy * d, x + sx * d + 1, y + sy * d + 1), True)


def angle_field(cx, cy):
    ys, xs = np.mgrid[0:H, 0:W]
    return np.arctan2(ys + 0.5 - cy, xs + 0.5 - cx), np.hypot(xs + 0.5 - cx, ys + 0.5 - cy)


def qtone(field, steps=8):
    return tone(np.round(np.clip(field, 0, 1) * steps) / steps)


def rays(cx, cy, n, phase=0.0):
    a, d = angle_field(cx, cy)
    k = np.floor((a + math.pi + phase) / (2 * math.pi) * n).astype(int)
    return (k % 2 == 0), d


# ------------------------------------------------------------------ props

def gold_bar(c, x, y, w=26, h=8, depth=5, shadow=True):
    ins = max(3, depth - 1)
    top = [(x + ins, y), (x + w - ins, y), (x + w, y + depth), (x, y + depth)]
    front = [(x, y + depth), (x + w, y + depth), (x + w - 2, y + depth + h), (x + 2, y + depth + h)]
    whole = c.poly_mask(top) | c.poly_mask(front)
    if shadow:
        c.put(shift(whole, 4, 2) & ~whole, bayer(13))
    c.put(dilate(whole), True)
    fm = c.poly_mask(front)
    c.put(fm, bayer(3))
    c.put(fm & ~shift(fm, 0, -3), bayer(9))
    c.put(fm & ~shift(fm, -5, 0), bayer(11))
    c.put(fm & ~shift(fm, 0, 1), False)
    tm = c.poly_mask(top)
    c.put(tm, False)
    c.put(tm & (c.ys == y + depth - 1) & (c.xs % 2 == 0), True)
    c.line([(x, y + depth), (x + w, y + depth)], 1, True)
    mx = x + w // 2
    c.rect(mx - 5, y + depth + 2, mx + 5, y + depth + h - 2, True)
    c.rect(mx - 4, y + depth + 3, mx + 4, y + depth + h - 3, False)
    c.put(c.rect_mask(mx - 3, y + depth + 3, mx + 3, y + depth + h - 3) & (c.xs % 2 == 0), True)
    c.line([(x + ins + 1, y + 1), (x + ins + 5, y + 1)], 1, True)
    return whole


def gold_pyramid(c, x, y, rows=3, w=26, h=8, depth=5):
    bh = h + depth - 1
    for r in range(rows):
        n = rows - r
        rx = x + r * (w // 2)
        ry = y - r * (h + depth // 2)
        for i in range(n):
            gold_bar(c, rx + i * w, ry, w, h, depth, shadow=(r == 0))


def cash_stack(c, x, y, w=30, d=10, h=12, band=True):
    top = [(x + 5, y), (x + w + 5, y), (x + w, y + d), (x, y + d)]
    side = [(x + w, y + d), (x + w + 5, y), (x + w + 5, y + h), (x + w, y + d + h)]
    front = [(x, y + d), (x + w, y + d), (x + w, y + d + h), (x, y + d + h)]
    allm = c.poly_mask(top) | c.poly_mask(side) | c.poly_mask(front)
    c.put(shift(allm, 3, 2) & ~allm, bayer(12))
    c.put(dilate(allm), True)
    c.put(c.poly_mask(front), hlines(2, 1))
    c.put(c.poly_mask(side), OR(hlines(2, 1), bayer(8)))
    c.put(c.poly_mask(top), False)
    c.outline_poly([(x + 8, y + 2), (x + w + 1, y + 2), (x + w - 2, y + d - 2), (x + 3, y + d - 2)], True)
    c.disc(x + w / 2 + 3, y + d / 2, 2.2, bayer(6))
    c.line([(x, y + d), (x + w, y + d)], 1, True)
    if band:
        bx = x + w // 2 - 4
        c.poly([(bx, y + d), (bx + 7, y + d), (bx + 12, y), (bx + 5, y)], True)
        c.rect(bx, y + d, bx + 7, y + d + h, True)
        c.rect(bx + 2, y + d + 2, bx + 5, y + d + h - 2, bayer(4))
    return allm


def bill(c, cx, cy, a, w=22, h=11):
    pts = rot_rect(cx, cy, w, h, a)
    m = c.poly_mask(pts)
    c.put(shift(m, 2, 3) & ~m, bayer(10))
    c.put(dilate(m), True)
    c.put(m, False)
    inner = c.poly_mask(rot_rect(cx, cy, w - 5, h - 5, a))
    c.put(inner & ~erode(inner), True)
    c.disc(cx, cy, 2.2, True)
    c.disc(cx, cy, 1.2, False)
    ca, sa = math.cos(a), math.sin(a)
    for s in (-1, 1):
        px, py = cx + s * (w / 2 - 4) * ca, cy + s * (w / 2 - 4) * sa
        c.put(c.rect_mask(round(px), round(py), round(px) + 1, round(py) + 1), True)


def money_bag(c, cx, cy, r=18, font=None):
    body = c.disc_mask(cx, cy, r) | c.ellipse_mask(cx, cy + r * 0.35, r * 1.08, r * 0.75)
    neck = c.poly_mask([(cx - 6, cy - r - 2), (cx + 6, cy - r - 2), (cx + 4, cy - r + 6), (cx - 4, cy - r + 6)])
    flap = c.poly_mask([(cx - 5, cy - r - 2), (cx - 13, cy - r - 9), (cx - 6, cy - r - 6), (cx - 1, cy - r - 11),
                        (cx + 3, cy - r - 6), (cx + 11, cy - r - 10), (cx + 5, cy - r - 2)])
    all_m = body | neck | flap
    c.ellipse(cx + 5, cy + r * 1.05 + 1, r * 1.2, 4, bayer(12))
    c.put(dilate(all_m), True)
    c.put(all_m, bayer(2))
    c.put(body & ~shift(body, -6, -5), bayer(7))
    c.put(body & ~shift(body, -3, -2), bayer(11))
    c.put(flap, bayer(4))
    c.put(flap & ~shift(flap, 1, 1), False)
    c.put(body & ~shift(body, 1, 1), False)
    c.rect(cx - 7, cy - r + 1, cx + 7, cy - r + 4, True)
    c.line([(cx - 6, cy - r + 2), (cx + 6, cy - r + 2)], 1, False)
    c.line([(cx + 5, cy - r + 3), (cx + 10, cy - r + 9), (cx + 8, cy - r + 11)], 1, True)
    for k in range(3):
        c.line([(cx - r * 0.6 + k * 2, cy - r * 0.5 + k * 6), (cx - r * 0.35 + k * 2, cy - r * 0.4 + k * 6)], 1, True)
    if font is not None:
        m = c.text_mask('$', cx - 5, cy - 5, font)
        c.put(dilate(m), False)
        c.put(m, True)
    c.put(c.ellipse_mask(cx - r * 0.45, cy - r * 0.2, 2.2, 4) & body, False)
    return all_m


def diamond(c, cx, cy, s=10):
    top = cy - s * 0.2
    girdle = [(cx - s, top), (cx - s * 0.55, cy - s * 0.75), (cx + s * 0.55, cy - s * 0.75), (cx + s, top)]
    crown = c.poly_mask(girdle)
    pav = c.poly_mask([(cx - s, top), (cx + s, top), (cx, cy + s * 0.95)])
    allm = crown | pav
    c.put(dilate(allm), True)
    c.put(crown, False)
    c.put(pav, bayer(2))
    c.put(pav & (c.xs > cx), bayer(8))
    c.line([(cx - s, top), (cx + s, top)], 1, True)
    c.line([(cx - s * 0.55, cy - s * 0.75), (cx - s * 0.3, top), (cx, cy - s * 0.75), (cx + s * 0.3, top),
            (cx + s * 0.55, cy - s * 0.75)], 1, True)
    c.line([(cx - s * 0.3, top), (cx, cy + s * 0.95), (cx + s * 0.3, top)], 1, True)
    c.put(c.poly_mask([(cx - s * 0.5, top - 1), (cx - s * 0.35, cy - s * 0.6), (cx - s * 0.15, top - 1)]), bayer(3))


def coin(c, cx, cy, r=5, edge=True):
    m = c.ellipse_mask(cx, cy, r, r * 0.45)
    if edge:
        sm = c.ellipse_mask(cx, cy + 2, r, r * 0.45) | c.rect_mask(cx - r + .5, cy, cx + r - .5, cy + 2)
        c.put(dilate(sm | m), True)
        c.put(sm & ~m, vlines(2))
    else:
        c.put(dilate(m), True)
    c.put(m, bayer(2))
    c.put(c.ellipse_mask(cx, cy, r - 2, (r - 2) * 0.45) & ~c.ellipse_mask(cx, cy, r - 3, max(.5, (r - 3) * 0.45)), True)


def deposit_boxes(c, x0, y0, x1, y1, bw, bh, field_fn, open_set=(), seed=3, font=None):
    rng = np.random.default_rng(seed)
    cols = int((x1 - x0) // bw)
    rows = int((y1 - y0) // bh)
    for j in range(rows):
        for i in range(cols):
            x, y = x0 + i * bw, y0 + j * bh
            c.rect(x, y, x + bw, y + bh, True)
            face = c.rect_mask(x + 1, y + 1, x + bw - 1, y + bh - 1)
            c.put(face, field_fn(0.0))
            c.put(c.rect_mask(x + 1, y + 1, x + bw - 1, y + 2) | c.rect_mask(x + 1, y + 1, x + 2, y + bh - 1), False)
            c.put(c.rect_mask(x + bw - 2, y + 2, x + bw - 1, y + bh - 1) | c.rect_mask(x + 2, y + bh - 2, x + bw - 1, y + bh - 1), field_fn(0.45))
            if (i, j) in open_set:
                c.rect(x + 2, y + 2, x + bw - 2, y + bh - 2, True)
                c.rect(x + 3, y + bh - 5, x + bw - 3, y + bh - 3, bayer(12))
                continue
            px, py = x + bw // 2, y + bh // 2
            c.rect(px - 5, py - 3, px + 5, py + 1, True)
            c.rect(px - 4, py - 2, px + 4, py, False)
            c.put(c.rect_mask(px - 3, py - 2, px + 3, py - 1) & (c.xs % 2 == 0), True)
            c.disc(x + 5, y + bh - 5, 1.6, True)
            c.disc(x + bw - 5, y + bh - 5, 1.6, True)
            c.put(c.rect_mask(x + 5, y + bh - 6, x + 6, y + bh - 5), False)
            c.put(c.rect_mask(x + bw - 5, y + bh - 6, x + bw - 4, y + bh - 5), False)


# ------------------------------------------------------------------ robber

def robber_head(c, hx, hy, rx=19, ry=24, mood='joy', halo=False, look=(0, 0)):
    head = c.ellipse_mask(hx, hy, rx, ry) | c.ellipse_mask(hx, hy - ry * 0.35, rx * 0.93, ry * 0.7)
    neck = c.rect_mask(hx - rx * 0.55, hy + ry * 0.6, hx + rx * 0.55, hy + ry + 6)
    m = head | neck
    if halo:
        c.put(dilate(dilate(m)) & ~dilate(m), False)
    c.put(dilate(m), True)
    c.put(m, True)
    sheen = head & ~shift(head, 3, 3) & shift(head, -1, -1)
    c.put(sheen & (c.ys < hy), bayer(11))
    c.put(head & ~shift(head, 1, 1) & (c.ys < hy - 4) & (c.xs < hx), False)
    ex = rx * 0.45
    ey = hy - ry * 0.12
    for s in (-1, 1):
        cx = hx + s * ex
        if mood == 'panic':
            c.put(c.ellipse_mask(cx, ey, 6.2, 6.0), False)
            c.put(c.ellipse_mask(cx, ey, 5.0, 4.8), True)
            c.put(c.ellipse_mask(cx + look[0], ey + look[1], 3.2, 3.2), False)
            c.put(c.disc_mask(cx + look[0], ey + look[1], 1.1), True)
        else:
            c.put(c.ellipse_mask(cx, ey, 6.5, 4.4), False)
            c.put(c.ellipse_mask(cx, ey, 5.3, 3.3), True)
            c.put(c.ellipse_mask(cx + look[0], ey + look[1], 2.8, 2.6), False)
            c.put(c.disc_mask(cx + look[0], ey + look[1], 1.3), True)
            if mood == 'joy':
                c.put(c.ellipse_mask(cx, ey + 3.5, 6.8, 2.2) & ~c.ellipse_mask(cx, ey - 20, 60, 22), True)
    my = hy + ry * 0.45
    if mood == 'panic':
        c.put(c.ellipse_mask(hx, my, 5.5, 7.5), False)
        c.put(c.ellipse_mask(hx, my, 4.0, 6.0), True)
        c.put(c.ellipse_mask(hx, my + 3, 2.5, 2.0), bayer(6))
    else:
        mouth = c.ellipse_mask(hx, my - 1, 8.5, 7.0) & (c.ys >= my - 3)
        c.put(mouth, False)
        inner = c.ellipse_mask(hx, my - 1, 7.0, 5.5) & (c.ys >= my - 2)
        c.put(inner, True)
        c.put(c.rect_mask(hx - 6, my - 2, hx + 6, my) & inner, False)
        c.put(c.ellipse_mask(hx, my + 3, 3.5, 1.6) & inner, bayer(6))
    return m


def arm(c, pts, width=9, stripe=6, y0=0):
    outer = c.mask(lambda d: d.line(pts, fill=1, width=width + 2, joint='curve'))
    inner = c.mask(lambda d: d.line(pts, fill=1, width=width, joint='curve'))
    c.put(outer, True)
    c.put(inner, lambda x, y: (y - y0) % stripe < stripe // 2)
    return outer


def sweat(c, x, y, s=1.0):
    m = c.poly_mask([(x, y - 5 * s), (x + 3 * s, y + 1 * s), (x - 3 * s, y + 1 * s)]) | c.disc_mask(x, y + 1 * s, 3 * s)
    c.put(dilate(m), True)
    c.put(m, False)
    c.put(m & ~shift(m, -1, -1), bayer(6))
    c.put(c.rect_mask(x - 1, y - 1, x, y + 1), True)


def shake_lines(c, cx, cy, r0, r1, angles, width=2, pat=True):
    for a in angles:
        c.line([(cx + math.cos(a) * r0, cy + math.sin(a) * r0), (cx + math.cos(a) * r1, cy + math.sin(a) * r1)],
               width, pat)


def torso(c, cx, top, half_sh, half_bot, bottom, stripe=6, halo=False):
    pts = [(cx - 9, top), (cx + 9, top), (cx + half_sh - 4, top + 5), (cx + half_sh, top + 12),
           (cx + half_bot, bottom), (cx - half_bot, bottom), (cx - half_sh, top + 12), (cx - half_sh + 4, top + 5)]
    m = c.poly_mask(pts)
    if halo:
        c.put(dilate(dilate(m)) & ~dilate(m), False)
    c.put(dilate(m), True)
    sp = lambda x, y: (y - top) % stripe < stripe // 2
    c.put(m, sp)
    c.put(m & ~shift(m, -9, 0), OR(sp, bayer(9)))
    c.put(m & ~shift(m, 2, 0) & ~sp(c.xs, c.ys), False)
    c.put(m & ~shift(m, 2, 0) & sp(c.xs, c.ys), bayer(8))
    col = c.ellipse_mask(cx, top + 1, 12, 5) & (c.ys >= top - 1)
    c.put(dilate(col), True)
    c.put(col, bayer(10))
    c.put(col & ~shift(col, 0, 1), False)
    return m


def seg7(c, x, y, ch, w=9, h=15, t=2, on=False, off=None):
    S = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc',
         '7': 'abc', '8': 'abcdefg', '9': 'abcfgd'}
    m2 = h // 2
    segs = {'a': (x + t, y, x + w - t, y + t), 'g': (x + t, y + m2 - t // 2, x + w - t, y + m2 + t - t // 2),
            'd': (x + t, y + h - t, x + w - t, y + h), 'f': (x, y + t, x + t, y + m2),
            'b': (x + w - t, y + t, x + w, y + m2), 'e': (x, y + m2 + 1, x + t, y + h - t),
            'c': (x + w - t, y + m2 + 1, x + w, y + h - t)}
    for k, r in segs.items():
        lit = k in S.get(ch, '')
        if lit:
            c.rect(*r, on)
        elif off is not None:
            c.rect(*r, off)


# ------------------------------------------------------------------ neko (v2 mascot)

from PIL import Image, ImageDraw, ImageFilter
from gen_neko_v2 import disc_grow, stamp as nstamp, MOUTH as NEKO_MOUTH, EYE as NEKO_EYE

SSK = 8


def ss_mask(fn, blur=0.0):
    img = Image.new('L', (W * SSK, H * SSK), 0)
    fn(ImageDraw.Draw(img), SSK)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur * SSK))
    a = np.asarray(img.resize((W, H), Image.BOX), np.float32) / 255.0
    return a >= 0.5


def ss_ell(cx, cy, rx, ry):
    return lambda d, k: d.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], fill=255)


def ss_union(*fns):
    def f(d, k):
        for fn in fns:
            fn(d, k)
    return f


def ss_poly(pts):
    return lambda d, k: d.polygon([(x * k, y * k) for x, y in pts], fill=255)


def ss_limb(pts, wd):
    def f(d, k):
        d.line([(x * k, y * k) for x, y in pts], fill=255, width=int(wd * k), joint='curve')
        for x, y in (pts[0], pts[-1]):
            d.ellipse([(x - wd / 2) * k, (y - wd / 2) * k, (x + wd / 2) * k, (y + wd / 2) * k], fill=255)
    return f


def rim(m, lw=2.0):
    return m & disc_grow(~m, lw)


def checker(c):
    return lambda x, y: ((x + y) % 2) == 1


def stamp_c(c, rows, cx, cy, flip=False):
    rr = [r for r in rows.strip('\n').split('\n')]
    if flip:
        rr = [r[::-1] for r in rr]
        rows = '\n'.join(rr)
    nstamp(c.ink, rows, int(round(cx)) - len(rr[0]) // 2, int(round(cy)) - len(rr) // 2)


EYE_HAPPY = """
...###...
.#######.
###...###
##.....##
#.......#
"""
EYE_WIDE = """
...###...
.#######.
.##oo####
##ooo####
##oo#####
#########
#########
#######o#
.#####oo.
.#######.
...###...
"""
MOUTH_OPEN = """
#......#......#
##....###....##
.##..##.##..##.
..####...####..
....#######....
.....#####.....
......###......
"""
MOUTH_SCREAM = """
...###...
.#######.
.#######.
#########
#########
####o####
.#ooooo#.
.#######.
...###...
"""


def neko_parts(c, hx, hy, u, ears='up'):
    head = ss_mask(ss_union(ss_ell(hx, hy - 0.02 * u, 0.96 * u, 0.78 * u), ss_ell(hx, hy + 0.2 * u, u, 0.66 * u)))
    if ears == 'up':
        L = [(hx - 0.88 * u, hy - 0.2 * u), (hx - 0.68 * u, hy - 1.1 * u), (hx - 0.2 * u, hy - 0.66 * u)]
        R = [(hx + 0.16 * u, hy - 0.7 * u), (hx + 0.6 * u, hy - 1.24 * u), (hx + 0.94 * u, hy - 0.2 * u)]
    else:
        L = [(hx - 0.92 * u, hy - 0.16 * u), (hx - 1.3 * u, hy - 0.92 * u), (hx - 0.36 * u, hy - 0.72 * u)]
        R = [(hx + 0.36 * u, hy - 0.72 * u), (hx + 1.3 * u, hy - 0.92 * u), (hx + 0.92 * u, hy - 0.16 * u)]
    ear_m = ss_mask(ss_union(ss_poly(L), ss_poly(R)), blur=0.12 * u)
    sil = ss_mask(lambda d, k: None) | head | ear_m
    sil = erode(erode(dilate(dilate(sil))))

    def shrink(P, s, towards):
        tx, ty = towards
        return [(tx + (x - tx) * s, ty + (y - ty) * s) for x, y in P]

    gL = shrink(L, 0.62, (L[1][0] * 0.35 + (L[0][0] + L[2][0]) * 0.325, L[1][1] * 0.35 + (L[0][1] + L[2][1]) * 0.325))
    gR = shrink(R, 0.62, (R[1][0] * 0.35 + (R[0][0] + R[2][0]) * 0.325, R[1][1] * 0.35 + (R[0][1] + R[2][1]) * 0.325))
    inner_ear = ss_mask(ss_union(ss_poly(gL), ss_poly(gR)), blur=0.05 * u) & ~head
    return sil, head, ear_m, inner_ear, (L, R)


def draw_part(c, m, lw=2.0):
    c.put(m, False)
    c.put(rim(m, lw), True)


def neko_head(c, hx, hy, u, eyes='normal', mouth='cat', ears='up', blush=False, lw=2.0):
    sil, head, ear_m, inner_ear, (L, R) = neko_parts(c, hx, hy, u, ears)
    draw_part(c, sil, lw)
    interior = sil & ~rim(sil, lw)
    c.put(inner_ear & interior & erode(interior), checker(c))
    shade = interior & ~shift(interior, -2, 0) & (c.xs > hx + 0.45 * u) & (c.ys > hy - 0.5 * u)
    c.put(shade, checker(c))
    x0, x1 = int(L[2][0] + 1), int(R[0][0])
    if x1 - x0 > 4:
        for x in range(x0, x1):
            col = np.nonzero(sil[:, x])[0]
            if not len(col):
                continue
            yt = col.min()
            c.ink[yt:yt + int(lw) + 1, x] = False
            off = [1, 2, 1, 0][(x - x0) % 4]
            c.ink[yt + off, x] = True
    fx = hx - 0.2 * u
    ey = hy + 0.22 * u
    exl, exr = fx - 0.4 * u, fx + 0.4 * u
    if eyes == 'normal':
        stamp_c(c, NEKO_EYE, exl, ey)
        stamp_c(c, NEKO_EYE, exr, ey)
    elif eyes == 'happy':
        stamp_c(c, EYE_HAPPY, exl, ey)
        stamp_c(c, EYE_HAPPY, exr, ey)
    elif eyes == 'wide':
        stamp_c(c, EYE_WIDE, exl - 1, ey - 2)
        stamp_c(c, EYE_WIDE, exr + 1, ey - 2)
    my = hy + 0.56 * u
    if mouth == 'cat':
        stamp_c(c, NEKO_MOUTH, fx, my)
    elif mouth == 'open':
        stamp_c(c, MOUTH_OPEN, fx, my + 1)
    elif mouth == 'scream':
        stamp_c(c, "#.#.#", fx, my - 5)
        stamp_c(c, MOUTH_SCREAM, fx, my + 2)
    if blush:
        for bx in (exl - 3, exr + 3):
            for k in range(3):
                c.line([(bx - 3 + k * 3, ey + 9), (bx - 1 + k * 3, ey + 6)], 1, True)
    wl = 2 if u >= 30 else 1
    for dy in (0.5 * u, 0.66 * u):
        yy = int(hy + dy)
        c.rect(hx - 1.08 * u, yy, hx - 0.74 * u, yy + wl, True)
        rx = np.nonzero(interior[yy])[0]
        if len(rx):
            c.rect(rx.max() - 0.3 * u, yy, rx.max() - 2, yy + wl, True)
    return sil


def neko_limb(c, pts, wd, paw=None, toes=None):
    m = ss_mask(ss_limb(pts, wd))
    if paw is not None:
        px, py, pr = paw
        m |= ss_mask(ss_ell(px, py, pr, pr))
    draw_part(c, m)
    if toes:
        px, py, pr = paw
        for a in toes:
            x0, y0 = px + math.cos(a) * (pr - 1.5), py + math.sin(a) * (pr - 1.5)
            x1, y1 = px + math.cos(a) * (pr - 4.5), py + math.sin(a) * (pr - 4.5)
            c.line([(x0, y0), (x1, y1)], 1, True)
    return m


def fade_to_white(c, m, strength):
    thr = (B8f[c.ys & 7, c.xs & 7] + 0.5) / 64.0
    c.ink &= ~(m & (strength > thr))


def calm_pool(c, cx, cy, rx, ry, nrays, phase, keep=None):
    d = np.hypot((c.xs + 0.5 - cx) / rx, (c.ys + 0.5 - cy) / ry)
    ramp = np.clip((1.0 - d) * 4.0, 0, 1)
    if keep is not None:
        ramp[keep] = 0
    fade_to_white(c, ramp > 0, ramp)
    a = np.arctan2(c.ys + 0.5 - cy, c.xs + 0.5 - cx)
    k = np.floor((a + math.pi + phase) / (2 * math.pi) * nrays).astype(int)
    rayband = (k % 2 == 0) & (d < 1.0) & (d > 0.25)
    c.put(rayband & (ramp >= 1), bayer(2))


def heart_bubble(c, cx, cy, r, tail):
    body = c.disc_mask(cx, cy, r)
    tails = [c.disc_mask(tx, ty, tr) for tx, ty, tr in tail]
    allm = body
    for t in tails:
        allm = allm | t
    c.put(disc_grow(allm, 2), False)
    for t in tails:
        c.put(t, False)
        c.put(rim(t, 1.5), True)
    c.put(body, False)
    c.put(rim(body, 2), True)
    s = r * 0.52
    hm = ss_mask(ss_union(ss_ell(cx - s * 0.5, cy - s * 0.25, s * 0.56, s * 0.56),
                          ss_ell(cx + s * 0.5, cy - s * 0.25, s * 0.56, s * 0.56),
                          ss_poly([(cx - s * 1.02, cy - s * 0.05), (cx + s * 1.02, cy - s * 0.05), (cx, cy + s * 1.05)])))
    c.put(hm, True)
    c.put(c.rect_mask(cx - s * 0.75, cy - s * 0.55, cx - s * 0.75 + 2, cy - s * 0.55 + 2), False)
    for a in (-2.2, -1.6, -1.0):
        c.line([(cx + math.cos(a) * (r + 4), cy + math.sin(a) * (r + 4)),
                (cx + math.cos(a) * (r + 8), cy + math.sin(a) * (r + 8))], 1, True)


# ------------------------------------------------------------------ WIN

def persp_floor(c, fy0, vx, cell, spread, v_a, v_b, lines=True):
    floor = c.rect_mask(0, fy0, W, H)
    t = np.clip((c.ys - fy0) / (H - fy0), 0, None)
    xf = vx + (c.xs - vx) / (1 + t * spread)
    col = np.floor((xf - vx) / cell)
    dy = np.clip(c.ys - fy0, 0, None)
    rowk = np.floor(np.sqrt(dy) * 1.1)
    tiles = ((col + rowk) % 2 == 0)
    c.put(floor & tiles, qtone(v_a))
    c.put(floor & ~tiles, qtone(v_b))
    if lines:
        xf2 = vx + (c.xs + 1 - vx) / (1 + t * spread)
        ev = floor & (np.floor((xf2 - vx) / cell) != col)
        eh = floor & (np.floor(np.sqrt(np.clip(dy - 1, 0, None)) * 1.1) != rowk)
        c.put(ev | eh, True)
    return floor


def open_door(c, DCX, DCY, DRX, DRY, TH, FLOOR):
    sx = DRX / DRY

    face = c.ellipse_mask(DCX, DCY, DRX, DRY)
    side = (c.ellipse_mask(DCX + TH, DCY, DRX, DRY) | (c.rect_mask(DCX, DCY - DRY, DCX + TH, DCY + DRY)
            & c.ellipse_mask(DCX + TH / 2, DCY, DRX + TH, DRY))) & ~face
    body = face | side
    c.put(shift(body, 14, 0) & ~body & (c.ys > FLOOR + 2) & (c.ys < FLOOR + 16), bayer(14))
    angs = [-1.2, -0.6, 0.0, 0.6, 1.2]
    c.put(dilate(side), True)
    c.put(side, OR(hlines(2), bayer(9)))
    c.put(side & ~shift(side, -3, 0), True)
    c.put(side & ~shift(side, 1, 0), False)
    for a in angs:
        by = int(DCY + math.sin(a) * DRY * 0.93)
        half = DRX * math.sqrt(max(0, 1 - ((by - DCY) / DRY) ** 2))
        bx0 = int(DCX + TH + half - 3)
        L = 26
        c.rect(bx0 + 4, by + 5, bx0 + L + 4, by + 9, bayer(14))
        c.rect(bx0, by - 6, bx0 + L + 1, by + 7, True)
        c.rect(bx0, by - 5, bx0 + L - 1, by + 6, False)
        c.rect(bx0, by + 1, bx0 + L - 1, by + 6, bayer(5))
        c.rect(bx0, by + 4, bx0 + L - 1, by + 6, bayer(11))
        c.rect(bx0, by - 4, bx0 + L - 1, by - 3, bayer(2))
        c.rect(bx0 + L - 4, by - 6, bx0 + L - 3, by + 7, True)
        c.rect(bx0 + L - 2, by - 4, bx0 + L, by + 5, bayer(6))
    c.put(dilate(face) & ~face, True)
    c.put(face, False)
    c.put(face & ~shift(face, -3, 0), bayer(5))
    c.put(c.ellipse_mask(DCX, DCY, DRX * 0.9, DRY * 0.9) & ~c.ellipse_mask(DCX, DCY, DRX * 0.9 - 2, DRY * 0.9 - 2), True)
    plate = c.ellipse_mask(DCX, DCY, DRX * 0.9 - 2, DRY * 0.9 - 2)
    c.put(plate & ~shift(plate, -3, 0), bayer(4))
    for a in angs + [math.pi - x for x in angs]:
        ex, ey = DCX + math.cos(a) * DRX * 0.78, DCY + math.sin(a) * DRY * 0.78
        c.line([(DCX, DCY), (ex, ey)], 5, True)
        c.line([(DCX, DCY), (ex, ey)], 1, False)
        c.put(c.ellipse_mask(ex, ey, 3, 4), True)
        c.put(c.ellipse_mask(ex - 0.5, ey - 1, 1.2, 1.5), False)
    gr = 18
    gear = c.ellipse_mask(DCX, DCY, gr * sx * 1.8, gr)
    for k in range(12):
        a = k / 12 * math.tau
        gear |= c.ellipse_mask(DCX + math.cos(a) * (gr + 2) * sx * 1.8, DCY + math.sin(a) * (gr + 2), 2, 2.6)
    c.put(dilate(gear), False)
    c.put(gear, True)
    c.put(c.ellipse_mask(DCX, DCY, (gr - 4) * sx * 1.8, gr - 4) & ~c.ellipse_mask(DCX, DCY, (gr - 5) * sx * 1.8, gr - 5), False)
    c.put(c.ellipse_mask(DCX, DCY, 6 * sx * 1.8, 7), False)
    c.put(c.ellipse_mask(DCX, DCY, 4 * sx * 1.8, 5), True)
    c.put(c.ellipse_mask(DCX - 1, DCY - 2, 1, 1.4), False)
    for k in range(18):
        a = k / 18 * math.tau + 0.2
        px, py = DCX + math.cos(a) * DRX * 0.95, DCY + math.sin(a) * DRY * 0.95
        c.put(c.disc_mask(px, py, 1.2), True)
    for hy in (DCY - 76, DCY + 58):
        c.rect(0, hy, 14, hy + 18, True)
        c.rect(1, hy + 1, 12, hy + 17, bayer(3))
        c.rect(1, hy + 1, 12, hy + 2, False)
        c.rect(9, hy + 1, 12, hy + 17, bayer(9))
        c.rect(4, hy - 4, 9, hy + 22, True)
        c.rect(5, hy - 3, 8, hy + 21, bayer(2))
        c.rect(5, hy - 3, 6, hy + 21, False)


def scene_win():
    c = Canvas(W, H, 0)
    f16 = load_font(16)
    LX, LY = 118, 200
    ray, dist = rays(LX, LY, 18, 0.17)
    glow = np.clip(1 - dist / 260, 0, 1)
    FLOOR = 180

    def wall_tone(base):
        v = base + np.where(ray, -0.25, 0.38) + (1 - glow) * 0.35
        return qtone(np.minimum(v, 0.75), 4)

    c.rect(0, 0, W, FLOOR, wall_tone(0.2))
    opens = {(2, 3): 'coins', (5, 1): 'dark', (8, 4): 'coins', (10, 2): 'dark', (0, 1): 'coins', (7, 0): 'dark'}
    deposit_boxes(c, 46, -8, 406, 118, 30, 21, lambda b: wall_tone(0.0 + b), open_set=set(opens))
    for (i, j), kind in opens.items():
        x, y = 46 + i * 30, -8 + j * 21
        if kind == 'coins':
            coin(c, x + 10, y + 14, 4, False)
            coin(c, x + 19, y + 15, 4, False)
            sparkle(c, x + 22, y + 8, 3)
    c.rect(46, 118, W, 122, True)
    c.rect(46, 119, W, 120, False)
    c.rect(46, 122, W, FLOOR, wall_tone(0.30))
    wain = c.rect_mask(46, 122, W, FLOOR)
    for px in range(46, W, 44):
        c.put(wain & c.rect_mask(px + 4, 127, px + 40, FLOOR - 5) & ~c.rect_mask(px + 5, 128, px + 39, FLOOR - 6), True)
        c.put(c.rect_mask(px + 5, 128, px + 39, 129), False)

    SH = 150
    for gx in [150, 212, 276, 338]:
        gold_bar(c, gx, SH - 15, 26, 8, 5)
        gold_bar(c, gx + 26, SH - 15, 26, 8, 5)
        gold_bar(c, gx + 13, SH - 28, 26, 8, 5)
    cash_stack(c, 54, SH - 23, 28, 9, 14)
    cash_stack(c, 92, SH - 23, 28, 9, 14)
    c.rect(46, SH, W, SH + 6, True)
    c.rect(46, SH + 1, W, SH + 5, bayer(3))
    c.rect(46, SH + 1, W, SH + 2, False)
    c.rect(46, SH + 6, W, SH + 10, bayer(12))
    for bx in range(64, W, 58):
        c.poly([(bx, SH + 5), (bx + 9, SH + 5), (bx + 2, SH + 18), (bx, SH + 18)], True)
        c.poly([(bx + 1, SH + 6), (bx + 6, SH + 6), (bx + 1, SH + 14)], bayer(4))

    pool = np.clip(1 - np.hypot((c.xs - 118) / 130, (c.ys - 214) / 36), 0, 1)
    persp_floor(c, FLOOR, LX, 26, 2.4, 0.78 - pool * 0.7, 0.62 - pool * 0.7)
    c.rect(0, FLOOR, W, FLOOR + 2, True)
    c.rect(0, FLOOR + 2, W, FLOOR + 4, bayer(12))

    pil = c.rect_mask(0, 0, 46, FLOOR)
    c.put(pil, True)
    bm = brick(16, 8)(c.xs, c.ys)
    c.put(pil & ~bm, bayer(10))
    c.put(pil & ~bm & shift(bm, 0, 1), bayer(5))
    c.rect(36, 0, 48, FLOOR + 1, True)
    c.rect(38, 0, 46, FLOOR, bayer(3))
    c.rect(38, 0, 39, FLOOR, False)
    c.rect(43, 0, 46, FLOOR, bayer(9))

    open_door(c, 14, 128, 30, 94, 12, FLOOR)

    NX, NG = 112, 236
    fig = NB.render('rich', face='happy', width=96)
    NB.backdrop(c, fig, NX, NG, 0.68, 6, 18)
    pool = c.ellipse_mask(124, 232, 110, 26)
    c.put(pool, bayer(3))
    c.put(c.ellipse_mask(124, 232, 94, 20), False)
    c.put(dilate(pool) & ~pool & (c.ys > FLOOR + 4), bayer(10))
    for cx_, cy_ in [(12, 234), (24, 238), (126, 238), (106, 232), (240, 226), (116, 222)]:
        coin(c, cx_, cy_, 5)
    gold_pyramid(c, 130, 220, 3, 32, 12, 7)
    cash_stack(c, 46, 208, 30, 10, 14)
    cash_stack(c, 80, 210, 30, 10, 14)
    cash_stack(c, 62, 194, 30, 10, 14)
    money_bag(c, 24, 214, 18, f16)
    diamond(c, 120, 224, 11)
    for cx_, cy_ in [(58, 238), (92, 236), (140, 236), (230, 236), (212, 238)]:
        coin(c, cx_, cy_, 5)

    shadow = c.ellipse_mask(NX, NG - 2, 40, 7)
    c.put(shadow, bayer(14))
    nsil = NB.place(c, fig, NX, NG, halo=2)
    near = disc_grow(nsil, 5)
    heart_bubble(c, 194, 90, 13, [(178, 106, 3.2), (171, 113, 2.2)])
    for bxx, byy, a in [(30, 80, 0.5), (190, 136, -0.6), (212, 176, 0.2), (40, 120, -0.3), (196, 196, 0.9)]:
        if not near[min(H - 1, byy), min(W - 1, bxx)]:
            bill(c, bxx, byy, a, 18, 9)
    for sx, sy, r in [(34, 100, 6), (182, 150, 4), (218, 112, 5), (200, 70, 3), (24, 150, 4), (166, 60, 3)]:
        if not near[min(H - 1, sy), min(W - 1, sx)]:
            sparkle(c, sx, sy, r, r > 4)
    NB.repaste(c)
    return c


# ------------------------------------------------------------------ TIME'S UP

def vault_door(c, cx, cy, r):
    c.disc(cx + 6, cy + 6, r + 10, bayer(15))
    c.disc(cx, cy, r + 10, True)
    rimm = c.ring_mask(cx, cy, r + 1, r + 9)
    c.put(rimm, bayer(5))
    c.put(rimm & ~shift(c.disc_mask(cx, cy, r + 9), -4, -4), bayer(11))
    c.put(c.ring_mask(cx, cy, r + 7, r + 9) & ((c.xs - cx) + (c.ys - cy) < -r * 0.5), False)
    for k in range(16):
        a = k / 16 * math.tau
        c.disc(cx + math.cos(a) * (r + 5), cy + math.sin(a) * (r + 5), 1.6, True)
    c.disc(cx, cy, r, True)
    face = c.disc_mask(cx, cy, r - 1)
    c.put(face, bayer(2))
    c.put(face & ~shift(face, -10, -10), bayer(6))
    c.put(face & ~shift(face, -4, -4), bayer(11))
    c.put(face & ~shift(face, 1, 1), False)
    for k in range(10):
        a = k / 10 * math.tau + 0.3
        rivet(c, cx + math.cos(a) * (r - 7), cy + math.sin(a) * (r - 7), 2.5)
    c.disc(cx, cy, r - 13, True)
    inner = c.disc_mask(cx, cy, r - 14)
    c.put(inner, bayer(1))
    c.put(inner & ~shift(inner, -5, -5), bayer(6))
    dr = r - 18
    c.disc(cx, cy, dr, True)
    c.disc(cx, cy, dr - 1, False)
    for k in range(50):
        a = k / 50 * math.tau
        L = 5 if k % 5 == 0 else 2
        c.line([(cx + math.cos(a) * (dr - 1), cy + math.sin(a) * (dr - 1)),
                (cx + math.cos(a) * (dr - 1 - L), cy + math.sin(a) * (dr - 1 - L))], 1, True)
    c.disc(cx, cy, 10, True)
    c.disc(cx, cy, 8, bayer(9))
    c.disc(cx - 2, cy - 2, 3, bayer(3))
    c.disc(cx - 3, cy - 3, 1.2, False)
    for a in [math.pi / 2 + 0.35, math.pi * 7 / 6 + 0.35, -math.pi / 6 + 0.35]:
        ex, ey = cx + math.cos(a) * (dr + 8), cy + math.sin(a) * (dr + 8)
        sx, sy = cx + math.cos(a) * 9, cy + math.sin(a) * 9
        c.line([(sx, sy), (ex, ey)], 6, True)
        c.line([(sx, sy), (ex, ey)], 2, False)
        c.disc(ex, ey, 5.5, True)
        c.disc(ex, ey, 4, bayer(3))
        c.disc(ex - 1.5, ey - 1.5, 1.3, False)


def gate(c, x0, x1, y_bot):
    for tx, lvl in [(x0 - 10, 6), (x1, 10)]:
        c.rect(tx, 0, tx + 10, H, True)
        c.rect(tx + 1, 0, tx + 9, H, bayer(lvl))
        c.rect(tx + 2, 0, tx + 3, H, False)
        c.rect(tx + 4, 0, tx + 6, H, True)
        for yy in range(6, H, 16):
            screw(c, tx + 5, yy, 2, 0.8)
    c.rect(x0, 0, x1, y_bot, bayer(15))
    for bx in range(x0 + 3, x1 - 2, 10):
        c.rect(bx - 1, 0, bx + 6, y_bot, True)
        c.rect(bx + 1, 0, bx + 4, y_bot, bayer(3))
        c.rect(bx + 1, 0, bx + 2, y_bot, False)
        c.rect(bx + 3, 0, bx + 4, y_bot, bayer(9))
    for yy in range(8, y_bot - 14, 16):
        c.rect(x0, yy, x1, yy + 7, True)
        c.rect(x0, yy + 1, x1, yy + 2, False)
        c.rect(x0, yy + 2, x1, yy + 5, bayer(5))
        c.rect(x0, yy + 4, x1, yy + 6, bayer(10))
        for bx in range(x0 + 5, x1 - 2, 10):
            c.disc(bx + 0.5, yy + 3.5, 1.5, True)
            c.put(c.rect_mask(bx, yy + 3, bx + 1, yy + 4), False)
    c.rect(x0 - 2, y_bot - 16, x1 + 2, y_bot + 1, True)
    rail = c.rect_mask(x0, y_bot - 14, x1, y_bot - 1)
    c.put(rail, lambda x, y: ((x + y) // 6) % 2 == 0)
    c.rect(x0, y_bot - 15, x1, y_bot - 14, False)
    c.rect(x0 - 2, y_bot + 1, x1 + 2, y_bot + 5, bayer(14))


def bell(c, cx, cy, r):
    c.rect(cx - 6, cy - r - 12, cx + 7, cy - r + 2, True)
    c.rect(cx - 5, cy - r - 11, cx + 6, cy - r + 1, bayer(4))
    c.rect(cx - 5, cy - r - 11, cx + 6, cy - r - 10, False)
    screw(c, cx, cy - r - 6, 2, 0.4)
    c.disc(cx + 5, cy + 5, r + 1, bayer(15))
    dome = c.disc_mask(cx, cy, r)
    c.put(dilate(dilate(dome)), False)
    c.put(dilate(dome) & ~dome, True)
    c.put(dome, bayer(1))
    c.put(dome & ~shift(dome, -7, -7), bayer(6))
    c.put(dome & ~shift(dome, -3, -3), bayer(11))
    c.put(c.ring_mask(cx, cy, r * 0.64, r * 0.74), True)
    c.put(c.ellipse_mask(cx - r * 0.38, cy - r * 0.42, r * 0.26, r * 0.14) & dome, False)
    c.put(c.ellipse_mask(cx - r * 0.12, cy - r * 0.2, r * 0.07, r * 0.07) & dome, False)
    c.disc(cx, cy, 4.5, True)
    c.disc(cx, cy, 3, bayer(4))
    c.disc(cx - 1, cy - 1, 1.1, False)
    hx, hy = cx + r + 5, cy + r * 0.1
    c.line([(cx + 4, cy + r + 5), (hx - 2, hy + 3)], 4, True)
    c.line([(cx + 4, cy + r + 5), (hx - 2, hy + 3)], 1, False)
    c.disc(hx - 1, hy, 5, True)
    c.disc(hx - 1, hy, 3.5, bayer(4))
    c.disc(hx - 2, hy - 1, 1.2, False)
    c.rect(cx - 1, cy + r + 1, cx + 9, cy + r + 9, True)
    c.rect(cx, cy + r + 2, cx + 8, cy + r + 8, bayer(6))
    c.rect(cx, cy + r + 2, cx + 8, cy + r + 3, False)


def timer_box(c, x, y, s='0000'):
    w, h = 72, 32
    c.rect(x + 4, y + 4, x + w + 4, y + h + 4, bayer(15))
    c.rect(x - 1, y - 1, x + w + 1, y + h + 1, False)
    c.rect(x, y, x + w, y + h, True)
    c.rect(x + 1, y + 1, x + w - 1, y + h - 1, bayer(3))
    c.rect(x + 1, y + 1, x + w - 1, y + 2, False)
    c.rect(x + w - 4, y + 2, x + w - 1, y + h - 1, bayer(9))
    c.rect(x + 5, y + 5, x + w - 6, y + h - 5, True)
    for i, ch in enumerate(s):
        dx = x + 10 + i * 13 + (5 if i >= 2 else 0)
        seg7(c, dx, y + 8, ch, 9, 16, 2, False)
    c.rect(x + 34, y + 12, x + 36, y + 14, False)
    c.rect(x + 34, y + 19, x + 36, y + 21, False)
    screw(c, x + 3, y + h // 2, 1.5)


def white_hand(c, x, y, s=1.0, flip=1, rot=0.0, spread=0.18):
    ca, sa = math.cos(rot), math.sin(rot)

    def P(dx, dy):
        return (x + (dx * ca - dy * sa) * flip, y + (dx * sa + dy * ca))

    palm = c.poly_mask([P(-6 * s, -4 * s), P(6 * s, -4 * s), P(7 * s, 5 * s), P(3 * s, 9 * s), P(-5 * s, 9 * s),
                        P(-7 * s, 4 * s)])
    fingers = []
    for k, L in enumerate([8, 10, 10, 8]):
        bx = (-4.8 + k * 3.2) * s
        ang = (k - 1.5) * spread
        tip = (bx + math.sin(ang) * L * s, -4 * s - math.cos(ang) * L * s)
        fingers.append(c.mask(lambda d, a=P(bx, -2 * s), b=P(*tip): d.line([a, b], fill=1, width=max(3, int(round(3 * s))))))
    thumb = c.mask(lambda d: d.line([P(6 * s, 4 * s), P(12 * s, -2 * s)], fill=1, width=max(3, int(round(3.4 * s)))))
    allm = palm | thumb
    for f in fingers:
        allm |= f
    c.put(dilate(dilate(allm)) & ~dilate(allm), False)
    for f in fingers + [thumb]:
        c.put(dilate(f), True)
        c.put(f, False)
    c.put(dilate(palm), True)
    c.put(palm | (thumb & ~dilate(palm)), False)
    c.put(thumb & dilate(palm) & ~palm, False)
    c.put(palm & ~shift(palm, -3, -3), bayer(6))
    for f in fingers:
        c.put(f & ~shift(f, -1, 0), bayer(6))
    return allm


def flashlight(c, x, y):
    cone = c.poly_mask([(x + 30, y - 4), (x + 104, y - 16), (x + 110, y + 12), (x + 30, y + 5)])
    fade = np.clip((c.xs - x - 30) / 80, 0, 1)
    c.put(cone & (c.ys > 200), qtone(0.0 + fade * 0.45, 4))
    body = c.poly_mask(rot_rect(x + 12, y + 1, 24, 8, -0.05))
    head = c.poly_mask(rot_rect(x + 27, y, 8, 12, -0.05))
    m = body | head
    c.put(shift(m, 2, 3) & ~m, bayer(15))
    c.put(dilate(m), True)
    c.put(body, bayer(6))
    c.put(body & ~shift(body, 0, 1), False)
    c.put(body & (c.xs % 4 == 0), True)
    c.put(head, bayer(2))
    c.put(head & ~shift(head, 0, 1), False)
    c.rect(x + 30, y - 5, x + 32, y + 6, False)


def crowbar(c, pts):
    c.line(pts, 6, True)
    c.line(pts, 4, bayer(3))
    c.line([(p[0], p[1] - 1) for p in pts], 1, False)


def scene_timeup():
    c = Canvas(W, H, 1)
    BX, BY = 24, 90
    ray, dist = rays(BX, BY, 18, 0.18)
    beam = ray & (dist > 20)
    fall = np.clip(1 - dist / 340, 0, 1)
    FLOOR = 198

    def wall_v(extra=0.0):
        v = np.where(beam, 0.12 + (1 - fall) * 0.5, 0.82) + extra - np.clip(1 - dist / 70, 0, 1) * 0.3
        return v

    wallm = c.rect_mask(0, 0, W, FLOOR)
    bm = brick(26, 11)(c.xs, c.ys)
    c.put(wallm, True)
    c.put(wallm & ~bm, qtone(wall_v(), 4))
    c.put(wallm & ~bm & shift(bm, 0, 1), qtone(wall_v(-0.4), 4))
    c.put(wallm & ~bm & shift(bm, 0, -1), qtone(wall_v(0.25), 4))

    persp_floor(c, FLOOR, 150, 30, 2.5, np.where(beam, 0.5, 1.0), np.where(beam, 0.38, 0.88))
    c.rect(0, FLOOR, W, FLOOR + 3, True)
    c.rect(0, FLOOR + 3, W, FLOOR + 4, bayer(6))

    VX, VY, VR = 168, 146, 50
    fx0, fy0, fx1 = VX - VR - 22, VY - VR - 22, VX + VR + 22
    c.rect(fx0 - 1, fy0 - 1, fx1 + 1, FLOOR, True)
    fr = c.rect_mask(fx0 + 1, fy0 + 1, fx1 - 1, FLOOR)
    c.put(fr, bayer(10))
    c.put(fr & ((c.ys - fy0) % 4 == 0), True)
    c.put(fr & ~shift(fr, 1, 1), bayer(4))
    for sx in (fx0 + 6, fx1 - 6):
        for sy in range(fy0 + 8, FLOOR, 18):
            rivet(c, sx, sy, 2)
    vault_door(c, VX, VY, VR)
    gate(c, VX - VR - 18, VX + VR + 18, 118)
    for sx in (VX - VR - 26, VX + VR + 26):
        for k in range(4):
            c.line([(sx - 9 + k * 6, 122 + k % 2 * 2), (sx - 12 + k * 6, 130 + k % 2 * 3)], 1, False)
    c.put(c.rect_mask(VX - VR - 20, 123, VX + VR + 20, 126), bayer(14))
    for k, dy in enumerate([96, 104]):
        c.line([(VX - VR - 38, dy), (VX - VR - 30, dy)], 2, False)
        c.line([(VX + VR + 30, dy), (VX + VR + 38, dy)], 2, False)

    timer_box(c, 158, 70)
    flashlight(c, 158, 214)
    crowbar(c, [(176, 238), (226, 228), (231, 222)])
    bag = money_bag(c, 134, 222, 13, load_font(16))
    for cx_, cy_ in [(152, 234), (162, 238), (118, 238)]:
        coin(c, cx_, cy_, 5)
    bill(c, 142, 206, 0.35, 18, 9)
    bill(c, 204, 212, -0.3, 18, 9)

    bell(c, BX, BY, 14)
    for a, r0, r1 in [(-2.4, 22, 30), (-1.9, 22, 31), (-1.4, 22, 30), (2.6, 21, 28)]:
        p0 = (BX + math.cos(a) * r0, BY + math.sin(a) * r0)
        p1 = (BX + math.cos(a) * r1, BY + math.sin(a) * r1)
        c.line([p0, p1], 4, False)
        c.line([p0, p1], 2, True)
    NX, NG = 96, 236
    fig = NB.render('panic', width=96, face_props=False)
    NB.backdrop(c, fig, NX, NG, 0.7, 6, 18)
    c.put(c.ellipse_mask(NX, NG - 2, 52, 5), bayer(14))
    nsil = NB.place(c, fig, NX, NG, halo=2)
    J = NG - fig['G'] + fig['J']
    for side in (-1, 1):
        for k in range(3):
            x0 = NX + side * (52 + k * 5)
            y0 = J - 62 + k * 12
            pts = [(x0, y0), (x0 + side * 3, y0 + 3), (x0, y0 + 6), (x0 + side * 3, y0 + 9)]
            lm = c.mask(lambda d, q=pts: d.line(q, fill=1, width=2))
            c.put(disc_grow(lm, 1.5) & ~nsil, False)
            c.put(lm & ~nsil, True)
    for sx, sy, s_ in [(NX + 62, J - 70, 1.3), (NX - 60, J - 62, 1.2), (NX + 64, J - 30, 1.0), (NX - 62, J - 26, 0.9)]:
        sweat(c, sx, sy, s_)
    NB.repaste(c)
    return c


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    out = os.environ.get('END_OUT_DIR') or os.path.join(root, 'source', 'images')
    os.makedirs(out, exist_ok=True)
    win = scene_win()
    win.save(os.path.join(out, 'end-win.png'))
    tu = scene_timeup()
    tu.save(os.path.join(out, 'end-timeup.png'))
    for name, cv in [('win', win), ('timeup', tu)]:
        cv.preview(os.path.join(out, f'end-{name}@3x.png'), 3)
    if PREVIEW:
        for name, cv in [('win', win), ('timeup', tu)]:
            g = Canvas(W, H, 0)
            g.ink = cv.ink.copy()
            g.put(g.rect_mask(40, 6, 360, 62) & (((g.xs + g.ys) % 8) < 2), False)
            g.rect(230, 66, 398, 238, True)
            g.rect(233, 69, 395, 235, False)
            g.preview(os.path.join(PREVIEW, f'end-{name}-guide@3x.png'), 3)


if __name__ == '__main__':
    main()
