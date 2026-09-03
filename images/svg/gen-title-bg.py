# Title backgrounds. Mostly SOLID black and white; dither only where one becomes
# the other.
#
# Earlier passes dithered every pixel and all five variants collapsed into the
# same grey speckle. Ordered dithering a field that is mostly 0 or 255 leaves
# those areas pure - the dots appear only across the short ramps between them,
# which is where they actually read as shading.
import math, subprocess

W, H = 400, 240
DIAL = (200, 126, 62)

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
        for y in range(max(0, int(cy - r - w)), min(H, int(cy + r + w + 1))):
            for x in range(max(0, int(cx - r - w)), min(W, int(cx + r + w + 1))):
                if r - w <= math.hypot(x - cx, y - cy) <= r + w:
                    self.g[y][x] = v
    def vramp(self, y0, y1, top, bot):
        for y in range(max(0, y0), min(H, y1)):
            t = (y - y0) / max(1, (y1 - y0))
            v = int(top + (bot - top) * t)
            for x in range(W):
                self.g[y][x] = v

def skyline(b, seed, baseY, minH, maxH):
    r = rnd(seed); x = -8
    while x < W + 8:
        w = 20 + r() * 26
        h = minH + r() * (maxH - minH)
        top = baseY - h
        b.rect(x, top, x + w, baseY, 0)
        if r() > 0.6:
            b.rect(x + w * 0.45, top - 9, x + w * 0.45 + 2, top, 0)
        wy = top + 7
        while wy < baseY - 6:
            wx = x + 5
            while wx < x + w - 6:
                if r() > 0.45:
                    b.rect(wx, wy, wx + 3, wy + 4, 255)
                wx += 8
            wy += 10
        x += w + 3 + r() * 4

def stars(b, seed, y1, n):
    r = rnd(seed)
    for _ in range(n):
        x, y = r() * W, r() * y1
        b.disc(x, y, 1 + r(), 255)

def clear_dial(b):
    cx, cy, rr = DIAL
    for y in range(max(0, cy - rr - 22), min(H, cy + rr + 22)):
        for x in range(max(0, cx - rr - 22), min(W, cx + rr + 22)):
            if math.hypot(x - cx, y - cy) <= rr + 16:
                b.g[y][x] = 255

def midnight():
    b = Buf(255)
    b.rect(0, 0, W, 74, 0)                 # solid night
    b.vramp(74, 126, 0, 255)               # the ONLY dithered band: horizon haze
    stars(b, 5, 66, 30)
    b.disc(76, 44, 26, 255); b.ring(76, 44, 26, 1.2, 0)
    b.disc(67, 36, 4, 0); b.disc(85, 52, 3, 0); b.disc(74, 58, 2, 0)
    skyline(b, 9, H, 70, 132)
    clear_dial(b)
    return b

def vault():
    b = Buf(255)
    for y in range(H):                     # shallow ramp, corners only
        for x in range(W):
            d = math.hypot((x - 200) / 200.0, (y - 120) / 120.0)
            b.g[y][x] = int(255 - ss(0.62, 1.35, d) * 190)
    for r in (112, 99):
        b.ring(*DIAL[:2], r, 2.2, 0)
    for i in range(12):
        a = i / 12 * 2 * math.pi
        bx, by = DIAL[0] + math.cos(a) * 106, DIAL[1] + math.sin(a) * 106
        b.disc(bx, by, 6, 255); b.ring(bx, by, 6, 1.4, 0)
    clear_dial(b)
    return b

def spotlight():
    b = Buf(0)
    # A hard edge left almost no mid-grey, so ordered dithering had nothing to
    # work on and the cone came out as flat black and white. The falloff is wide
    # now - both across the beam and down its length - so the ramp is long enough
    # for the dither to actually appear.
    for y in range(H):
        for x in range(W):
            hw = 34 + y * 1.18
            dx = abs(x - 200) / hw
            edge = 1.0 - ss(0.30, 1.30, dx)          # broad soft shoulder
            fall = 1.0 - ss(0.05, 1.30, y / H)       # dims with depth
            v = edge * (0.30 + fall * 0.70)
            b.g[y][x] = int(255 * max(0.0, min(1.0, v)))
    for y in range(206, H):                          # lit floor for the robbers
        for x in range(W):
            b.g[y][x] = max(b.g[y][x], 255)
    clear_dial(b)
    return b

for name, build in (('01-midnight', midnight), ('04-vault', vault), ('05-spotlight', spotlight)):
    b = build()
    pgm = f"P2\n{W} {H}\n255\n" + "\n".join(" ".join(str(v) for v in row) for row in b.g) + "\n"
    open(f"/tmp/bg-{name}.pgm", "w").write(pgm)
    subprocess.run(["magick", f"/tmp/bg-{name}.pgm", "-ordered-dither", "o4x4",
                    f"/tmp/bg-{name}.png"], check=True)
    print("wrote", name)
