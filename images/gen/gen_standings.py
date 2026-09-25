import os
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdart import Canvas, bayer, dilate
from gen_neko_v2 import disc_grow, shift

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
EXPR = os.path.join(ROOT, 'prototypes', 'neko', 'v2', 'expressions')
OUT = os.path.join(ROOT, 'source', 'images')
PREVIEW = os.environ.get('PREVIEW_DIR')

W, H = 400, 240
BANNER = (16, 44, 383, 62)
BOARD = (16, 68, 384, 240)
BEZEL = 7
TITLE = 'MOST WANTED'
TITLE_TOP = 5
HEAD_XS = (6, 364)
HEAD_Y = 5
PAGES = {
    'streak': dict(heads=('laugh', 'excited'), flip=(False, False), deco='flame'),
    'total': dict(heads=('rich', 'happy'), flip=(False, False), deco='coin'),
}
BOLT_YS = [72, 148, 224]


def checker(x, y):
    return (x + y) % 2 == 0


def glyph(rows):
    return [r for r in rows.strip().split()]


LETTERS = {
    'S': glyph('.#### ##... ##... .###. ...## ...## ####.'),
    'T': glyph('###### ..##.. ..##.. ..##.. ..##.. ..##.. ..##..'),
    'A': glyph('.###. ##.## ##.## ##### ##.## ##.## ##.##'),
    'N': glyph('##..## ###.## ###.## ###### ##.### ##.### ##..##'),
    'D': glyph('####. ##.## ##.## ##.## ##.## ##.## ####.'),
    'I': glyph('## ## ## ## ## ## ##'),
    'G': glyph('.##### ##.... ##.... ##.### ##..## ##..## .#####'),
    'M': glyph('##...## ###.### ####### ##.#.## ##...## ##...## ##...##'),
    'W': glyph('##...## ##...## ##...## ##.#.## ####### ###.### ##...##'),
    'O': glyph('.###. ##.## ##.## ##.## ##.## ##.## .###.'),
    'E': glyph('##### ##... ##... ####. ##... ##... #####'),
    ' ': glyph('. . . . . . .'),
}


def open_disc(m, r):
    return disc_grow(~disc_grow(~m, r), r)


def word_mask(text, cw, ch, gap):
    widths = [len(LETTERS[c][0]) * cw for c in text]
    total = sum(widths) + gap * (len(text) - 1)
    m = np.zeros((7 * ch, total), bool)
    x = 0
    for c, w in zip(text, widths):
        for j, row in enumerate(LETTERS[c]):
            for i, v in enumerate(row):
                if v == '#':
                    m[j * ch:(j + 1) * ch, x + i * cw:x + (i + 1) * cw] = True
        x += w + gap
    return m


def close_disc(m, r, pad=8):
    p = np.pad(m, pad)
    p = ~disc_grow(~disc_grow(p, r), r)
    return p[pad:-pad, pad:-pad]


def fill_holes(m):
    free = ~m
    reach = np.zeros_like(m)
    reach[0, :] = free[0, :]
    reach[-1, :] = free[-1, :]
    reach[:, 0] = free[:, 0]
    reach[:, -1] = free[:, -1]
    while True:
        nxt = dilate(reach) & free
        if (nxt == reach).all():
            return ~reach
        reach = nxt


def wordmark(c, text, cx, top, cw=4, ch=4, gap=3, depth=3, rnd=1.6, close=6.0, inset=8, side=2, low=False):
    wm = word_mask(text, cw, ch, gap)
    h, w = wm.shape
    x0 = cx - (w + depth) // 2
    m = np.zeros((H, W), bool)
    m[top:top + h, x0:x0 + w] = wm
    m = open_disc(m, rnd)
    o1 = disc_grow(m, 2.2)
    ext = o1.copy()
    for s_ in range(1, depth + 1):
        ext |= shift(o1, s_, s_)
    ext = fill_holes(close_disc(ext, close))
    ys, xs = np.nonzero(ext)
    ext[ys.min():ys.max() + 1, xs.min() + inset:xs.max() + 1 - inset] = True
    o2 = disc_grow(ext, 1.2)
    o3 = disc_grow(o2, 1.5)
    sh = disc_grow(shift(o3, 2, 2), 1.0) & ~o3
    c.ink[sh] = checker(c.xs, c.ys)[sh] | c.ink[sh]
    c.ink[o3] = True
    c.ink[o2] = False
    c.ink[ext] = True
    if side:
        sd = np.zeros_like(m)
        for s_ in range(1, side + 1):
            sd |= shift(m, s_, s_)
        sd &= ~m
        c.ink[sd] = checker(c.xs, c.ys)[sd]
    c.ink[m] = False
    if low:
        lo = m & ~shift(m, 0, -1)
        c.ink[lo] = checker(c.xs, c.ys)[lo]
    return o2


def backdrop(c):
    x, y = c.xs, c.ys
    u = (x + y + 8) // 16
    v = (x - y + 1608) // 16
    alt = (u + v) % 2 == 0
    c.ink[:] = np.where(alt, bayer(13)(x, y), True)
    edge = ((x + y + 8) % 16 == 0) | ((x - y + 1608) % 16 == 0)
    c.ink[edge & (x % 2 == 0)] = False


def sprite(c, rows, x, y, val=False, outline=True):
    rows = rows.strip().split()
    m = np.zeros((H, W), bool)
    for j, r in enumerate(rows):
        for i, ch_ in enumerate(r):
            if ch_ == '#':
                xx, yy = x + i, y + j
                if 0 <= xx < W and 0 <= yy < H:
                    m[yy, xx] = True
    if outline:
        c.ink[disc_grow(m, 1) & ~m] = not val
    c.ink[m] = val
    return m


SPARK_XS = """
.#.
###
.#.
"""
SPARK_S = """
..#..
..#..
#####
..#..
..#..
"""
SPARK_M = """
...#...
...#...
..###..
#######
..###..
...#...
...#...
"""
SPARK_L = """
....#....
....#....
....#....
...###...
#########
...###...
....#....
....#....
....#....
"""
def load_head(name):
    im = np.array(Image.open(os.path.join(EXPR, 'neko-%s-28.png' % name)).convert('LA'))
    ink = im[..., 0] < 128
    al = im[..., 1] > 127
    seen = np.zeros_like(al)
    best = None
    for sy, sx in zip(*np.nonzero(al)):
        if seen[sy, sx]:
            continue
        comp = []
        stack = [(sy, sx)]
        seen[sy, sx] = True
        while stack:
            py, px = stack.pop()
            comp.append((py, px))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    qy, qx = py + dy, px + dx
                    if 0 <= qy < al.shape[0] and 0 <= qx < al.shape[1] and al[qy, qx] and not seen[qy, qx]:
                        seen[qy, qx] = True
                        stack.append((qy, qx))
        if best is None or len(comp) > len(best):
            best = comp
    keep = np.zeros_like(al)
    for py, px in best:
        keep[py, px] = True
    ys, xs = np.nonzero(keep)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    return ink[sl] & keep[sl], keep[sl]


def head(c, name, x, y, flip=False):
    ink, al = load_head(name)
    if flip:
        ink, al = ink[:, ::-1], al[:, ::-1]
    h, w = al.shape
    A = np.zeros((H, W), bool)
    I = np.zeros((H, W), bool)
    A[y:y + h, x:x + w] = al
    I[y:y + h, x:x + w] = ink
    halo = disc_grow(A, 2.2)
    c.ink[disc_grow(halo, 1.5) & ~halo] = True
    c.ink[halo] = False
    c.ink[A] = I[A]


def banner(c):
    x0, y0, x1, y1 = BANNER
    sh = c.mask(lambda d: d.rounded_rectangle([x0 + 2, y0 + 2, x1 + 2, y1 + 2], 5, fill=1))
    c.ink[sh] = checker(c.xs, c.ys)[sh] | c.ink[sh]
    outer = c.mask(lambda d: d.rounded_rectangle([x0, y0, x1, y1], 5, fill=1))
    body = c.mask(lambda d: d.rounded_rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], 4, fill=1))
    c.ink[outer] = False
    c.ink[body] = True
    c.rect(x0 + 3, y0 + 3, x1 - 2, y1 - 2, False)


def board(c):
    x0, y0, x1, y1 = BOARD
    b = BEZEL
    c.rect(x0 - b - 1, y0 - 4, x1 + b + 1, H, True)
    c.rect(x0 - b, y0 - 3, x1 + b, H, False)
    c.rect(x0 - b + 1, y0 - 2, x1 + b - 1, H, checker)
    c.rect(x0 - 2, y0 - 1, x1 + 2, H, False)
    c.rect(x0 - 1, y0, x1 + 1, H, True)
    c.rect(x0, y0, x1, y1, True)


def spark(c, rows, cx, cy):
    n = len(rows.strip().split())
    sprite(c, rows, cx - n // 2, cy - n // 2)


BOLT = """
.##.
####
###.
.#..
"""


def bolts(c):
    x0, y0, x1, y1 = BOARD
    for y in BOLT_YS:
        for x in (x0 - BEZEL + 1, x1 + 2):
            m = np.zeros((H, W), bool)
            for j, r in enumerate(BOLT.strip().split()):
                for i, ch_ in enumerate(r):
                    m[y + j, x + i] = ch_ == '#'
            ring = c.rect_mask(x - 1, y - 1, x + 5, y + 5) & ~c.rect_mask(x, y, x + 4, y + 4)
            ring &= ~(c.rect_mask(x - 1, y - 1, x, y) | c.rect_mask(x + 4, y - 1, x + 5, y) |
                      c.rect_mask(x - 1, y + 4, x, y + 5) | c.rect_mask(x + 4, y + 4, x + 5, y + 5))
            c.ink[ring] = True
            c.ink[c.rect_mask(x, y, x + 4, y + 4)] = True
            c.ink[m] = False


def ss_mask(fn, k=6):
    im = Image.new('L', (W * k, H * k), 0)
    fn(ImageDraw.Draw(im), k)
    return np.asarray(im.resize((W, H), Image.BOX), np.float32) / 255.0 >= 0.5


FLAME_OUT = [
    [(-6.5, 3), (-4.5, -3), (-1.5, -7), (0.5, -12.5), (1.8, -6), (4, -3.5), (5.5, -8.5), (7.2, -2), (7, 3)],
    [(-6.5, 1), (-8, -5.5), (-3.5, -2)],
]
FLAME_IN = [(-3.5, 3.5), (-1, -1.5), (0.8, -5.5), (1.6, -0.5), (3.5, 3.5)]


def flame(c, cx, cy, s=1.2, mirror=False):
    sx = -s if mirror else s

    def P(pts, k):
        return [((cx + x * sx) * k, (cy + y * s) * k) for x, y in pts]

    def outer(d, k):
        d.ellipse([(cx - 7 * s) * k, (cy - 3.5 * s) * k, (cx + 7 * s) * k, (cy + 8 * s) * k], fill=255)
        for p in FLAME_OUT:
            d.polygon(P(p, k), fill=255)

    def inner(d, k):
        d.ellipse([(cx - 3.6 * s) * k, (cy + 0.5 * s) * k, (cx + 3.6 * s) * k, (cy + 7.2 * s) * k], fill=255)
        d.polygon(P(FLAME_IN, k), fill=255)

    o, i = ss_mask(outer), ss_mask(inner)
    c.ink[disc_grow(o, 1.5)] = True
    c.ink[o] = False
    c.ink[i] = True


DOLLAR = """
..#..
.####
#.#..
.###.
..#.#
####.
..#..
"""


def coin(c, cx, cy, r=8.5):
    body = c.disc_mask(cx, cy, r)
    c.ink[disc_grow(body, 1.5)] = True
    c.ink[body] = False
    rim = c.ring_mask(cx, cy, r - 1.5, r) & ((c.xs + 0.5 - cx) + (c.ys + 0.5 - cy) > 2)
    c.ink[rim] = checker(c.xs, c.ys)[rim]
    rows = DOLLAR.strip().split()
    x0, y0 = int(round(cx - 2.5)), int(round(cy - 3.5))
    for j, row in enumerate(rows):
        for i, ch_ in enumerate(row):
            if ch_ == '#':
                c.ink[y0 + j, x0 + i] = True


def sparkles(c, plate):
    ys, xs = np.nonzero(plate)
    l, r = xs.min(), xs.max()
    for rows, cx, cy in [
        (SPARK_L, l + 2, 6), (SPARK_M, r - 2, 36),
        (SPARK_XS, 22, 41), (SPARK_XS, 377, 41),
        (SPARK_S, 3, 98), (SPARK_XS, 4, 150), (SPARK_S, 3, 208),
        (SPARK_XS, 395, 84), (SPARK_S, 396, 168), (SPARK_XS, 395, 226),
    ]:
        spark(c, rows, cx, cy)


def decorate(c, kind, plate):
    ys, xs = np.nonzero(plate)
    gl = (HEAD_XS[0] + 34 + xs.min()) // 2
    gr = (HEAD_XS[1] - 3 + xs.max()) // 2 + 1
    if kind == 'flame':
        flame(c, gl, 21)
        flame(c, gr, 21, mirror=True)
    elif kind == 'coin':
        coin(c, gl, 21)
        coin(c, gr, 21)
        spark(c, SPARK_S, gl + 7, 9)
        spark(c, SPARK_S, gr - 7, 9)


def build(page):
    cfg = PAGES[page]
    c = Canvas(W, H, 1)
    backdrop(c)
    board(c)
    bolts(c)
    banner(c)
    for n, x, f in zip(cfg['heads'], HEAD_XS, cfg['flip']):
        head(c, n, x, HEAD_Y, f)
    plate = wordmark(c, TITLE, 200, TITLE_TOP)
    decorate(c, cfg['deco'], plate)
    sparkles(c, plate)
    return c


def check(c):
    assert not c.ink[47:60, 20:381].any(), 'banner interior not clean'
    x0, y0, x1, y1 = BOARD
    assert c.ink[y0:y1, x0:x1].all(), 'board interior not solid black'


def main():
    for page in PAGES:
        c = build(page)
        check(c)
        c.save(os.path.join(OUT, 'standings-%s.png' % page))
        if PREVIEW:
            c.preview(os.path.join(PREVIEW, 'standings-%s@3x.png' % page), 3)


if __name__ == '__main__':
    main()
