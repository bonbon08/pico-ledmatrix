# Demo: Autorennen von hinten (Pseudo-3D). Jede Bildzeile unter dem Horizont steht fuer eine
# Entfernung; die Strasse wird nach hinten schmaler, Kurven verschieben sie seitlich (die
# Kruemmung wird von vorne nach hinten aufsummiert). Sonnenuntergang, Palmen, langsamere Autos.
import time, math, random
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
HOR = 6            # Horizont-Zeile
SPEED = 0.55       # Strecke pro Bild
DSCALE = 5.0       # Entfernung je Tiefenstufe
PX = 6.0           # Pixel je Strassen-Einheit in der untersten Zeile (Strasse = 2 Einheiten breit)
STRIPE = 2.5       # Laenge eines Streifens

# Strecke: (Laenge, Kruemmung), negativ = links
TRACK = ((50, 0), (45, 0.0022), (25, 0), (40, -0.0035), (15, 0), (35, 0.0045), (30, -0.0015),
         (40, 0), (30, -0.004), (20, 0.002), (45, 0))
TRACK_LEN = sum(l for l, _ in TRACK)

def curv(d):
    # Kruemmung an Streckenposition d, an den Uebergaengen weich ueberblendet
    d %= TRACK_LEN
    acc = 0
    for i, (l, c) in enumerate(TRACK):
        if d < acc + l:
            into = d - acc
            if into < 8:
                prev = TRACK[i - 1][1]
                return prev + (c - prev) * into / 8
            return c
        acc += l
    return 0

ROWS = list(range(HOR + 1, H))
P = [(y - HOR) / (H - HOR) for y in ROWS]          # Perspektive 0 (Horizont) .. 1 (vorne)
DIST = [(1 / p - 1) * DSCALE for p in P]           # Entfernung je Zeile

def lerp(a, b, f):
    return (int(a[0] + (b[0] - a[0]) * f), int(a[1] + (b[1] - a[1]) * f), int(a[2] + (b[2] - a[2]) * f))

SKY = []
for y in range(HOR + 1):
    f = y / HOR
    SKY.append(lerp((40, 0, 110), (255, 50, 90), f / 0.7) if f < 0.7 else lerp((255, 50, 90), (255, 160, 30), (f - 0.7) / 0.3))
MOUNTAINS = [0, 1, 1, 2, 2, 1, 0, 0, 1, 2, 3, 2, 1, 1, 0, 1, 1, 0, 0, 1, 2, 2, 1, 0, 0, 0, 1, 2, 1, 0, 0, 1]

def hline(y, x0, x1, c):
    # Pixel x0..x1-1 der Zeile y in einer Farbe fuellen (Zeile liegt in zwei Matrizen)
    x0 = max(0, x0)
    x1 = min(W, x1)
    if x0 >= x1:
        return
    buf = m.buf
    while x0 < x1:
        e = min(x1, (x0 // 8 + 1) * 8)       # bis zum Ende dieser Matrix
        j = m.xy(x0, y) * 3
        buf[j:j + 3 * (e - x0)] = c * (e - x0)
        x0 = e

SKY_B = [bytes(c) for c in SKY]
# Sonne als vorberechnete Pixel relativ zur Mitte, mit Streifen in Zeile 4 und 6
SUN = [(dx, y, (255, 220 - y * 18, 40)) for y in range(1, HOR + 1) if y not in (4, 6)
       for dx in range(-5, 6) if dx * dx + (y + 0.5 - HOR) ** 2 < 4.6 ** 2]
GRASS = (bytes((25, 115, 30)), bytes((40, 150, 40)))
RUMBLE = (bytes((240, 240, 240)), bytes((240, 20, 20)))
ROAD_C = (bytes((80, 80, 90)), bytes((95, 95, 105)))
LANE = bytes((240, 240, 240))

CAR = (".RWWR.",
       "LRRRRL",
       "KK..KK")
CAR_COL = {"R": (230, 0, 20), "W": (40, 40, 70), "L": (255, 220, 0), "K": (20, 20, 20)}

pos = 0.0
player_x = 0.4      # rechte Spur
bg = 0.0
traffic = [[random.uniform(15, 60), random.choice((-0.5, 0.5)), random.choice(((30, 90, 255), (255, 200, 0), (240, 240, 240)))]
           for _ in range(2)]

while True:
    t = time.ticks_ms()
    c_now = curv(pos)
    pos = (pos + SPEED) % TRACK_LEN
    bg += c_now * SPEED * 120
    # Fliehkraft und automatisches Gegenlenken
    player_x += c_now * SPEED * 18
    player_x += (0.4 - player_x) * 0.06
    # Himmel, Sonne, Berge
    for y in range(HOR + 1):
        hline(y, 0, W, SKY_B[y])
    sx = int(8 - bg * 0.3)
    for dx, y, c in SUN:
        m.set(sx + dx, y, c)
    for x in range(W):
        h = MOUNTAINS[int(x + bg) % len(MOUNTAINS)]
        for k in range(h):
            m.set(x, HOR - k, (70, 10, 70))
    # Strasse, von vorne nach hinten: Kruemmung aufsummieren
    offs = [0.0] * len(ROWS)
    slope = 0.0
    off = 0.0
    prev = 0.0
    for i in range(len(ROWS) - 1, -1, -1):
        d = DIST[i]
        step = d - prev
        slope += curv(pos + d) * step
        off += slope * step
        prev = d
        offs[i] = off
    for i, y in enumerate(ROWS):
        p = P[i]
        d = DIST[i]
        stripe = int((pos + d) / STRIPE) & 1
        cx = 8 + (offs[i] - player_x) * p * PX
        hw = p * PX
        rumble = max(0.6, hw * 0.16)
        lane = max(0.35, hw * 0.05)
        # Pixel x gehoert zu einem Bereich, wenn |x + 0.5 - cx| < Breite
        def span(wd):
            return int(math.ceil(cx - wd - 0.5)), int(math.floor(cx + wd - 0.5 - 1e-6)) + 1
        hline(y, 0, W, GRASS[stripe])
        a, b = span(hw + rumble)
        hline(y, a, b, RUMBLE[stripe])
        a, b = span(hw)
        hline(y, a, b, ROAD_C[stripe])
        if stripe:
            a, b = span(lane)
            hline(y, a, b, LANE)

    # Palmen und Autos von hinten nach vorne
    objs = []
    base = int(pos / 12) * 12
    for k in range(1, 6):
        d = base + k * 12 - pos
        objs.append((d, "palme", 2.3 if k % 2 else -2.3, None))
    for tr in traffic:
        tr[0] -= SPEED * 0.45          # wir sind schneller
        if tr[0] < -1:
            tr[0] = random.uniform(40, 60)
            tr[1] = random.choice((-0.5, 0.5))
        objs.append((tr[0], "auto", tr[1], tr[2]))
    objs.sort(key=lambda o: -o[0])
    for d, kind, wx, col in objs:
        if d <= 0.3 or d > DIST[0]:
            continue
        p = 1 / (d / DSCALE + 1)
        yb = HOR + p * (H - HOR)
        best = min(len(ROWS) - 1, max(0, int(yb + 0.5) - HOR - 1))   # Zeile in dieser Entfernung
        cx = 8 + (offs[best] + wx - player_x) * p * PX
        if kind == "palme":
            hgt = max(1, int(1.5 * p * PX + 0.5))
            x = int(cx)
            for k in range(hgt):
                m.set(x, int(yb) - 1 - k, (120, 60, 20))
            top = int(yb) - hgt
            rw = int(0.5 * p * PX + 0.5)
            for dx in range(-rw, rw + 1):
                m.set(x + dx, top, (20, 170, 40))
            if rw:
                m.set(x, top - 1, (20, 170, 40))
        else:
            w = max(1, int(0.8 * p * PX))
            h = max(1, int(0.45 * p * PX))
            x0 = int(cx - w / 2 + 0.5)
            for yy in range(int(yb) - h, int(yb)):
                for xx in range(x0, x0 + w):
                    m.set(xx, yy, col)
            if w >= 3:
                m.set(x0, int(yb) - 1, (255, 30, 0)); m.set(x0 + w - 1, int(yb) - 1, (255, 30, 0))
    # eigenes Auto, wackelt in Kurven etwas
    lean = 1 if c_now > 0.002 else -1 if c_now < -0.002 else 0
    for ry, row in enumerate(CAR):
        for rx, ch in enumerate(row):
            if ch != ".":
                m.set(5 + rx + (lean if ry == 0 else 0), 13 + ry, CAR_COL[ch])
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
