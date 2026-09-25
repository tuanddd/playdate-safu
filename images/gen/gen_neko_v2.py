import os
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdart import B4, dilate, erode

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
REF = os.path.join(ROOT, 'art-references', 'wagmi-neko-5.png')
OUT = os.path.join(ROOT, 'prototypes', 'neko', 'v2')

SCALE = 0.6
GREY = 8
K = 8


def pat(level, h, w):
    ys, xs = np.mgrid[0:h, 0:w]
    return B4[ys & 3, xs & 3] < level


def grow(m, t=1):
    for _ in range(t):
        m = dilate(m)
    return m


def zhang_suen(img):
    im = np.pad(img.astype(np.uint8), 1)
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            P2 = im[:-2, 1:-1]; P3 = im[:-2, 2:]; P4 = im[1:-1, 2:]; P5 = im[2:, 2:]
            P6 = im[2:, 1:-1]; P7 = im[2:, :-2]; P8 = im[1:-1, :-2]; P9 = im[:-2, :-2]
            C = im[1:-1, 1:-1]
            nb = [P2, P3, P4, P5, P6, P7, P8, P9]
            B = sum(n.astype(int) for n in nb)
            seq = nb + [P2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(int) for i in range(8))
            if step == 0:
                c1 = (P2 * P4 * P6) == 0
                c2 = (P4 * P6 * P8) == 0
            else:
                c1 = (P2 * P4 * P8) == 0
                c2 = (P2 * P6 * P8) == 0
            m = (C == 1) & (B >= 2) & (B <= 6) & (A == 1) & c1 & c2
            if m.any():
                changed = True
                im[1:-1, 1:-1][m] = 0
    return im[1:-1, 1:-1].astype(bool)


def load_ref():
    a = np.array(Image.open(REF).convert('RGBA')).astype(np.float32)
    al = a[..., 3:] / 255.0
    c = a[..., :3] * al + 255 * (1 - al)
    l = c.mean(-1)
    sat = c.max(-1) - c.min(-1)
    return c, l, sat, al[..., 0]


def down(m, w, h):
    return np.asarray(Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BOX), np.float32) / 255.0


class SS:
    def __init__(self, w, h, k=K):
        self.w, self.h, self.k = w, h, k
        self.img = Image.new('L', (w * k, h * k), 0)
        self.d = ImageDraw.Draw(self.img)

    def disc(self, x, y, r):
        k = self.k
        self.d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=255)

    def ell(self, x, y, rx, ry):
        k = self.k
        self.d.ellipse([(x - rx) * k, (y - ry) * k, (x + rx) * k, (y + ry) * k], fill=255)

    def poly(self, pts):
        k = self.k
        self.d.polygon([(x * k, y * k) for x, y in pts], fill=255)

    def mask(self, t=0.5):
        a = np.asarray(self.img.resize((self.w, self.h), Image.BOX), np.float32) / 255.0
        return a >= t


def ref_layers():
    c, l, sat, al = load_ref()
    neutral = sat < 40
    ink = (l < 140) & neutral
    red = sat >= 40
    grey = (l >= 110) & (l < 238) & neutral
    return dict(l=l, ink=ink, red=red, grey=grey, al=al)


EYES_REF = [(68.5, 122.5), (115.2, 121.2)]
FACE_CUT = [(78, 127, 108, 149), (34, 130, 44, 150), (50, 131, 60, 148), (130, 122, 157, 143)]
THIN = [(70, 50, 118, 74)]


def stamp(ink, rows, x, y):
    rows = [r for r in rows.strip('\n').split('\n')]
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            yy, xx = y + j, x + i
            if 0 <= yy < ink.shape[0] and 0 <= xx < ink.shape[1]:
                if ch == '#':
                    ink[yy, xx] = True
                elif ch == 'o':
                    ink[yy, xx] = False


EYE = """
..###..
.#####.
##o####
#######
#######
#######
.#####.
..###..
"""
MOUTH = """
#......#......#
##....###....##
.##..##.##..##.
..####...####..
"""
NOSE = """
#.#.#
"""


def tuft(out):
    out[33:43, 49:64] = False
    img = Image.new('1', (out.shape[1], out.shape[0]), 0)
    d = ImageDraw.Draw(img)
    zz = [(47, 41), (49, 38), (51, 39), (53, 36), (56, 39), (59, 36), (61, 39), (63, 37), (65, 39)]
    d.line(zz, fill=1, width=1)
    d.line([(53, 31), (53, 36)], fill=1, width=1)
    d.line([(59, 31), (59, 36)], fill=1, width=1)
    m = np.array(img, dtype=bool)
    m2 = m.copy()
    m2[1:, :] |= m[:-1, :]
    out |= m2 | np.roll(m & (np.arange(out.shape[1])[None, :] >= 53) & (np.arange(out.shape[1])[None, :] <= 59) & (np.arange(out.shape[0])[:, None] < 36), 1, axis=1)


def in_rects(xs, ys, rects):
    m = np.zeros(xs.shape, bool)
    for x0, y0, x1, y1 in rects:
        m |= (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)
    return m


def scene(scale=SCALE, lw=2.0, grey_level=GREY, heart='solid', shine=True):
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
            ss.disc((x + 0.5) * scale, (y + 0.5) * scale, 0.62 if t else lw / 2.0)
    ink = ss.mask(0.5)
    rays0 = L['grey'] & (yy < 32)
    rsk = zhang_suen(rays0)
    ss2 = SS(w, h)
    ys2, xs2 = np.nonzero(rsk)
    for x, y in zip(xs2, ys2):
        ss2.disc((x + 0.5) * scale, (y + 0.5) * scale, 0.55)
    rays = ss2.mask(0.5)
    greyfree = L['grey'] & ~grow(L['ink'], 2) & ~(yy < 32) & ~in_rects(xx, yy, FACE_CUT)
    greyc = down(greyfree.astype(np.float32), w, h) >= 0.45
    redc = down(L['red'].astype(np.float32), w, h) >= 0.5
    inside = down((L['al'] > 0.5).astype(np.float32), w, h) >= 0.5
    out = ink | rays
    out |= greyc & ~out & pat(grey_level, h, w)
    hy = np.mgrid[0:h, 0:w][0]
    heartm = redc & (hy < h * 0.3)
    btn = redc & ~heartm
    if heart == 'solid':
        out |= heartm
        hys, hxs = np.nonzero(heartm)
        out[hys.min() + 2, hxs.min() + 2] = False
    else:
        out |= heartm & pat(10, h, w)
    out |= btn & ~out & pat(10, h, w)
    tuft(out)
    eye = EYE if shine else EYE.replace('o', '#')
    stamp(out, eye, 38, 69)
    stamp(out, eye, 66, 69)
    stamp(out, NOSE, 53, 79)
    stamp(out, MOUTH, 48, 81)
    out[80, 29:31] = False
    out[85, 26] = False
    out[85, 30] = False
    stamp(out, '##########\n##########', 23, 81)
    stamp(out, '##########\n##########', 23, 86)
    stamp(out, '##########\n##########', 82, 77)
    stamp(out, '##########\n##########', 82, 82)
    alpha = inside | out
    return dict(ink=out, alpha=alpha, w=w, h=h)


def preview(ink, path, scale=3):
    rgb = np.stack([np.where(ink, 0x31, 0xB1), np.where(ink, 0x2F, 0xAF), np.where(ink, 0x28, 0xA8)], -1).astype(np.uint8)
    Image.fromarray(rgb, 'RGB').resize((ink.shape[1] * scale, ink.shape[0] * scale), Image.NEAREST).save(path)


def compare(ink, path, scale=3):
    h, w = ink.shape
    ref = Image.open(REF).convert('RGBA')
    bg = Image.new('RGBA', ref.size, (255, 255, 255, 255))
    bg.alpha_composite(ref)
    g = bg.convert('L').resize((w, h), Image.LANCZOS).convert('RGB')
    mine = Image.fromarray(np.where(ink, 0, 255).astype(np.uint8), 'L').convert('RGB')
    out = Image.new('RGB', (w * 2 + 6, h), (255, 255, 255))
    out.paste(g, (0, 0))
    out.paste(mine, (w + 6, 0))
    out.resize((out.width * scale, out.height * scale), Image.NEAREST).save(path)


def flood(free, seed):
    H, W = free.shape
    reg = np.zeros_like(free)
    stack = [seed]
    reg[seed] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and free[yy, xx] and not reg[yy, xx]:
                reg[yy, xx] = True
                stack.append((yy, xx))
    return reg


def head_ref():
    L = ref_layers()
    ink = L['ink'] | L['red']
    free = ~grow(ink, 1)
    free[164:, :] = False
    reg = flood(free, (100, 100))
    sil = grow(reg, 3)
    cx = 104
    for y in range(140, sil.shape[0]):
        row = sil[y].copy()
        for x in range(cx, sil.shape[1]):
            xm = 2 * cx - x
            row[x] = sil[y, xm] if 0 <= xm < sil.shape[1] else False
        sil[y] = row
    bg = flood(np.pad(~sil, 1, constant_values=True), (0, 0))[1:-1, 1:-1]
    sil = ~bg
    return L, reg, sil


def shift(m, dx, dy):
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(0, dy):min(h, h + dy), max(0, dx):min(w, w + dx)] = m[max(0, -dy):min(h, h - dy), max(0, -dx):min(w, w - dx)]
    return out


def disc_grow(m, r):
    out = m.copy()
    ri = int(np.ceil(r))
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            if (dx or dy) and dx * dx + dy * dy <= r * r:
                out |= shift(m, dx, dy)
    return out


def erode_n(m, n):
    for _ in range(n):
        m = erode(m)
    return m


HEAD_FACE = {
    48: dict(line=2, eye="""
.###.
#o###
#####
#####
#####
.###.
""", mouth="""
#...#...#
##.###.##
.###.###.
""", nose="", wl=1),
    28: dict(line=1, eye="""
##
##
##
""", mouth="""
#.#.#
.#.#.
""", nose="", wl=1),
}


def head_only(width, grey_level=8):
    L, reg, sil = head_ref()
    ys, xs = np.nonzero(sil)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    sc = width / float(x1 - x0)
    pad = 6
    w = width + 2 * pad
    h = int(round((y1 - y0) * sc)) + 2 * pad
    big = Image.fromarray((sil[y0:y1, x0:x1] * 255).astype(np.uint8))
    tw, th = width, int(round((y1 - y0) * sc))
    outer_s = np.asarray(big.resize((tw, th), Image.BOX), np.float32) / 255.0 >= 0.5
    outer = np.zeros((h, w), bool)
    outer[pad:pad + th, pad:pad + tw] = outer_s
    cfg = HEAD_FACE[width]
    outer = erode(grow(outer, 1))
    rows = np.nonzero(outer.any(1))[0]
    for y in range(rows.min() + int(len(rows) * 0.45), rows.max() + 1):
        xs_ = np.nonzero(outer[y])[0]
        if len(xs_):
            outer[y, xs_.min():xs_.max() + 1] = True
    if cfg['line'] == 2:
        inner = ~disc_grow(~outer, 2.0)
    else:
        inner = erode_n(outer, 1)
    ink = outer & ~inner
    yyr = np.mgrid[0:reg.shape[0], 0:reg.shape[1]][0]
    greyr = (L['grey'] & reg & ~grow(L['ink'], 2) & (yyr < 75))[y0:y1, x0:x1]
    gs = np.asarray(Image.fromarray((greyr * 255).astype(np.uint8)).resize((tw, th), Image.BOX), np.float32) / 255.0 >= 0.4
    grey = np.zeros((h, w), bool)
    grey[pad:pad + th, pad:pad + tw] = gs
    ink |= grey & inner & pat(grey_level, h, w)

    def P(x, y):
        return int(round((x - x0) * sc)) + pad, int(round((y - y0) * sc)) + pad

    def stamp_c(rows, cx, cy):
        rr = [r for r in rows.strip('\n').split('\n')]
        stamp(ink, rows, cx - len(rr[0]) // 2, cy - len(rr) // 2)

    (lx, ly), (rx, ry) = P(*EYES_REF[0]), P(*EYES_REF[1])
    ey = (ly + ry) // 2
    mid = (lx + rx) // 2
    half = max(1, (rx - lx) // 2)
    stamp_c(cfg['eye'], mid - half, ey)
    stamp_c(cfg['eye'], mid + half, ey)
    mx, my = P(92.5, 139.5)
    nx, ny = P(92, 133)
    if cfg['nose']:
        stamp_c(cfg['nose'], mid, my - 2)
    stamp_c(cfg['mouth'], mid, my)
    for wy in (135, 144):
        a, yy = P(39, wy)
        b, _ = P(55, wy)
        ink[yy, a:b + 1] = True
    for wy in (129, 138):
        a, yy = P(135, wy)
        right = np.nonzero(outer[yy])[0].max()
        ink[yy, a:right - cfg['line'] - 1] = True
    alpha = outer.copy()
    alpha |= ink
    fix = TUFT_FIX.get(width)
    if width == 28:
        fix28(ink, alpha)
    if fix:
        (r0, r1, c0, c1), rows, (sx, sy) = fix
        ink[r0:r1, c0:c1] = False
        alpha[r0:r1, c0:c1] = False
        rr = [r for r in rows.strip('\n').split('\n')]
        for j, r in enumerate(rr):
            for i, ch in enumerate(r):
                if ch == '#':
                    ink[sy + j, sx + i] = True
                    alpha[sy + j, sx + i] = True
        below = np.zeros_like(alpha)
        for i in range(len(rr[0])):
            col = [j for j, r in enumerate(rr) if r[i] == '#']
            if col:
                for yy in range(sy + max(col) + 1, r1 + 2):
                    if not ink[yy, sx + i]:
                        alpha[yy, sx + i] = True
    return dict(ink=ink, alpha=alpha)


TUFT_FIX = {
    48: ((13, 18, 20, 33), '''
...#...#...#...
..#.#.#.#.#.#..
##...#...#...##
''', (19, 14)),
}

TOP28 = [
    '                    ##          ',
    '                   #::#         ',
    '       ##         #:::#         ',
    '      #::#       #::::#         ',
    '      #:::#.#.#.#:::::.#        ',
    '      #::::#.#.#........#       ',
    '      #..................#      ',
]


def fix28(ink, alpha):
    ink[:13, :] = False
    alpha[:13, :] = False
    ys, xs = np.mgrid[0:ink.shape[0], 0:ink.shape[1]]
    for j, r in enumerate(TOP28):
        y = 6 + j
        for i, ch in enumerate(r):
            x = 4 + i
            if ch == ' ':
                ink[y, x] = False
                alpha[y, x] = False
            elif ch == '#':
                ink[y, x] = True
                alpha[y, x] = True
            elif ch == '.':
                ink[y, x] = False
                alpha[y, x] = True
            elif ch == ':':
                ink[y, x] = bool((x + y) % 2)
                alpha[y, x] = True
    for y in (27, 29):
        xs_ = np.nonzero(alpha[y])[0]
        right = xs_.max()
        ink[y, 20:right] = False
        ink[y, right - 6:right - 2] = True
    for x in range(ink.shape[1]):
        if alpha[35, x] and not ink[35, x] and ink[35, x - 1] and ink[35, x + 1]:
            ink[35, x] = True


def save_rgba(ink, alpha, path):
    a = np.where(ink, 0, 255).astype(np.uint8)
    rgba = np.zeros(ink.shape + (4,), np.uint8)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = a
    rgba[..., 3] = np.where(alpha | ink, 255, 0)
    Image.fromarray(rgba, 'RGBA').save(path)


def crop(ink, alpha):
    ys, xs = np.nonzero(alpha | ink)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    return ink[sl], alpha[sl]


def main():
    os.makedirs(OUT, exist_ok=True)
    s = scene()
    ink, alpha = crop(s['ink'], s['alpha'])
    save_rgba(ink, alpha, os.path.join(OUT, 'neko-v2-scene.png'))
    preview(np.where(alpha, ink, False), os.path.join(OUT, 'neko-v2-scene@3x.png'), 3)
    compare(s['ink'], os.path.join(OUT, 'neko-v2-compare@3x.png'), 3)
    for wd in (48, 28):
        d = head_only(wd)
        ink, alpha = crop(d['ink'], d['alpha'])
        save_rgba(ink, alpha, os.path.join(OUT, 'neko-v2-head-%d.png' % wd))
        preview(np.where(alpha, ink, False), os.path.join(OUT, 'neko-v2-head-%d@6x.png' % wd), 6)


if __name__ == '__main__':
    main()
