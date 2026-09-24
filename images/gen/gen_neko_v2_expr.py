import os
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdart import load_font
from gen_neko_v2 import head_only, crop

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'prototypes', 'neko', 'v2')
EXPR = os.path.join(OUT, 'expressions')
SCRATCH = os.environ.get('NEKO_SCRATCH')

PAD = {48: (3, 10, 12, 1), 28: (2, 6, 7, 1)}
GEOM = {
    48: dict(eyes=((12, 31.5), (30, 31.5)), mx=21, my=39, brow_y=25, clear=(8, 18, 40, 47),
             ear=dict(cols=26, rows=8, dup=(6, 7), n=4)),
    28: dict(eyes=((6.5, 19), (18.5, 19)), mx=13, my=22, brow_y=15, clear=(5, 12, 23, 28),
             ear=dict(cols=16, rows=4, dup=(2, 3), n=2)),
}


def rows_of(s):
    return [r for r in s.strip('\n').split('\n')]


class Face:
    def __init__(self, size):
        self.size = size
        d = head_only(size)
        ink, alpha = crop(d['ink'], d['alpha'])
        l, t, r, b = PAD[size]
        h, w = ink.shape
        self.ox, self.oy = l, t
        self.ink = np.zeros((h + t + b, w + l + r), bool)
        self.alpha = np.zeros_like(self.ink)
        self.ink[t:t + h, l:l + w] = ink
        self.alpha[t:t + h, l:l + w] = alpha
        self.head = self.alpha.copy()
        self.g = GEOM[size]
        x0, y0, x1, y1 = self.g['clear']
        self.ink[t + y0:t + y1, l + x0:l + x1] = False

    def put(self, s, x, y, flip=False):
        rr = rows_of(s)
        if flip:
            rr = [r[::-1] for r in rr]
        H, W = self.ink.shape
        for j, r in enumerate(rr):
            for i, ch in enumerate(r):
                yy, xx = self.oy + y + j, self.ox + x + i
                if not (0 <= yy < H and 0 <= xx < W):
                    continue
                if ch == '#':
                    self.ink[yy, xx] = True
                    self.alpha[yy, xx] = True
                elif ch == 'o':
                    self.ink[yy, xx] = False
                    self.alpha[yy, xx] = True
                elif ch == ':':
                    self.ink[yy, xx] = bool((xx + yy) % 2)
                    self.alpha[yy, xx] = True
                elif ch == '_':
                    if self.head[yy, xx]:
                        self.ink[yy, xx] = False

    def at(self, s, cx, cy, flip=False):
        rr = rows_of(s)
        self.put(s, int(round(cx - len(rr[0]) / 2.0)), int(round(cy - len(rr) / 2.0)), flip)

    def eyes(self, s, mirror=False, dy=0, dx=0, right=None):
        (lx, ly), (rx, ry) = self.g['eyes']
        self.at(s, lx + 0.5 + dx, ly + dy)
        self.at(right or s, rx + 0.5 + dx, ry + dy, flip=mirror and right is None)

    def brows(self, s, dy=0, spread=0):
        (lx, _), (rx, _) = self.g['eyes']
        by = self.g['brow_y'] + dy
        self.at(s, lx + 0.5 - spread, by)
        self.at(s, rx + 0.5 + spread, by, flip=True)

    def mouth(self, s, dy=0, dx=0):
        rr = rows_of(s)
        self.put(s, int(self.g['mx'] + dx - len(rr[0]) // 2), self.g['my'] + dy)

    def cheeks(self, s, dy=0):
        (lx, ly), (rx, ry) = self.g['eyes']
        off = 5 if self.size == 48 else 3
        self.at(s, lx + 0.5 - 1, ly + off + dy)
        self.at(s, rx + 0.5 + 1, ry + off + dy)

    def perk(self):
        e = self.g['ear']
        c0 = self.ox + e['cols']
        top = self.oy
        n = e['n']
        a, b = e['dup']
        for arr in (self.ink, self.alpha):
            blk = arr[top:top + e['rows'], c0:].copy()
            arr[top - n:top + e['rows'], c0:] = False
            arr[top - n:top - n + e['rows'], c0:] = blk
            for k in range(n):
                src = blk[a] if k % 2 == 0 else blk[b]
                arr[top - n + e['rows'] + k, c0:] = src
        self.head = self.alpha.copy()

    def scorch_tuft(self, spikes):
        for s, x, y in spikes:
            self.put(s, x, y)


E48 = dict(
    base="""
.###.
#o###
#####
#####
#####
.###.
""",
    happy="""
..###..
.##.##.
##...##
#.....#
""",
    closed="""
#.....#
##...##
.##.##.
..###..
""",
    laugh="""
##.....
.###...
...###.
.###...
##.....
""",
    squint="""
.#####.
#######
.#####.
""",
    lid="""
#######
.#####.
.#####.
..###..
""",
    lid_low="""
#######
.#####.
..###..
""",
    sleepy="""
#######
.#o###.
..###..
""",
    big="""
..###..
.#####.
#oo####
#oo####
#######
#######
.#####.
..###..
""",
    wet="""
..###..
.#####.
#oo####
#oo####
#######
#####o#
.#####.
..###..
""",
    ring="""
..###..
.#...#.
#.....#
#..#..#
#.....#
.#...#.
..###..
""",
    ringbig="""
..#####..
.##...##.
##.....##
#.......#
#...#...#
#.......#
##.....##
.##...##.
..#####..
""",
    dot="""
.##.
####
####
.##.
""",
    dollar="""
..#..
.####
#.#..
.###.
..#.#
####.
..#..
""",
    spiral="""
.#####.
#.....#
#.###.#
#.#.#.#
#.#...#
#..###.
.#.....
""",
    x="""
##..##
.####.
..##..
.####.
##..##
""",
    angry="""
##...
####.
#####
#####
.###.
""",
    sad="""
...##
.####
#o###
#####
.###.
""",
    side="""
..###..
.#...#.
###...#
###...#
###...#
.#...#.
..###..
""",
    side_lid="""
#######
####...
.##....
""",
    mask_hole="""
..ooooo..
.ooooooo.
ooooooooo
ooooooooo
ooooooooo
ooooooooo
ooooooooo
.ooooooo.
""",
    mask_lid="""
ooooooooo
ooooooooo
ooooooooo
ooooooooo
.ooooooo.
""",
)

M48 = dict(
    w="""
#...#...#
##.###.##
.###.###.
""",
    open="""
#.......#
#########
.#######.
..##o##..
...###...
""",
    laugh="""
#.........#
###########
.#########.
.####o####.
..##ooo##..
...#####...
""",
    frown="""
..###..
.#...#.
#.....#
""",
    wobble="""
.##..##..##.
#..##..##..#
""",
    teeth="""
###########
#..#...#..#
###########
#..#...#..#
###########
""",
    o="""
.##.
#..#
#..#
.##.
""",
    bigo="""
..###..
.#####.
#######
#######
#######
.#####.
..###..
""",
    talk="""
.#######.
.#ooooo#.
..#ooo#..
...###...
""",
    flat="""
#######
""",
    smirk="""
.........#
........##
#......##.
.#######..
""",
    tongue="""
#...#...#
##.###.##
.###.###.
...#o#...
...#o#...
....#....
""",
    grin="""
##.......##
.##..#..##.
..###.###..
""",
    tiny="""
###
""",
    wail="""
.##..##..##.
#..##..##..#
#oooooooooo#
.#oooooooo#.
..########..
""",
    cough="""
.###.
#...#
.###.
""",
)

B48 = dict(
    angry="""
##.....
.####..
....###
""",
    sad="""
....###
..###..
##.....
""",
    flat="""
######
""",
    think="""
..####
##....
""",
)

P48 = dict(
    excl="""
###
###
###
###
###
.#.
...
###
###
""",
    q="""
.#####.
##...##
.....##
....##.
...##..
...##..
.......
...##..
...##..
""",
    sweat="""
...#...
..###..
.##o##.
##ooo##
#ooooo#
#ooooo#
##ooo##
.#####.
""",
    vein="""
..##...##..
..##...##..
####...####
####...####
...........
####...####
####...####
..##...##..
..##...##..
""",
    zbig="""
######
######
...##.
..##..
.##...
######
######
""",
    zsmall="""
####
..#.
.#..
####
""",
    spark="""
...#...
...#...
..###..
#######
..###..
...#...
...#...
""",
    twink="""
.#.
###
.#.
""",
    star="""
...#...
..###..
#######
.#####.
..###..
.##.##.
.#...#.
""",
    arcs="""
#....#..
.#....#.
.#....#.
.#....#.
.#....#.
#....#..
""",
    tear="""
..#..
.#o#.
#ooo#
#ooo#
.###.
""",
    blush="""
..#..#..#
.#..#..#.
""",
    puff="""
...###.....
..#ooo#.##.
.#ooooo#oo#
#ooooooooo#
#ooooooooo#
.#########.
""",
    puff_s="""
.##.
#oo#
.##.
""",
    soot="""
..::::..
.::::::.
::::::::
.::::::.
""",
    soot_s="""
.::::.
::::::
.::::.
""",
    gloom="""
#..#..#
#..#..#
#..#..#
#..#..#
#..#..#
...#...
...#...
""",
    shake_l="""
##..
.##.
..##
""",
    tick_l="""
##...
.##..
..##.
""",
    ribbon="""
.....##
...####
######.
####...
#####..
..#####
....###
""",
    bubble="""
.###.
#ooo#
#oo.#
#ooo#
.###.
""",
)

E28 = dict(
    base="##\n##\n##",
    happy=".##.\n#..#",
    closed="#..#\n.##.",
    laugh="##..\n..##\n##..",
    squint="####\n.##.",
    lid="####\n.##.",
    lid_low="####",
    sleepy="####\n.#o.",
    big=".##.\n#o##\n####\n.##.",
    wet=".##.\n#o##\n###o\n.##.",
    ring=".###.\n#...#\n#.#.#\n#...#\n.###.",
    dot="##\n##",
    dollar=".#.\n###\n#..\n###\n..#\n###\n.#.",
    spiral=".###.\n#...#\n#.#.#\n#..#.\n.#...",
    x="#.#\n.#.\n#.#",
    angry="#..\n##.\n##.",
    sad="..#\n.##\n.##",
    side=".##.\n##.#\n##.#\n.##.",
    side_lid="####\n##..",
    mask_hole=".oooo.\noooooo\noooooo\n.oooo.",
    mask_lid="oooooo\noooooo\n.oooo.",
)

M28 = dict(
    w="#.#.#\n.#.#.",
    open="#.#.#\n.###.\n..#..",
    laugh="#####\n.#o#.\n..#..",
    frown=".###.\n#...#",
    wobble=".#..#.\n#.##.#",
    teeth="#####\n#.#.#\n#####",
    o=".#.\n#.#\n.#.",
    bigo=".##.\n####\n####\n.##.",
    talk="#.#.#\n.#o#.\n..#..",
    flat="###",
    smirk="....#\n#..#.\n.##..",
    tongue="#.#.#\n.#.#.\n...#.",
    grin="#...#\n.#.#.\n..#..",
    tiny="##",
    wail=".#..#.\n#.##.#\n#oooo#\n.####.",
    cough=".#.\n#.#\n.#.",
)

B28 = dict(
    angry="##..\n..##",
    sad="..##\n##..",
    flat="###",
    think=".##\n#..",
)

P28 = dict(
    excl="##\n##\n##\n..\n##",
    q=".##.\n#..#\n..#.\n.#..\n....\n.#..",
    sweat=".#.\n#o#\n#o#\n.#.",
    vein=".#.#.\n##.##\n.....\n##.##\n.#.#.",
    zbig="####\n..#.\n.#..\n####",
    zsmall="###\n.#.\n###",
    spark="..#..\n..#..\n##.##\n..#..\n..#..",
    twink=".#.\n#.#\n.#.",
    star="..#..\n.###.\n#####\n.#.#.",
    arcs="#...\n.#.#\n.#.#\n#...",
    tear=".#.\n#o#\n.#.",
    blush="#.#.#",
    puff=".##.#.\n#oo#o#\n#oooo#\n.####.",
    puff_s="##\n##",
    soot=":::\n:::",
    soot_s="::",
    gloom="#.#\n#.#\n#.#",
    shake_l="#.\n.#",
    tick_l="#..\n.#.\n..#",
    ribbon="#..\n##.\n###\n##.\n#..",
    bubble=".#.\n#o#\n.#.",
)


def mask_band(f):
    y0, y1 = (26, 38) if f.size == 48 else (16, 22)
    band = np.zeros_like(f.ink)
    band[f.oy + y0:f.oy + y1, :] = True
    f.ink |= band & f.head


def build(name, size):
    f = Face(size)
    big = size == 48
    E, M, B, P = (E48, M48, B48, P48) if big else (E28, M28, B28, P28)
    W = f.ink.shape[1] - f.ox
    (lx, ly), (rx, ry) = f.g['eyes']

    def prop(key, x, y, flip=False):
        f.put(P[key], x, y, flip)

    def pick(a, b):
        return a if big else b

    def sweat_r():
        prop('sweat', *pick((W - 11, 4), (W - 7, 2)))

    def excl(dx=0):
        prop('excl', *pick((W - 8 + dx, -9), (W - 4 + dx, -6)))

    def vein():
        prop('vein', *pick((W - 13, -8), (W - 7, -5)))

    if name == 'neutral':
        f.eyes(E['base']); f.mouth(M['w'])
    elif name == 'smiling':
        f.eyes(E['happy']); f.mouth(M['w'])
    elif name == 'happy':
        f.eyes(E['happy']); f.mouth(M['open'])
        if big:
            f.cheeks(P['blush'], dy=1)
    elif name == 'laugh':
        f.eyes(E['laugh'], mirror=True); f.mouth(M['laugh'])
        if big:
            prop('tick_l', 1, -1); prop('tick_l', 5, -7)
            prop('tick_l', 38, -8, flip=True); prop('tick_l', 46, -2, flip=True)
        else:
            prop('tick_l', 0, 0); prop('tick_l', 24, -3, flip=True)
    elif name == 'excited':
        f.eyes(E['wet']); f.mouth(M['open'])
        if big:
            f.cheeks(P['blush'], dy=2)
        prop('spark', *pick((W - 9, -9), (W - 5, -6))); prop('twink', *pick((-2, 0), (-1, -1)))
    elif name == 'rich':
        f.eyes(E['dollar']); f.mouth(M['open'])
        prop('spark', *pick((W - 9, -9), (W - 5, -6)))
        if big:
            prop('spark', -3, -3); prop('twink', W - 1, 5)
        else:
            prop('twink', -1, -1)
    elif name == 'wink':
        f.at(E['happy'], lx + 0.5, ly + pick(0.5, 0))
        f.at(E['base'], rx + 0.5, ry)
        f.mouth(M['w'])
        prop('twink', *pick((W - 6, -4), (W - 4, -4)))
    elif name == 'smug':
        f.eyes(E['lid_low'], dy=1)
        f.mouth(M['smirk'], dx=1)
    elif name == 'talking':
        f.eyes(E['base']); f.mouth(M['talk'])
    elif name == 'thinking':
        f.eyes(E['base'], dy=-1, dx=1)
        f.at(B['flat'], rx + 1.5, f.g['brow_y'] - pick(2, 1))
        f.mouth(M['flat'] if big else "##", dx=pick(2, 1), dy=1)
        prop('q', *pick((W - 11, -10), (W - 6, -6)))
    elif name == 'listening':
        f.perk()
        f.eyes(E['squint'], dy=0.5)
        f.mouth(M['w'])
        prop('arcs', *pick((W - 13, 1), (W - 7, -1)))
    elif name == 'focused':
        f.eyes(E['lid'], dy=1); f.brows(B['angry'], dy=1)
        f.mouth(M['flat'], dy=1)
    elif name == 'turning':
        f.eyes(E['lid'], dy=1, dx=1); f.brows(B['flat'], dy=2)
        f.mouth(M['tongue'])
    elif name == 'sneaky':
        f.eyes(E['side_lid'], dy=1)
        f.mouth(M['grin'])
    elif name == 'shifty':
        f.eyes(E['side'])
        f.brows(B['flat'], dy=1)
        f.mouth(M['wobble'], dy=1)
    elif name == 'surprise':
        f.eyes(E['big']); f.mouth(M['o'])
        excl()
    elif name == 'shocked':
        f.eyes(E.get('ringbig', E['ring'])); f.mouth(M['bigo'])
        excl(-3); excl(2)
    elif name == 'caught':
        f.eyes(E['ring']); f.mouth(M['tiny'], dy=1)
        prop('gloom', *pick((18, 14), (11, 10)))
        sweat_r(); excl(2)
    elif name == 'nervous':
        f.eyes(E['dot']); f.mouth(M['wobble'], dy=1)
        sweat_r()
    elif name == 'panicked':
        f.eyes(E.get('ringbig', E['ring'])); f.brows(B['sad'], dy=pick(-2, -1))
        f.mouth(M['wail'])
        sweat_r()
        prop('sweat', *pick((-4, 12), (-2, 7)), flip=True)
        if big:
            prop('tick_l', 1, -1); prop('tick_l', 46, -2, flip=True)
    elif name == 'sad':
        f.eyes(E['sad'], mirror=True)
        f.brows(B['sad'], dy=-1)
        f.mouth(M['frown'], dy=1)
    elif name == 'crying':
        f.eyes(E['wet'])
        f.brows(B['sad'], dy=-1)
        f.mouth(M['wobble'], dy=pick(2, 1))
        if big:
            f.at(P['tear'], lx + 0.5, ly + 7.5); f.at(P['tear'], rx + 1.5, ry + 7.5)
        else:
            f.at(P['tear'], lx - 0.5, ly + 4); f.at(P['tear'], rx + 1.5, ry + 4)
    elif name == 'upset':
        f.eyes(E['angry'], mirror=True, dy=0.5)
        f.brows(B['angry'])
        f.mouth(M['frown'], dy=1)
        vein()
    elif name == 'raged':
        f.eyes(E['angry'], mirror=True, dy=0.5)
        f.brows(B['angry'])
        f.mouth(M['teeth'])
        vein()
        prop('vein', *pick((-2, -2), (-1, -2)))
    elif name == 'dizzy':
        f.eyes(E['spiral'], mirror=True); f.mouth(M['wobble'], dy=1)
        if big:
            prop('star', 2, -4); prop('twink', 20, -9); prop('star', W - 12, -8)
        else:
            prop('twink', 1, -3); prop('twink', 12, -6); prop('twink', W - 6, -5)
    elif name == 'charred':
        f.eyes(E['x']); f.mouth(M['cough'], dy=1)
        if big:
            prop('soot', 7, 19); prop('soot_s', 33, 21); prop('soot', 31, 41); prop('soot_s', 9, 42)
            f.put(".#\n#.\n.#\n#.\n.#\n#.", 21, 3); f.put("#.\n.#\n#.\n.#\n#.\n.#", 26, 2); f.put(".#\n#.\n.#\n#.\n.#", 31, 4)
            prop('puff', 20, -8); prop('puff_s', 33, -9)
        else:
            prop('soot', 4, 13); prop('soot_s', 20, 24)
            prop('puff', 10, -6)
    elif name == 'sleepy':
        f.eyes(E['sleepy'], dy=1); f.mouth(M['w'])
        prop('zsmall', *pick((W - 8, -2), (W - 5, -2)))
    elif name == 'sleeping':
        f.eyes(E['closed'], dy=1); f.mouth(M['w'])
        if big:
            prop('zbig', W - 9, -9); prop('zsmall', W - 14, 0)
        else:
            prop('zbig', W - 5, -6); prop('zsmall', W - 8, -1)
    elif name.startswith('mask'):
        mask_band(f)
        mood = name.split('-')[1]
        narrow = mood in ('focused', 'smug')
        hole = E['mask_lid'] if narrow else E['mask_hole']
        dyh = 1 if narrow else 0
        f.at(hole, lx + 0.5, ly + dyh); f.at(hole, rx + 0.5, ry + dyh)
        prop('ribbon', *pick((50, 28), (30, 16)))
        if mood == 'neutral':
            f.eyes(pick(E['base'], E['dot'])); f.mouth(M['w'])
        elif mood == 'focused':
            f.eyes(E['lid_low'], dy=1); f.mouth(M['flat'], dy=1)
        elif mood == 'smug':
            f.eyes(E['lid_low'], dy=1); f.mouth(M['smirk'], dx=1)
        elif mood == 'panic':
            f.eyes(pick(E['ring'], "#")); f.mouth(M['bigo'])
            sweat_r()
    else:
        raise KeyError(name)
    return f


NAMES = [
    'neutral', 'smiling', 'happy', 'laugh', 'excited', 'rich', 'wink', 'smug',
    'talking', 'thinking', 'listening', 'focused', 'turning', 'sneaky', 'shifty', 'surprise',
    'shocked', 'caught', 'nervous', 'panicked', 'sad', 'crying', 'upset', 'raged',
    'dizzy', 'charred', 'sleepy', 'sleeping', 'mask-neutral', 'mask-focused', 'mask-smug', 'mask-panic',
]


def to_rgba(f):
    a = np.where(f.ink, 0, 255).astype(np.uint8)
    rgba = np.zeros(f.ink.shape + (4,), np.uint8)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = a
    rgba[..., 3] = np.where(f.alpha | f.ink, 255, 0)
    return Image.fromarray(rgba, 'RGBA')


def sheet(imgs, font, cols=8):
    s48 = imgs[NAMES[0]][48].size
    s28 = imgs[NAMES[0]][28].size
    cw = s48[0] + s28[0] + 14
    ch = s48[1] + 16
    rows = (len(NAMES) + cols - 1) // cols
    W, Hh = cols * cw + 8, rows * ch + 8
    im = Image.new('RGBA', (W, Hh), (255, 255, 255, 255))
    d = ImageDraw.Draw(im)
    for k, n in enumerate(NAMES):
        cx, cy = 4 + (k % cols) * cw, 4 + (k // cols) * ch
        im.alpha_composite(imgs[n][48], (cx + 4, cy + 2))
        im.alpha_composite(imgs[n][28], (cx + 8 + s48[0], cy + 2 + s48[1] - s28[1]))
        tw = d.textlength(n, font=font)
        d.text((cx + (cw - tw) // 2, cy + s48[1] + 4), n, fill=(0, 0, 0, 255), font=font)
    rgb = np.array(im.convert('L'))
    bw = Image.fromarray(np.where(rgb < 128, 0, 255).astype(np.uint8), 'L')
    return bw


def main():
    os.makedirs(EXPR, exist_ok=True)
    font = load_font(8)
    imgs = {}
    for n in NAMES:
        imgs[n] = {}
        for sz in (48, 28):
            f = build(n, sz)
            im = to_rgba(f)
            im.save(os.path.join(EXPR, 'neko-%s-%d.png' % (n, sz)))
            imgs[n][sz] = im
    sh = sheet(imgs, font)
    sh.save(os.path.join(OUT, 'neko-v2-expressions-sheet.png'))
    sh.resize((sh.width * 3, sh.height * 3), Image.NEAREST).save(os.path.join(OUT, 'neko-v2-expressions-sheet@3x.png'))
    if SCRATCH:
        for sz, sc in ((48, 5), (28, 6)):
            tiles = [imgs[n][sz] for n in NAMES]
            w, h = tiles[0].size
            out = Image.new('RGBA', (8 * (w + 4), 4 * (h + 4)), (177, 175, 168, 255))
            for k, t in enumerate(tiles):
                out.alpha_composite(t, ((k % 8) * (w + 4), (k // 8) * (h + 4)))
            out.resize((out.width * sc, out.height * sc), Image.NEAREST).save(os.path.join(SCRATCH, 'all%d.png' % sz))


if __name__ == '__main__':
    main()
