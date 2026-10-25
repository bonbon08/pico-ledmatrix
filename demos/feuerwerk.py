# Demo: Feuerwerk. Raketen steigen auf und explodieren als Kugel, Ring, Goldregen oder
# Glitzer. Das Bild wird nicht geloescht, sondern nur abgedunkelt -> leuchtende Spuren.
import time, random, math, micropython
import matrix as m

W, H = m.W, m.H
FRAME_MS = 35
TRAIL = 175        # wie stark das Bild pro Bild nachleuchtet (0-255, groesser = laengere Spuren)
GRAVITY = 0.012
LAUNCH = 0.025     # Chance pro Bild fuer eine neue Rakete
FINALE = 0.0015    # Chance pro Bild fuer ein Finale mit mehreren Raketen
MAX_SPARKS = 160   # mehr Funken gleichzeitig schafft der Pico nicht fluessig

COLORS = ((255, 30, 30), (30, 255, 60), (40, 90, 255), (255, 200, 0), (255, 40, 200),
          (0, 230, 255), (255, 120, 0), (200, 80, 255))
GOLD = (255, 150, 20)

@micropython.viper
def fade(b: ptr8, n: int, f: int):
    for i in range(n):
        b[i] = (b[i] * f) >> 8

def add(x, y, c, f=255):
    # Farbe aufaddieren statt ueberschreiben, damit sich Funken ueberlagern
    x = int(x + 0.5)
    y = int(y + 0.5)
    if 0 <= x < W and 0 <= y < H:
        b = m.buf
        j = m.xy(x, y) * 3
        for k in range(3):
            v = b[j + k] + (c[k] * f >> 8)
            b[j + k] = v if v < 255 else 255

rockets = []       # [x, y, vx, vy]
sparks = []        # [x, y, vx, vy, Leben, max. Leben, Farbe, Art]

def launch():
    x = random.uniform(2, W - 3)
    rockets.append([x, float(H), (W / 2 - x) * random.uniform(0, 0.012),
                    -random.uniform(0.42, 0.55)])

def explode(x, y):
    kind = random.choice(("kugel", "kugel", "ring", "gold", "glitzer"))
    c1 = random.choice(COLORS)
    c2 = random.choice(COLORS) if random.random() < 0.35 else c1
    n = 22 if kind == "ring" else 30
    n = max(10, min(n, MAX_SPARKS - len(sparks)))   # sind schon viele Funken unterwegs, kleiner
    for i in range(n):
        if kind == "ring":
            a = i * 2 * math.pi / n
            v = 0.42
        else:
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(0.1, 0.45)
        if kind == "gold":
            v *= 0.6
            col, life = GOLD, random.randrange(45, 70)
        elif kind == "glitzer":
            col, life = (255, 255, 255), random.randrange(25, 45)
        else:
            col, life = (c1 if i % 2 else c2), random.randrange(22, 38)
        sparks.append([x, y, math.cos(a) * v, math.sin(a) * v, life, life, col, kind])
    # kurzer heller Blitz in der Mitte
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        add(x + dx, y + dy, (255, 255, 255), 200 if dx or dy else 255)

frame = 0
while True:
    t = time.ticks_ms()
    frame += 1
    fade(m.buf, W * H * 3, TRAIL)
    if random.random() < LAUNCH and len(rockets) < 3:
        launch()
    if random.random() < FINALE:
        for _ in range(4):
            launch()
    # Raketen steigen, werden langsamer und explodieren am hoechsten Punkt
    keep = []
    for r in rockets:
        r[0] += r[2]
        r[1] += r[3]
        r[3] += GRAVITY
        add(r[0], r[1], (255, 210, 150))
        if random.random() < 0.5 and len(sparks) < MAX_SPARKS:
            sparks.append([r[0], r[1] + 1, random.uniform(-0.05, 0.05), 0.05, 8, 8, GOLD, "funke"])
        if r[3] > -0.08 or r[1] < 2:
            explode(r[0], r[1])
        else:
            keep.append(r)
    rockets = keep
    # Funken
    keep = []
    for s in sparks:
        x, y, vx, vy, life, maxl, col, kind = s
        drag = 0.9 if kind == "gold" else 0.94
        s[2] = vx * drag
        s[3] = vy * drag + (GRAVITY * 0.5 if kind == "gold" else GRAVITY)
        s[0] = x + s[2]
        s[1] = y + s[3]
        s[4] = life - 1
        if s[4] <= 0 or s[1] >= H:
            continue
        f = s[4] * 255 // maxl
        if kind == "glitzer" and random.random() < 0.4:
            f = 0 if random.random() < 0.5 else 255
        add(s[0], s[1], col, f)
        keep.append(s)
    sparks = keep
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
