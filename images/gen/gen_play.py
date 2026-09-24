import math
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdart import (Canvas, bayer, tone, brushed, vlines, hlines, OR, AND, NOT,
                   dilate, erode, load_font, B4)

OUT = 'source/images'
PREV = os.environ.get('PREV')

CX, CY = 122, 120


def sprite(c, rows, x, y):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            xx, yy = x + i, y + j
            if ch == '.' or not (0 <= xx < c.w and 0 <= yy < c.h):
                continue
            if ch == '#':
                v = True
            elif ch == 'o':
                v = False
            else:
                lv = {'+': 4, ':': 8, '=': 12}[ch]
                v = B4[yy & 3, xx & 3] < lv
            c.ink[yy, xx] = v
            if c.alpha is not None:
                c.alpha[yy, xx] = True


def rrect_mask(c, x0, y0, x1, y1, r):
    m = c.rect_mask(x0, y0, x1, y1)
    for cx, cy, sx, sy in ((x0 + r, y0 + r, -1, -1), (x1 - r, y0 + r, 1, -1),
                           (x0 + r, y1 - r, -1, 1), (x1 - r, y1 - r, 1, 1)):
        q = ((c.xs + 0.5 - cx) * sx > 0) & ((c.ys + 0.5 - cy) * sy > 0)
        m &= ~(q & ~c.disc_mask(cx, cy, r))
    return m


def polar(c):
    dx = c.xs + 0.5 - CX
    dy = c.ys + 0.5 - CY
    return np.hypot(dx, dy), np.arctan2(dy, dx), dx, dy


def bolt(c, x, y, r=3.0):
    m = c.disc_mask(x, y, r)
    obj(c, m, fill=False, shade=9, shw=1, sh=1, sh_level=16)
    c.put(m & ~c.disc_mask(x - 0.8, y - 0.8, r), bayer(9))
    c.put(c.rect_mask(int(x) - 1, int(y), int(x) + 2, int(y) + 1), True)


def small_rivet(c, x, y):
    m = c.disc_mask(x, y, 2.5)
    obj(c, m, fill=False, shade=8, shw=1, sh=2, sh_level=12)
    c.put(c.rect_mask(int(x), int(y), int(x) + 1, int(y) + 1) & ~c.disc_mask(x - 1, y - 1, 0.1), False)


def tiny_screw(c, x, y):
    sprite(c, ['.###.', '#oo:#', '#####', '#::=#', '.###.'], x - 2, y - 2)


def door_face(c):
    face = c.rect_mask(8, 8, 392, 232)
    shade = np.clip(0.03 + 0.05 * (c.ys - 8) / 224.0 + 0.02 * (c.xs / 400.0), 0, 1)
    rng = np.random.default_rng(7)
    streak = rng.random(8192)
    base = tone(shade)(c.xs, c.ys)
    s = streak[(c.ys * 131 + (c.xs // 53) * 7) % 8192]
    str_ = (s > 0.978) & ((c.xs % 2) == (c.ys % 2))
    s2 = streak[(c.ys * 57 + (c.xs // 19) * 13 + 99) % 8192]
    str2 = (s2 > 0.992)
    wear = (rng.random(c.ink.shape) > 0.9975)
    c.ink[face] = (base | str_ | str2 | wear)[face]


def shift(m, dx, dy):
    out = np.zeros_like(m)
    h, w = m.shape
    ys0, ys1 = max(0, dy), h + min(0, dy)
    xs0, xs1 = max(0, dx), w + min(0, dx)
    out[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def solid(c, m, base=5, lo=12, hi=False, sh=3, sh_level=11, outline=True):
    if sh:
        c.put(shift(m, sh, sh) & ~m, bayer(sh_level))
    if outline:
        c.put(dilate(m) & ~m, True)
    c.put(m, bayer(base))
    c.put(m & ~shift(m, -1, -1) & ~shift(m, -2, -2), bayer(lo))
    c.put(m & ~shift(m, 1, 1), hi)


def seam_h(c, y, x0, x1):
    c.rect(x0, y, x1, y + 1, True)
    c.rect(x0, y + 1, x1, y + 2, False)
    c.rect(x0, y - 1, x1, y, bayer(6))


def seam_v(c, x, y0, y1):
    c.rect(x, y0, x + 1, y1, True)
    c.rect(x + 1, y0, x + 2, y1, False)
    c.rect(x - 1, y0, x, y1, bayer(6))


def jamb(c):
    c.frame(0, 0, 400, 240, 8, True)
    c.put(c.rect_mask(2, 2, 398, 6) & ~c.rect_mask(394, 0, 400, 240), bayer(10))
    c.put(c.rect_mask(2, 2, 6, 238) & ~c.rect_mask(0, 234, 400, 240), bayer(10))
    c.put(c.rect_mask(2, 2, 398, 3) & ~c.rect_mask(397, 0, 400, 240), bayer(5))
    c.put(c.rect_mask(2, 2, 3, 237), bayer(5))
    c.put(c.rect_mask(394, 3, 398, 238), bayer(14))
    c.put(c.rect_mask(3, 234, 398, 238), bayer(14))
    c.rect(7, 7, 393, 8, bayer(8))
    c.rect(7, 7, 8, 233, bayer(8))
    c.rect(8, 8, 392, 9, False)
    c.rect(8, 8, 9, 232, False)
    c.rect(8, 231, 392, 232, bayer(12))
    c.rect(391, 8, 392, 232, bayer(12))
    for x in range(20, 400, 24):
        jamb_bolt(c, x, 4)
        jamb_bolt(c, x, 236)
    for y in range(28, 230, 24):
        jamb_bolt(c, 4, y)
        jamb_bolt(c, 396, y)


def jamb_bolt(c, x, y):
    sprite(c, ['.##.', '#oo#', '#o:#', '.##.'], x - 2, y - 2)


def channel(c):
    x0, y0, x1, y1 = 216, 12, 386, 228
    c.put(shift(c.rect_mask(x0, y0, x1, y1), 2, 2) & ~c.rect_mask(x0, y0, x1, y1), bayer(11))
    c.rect(x0, y0, x1, y1, True)
    lip = c.rect_mask(x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    c.put(lip, bayer(6))
    c.put(lip & ((c.xs < x0 + 3) | (c.ys < y0 + 3)), bayer(2))
    c.put(lip & ((c.xs >= x1 - 3) | (c.ys >= y1 - 3)) & ~((c.xs < x0 + 3) & (c.ys >= y1 - 3 - (c.xs - x0))) & ~((c.ys < y0 + 3) & (c.xs >= x1 - 3 - (c.ys - y0))), bayer(11))
    c.put(lip & ((c.xs == x0 + 1) | (c.ys == y0 + 1)) & (c.xs < x1 - 2) & (c.ys < y1 - 2), False)
    r0x, r0y, r1x, r1y = x0 + 5, y0 + 5, x1 - 5, y1 - 5
    c.rect(r0x, r0y, r1x, r1y, True)
    rec = c.rect_mask(r0x + 1, r0y + 1, r1x - 1, r1y - 1)
    fill = OR(bayer(9), AND(vlines(6, 1), NOT(hlines(2))))
    c.put(rec, fill)
    c.put(rec & ((c.ys < r0y + 3) | (c.xs < r0x + 3)), bayer(14))
    c.put(rec & (((c.ys >= r0y + 3) & (c.ys < r0y + 5) & (c.xs >= r0x + 3)) | ((c.xs >= r0x + 3) & (c.xs < r0x + 5) & (c.ys >= r0y + 3))), bayer(12))
    c.put(rec & ((c.ys == r1y - 2) | (c.xs == r1x - 2)) & (c.xs > r0x + 1) & (c.ys > r0y + 1), False)
    c.put(rec & ((c.ys == r1y - 3) | (c.xs == r1x - 3)) & (c.xs > r0x + 2) & (c.ys > r0y + 2), bayer(4))
    for yy in (84, 152):
        for xx in (r0x + 3, r1x - 4):
            bracket(c, xx, yy)
    for xx, yy in ((x0 + 3, y0 + 3), (x1 - 4, y0 + 3), (x0 + 3, y1 - 4), (x1 - 4, y1 - 4)):
        sprite(c, ['.#.', '#o#', '.#.'], xx - 1, yy - 1)


def bracket(c, x, y):
    c.rect(x - 3, y - 2, x + 3, y + 3, True)
    c.rect(x - 2, y - 1, x + 2, y + 2, bayer(4))
    c.rect(x - 2, y - 1, x + 2, y, False)
    c.put(c.rect_mask(x - 1, y, x, y + 1), True)


def timer_bezel(c):
    x0, y0, x1, y1 = 14, 10, 129, 55
    c.rect(x0 + 3, y0 + 3, x1 + 3, y1 + 3, bayer(10))
    m = rrect_mask(c, x0, y0, x1, y1, 3)
    c.put(m, True)
    band = rrect_mask(c, x0 + 1, y0 + 1, x1 - 1, y1 - 1, 2)
    c.put(band, bayer(7))
    c.put(band & (c.ys < y0 + 3), bayer(2))
    c.put(band & (c.xs < x0 + 3), bayer(3))
    c.put(band & (c.ys >= y1 - 3), bayer(12))
    c.put(band & (c.xs >= x1 - 3), bayer(11))
    c.put(band & (c.ys == y0 + 1) & (c.xs < x1 - 3), False)
    c.put(band & (c.xs == x0 + 1) & (c.ys < y1 - 3), False)
    c.rect(x0 + 5, y0 + 5, x1 - 5, y1 - 5, True)
    c.rect(x0 + 6, y0 + 6, x1 - 6, y1 - 6, bayer(14))
    c.rect(x0 + 6, y1 - 7, x1 - 6, y1 - 6, bayer(8))
    c.rect(x1 - 7, y0 + 6, x1 - 6, y1 - 6, bayer(8))
    c.rect(22, 18, 121, 47, False)
    for sx, sy in ((x0 + 3, y0 + 3), (x1 - 4, y0 + 3), (x0 + 3, y1 - 4), (x1 - 4, y1 - 4)):
        tiny_screw_small(c, sx, sy)


def tiny_screw_small(c, x, y):
    sprite(c, ['.#.', '#o#', '.#.'], x - 1, y - 1)


def dial_area(c):
    d, ang, dx, dy = polar(c)
    LA = math.atan2(-0.78, -0.62)
    upl = np.cos(ang - LA)
    sh = np.hypot(c.xs + 0.5 - CX - 4, c.ys + 0.5 - CY - 4) <= 79.5
    c.put(sh & (d > 78.5), bayer(11))
    c.put((d > 77.2) & (d <= 78.6), True)

    outer = (d > 74.8) & (d <= 77.2)
    c.put(outer, tone(np.clip(0.45 - 0.5 * upl, 0.0, 0.95)))
    c.put(outer & (upl > 0.3), False)
    face = (d > 66.2) & (d <= 74.8)
    fv = np.clip(0.44 - 0.34 * upl, 0.0, 0.8)
    fq = np.round(fv * 8) / 8
    c.put(face, tone(fq))
    c.put(face & (np.abs(d - 72.8) < 0.5), tone(np.clip(fq + 0.35, 0, 1)))
    c.put(face & (np.abs(d - 67.6) < 0.5) & (upl > 0.1), False)
    spec = face & (np.abs(d - 70.3) < 1.3) & (upl > 0.93)
    c.put(spec, False)
    c.put(face & (np.abs(d - 70.3) < 0.6) & (upl > 0.75), False)
    c.put(face & (np.abs(d - 71) < 0.6) & (upl < -0.96) & ((c.xs + c.ys) % 2 == 0), False)
    c.put((d > 74.8) & (d <= 75.6), True)
    inner = (d > 64.4) & (d <= 66.2)
    c.put(inner, tone(np.clip(0.55 + 0.45 * upl, 0.1, 1.0)))
    c.put(inner & (upl < -0.4), False)
    c.put((d > 65.6) & (d <= 66.4), True)
    c.put((d > 63.6) & (d <= 64.4), True)
    lip = (d > 61) & (d <= 63.6)
    c.put(lip, tone(np.clip(0.86 + 0.14 * upl, 0.75, 1.0)))
    c.put(lip & (d > 62.8) & (upl < -0.6), bayer(9))
    c.put(d <= 61, False)

    for k in range(12):
        a = k * math.tau / 12 + math.tau / 24
        bx, by = CX + math.cos(a) * 70.5, CY + math.sin(a) * 70.5
        bolt(c, bx, by, 2.6)

    c.poly([(113, 44), (131, 44), (122.5, 62)], False)
    c.poly([(118, 49), (130, 49), (124.5, 61.5)], bayer(12))
    c.poly([(116, 47), (128, 47), (122, 59.5)], True)
    c.put(c.rect_mask(118, 48, 126, 49), False)
    c.put(c.rect_mask(118, 48, 126, 49) & c.rect_mask(0, 0, 0, 0), True)


def prompt_plate(c):
    x0, y0, x1, y1 = 62, 182, 183, 224
    c.put(rrect_mask(c, x0 + 3, y0 + 3, x1 + 3, y1 + 3, 5), bayer(10))
    c.put(rrect_mask(c, x0 - 1, y0 - 1, x1 + 1, y1 + 1, 6), False)
    c.put(rrect_mask(c, x0, y0, x1, y1, 5), True)
    key = rrect_mask(c, x0 + 2, y0 + 2, x1 - 2, y1 - 2, 3)
    c.put(key & ~erode(key), False)
    cy = (y0 + y1) / 2
    for rx in (x0 + 6.5, x1 - 6.5):
        c.disc(rx, cy, 3.6, True)
        c.disc(rx, cy, 2.7, bayer(4))
        c.put(c.disc_mask(rx, cy, 2.7) & ~c.disc_mask(rx - 0.9, cy - 0.9, 2.7), bayer(12))
        c.disc(rx - 0.9, cy - 0.9, 1.0, False)
    c.put(c.rect_mask(74, 185, 171, 221) & ~c.rect_mask(0, 0, 0, 0), True)


def obj(c, m, fill=False, shade=8, shw=2, sh=3, sh_level=12, below=None):
    if sh:
        sm = shift(m, sh, sh) & ~m
        if below is not None:
            sm &= ~below
        c.put(sm, bayer(sh_level))
    c.put(dilate(m) & ~m, True)
    c.put(m, fill if isinstance(fill, bool) else bayer(fill))
    c.put(m & ~shift(m, -shw, -shw), bayer(shade))


def handle(c):
    hx, hy = 37.5, 185.5
    R = 20
    angs = [math.radians(a) for a in (-60, 30, 120, 210)]
    esc = c.disc_mask(hx, hy, 13)
    obj(c, esc, fill=2, shade=9, shw=2, sh=3, sh_level=11)
    c.put(esc & ~shift(esc, 1, 1), False)
    for k in range(8):
        a = k * math.tau / 8 + math.tau / 16
        px, py = int(hx + math.cos(a) * 10.5), int(hy + math.sin(a) * 10.5)
        c.put(c.rect_mask(px, py, px + 1, py + 1), True)
    arms = np.zeros_like(esc)
    for a in angs:
        ex, ey = hx + math.cos(a) * R, hy + math.sin(a) * R
        arms |= c.mask(lambda dr, ex=ex, ey=ey: dr.line([(hx, hy), (ex, ey)], fill=1, width=5))
        arms |= c.disc_mask(ex, ey, 4.8)
    c.put(shift(arms, 3, 3) & ~arms & ~esc, bayer(12))
    c.put(shift(arms, 2, 2) & ~arms & esc, bayer(12))
    obj(c, arms, fill=False, shade=8, shw=2, sh=0)
    for a in angs:
        ex, ey = hx + math.cos(a) * R, hy + math.sin(a) * R
        c.put(c.disc_mask(ex - 1.6, ey - 1.6, 1.1), True)
        c.put(c.disc_mask(ex - 1.6, ey - 1.6, 1.1) & ~c.disc_mask(ex - 1.1, ey - 1.1, 0.6), True)
        kn = c.disc_mask(ex, ey, 4.8)
        c.put(kn & ~shift(kn, -1, -1), True)
        c.put(c.rect_mask(int(ex - 2), int(ey - 2), int(ex - 1), int(ey - 1)), False)
    hub = c.disc_mask(hx, hy, 7.5)
    c.put(dilate(hub) & ~hub, True)
    c.put(hub, False)
    c.put(hub & ~shift(hub, -2, -2), bayer(8))
    c.ring(hx, hy, 3.5, 4.5, True)
    c.disc(hx, hy, 3.5, bayer(6))
    c.put(c.disc_mask(hx, hy, 3.5) & ~shift(c.disc_mask(hx, hy, 3.5), -1, -1), bayer(12))
    c.put(c.rect_mask(int(hx) - 1, int(hy) - 1, int(hx), int(hy)), False)


def maker_plate(c):
    cx, cy = 199.5, 210
    m = c.ellipse_mask(cx, cy, 10.5, 15)
    obj(c, m, fill=False, shade=8, shw=2, sh=3, sh_level=11)
    ring = c.ellipse_mask(cx, cy, 8, 12.5) & ~c.ellipse_mask(cx, cy, 7, 11.5)
    c.put(ring & ((c.xs + c.ys) % 2 == 0), True)
    for sy in (cy - 11.5, cy + 11):
        c.put(c.disc_mask(cx, sy, 1.6), True)
        c.put(c.rect_mask(int(cx) - 1, int(sy), int(cx) + 2, int(sy) + 1), False)
    kh = c.disc_mask(cx, cy - 3, 3.2) | c.poly_mask([(cx - 1.5, cy - 2), (cx + 1.5, cy - 2), (cx + 3, cy + 6), (cx - 3, cy + 6)])
    c.put(shift(kh, 1, 1) & ~kh, bayer(10))
    c.put(shift(kh, -1, -1) & ~kh, bayer(12))
    c.put(kh, True)


def left_rivets(c):
    for y in (72, 92, 112):
        small_rivet(c, 14.5, y + 0.5)
    for y in (76, 100, 156, 180):
        small_rivet(c, 206.5, y + 0.5)


def play_bg():
    c = Canvas(400, 240, 0)
    door_face(c)
    seam_h(c, 62, 9, 215)
    seam_h(c, 132, 9, 46)
    seam_h(c, 132, 199, 215)
    left_rivets(c)
    timer_bezel(c)
    dial_area(c)
    handle(c)
    maker_plate(c)
    prompt_plate(c)
    channel(c)
    jamb(c)
    c.save(os.path.join(OUT, 'play-bg.png'))
    return c


def plaque():
    c = Canvas(32, 32, 0)
    c.enable_alpha()
    W = 29
    sh = rrect_mask(c, 3, 3, W + 3, W + 3, 2) & ~rrect_mask(c, 0, 0, W, W, 2)
    c.put(sh, bayer(8))
    body = rrect_mask(c, 0, 0, W, W, 2)
    c.put(body, True)
    c.put(rrect_mask(c, 2, 2, W - 2, W - 2, 1), False)
    key = c.rect_mask(3, 3, W - 3, W - 3) & ~c.rect_mask(4, 4, W - 4, W - 4)
    dotted = ((c.xs + c.ys) % 2 == 0)
    c.put(key & dotted, True)
    c.put(c.rect_mask(2, W - 3, W - 2, W - 2), bayer(4))
    c.put(c.rect_mask(W - 3, 2, W - 2, W - 2), bayer(4))
    for sx, sy in ((7, 7), (W - 7, 7), (7, W - 7), (W - 7, W - 7)):
        c.put(c.rect_mask(max(sx - 3, 4 if sx < 12 else 20), max(sy - 3, 4 if sy < 12 else 20),
                          min(sx + 4, 12 if sx < 12 else W - 4), min(sy + 4, 12 if sy < 12 else W - 4)), False)
        sprite(c, ['.###.', '#ooo#', '#####', '#oo:#', '.###.'], sx - 2, sy - 2)
    c.save(os.path.join(OUT, 'plaque.png'))
    return c


def panel_img():
    c = Canvas(40, 40, 0)
    c.enable_alpha()
    W = 36
    sh = rrect_mask(c, 4, 4, W + 4, W + 4, 3) & ~rrect_mask(c, 0, 0, W, W, 3)
    c.put(sh, bayer(8))
    c.put(rrect_mask(c, 0, 0, W, W, 3), True)
    band = c.rect_mask(3, 3, W - 3, W - 3)
    c.put(band, bayer(6))
    c.put(band & ((c.xs < 5) | (c.ys < 5)), bayer(3))
    c.put(band & ((c.xs >= W - 5) | (c.ys >= W - 5)) & ~((c.xs < 5) & (c.ys >= W - 5)) & ~((c.ys < 5) & (c.xs >= W - 5)), bayer(10))
    c.put(band & ((c.xs == 3) | (c.ys == 3)) & (c.xs < W - 4) & (c.ys < W - 4), False)
    c.put(c.rect_mask(5, 5, W - 5, W - 5), True)
    c.put(c.rect_mask(6, 6, W - 6, W - 6), False)
    for rx, ry in ((9, 9), (W - 9, 9), (9, W - 9), (W - 9, W - 9)):
        sprite(c, ['..###..', '.#oo:#.', '#oooo:#', '#ooo::#', '#o::::#', '.#::=#.', '..###..'], rx - 3, ry - 3)
    c.save(os.path.join(OUT, 'panel.png'))
    return c


def chip():
    c = Canvas(16, 16, 0)
    c.enable_alpha()
    W = 14
    sh = rrect_mask(c, 2, 2, W + 2, W + 2, 3) & ~rrect_mask(c, 0, 0, W, W, 3)
    c.put(sh, bayer(8))
    c.put(rrect_mask(c, 0, 0, W, W, 3), True)
    k = rrect_mask(c, 2, 2, W - 2, W - 2, 1)
    c.put(k & ~erode(k), False)
    c.save(os.path.join(OUT, 'chip.png'))
    return c


if __name__ == '__main__':
    outs = {'play-bg': play_bg(), 'plaque': plaque(), 'panel': panel_img(), 'chip': chip()}
    if PREV:
        os.makedirs(PREV, exist_ok=True)
        for k, c in outs.items():
            c.preview(os.path.join(PREV, k + '.png'), 3 if k == 'play-bg' else 10)
