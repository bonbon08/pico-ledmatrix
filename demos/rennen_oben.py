# Demo: Autorennen von oben. Vier Autos fahren selbststaendig ueber eine 64x64 Pixel grosse
# Strecke, die Kamera faehrt mit dem ersten Auto mit. Die Strecke wird beim Start einmal aus
# einer geschlossenen Spline-Kurve berechnet; pro Bild wird nur der sichtbare Ausschnitt kopiert.
import time, math, random, micropython, array, gc
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
WW = WH = 64       # Groesse der Welt
ROAD = 2.3         # halbe Strassenbreite
CURB = 3.2         # bis hier Randstein
CARS = ((255, 210, 0), (30, 120, 255), (255, 0, 200), (0, 230, 255))   # keine Randstein-/Rasenfarben

# Eckpunkte der Strecke (geschlossene Runde), werden als Catmull-Rom-Spline verbunden
POINTS = ((10, 10), (32, 7), (54, 10), (57, 25), (44, 31), (52, 44), (55, 56), (33, 55),
          (22, 45), (10, 55), (7, 37), (17, 27))

# Felder der Welt: 0/1 Rasen hell/dunkel, 2/3 Strasse, 4/5 Randstein rot/weiss,
# 6/7 Startlinie weiss/schwarz, 8 Baum
PAL = bytes((40, 150, 40,  30, 125, 30,  90, 90, 95,  75, 75, 80,  230, 20, 20,  230, 230, 230,
             240, 240, 240,  20, 20, 20,  10, 70, 20))

# Grosse Puffer zuerst anlegen: danach ist der Speicher durch die vielen Bahnpunkte zerstueckelt
# und 4 KB am Stueck waeren nicht mehr frei.
gc.collect()
WORLD = bytearray(WW * WH)
_near = bytearray(WW * WH)     # 255 - Abstand zur Mittellinie x 40 (0 = weit weg)
_param = bytearray(WW * WH)    # naechster Bahnpunkt / 2

def spline():
    pts = []
    n = len(POINTS)
    for i in range(n):
        p0, p1, p2, p3 = POINTS[i - 1], POINTS[i], POINTS[(i + 1) % n], POINTS[(i + 2) % n]
        seg = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
        steps = max(4, int(seg * 2))
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            pts.append(tuple(0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in range(2)))
    return pts

PATH = spline()
NP = len(PATH)

def build_world(world, near, param):
    r = int(CURB) + 1
    for i, (x, y) in enumerate(PATH):
        if i % 25 == 0:
            # Ladebalken, die Berechnung dauert ein paar Sekunden
            for k in range(i * W // NP + 1):
                m.set(k, 7, (255, 210, 0)); m.set(k, 8, (255, 210, 0))
            m.show()
        cx, cy = int(x), int(y)
        for yy in range(max(0, cy - r), min(WH, cy + r + 1)):
            for xx in range(max(0, cx - r), min(WW, cx + r + 1)):
                d = math.sqrt((xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2)
                if d <= CURB:
                    j = yy * WW + xx
                    nq = 255 - int(d * 40)
                    if nq > near[j]:
                        near[j] = nq
                        param[j] = i >> 1
    for j in range(WW * WH):
        x, y = j % WW, j // WW
        if near[j] == 0:
            if random.random() < 0.05:
                world[j] = 8
            else:
                world[j] = (x // 3 + y // 3) & 1
        elif near[j] > 255 - ROAD * 40:
            if param[j] == 0:
                world[j] = 6 + ((x + y) & 1)          # karierte Startlinie
            else:
                world[j] = 2 + (1 if random.random() < 0.2 else 0)
        else:
            world[j] = 4 + ((param[j] * 2 // 3) & 1)

@micropython.viper
def paint(world: ptr8, ox: int, oy: int, pal: ptr8, idx: ptr16, buf: ptr8):
    for y in range(16):
        wy = oy + y
        for x in range(16):
            wx = ox + x
            t = 0
            if wx >= 0 and wx < 64 and wy >= 0 and wy < 64:
                t = world[wy * 64 + wx]
            p = t * 3
            j = idx[y * 16 + x]
            buf[j] = pal[p]
            buf[j + 1] = pal[p + 1]
            buf[j + 2] = pal[p + 2]

m.clear()
m.show()
build_world(WORLD, _near, _param)
del _near, _param
gc.collect()
IDX = array.array('H', [m.xy(i % W, i // W) * 3 for i in range(W * H)])

def curvature(i, ahead):
    # Richtungsaenderung der Bahn auf den naechsten Punkten -> wie scharf die Kurve ist
    a = PATH[i % NP]
    b = PATH[(i + ahead // 2) % NP]
    c = PATH[(i + ahead) % NP]
    a1 = math.atan2(b[1] - a[1], b[0] - a[0])
    a2 = math.atan2(c[1] - b[1], c[0] - b[0])
    d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
    return abs(d)

class Car:
    def __init__(self, n):
        # Startaufstellung: versetzt in zwei Reihen hinter der Startlinie
        i = (NP - 3 - 5 * n) % NP
        self.lane = 1.0 if n % 2 else -1.0
        p, q = PATH[i], PATH[(i + 1) % NP]
        hx, hy = q[0] - p[0], q[1] - p[1]
        hl = math.sqrt(hx * hx + hy * hy) or 1
        self.x, self.y = p[0] - hy / hl * self.lane, p[1] + hx / hl * self.lane
        self.h = math.atan2(hy, hx)
        self.i = i
        self.v = 0.0
        self.vmax = 0.30 + random.uniform(-0.03, 0.03)
        self.col = CARS[n % len(CARS)]

    def update(self):
        # naechsten Bahnpunkt nachfuehren
        best, bi = 1e9, self.i
        for k in range(12):
            j = (self.i + k) % NP
            p = PATH[j]
            d = (p[0] - self.x) ** 2 + (p[1] - self.y) ** 2
            if d < best:
                best, bi = d, j
        self.i = bi
        # Ziel etwas voraus, seitlich auf der eigenen Spur
        a = PATH[(bi + 6) % NP]
        b = PATH[(bi + 7) % NP]
        hx, hy = b[0] - a[0], b[1] - a[1]
        hl = math.sqrt(hx * hx + hy * hy) or 1
        tx, ty = a[0] - hy / hl * self.lane, a[1] + hx / hl * self.lane
        want = math.atan2(ty - self.y, tx - self.x)
        d = (want - self.h + math.pi) % (2 * math.pi) - math.pi
        self.h += max(-0.12, min(0.12, d))
        # vor Kurven bremsen
        vt = self.vmax * (1 - 0.55 * min(1.0, curvature(bi, 14) / 1.2))
        self.v += max(-0.02, min(0.008, vt - self.v))
        self.x += math.cos(self.h) * self.v
        self.y += math.sin(self.h) * self.v
        if random.random() < 0.01:
            self.lane = max(-1.2, min(1.2, self.lane + random.uniform(-0.6, 0.6)))

cars = [Car(n) for n in range(len(CARS))]
camx, camy = cars[0].x, cars[0].y

def draw_car(c, ox, oy):
    ch, sh = math.cos(c.h), math.sin(c.h)
    cx, cy = c.x - ox, c.y - oy
    dark = (c.col[0] // 3, c.col[1] // 3, c.col[2] // 3)
    for y in range(int(cy) - 2, int(cy) + 3):
        for x in range(int(cx) - 2, int(cx) + 3):
            if not (0 <= x < W and 0 <= y < H):
                continue
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            along = dx * ch + dy * sh
            across = -dx * sh + dy * ch
            if abs(across) <= 0.8 and abs(along) <= 1.4:
                m.set(x, y, (200, 230, 255) if along > 0.7 else dark if along < -0.7 else c.col)

while True:
    t = time.ticks_ms()
    for c in cars:
        c.update()
    # Autos nicht ineinander fahren lassen
    for a in cars:
        for b in cars:
            if a is not b:
                dx, dy = b.x - a.x, b.y - a.y
                d2 = dx * dx + dy * dy
                if d2 < 2.2:
                    # wer hinten ist, bremst
                    if dx * math.cos(a.h) + dy * math.sin(a.h) > 0:
                        a.v *= 0.85
                        a.lane = -b.lane if abs(b.lane) > 0.3 else (1 if a.lane >= 0 else -1)
    # Kamera folgt dem ersten Auto, schaut etwas voraus
    lead = cars[0]
    camx += (lead.x + math.cos(lead.h) * 3 - camx) * 0.15
    camy += (lead.y + math.sin(lead.h) * 3 - camy) * 0.15
    ox, oy = int(camx) - W // 2, int(camy) - H // 2
    paint(WORLD, ox, oy, PAL, IDX, m.buf)
    for c in cars:
        draw_car(c, ox, oy)
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
