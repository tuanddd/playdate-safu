# Title-screen background variants for Safu.
#
# The title art (SAFU, dial, CRACK IT, both robbers) is solid black on white, so
# any background that goes dark eats it. Everything here stays a light field:
# thin black linework and low-density ordered dither only.
#
# The protection mask follows the artwork's actual contour - no bounding boxes.
# Ink is morphologically closed to seal the dial's tick gaps, the true outside is
# flooded from the top row alone (both robbers run off the bottom and side edges,
# so seeding those would leak straight into their bodies), and whatever the flood
# cannot reach is interior: letter counters, eye holes, the dial face, the
# pointing hand, the right robber's torso. Dilating that gives the halo.
import math, subprocess, collections

W, H = 400, 240
DIAL = (206, 130, 66)
SRC = 'images/title-robbers-1bit.png'
OUT = 'images'


def ss(e0, e1, v):
    t = max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def rnd(seed):
    s = [seed & 0xffffffff]
    def f():
        s[0] = (s[0] * 1664525 + 1013904223) & 0xffffffff
        return s[0] / 4294967296
    return f


class Buf:
    def __init__(self, fill=255):
        self.g = [[fill] * W for _ in range(H)]

    def px(self, x, y, v):
        if 0 <= x < W and 0 <= y < H:
            self.g[y][x] = v

    def rect(self, x0, y0, x1, y1, v):
        for y in range(max(0, int(y0)), min(H, int(y1))):
            for x in range(max(0, int(x0)), min(W, int(x1))):
                self.g[y][x] = v

    def disc(self, cx, cy, r, v):
        for y in range(max(0, int(cy - r)), min(H, int(cy + r + 1))):
            for x in range(max(0, int(cx - r)), min(W, int(cx + r + 1))):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.g[y][x] = v

    def ring(self, cx, cy, r, w, v):
        for y in range(max(0, int(cy - r - w - 1)), min(H, int(cy + r + w + 2))):
            for x in range(max(0, int(cx - r - w - 1)), min(W, int(cx + r + w + 2))):
                if r - w <= math.hypot(x - cx, y - cy) <= r + w:
                    self.g[y][x] = v

    def seg(self, x0, y0, x1, y1, w, v):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if w <= 1:
                self.px(int(x), int(y), v)
            else:
                self.disc(x, y, w / 2, v)

    def frame(self, x0, y0, x1, y1, w, v):
        self.seg(x0, y0, x1, y0, w, v)
        self.seg(x0, y1, x1, y1, w, v)
        self.seg(x0, y0, x0, y1, w, v)
        self.seg(x1, y0, x1, y1, w, v)

    def poly(self, pts, v):
        ys = [p[1] for p in pts]
        for y in range(max(0, int(min(ys))), min(H, int(max(ys)) + 1)):
            xs = []
            for i in range(len(pts)):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % len(pts)]
                if (ay <= y < by) or (by <= y < ay):
                    xs.append(ax + (bx - ax) * (y - ay) / (by - ay))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(max(0, int(xs[i])), min(W, int(xs[i + 1]) + 1)):
                    self.g[y][x] = v

    def outline(self, pts, w, v):
        for i in range(len(pts)):
            a, bb = pts[i], pts[(i + 1) % len(pts)]
            self.seg(a[0], a[1], bb[0], bb[1], w, v)


def read_pgm(path):
    d = open(path).read().split()
    assert d[0] == 'P2'
    w, h = int(d[1]), int(d[2])
    v = [int(x) for x in d[4:]]
    return w, h, [v[y * w:(y + 1) * w] for y in range(h)]


def write_png(grid, path, dither):
    pgm = f"P2\n{W} {H}\n255\n" + "\n".join(" ".join(str(v) for v in r) for r in grid) + "\n"
    open('/tmp/_safu.pgm', 'w').write(pgm)
    cmd = ['magick', '/tmp/_safu.pgm']
    if dither:
        cmd += ['-ordered-dither', 'o4x4']
    subprocess.run(cmd + ['-depth', '1', path], check=True)


def dilate(m, r):
    t = [[any(row[max(0, x - r):x + r + 1]) for x in range(W)] for row in m]
    return [[any(t[yy][x] for yy in range(max(0, y - r), min(H, y + r + 1)))
             for x in range(W)] for y in range(H)]


def erode(m, r):
    t = [[all(row[max(0, x - r):x + r + 1]) and x >= r and x < W - r for x in range(W)] for row in m]
    return [[all(t[yy][x] for yy in range(max(0, y - r), min(H, y + r + 1)))
             for x in range(W)] for y in range(H)]


# ---------------------------------------------------------------- artwork mask
subprocess.run(['magick', SRC, '-colorspace', 'Gray', '-compress', 'none', 'pgm:/tmp/_tr.pgm'], check=True)
_, _, art = read_pgm('/tmp/_tr.pgm')
ink = [[art[y][x] < 128 for x in range(W)] for y in range(H)]

SEAL = 3
sealed = erode(dilate(ink, SEAL), SEAL)
sealed = [[sealed[y][x] or ink[y][x] for x in range(W)] for y in range(H)]

outside = [[False] * W for _ in range(H)]
q = collections.deque()
for x in range(W):
    if not sealed[0][x]:
        outside[0][x] = True; q.append((x, 0))
while q:
    x, y = q.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < W and 0 <= ny < H and not outside[ny][nx] and not sealed[ny][nx]:
            outside[ny][nx] = True; q.append((nx, ny))

core = [[not outside[y][x] for x in range(W)] for y in range(H)]
prot = dilate(core, 3)

write_png([[0 if prot[y][x] else 255 for x in range(W)] for y in range(H)],
          '/tmp/_mask.png', False)


def compose(b, name, dither=True):
    write_png(b.g, '/tmp/_bg.png', dither)
    subprocess.run(['magick', '/tmp/_bg.png', '-colorspace', 'Gray', '-compress', 'none', 'pgm:/tmp/_bg.pgm'], check=True)
    _, _, bg = read_pgm('/tmp/_bg.pgm')
    out = [[0 if ink[y][x] else (255 if prot[y][x] else (0 if bg[y][x] < 128 else 255))
            for x in range(W)] for y in range(H)]
    write_png(out, f'{OUT}/{name}.png', False)
    subprocess.run(['magick', f'{OUT}/{name}.png', '-filter', 'point', '-resize', '400%',
                    f'{OUT}/{name}@4x.png'], check=True)
    print('wrote', name)


HOR = 176


def floor_plane(b):
    for y in range(HOR):
        b.g[y] = [int(255 - ss(0.15, 1.0, y / HOR) * 26)] * W
    for y in range(HOR, H):
        v = int(226 + ss(0.0, 1.0, (y - HOR) / (H - HOR)) * 29)
        b.g[y] = [v] * W
    b.seg(0, HOR, W, HOR, 2, 0)
    VPY, Y0 = HOR + 5, HOR + 24
    for i in range(-6, 13):
        if i == 0:
            continue
        t = (Y0 - VPY) / (H + 2 - VPY)                         # start below the vanishing point,
        x0 = 200 + i * 74 * t                                  # where the boards have separated
        if -30 < x0 < W + 30:
            b.seg(x0, Y0, 200 + i * 74, H + 2, 1, 0)
    k, prev = 2, HOR
    while True:
        y = HOR + 5.5 * (k ** 1.7)
        if y > H or y - prev < 9:
            break
        b.seg(0, y, W, y, 1, 0)
        prev = y
        k += 1
    b.rect(0, HOR - 13, W, HOR - 11, 0)
    return b


def bolt(b, bx, by, r=5):
    b.disc(bx, by, r, 255); b.ring(bx, by, r, 1.3, 0)
    b.seg(bx - r + 2, by, bx + r - 2, by, 1, 0)
    b.seg(bx, by - r + 2, bx, by + r - 2, 1, 0)


# ------------------------------------------------------- 6. vault + ground (kept)
def vault_ground():
    b = floor_plane(Buf(255))
    cx, cy = DIAL[0], DIAL[1]
    for y in range(HOR):
        for x in range(W):
            d = math.hypot(x - cx, y - cy)
            if 104 < d < 132:
                b.g[y][x] = 202
    for rad in (92, 102, 132):
        for y in range(max(0, cy - rad - 2), min(HOR, cy + rad + 3)):
            for x in range(W):
                if abs(math.hypot(x - cx, y - cy) - rad) <= 1.4:
                    b.g[y][x] = 0
    for i in range(16):
        a = i / 16 * 2 * math.pi - math.pi / 2
        bx, by = cx + math.cos(a) * 117, cy + math.sin(a) * 117
        if by < HOR - 6:
            bolt(b, bx, by)
    return b


# ------------------------------------------------------ 7. safe-deposit box wall
def deposit_wall():
    b = Buf(246)
    r = rnd(21)
    bw, bh = 46, 30
    for row in range(-1, H // bh + 2):
        for col in range(-1, W // bw + 2):
            x = col * bw + (bw // 2 if row % 2 else 0)
            y = row * bh
            b.rect(x + 1, y + 1, x + bw - 1, y + bh - 1, 255)
            b.frame(x + 1, y + 1, x + bw - 2, y + bh - 2, 1.4, 0)
            k = r()
            if k > 0.86:
                b.rect(x + 3, y + 3, x + bw - 3, y + bh - 3, 96)     # open / emptied
            elif k > 0.62:
                b.rect(x + 3, y + 3, x + bw - 3, y + bh - 3, 214)
            b.disc(x + bw - 10, y + bh / 2, 2.4, 0)                  # keyhole
            b.seg(x + 7, y + bh / 2 - 1, x + bw - 17, y + bh / 2 - 1, 1, 0)
    return b


# ----------------------------------------------------------- 8. searchlight beams
def searchlights():
    b = Buf(188)
    for y in range(H):
        for x in range(W):
            v = b.g[y][x]
            for ox, oy, ang, spread in ((-30, -40, 0.72, 0.30), (430, -40, 2.42, 0.30)):
                dx, dy = x - ox, y - oy
                d = math.hypot(dx, dy)
                if d < 1:
                    continue
                off = abs(math.atan2(dy, dx) - ang)
                lit = (1.0 - ss(spread * 0.35, spread, off)) * (1.0 - ss(0.1, 1.0, d / 520))
                v = max(v, int(188 + lit * 67))
            b.g[y][x] = v
    for ox, oy, ang, spread in ((-30, -40, 0.72, 0.30), (430, -40, 2.42, 0.30)):
        for s in (-1, 1):
            a = ang + s * spread
            b.seg(ox, oy, ox + math.cos(a) * 620, oy + math.sin(a) * 620, 1, 0)
    b.seg(0, HOR + 34, W, HOR + 34, 2, 0)
    return b


# --------------------------------------------------------------- 9. blueprint
def blueprint():
    b = Buf(255)
    for y in range(0, H, 8):                                   # fine grid
        for x in range(0, W, 8):
            b.px(x, y, 140)
    for y in range(0, H, 40):
        b.seg(0, y, W, y, 1, 218)
    for x in range(0, W, 40):
        b.seg(x, 0, x, H, 1, 218)
    b.frame(10, 10, W - 11, H - 11, 1.4, 0)                    # sheet border
    b.frame(14, 14, W - 15, H - 15, 1, 0)
    for x, y in ((10, 10), (W - 11, 10), (10, H - 11), (W - 11, H - 11)):
        b.seg(x - 7, y, x + 7, y, 1, 0); b.seg(x, y - 7, x, y + 7, 1, 0)
    cx, cy = DIAL[0], DIAL[1]
    for rad in (86, 118):                                      # dashed setting-out circles
        for i in range(0, 360, 6):
            a0, a1 = math.radians(i), math.radians(i + 3)
            b.seg(cx + math.cos(a0) * rad, cy + math.sin(a0) * rad,
                  cx + math.cos(a1) * rad, cy + math.sin(a1) * rad, 1, 0)
    b.seg(cx - 150, cy, cx + 150, cy, 1, 190)                  # centre lines
    b.seg(cx, cy - 130, cx, cy + 130, 1, 190)
    b.seg(28, 30, 28, 210, 1, 0)                               # dimension rule
    for y in range(30, 211, 20):
        b.seg(24, y, 32, y, 1, 0)
    b.seg(30, 224, 370, 224, 1, 0)
    for x in range(30, 371, 20):
        b.seg(x, 220, x, 228, 1, 0)
    return b


# --------------------------------------------------------------- 10. brick wall
def brick_wall():
    b = Buf(255)
    r = rnd(33)
    bw, bh = 52, 20
    for row in range(-1, H // bh + 2):
        y = row * bh
        off = (bw // 2) if row % 2 else 0
        b.seg(0, y, W, y, 1.6, 0)
        for col in range(-1, W // bw + 2):
            x = col * bw + off
            b.seg(x, y, x, y + bh, 1.6, 0)
            if r() > 0.7:
                b.rect(x + 3, y + 3, x + bw - 3, y + bh - 3, 226)
    for y in range(H - 30, H):                                 # skirting shadow
        v = int(255 - ss(0.0, 1.0, (y - (H - 30)) / 30) * 90)
        for x in range(W):
            b.g[y][x] = min(b.g[y][x], v)
    return b


# ---------------------------------------------------------------- 11. money rain
def money_rain():
    b = Buf(255)
    r = rnd(11)
    for _ in range(38):
        cx, cy = r() * W, r() * H
        a = (r() - 0.5) * 1.5
        w, h = 20 + r() * 8, 10 + r() * 4
        ca, sa = math.cos(a), math.sin(a)
        pts = [(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)
               for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
        b.poly(pts, 255 if r() > 0.4 else 216)
        b.outline(pts, 1.4, 0)
        b.disc(cx, cy, 3.4, 255); b.ring(cx, cy, 3.4, 1.2, 0)
        b.seg(cx - w * 0.6 * ca, cy - w * 0.6 * sa, cx - w * 0.3 * ca, cy - w * 0.3 * sa, 1, 0)
        b.seg(cx + w * 0.3 * ca, cy + w * 0.3 * sa, cx + w * 0.6 * ca, cy + w * 0.6 * sa, 1, 0)
    for _ in range(22):                                        # loose coins
        cx, cy, rad = r() * W, r() * H, 4 + r() * 4
        b.disc(cx, cy, rad, 255); b.ring(cx, cy, rad, 1.3, 0)
        b.ring(cx, cy, rad * 0.55, 1, 0)
    return b


# ---------------------------------------------------------------- 12. laser grid
def laser_grid():
    b = Buf(255)
    beams = [(0, 40, W, 150), (W, 26, 0, 132), (0, 96, W, 214), (W, 84, 0, 198),
             (0, 158, W, 62), (W, 210, 0, 70)]
    for x0, y0, x1, y1 in beams:
        for pad, v in ((5, 232), (3, 196)):
            n = W * 2
            for i in range(n + 1):
                t = i / n
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                for o in range(-pad, pad + 1):
                    if 0 <= int(y) + o < H and 0 <= int(x) < W:
                        b.g[int(y) + o][int(x)] = min(b.g[int(y) + o][int(x)], v)
        b.seg(x0, y0, x1, y1, 1, 0)
    for x0, y0, x1, y1 in beams:                               # wall emitters
        for ex, ey in ((x0, y0), (x1, y1)):
            ex = min(max(ex, 5), W - 6)
            b.rect(ex - 5, ey - 6, ex + 6, ey + 7, 255)
            b.frame(ex - 5, ey - 6, ex + 5, ey + 6, 1.4, 0)
            b.disc(ex, ey, 2, 0)
    return b


# ------------------------------------------------ 13. searchlights, hard contrast
def searchlights_hard():
    b = Buf(150)
    for y in range(H):                                         # dark room, darker up top
        b.g[y] = [int(112 + ss(0.0, 1.0, y / H) * 52)] * W
    lamps = ((-26, -36, 0.66, 0.27), (426, -36, math.pi - 0.66, 0.27))
    for y in range(H):
        for x in range(W):
            lit = 0.0
            for ox, oy, ang, spread in lamps:
                dx, dy = x - ox, y - oy
                d = math.hypot(dx, dy)
                if d < 1:
                    continue
                off = abs(math.atan2(dy, dx) - ang)
                cone = 1.0 - ss(spread * 0.74, spread, off)     # tight shoulder
                lit = max(lit, cone * (1.0 - ss(0.18, 1.15, d / 540)))
            base = b.g[y][x]
            b.g[y][x] = int(base + lit * (255 - base))
    for ox, oy, ang, spread in lamps:                          # hard beam edges
        for s_ in (-1, 1):
            a = ang + s_ * spread
            b.seg(ox, oy, ox + math.cos(a) * 640, oy + math.sin(a) * 640, 1.6, 0)
    r = rnd(41)
    for _ in range(300):                                       # dust in the beams
        x, y = r() * W, r() * H
        for ox, oy, ang, spread in lamps:
            off = abs(math.atan2(y - oy, x - ox) - ang)
            if off < spread * 0.8:
                b.px(int(x), int(y), 255 if r() > 0.35 else 120)
                break
    b.disc(110, 232, 66, 255)                                  # pools where they land
    b.disc(296, 232, 66, 255)
    b.ring(110, 232, 66, 1.4, 0)
    b.ring(296, 232, 66, 1.4, 0)
    b.seg(0, HOR + 30, W, HOR + 30, 2, 0)
    return b


# ------------------------------------------------- 14. vault door set in brickwork
def vault_brick():
    b = floor_plane(Buf(255))
    cx, cy = DIAL[0], DIAL[1]
    r = rnd(33)
    bw, bh, PLINTH = 52, 20, 13
    base = HOR - PLINTH
    for row in range(-1, base // bh + 2):                      # brickwork down to the plinth
        y = row * bh
        if y >= base:
            break
        yb = min(y + bh, base)
        b.seg(0, y, W, y, 1.6, 0)
        for col in range(-1, W // bw + 2):
            x = col * bw + ((bw // 2) if row % 2 else 0)
            b.seg(x, y, x, yb, 1.6, 0)
            if r() > 0.68:
                b.rect(x + 3, y + 3, x + bw - 3, yb - 3, 228)
    b.rect(0, base, W, HOR, 238)                               # plinth the wall stands on
    b.seg(0, base, W, base, 1.6, 0)
    b.seg(0, HOR, W, HOR, 2, 0)
    for y in range(HOR + 1, HOR + 10):                         # contact shadow onto the floor
        v = 192 + (y - HOR) * 7
        for x in range(W):
            b.g[y][x] = min(b.g[y][x], v)
    for y in range(HOR):                                       # recess: jamb, then door face
        for x in range(W):
            d = math.hypot(x - cx, y - cy)
            if d < 118:
                b.g[y][x] = 208 if 96 < d < 116 else 248
            elif d < 133:
                b.g[y][x] = 216
    for i in range(0, 360, 9):                                 # voussoirs ringing the opening
        a = math.radians(i)
        if cy + math.sin(a) * 133 < HOR:
            b.seg(cx + math.cos(a) * 118, cy + math.sin(a) * 118,
                  cx + math.cos(a) * 133, cy + math.sin(a) * 133, 1, 0)
    for rad, w in ((92, 1.4), (116, 2.4), (133, 1.6)):
        for y in range(max(0, cy - rad - 3), min(HOR, cy + rad + 3)):
            for x in range(W):
                if abs(math.hypot(x - cx, y - cy) - rad) <= w:
                    b.g[y][x] = 0
    for y in range(HOR):                                       # the recess is sunk, so it shades
        for x in range(W):
            d = math.hypot(x - cx, y - cy)
            if 116 < d < 133:
                lit = (x - cx) * 0.62 + (y - cy) * 0.78
                if lit < -22:
                    b.g[y][x] = min(b.g[y][x], 150)
    for i in range(16):
        a = i / 16 * 2 * math.pi - math.pi / 2
        by = cy + math.sin(a) * 106
        if by < HOR - 5:
            bolt(b, cx + math.cos(a) * 106, by, 4.4)
    return b


VARIANTS = (('title-bg-06-vault-ground', vault_ground),
            ('title-bg-13-searchlights-hard', searchlights_hard),
            ('title-bg-14-vault-brick', vault_brick),
            ('title-bg-07-deposit-wall', deposit_wall),
            ('title-bg-08-searchlights', searchlights),
            ('title-bg-09-blueprint', blueprint),
            ('title-bg-10-brick-wall', brick_wall),
            ('title-bg-11-money-rain', money_rain),
            ('title-bg-12-laser-grid', laser_grid))

for name, build in VARIANTS:
    compose(build(), name)


# ---------------------------------------------------------------- game plate
# The background alone: title, dial and CTA lifted out, their halos left as the
# white they already were, so the game blits this and draws those three on top
# in their original positions with no seam.
def plate(src, name):
    subprocess.run(['magick', f'{OUT}/{src}.png', '-colorspace', 'Gray', '-compress', 'none',
                    'pgm:/tmp/_full.pgm'], check=True)
    _, _, full = read_pgm('/tmp/_full.pgm')
    lab = [[0] * W for _ in range(H)]
    n = 0
    for sy in range(H):
        for sx in range(W):
            if prot[sy][sx] and not lab[sy][sx]:
                n += 1
                lab[sy][sx] = n
                dq = collections.deque([(sx, sy)])
                while dq:
                    x, y = dq.popleft()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < W and 0 <= ny < H and prot[ny][nx] and not lab[ny][nx]:
                            lab[ny][nx] = n
                            dq.append((nx, ny))
    keep = {lab[150][30], lab[110][370]}                       # the two robbers stay
    out = [[255 if (lab[y][x] and lab[y][x] not in keep) else full[y][x]
            for x in range(W)] for y in range(H)]
    write_png(out, f'{OUT}/{name}.png', False)
    subprocess.run(['magick', f'{OUT}/{name}.png', '-filter', 'point', '-resize', '400%',
                    f'{OUT}/{name}@4x.png'], check=True)
    print('wrote', name, '- components:', n, 'kept:', sorted(keep))


plate('title-bg-14-vault-brick', 'title-screen-bg')
