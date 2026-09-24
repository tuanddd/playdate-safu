import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdart import Canvas, bayer, tone, dilate, erode, load_font, B4
from gen_neko_v2 import (ref_layers, zhang_suen, in_rects, SS, down, pat, grow, stamp,
                         EYES_REF, FACE_CUT, THIN, disc_grow, shift)

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'prototypes', 'neko', 'v2', 'title')
PREVIEW = os.environ.get('PREVIEW_DIR')

W, H = 400, 240
DCX, DCY, DR = 200, 126, 62
DIAL_COVER = 72
DOOR_R = 99
FLOOR_Y = 222
NEKO_SCALE = 0.84
NEKO_OX, NEKO_OY = 250, 40
NEKO_CUT = 162
CTA_Y = 206


EYE_B = """
...####...
.########.
.########.
##oo######
##oo######
##########
##########
##########
##########
.########.
.########.
...####...
"""
MOUTH_B = """
#.........#.........#
##.......###.......##
.##.....##.##.....##.
..##...##...##...##..
...#####.....#####...
"""
def scene_at(scale):
    f = scale / 0.6
    L = ref_layers()
    H0, W0 = L['l'].shape
    w, h = int(round(W0 * scale)), int(round(H0 * scale))
    yy, xx = np.mgrid[0:H0, 0:W0]
    eyes0 = np.zeros_like(L['ink'])
    for ex, ey in EYES_REF:
        eyes0 |= ((xx - ex) / 9.0) ** 2 + ((yy - ey) / 10.0) ** 2 <= 1
    sk = zhang_suen(L['ink'] & ~eyes0)
    ys, xs = np.nonzero(sk)
    keep = ~in_rects(xs, ys, FACE_CUT)
    thin = in_rects(xs, ys, THIN)
    ss = SS(w, h)
    for x, y, k, t in zip(xs, ys, keep, thin):
        if k:
            ss.disc((x + 0.5) * scale, (y + 0.5) * scale, 0.7 if t else 1.25)
    ink = ss.mask(0.5)
    rays0 = L['grey'] & (yy < 32)
    rsk = zhang_suen(rays0)
    ss2 = SS(w, h)
    ys2, xs2 = np.nonzero(rsk)
    for x, y in zip(xs2, ys2):
        ss2.disc((x + 0.5) * scale, (y + 0.5) * scale, 0.9)
    rays = ss2.mask(0.5)
    greyfree = L['grey'] & ~grow(L['ink'], 2) & ~(yy < 32) & ~in_rects(xx, yy, FACE_CUT)
    greyc = down(greyfree.astype(np.float32), w, h) >= 0.45
    redc = down(L['red'].astype(np.float32), w, h) >= 0.5
    inside = down((L['al'] > 0.5).astype(np.float32), w, h) >= 0.5
    out = ink.copy()
    out |= greyc & ~out & pat(8, h, w)
    hy = np.mgrid[0:h, 0:w][0]
    heartm = redc & (hy < h * 0.3)
    out |= heartm
    hys, hxs = np.nonzero(heartm)
    out[hys.min() + 3:hys.min() + 5, hxs.min() + 3:hxs.min() + 5] = False
    sx = lambda v: int(round(v * f))
    out[sx(33):sx(43), sx(49):sx(64)] = False
    img = Image.new('1', (w, h), 0)
    d = ImageDraw.Draw(img)
    zz = [(47, 41), (49, 38), (51, 39), (53, 36), (56, 39), (59, 36), (61, 39), (63, 37), (65, 39)]
    d.line([(x * f, y * f) for x, y in zz], fill=1, width=2)
    for x in (53, 59):
        d.line([(x * f, 31 * f), (x * f, 36 * f)], fill=1, width=2)
    out |= np.array(img, dtype=bool)
    stamp(out, EYE_B, sx(38.5) - 1, sx(69) - 1)
    stamp(out, EYE_B, sx(66.5) - 1, sx(69) - 1)
    stamp(out, "#.#.#", sx(55.5) - 2, sx(79.5) - 1)
    stamp(out, MOUTH_B, sx(55.5) - 10, sx(81.5))
    for (x, y) in ((23, 81), (23, 86)):
        out[sx(y):sx(y) + 2, sx(x) - 2:sx(x + 10)] = True
    for (x, y) in ((82, 77), (82, 82)):
        out[sx(y):sx(y) + 2, sx(x):sx(x + 10)] = True
    alpha = inside | out
    return dict(ink=out, alpha=alpha, inside=inside, rays=rays, w=w, h=h, f=f)


def checker(x, y):
    return (x + y) % 2 == 0


def ss_mask(w, h, fn, k=4):
    img = Image.new('L', (w * k, h * k), 0)
    fn(ImageDraw.Draw(img), k)
    return np.asarray(img.resize((w, h), Image.BOX), np.float32) / 255.0 >= 0.5


def wall(c):
    d = np.hypot((c.xs - 200) / 250.0, (c.ys - 120) / 170.0)
    field = np.clip(0.6 + 0.3 * d, 0, 0.92)
    bw, bh = 26, 11
    row = c.ys // bh
    off = np.where(row % 2 == 1, bw // 2, 0)
    bx = (c.xs + off) % bw
    by = c.ys % bh
    mortar = (by == 0) | (bx == 0)
    c.ink[:] = tone(field)(c.xs, c.ys) | mortar
    top = (by == 1) & (bx > 1) & (bx < bw - 2) & (c.xs % 2 == 0)
    c.ink[top] = False
    edge = (by == bh - 1) & ~mortar
    c.ink[edge] = True
    rng = np.random.default_rng(7)
    for _ in range(22):
        r = int(rng.integers(0, H // bh + 1))
        b = int(rng.integers(0, W // bw + 2))
        x0 = b * bw - (bw // 2 if r % 2 else 0) + 1
        y0 = r * bh + 1
        m = c.rect_mask(x0, y0, x0 + bw - 1, y0 + bh - 2)
        c.ink[m] = bayer(13)(c.xs, c.ys)[m]


def floor(c):
    m = c.ys >= FLOOR_Y
    f = np.clip(0.7 + (c.ys - FLOOR_Y) * 0.012, 0, 1)
    c.ink[m] = tone(f)(c.xs, c.ys)[m]
    c.ink[m & ((c.ys - FLOOR_Y) % 6 == 5)] = True
    c.rect(0, FLOOR_Y - 2, W, FLOOR_Y, True)
    c.rect(0, FLOOR_Y, W, FLOOR_Y + 1, lambda x, y: x % 2 == 0)


def pool(c, cx, cy, rx, ry):
    e = ((c.xs + 0.5 - cx) / rx) ** 2 + ((c.ys + 0.5 - cy) / ry) ** 2
    m = (e <= 1) & (c.ys < FLOOR_Y - 2)
    f = np.clip(0.08 + 0.7 * e ** 1.8, 0, 1)
    old = c.ink.copy()
    c.ink[m] = tone(f)(c.xs, c.ys)[m] | (old & ~tone(0.6)(c.xs, c.ys))[m] & (f[m] > 0.3)
    fe = ((c.xs + 0.5 - cx) / (rx + 10)) ** 2 + ((c.ys + 0.5 - (FLOOR_Y + 12)) / 12.0) ** 2
    fm = (fe <= 1) & (c.ys > FLOOR_Y)
    ff = np.clip(0.2 + 0.6 * fe, 0, 1)
    c.ink[fm] = tone(ff)(c.xs, c.ys)[fm] | ((c.ys[fm] - FLOOR_Y) % 6 == 5)


def door(c):
    cx, cy = DCX, DCY
    hx = DCX - DOOR_R
    for hy in (80, 172):
        c.rect(hx - 15, hy - 13, hx + 12, hy + 13, True)
        c.rect(hx - 13, hy - 11, hx + 10, hy + 11, bayer(4))
        c.rect(hx - 13, hy - 11, hx + 10, hy - 9, False)
        c.rect(hx - 13, hy + 8, hx + 10, hy + 11, bayer(10))
        c.rect(hx - 7, hy - 15, hx - 1, hy + 15, True)
        c.rect(hx - 6, hy - 14, hx - 4, hy + 14, False)
    c.disc(cx + 3, cy + 4, DOOR_R + 2, True)
    c.disc(cx, cy, DOOR_R + 2, True)
    ang = np.arctan2(c.ys + 0.5 - cy, c.xs + 0.5 - cx)
    dist = np.hypot(c.xs + 0.5 - cx, c.ys + 0.5 - cy)
    light = -np.cos(ang + math.pi * 0.75)
    face = dist < DOOR_R - 1
    f = np.clip(0.24 - 0.12 * light, 0, 1)
    c.ink[face] = tone(f)(c.xs, c.ys)[face]
    c.ink[(dist >= DOOR_R - 4) & (dist < DOOR_R - 3) & (light > 0)] = False
    c.ink[(dist >= 84) & (dist < 87)] = True
    c.ink[(dist >= 87) & (dist < 88) & (light > -0.3)] = False
    for i in range(16):
        a = i * math.pi * 2 / 16 + math.pi / 16
        bx, by = cx + math.cos(a) * 92.5, cy + math.sin(a) * 92.5
        c.disc(bx + 1, by + 1, 3.0, True)
        c.disc(bx, by, 3.0, True)
        c.disc(bx, by, 2.0, False)
        c.ink[int(by) + 1, int(bx) + 1] = True
    inner = (dist < 84) & (dist >= DIAL_COVER)
    f2 = np.clip(0.4 + 0.18 * light, 0, 1)
    c.ink[inner] = tone(f2)(c.xs, c.ys)[inner]
    c.ink[(dist >= 83) & (dist < 84) & (light > 0)] = False
    for i in range(8):
        a = i * math.pi / 4 + math.pi / 8
        m = line_mask(c, [(cx + math.cos(a) * 75, cy + math.sin(a) * 75), (cx + math.cos(a) * 82, cy + math.sin(a) * 82)], 3)
        c.ink[m] = True


def dial_cut(c):
    m = c.disc_mask(DCX, DCY, DIAL_COVER)
    c.ink[m] = False
    return m


def line_mask(c, pts, w):
    return ss_mask(W, H, lambda d, k: d.line([(x * k, y * k) for x, y in pts], fill=255, width=max(1, int(w * k))))


def draw_dial(c, pos=0):
    cx, cy, r = DCX, DCY, DR
    rim = int(r * 0.12) + 2
    hub = int(r * 0.30)
    nr = r - int(r * 0.36)
    c.disc(cx, cy, r + rim, True)
    c.disc(cx, cy, r, False)
    c.put(c.disc_mask(cx, cy, nr - 9), bayer(13))
    ang = np.degrees(np.arctan2(c.xs + 0.5 - cx, -(c.ys + 0.5 - cy))) % 360
    dist = np.hypot(c.xs + 0.5 - cx, c.ys + 0.5 - cy)
    arc = (dist >= r - 3.5) & (dist <= r - 0.5) & (ang >= 95) & (ang <= 200)
    c.ink[arc] = checker(c.xs, c.ys)[arc]
    c.ink[(dist >= nr - 9.5) & (dist <= nr - 8.5)] = True
    for n in range(0, 100, 2):
        a = math.radians((pos - n) * 3.6)
        sa, ca = math.sin(a), math.cos(a)
        c.ink[line_mask(c, [(cx + sa * (r + 2), cy - ca * (r + 2)), (cx + sa * (r + rim - 1), cy - ca * (r + rim - 1))], 2)] = False
    for n in range(100):
        a = math.radians((pos - n) * 3.6)
        sa, ca = math.sin(a), math.cos(a)
        if n % 10 == 0:
            lw, inner = 3, r - r * 0.20
        elif n % 5 == 0:
            lw, inner = 2, r - r * 0.15
        else:
            lw, inner = 1, r - r * 0.09
        c.ink[line_mask(c, [(cx + sa * (r - 2), cy - ca * (r - 2)), (cx + sa * inner, cy - ca * inner)], lw)] = True
    font = load_font(8)
    for n in range(0, 100, 10):
        a = math.radians((pos - n) * 3.6)
        tmp = Image.new('L', (40, 40), 0)
        ImageDraw.Draw(tmp).text((12, 14), str(n), fill=255, font=font)
        tmp = tmp.rotate(-(pos - n) * 3.6, resample=Image.BILINEAR)
        t = np.asarray(tmp) > 110
        ys, xs = np.nonzero(t)
        t = t[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        th, tw = t.shape
        x0 = int(round(cx + math.sin(a) * nr - tw / 2))
        y0 = int(round(cy - math.cos(a) * nr - th / 2))
        c.ink[y0:y0 + th, x0:x0 + tw] |= t
    c.ink[(dist >= r + rim - 2.5) & (dist <= r + rim - 1.5) & (ang >= 285) & (ang <= 345)] = False
    c.disc(cx, cy, hub, True)
    c.put(c.disc_mask(cx, cy, hub - 2), bayer(9))
    c.ink[(dist >= hub - 2.5) & (dist <= hub - 1.5) & (ang >= 290) & (ang <= 350)] = False
    for i in range(4):
        a = math.radians(pos * 3.6 + i * 90)
        sa, ca = math.sin(a), math.cos(a)
        c.ink[line_mask(c, [(cx + sa * hub * 0.35, cy - ca * hub * 0.35), (cx + sa * hub * 0.86, cy - ca * hub * 0.86)], 3)] = True
    c.disc(cx, cy, max(3, hub * 0.25), False)
    c.disc(cx, cy, max(2, hub * 0.13), True)


def bundle(c, x, y, w=40, h=10):
    c.rect(x, y, x + w, y + h, True)
    c.rect(x + 1, y + 1, x + w - 1, y + h - 1, False)
    c.rect(x + 2, y + 3, x + w - 2, y + 4, lambda xx, yy: xx % 3 != 0)
    c.rect(x + 2, y + h - 3, x + w - 1, y + h - 1, checker)
    m = w // 2
    c.rect(x + m - 5, y, x + m + 5, y + h, True)
    c.rect(x + m - 4, y + 1, x + m + 4, y + h - 1, checker)
    c.rect(x + m - 2, y + 2, x + m + 2, y + h - 2, False)
    c.ink[y + 3:y + h - 3, x + m - 1:x + m + 1] = True


def stack(c, x, y_top, n, w=40, h=10, sway=(0, 1, 0, -1, 0, 1)):
    for i in reversed(range(n)):
        bundle(c, x + sway[i % len(sway)], y_top + i * (h - 1), w, h)


def cash_pile(c):
    top = NEKO_OY + NEKO_CUT - 2
    stack(c, 344, top + 1, 5, sway=(1, 0, -1, 0, 1))
    stack(c, 302, top - 1, 5, sway=(0, 1, 0, -1, 0))
    stack(c, 372, top + 18, 3, w=38, sway=(0, -1, 0))
    bundle(c, 72, FLOOR_Y + 5, 32, 10)
    bundle(c, 76, FLOOR_Y - 4, 30, 10)


def money_bag(c, cx, by):
    sil = c.mask(lambda d: (d.ellipse([cx - 25, by - 40, cx + 25, by], fill=1),
                            d.polygon([(cx - 9, by - 37), (cx + 9, by - 37), (cx + 14, by - 52), (cx - 14, by - 52)], fill=1),
                            d.ellipse([cx - 17, by - 58, cx - 2, by - 47], fill=1),
                            d.ellipse([cx + 2, by - 58, cx + 17, by - 47], fill=1)))
    c.ink[disc_grow(sil, 3.2)] = True
    inner = erode(erode(sil))
    c.ink[inner] = False
    rim = np.hypot((c.xs - cx) / 25.0, (c.ys - by + 20) / 20.0)
    sh = inner & (((c.xs - cx) * 0.7 + (c.ys - by + 20)) > 12)
    c.ink[sh] = checker(c.xs, c.ys)[sh]
    c.rect(cx - 12, by - 42, cx + 12, by - 37, True)
    c.rect(cx - 10, by - 41, cx + 10, by - 40, False)
    dollar = ["...##...", ".######.", "##.##.##", "##.##...", ".######.", "...##.##", "##.##.##", ".######.", "...##..."]
    for j, r in enumerate(dollar):
        for i, ch in enumerate(r):
            if ch == '#':
                c.ink[by - 26 + j, cx - 4 + i] = True


LETTERS = {
    'S': ['.####', '##...', '##...', '.###.', '...##', '...##', '####.'],
    'A': ['.###.', '##.##', '##.##', '#####', '##.##', '##.##', '##.##'],
    'F': ['#####', '##...', '##...', '####.', '##...', '##...', '##...'],
    'U': ['##.##', '##.##', '##.##', '##.##', '##.##', '##.##', '.###.'],
}


def open_disc(m, r):
    return disc_grow(~disc_grow(~m, r), r)


def wordmark(c, cx, top, cell=6, cw=7, gap=6, depth=4):
    text = 'SAFU'
    lw = 5 * cw
    total = len(text) * lw + (len(text) - 1) * gap
    x0 = cx - total // 2
    m = np.zeros((H, W), bool)
    for k, ch in enumerate(text):
        for j, row in enumerate(LETTERS[ch]):
            for i, v in enumerate(row):
                if v == '#':
                    xx = x0 + k * (lw + gap) + i * cw
                    yy = top + j * cell
                    m[yy:yy + cell, xx:xx + cw] = True
    m = open_disc(m, 2.2)
    o1 = disc_grow(m, 2.5)
    ext = o1.copy()
    for s_ in range(1, depth + 1):
        ext |= shift(o1, s_, s_)
    o2 = disc_grow(ext, 1.5)
    shadow = disc_grow(shift(ext, 3, 3), 1.5) & ~o2
    c.ink[shadow] = checker(c.xs, c.ys)[shadow] | c.ink[shadow]
    c.ink[o2] = False
    c.ink[ext] = True
    c.ink[o1 & ~m] = True
    c.ink[m] = False
    low = m & ~shift(m, 0, -2)
    c.ink[low] = checker(c.xs, c.ys)[low]
    return m


def neko(c):
    s = scene_at(NEKO_SCALE)
    ink, al, rays = s['ink'].copy(), s['alpha'].copy(), s['rays'].copy()
    for a in (ink, al, rays):
        a[NEKO_CUT:, :] = False
    h, w = ink.shape

    def place(a):
        out = np.zeros((H, W), bool)
        y1, x1 = min(H, NEKO_OY + h), min(W, NEKO_OX + w)
        out[NEKO_OY:y1, NEKO_OX:x1] = a[:y1 - NEKO_OY, :x1 - NEKO_OX]
        return out

    ink, al, rays = place(ink), place(al), place(rays)
    body = al | ink
    halo = disc_grow(body, 2.6)
    c.ink[halo] = False
    c.ink[body] = ink[body]
    rh = disc_grow(rays, 1.3) & ~body
    c.ink[rh] = False
    c.ink[rays] = True
    return body


def listen_waves(c, cx, cy):
    for r in (10, 16, 22):
        m = ss_mask(W, H, lambda d, k, r=r: d.arc([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], 150, 210, fill=255, width=int(2 * k)))
        c.ink[disc_grow(m, 1.3)] = False
        c.ink[m] = True


def label(c, text, x, y):
    font = load_font(8)
    bb = font.getbbox(text)
    w, h = bb[2] + 8, 13
    tag = c.mask(lambda d: d.rounded_rectangle([x, y, x + w - 1, y + h - 1], 4, fill=1))
    tail = c.poly_mask([(x + 4, y + h - 2), (x + 11, y + h - 2), (x + 2, y + h + 4)])
    body = tag | tail
    c.ink[disc_grow(body, 1.0)] = False
    c.ink[body] = True
    t = c.text_mask(text, x + 4, y + 3 - bb[1] + 1, font)
    c.ink[t] = False


def chip(c, x, y, w, h, icon, text, font):
    sh = c.mask(lambda d: d.rounded_rectangle([x + 2, y + 2, x + w + 1, y + h + 1], 7, fill=1))
    c.ink[sh] = checker(c.xs, c.ys)[sh] | c.ink[sh]
    body = c.mask(lambda d: d.rounded_rectangle([x, y, x + w - 1, y + h - 1], 7, fill=1))
    c.ink[disc_grow(body, 1.0) & ~body & ~sh] = False
    c.ink[body] = True
    ring = c.mask(lambda d: d.rounded_rectangle([x + 2, y + 2, x + w - 3, y + h - 3], 5, outline=1, width=1))
    c.ink[ring] = False
    tw = font.getbbox(text)[2]
    total = 14 + 5 + tw
    ix = x + (w - total) // 2
    iy = y + (h - 14) // 2
    c.ink[c.disc_mask(ix + 7, iy + 7, 7)] = False
    g = c.text_mask(icon, ix + 5, iy + 2, font)
    c.ink[g] = True
    t = c.text_mask(text, ix + 19, iy + 2, font)
    c.ink[t] = False


def ctas(c, y):
    font = load_font(8)
    items = [('A', 'CRACK IT'), ('B', 'TUTORIAL')]
    ws = [14 + 5 + font.getbbox(t)[2] + 24 for _, t in items]
    gap = 10
    x = 200 - (sum(ws) + gap) // 2
    for (ic, t), w in zip(items, ws):
        chip(c, x, y, w, 26, ic, t, font)
        x += w + gap


def build(with_dial, with_buttons):
    c = Canvas(W, H, 0)
    wall(c)
    pool(c, 326, 118, 84, 118)
    floor(c)
    door(c)
    dial_cut(c)
    money_bag(c, 44, FLOOR_Y + 8)
    neko(c)
    cash_pile(c)
    label(c, 'CLICK!', 350, 44)
    wordmark(c, 200, 4)
    dial_cut(c)
    if with_dial:
        draw_dial(c)
    if with_buttons:
        ctas(c, CTA_Y)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    full = build(True, True)
    full.save(os.path.join(OUT, 'neko-v2-title.png'))
    full.preview(os.path.join(OUT, 'neko-v2-title@3x.png'), 3)
    plate = build(False, False)
    plate.save(os.path.join(OUT, 'neko-v2-title-plate.png'))
    plate.save(os.path.join(ROOT, 'source', 'images', 'title-neko.png'))
    if PREVIEW:
        plate.preview(os.path.join(PREVIEW, 'plate@3x.png'), 3)


if __name__ == '__main__':
    main()
