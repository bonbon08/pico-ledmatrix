# Demo: Blauer Kirschbluetenbaum bei Nacht. Die Blueten schimmern, Windboeen laufen als
# Lichtwelle durch die Krone, Bluetenblaetter trudeln herab und bleiben kurz am Boden liegen.
import time, random, math
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
PETALS = 7         # max. gleichzeitig fallende Bluetenblaetter
PETAL_RATE = 0.06  # Chance pro Bild fuer ein neues Bluetenblatt

# B = Bluete, T = Stamm/Ast, G = Boden, * = Stern
ART = (
    "..*.............",
    "......BBB.....*.",
    "...BBBBBBBB.BB..",
    "..BBBBBBBBBBBBB.",
    ".BBBBBBBBBBBBBBB",
    ".BBBBBBBBBBBBBB.",
    "BBBBBTBBBBBTBBB.",
    ".BBBBBTBBBTBBBB.",
    "..BBB.TBBT.BBB..",
    ".......TT.......",
    "*......TT.......",
    ".......TT.....*.",
    ".......TT.......",
    ".......TT.......",
    "......TTTT......",
    "GGGGGTTTTTTGGGGG",
)

BLUES = ((10, 40, 255), (40, 100, 255), (90, 160, 255), (160, 210, 255))
TRUNK = (110, 45, 15)
GROUND = (5, 30, 25)
PETAL = (170, 215, 255)

SIN = [int(128 + 127 * math.sin(i * 2 * math.pi / 256)) for i in range(256)]

blossoms, trunk, ground, stars = [], [], [], []
for y, row in enumerate(ART):
    for x, ch in enumerate(row):
        if ch == "B":
            # aussen eher hell, innen eher dunkel -> wirkt plastischer
            edge = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                       if not (0 <= x + dx < W and 0 <= y + dy < H) or ART[y + dy][x + dx] != "B")
            shade = min(3, max(0, random.randrange(3) + (1 if edge else 0) - (1 if y > 6 else 0)))
            blossoms.append((x, y, BLUES[shade], random.randrange(256), random.randrange(2, 5)))
        elif ch == "T":
            trunk.append((x, y))
        elif ch == "G":
            ground.append((x, y))
        elif ch == "*":
            stars.append((x, y, random.randrange(256)))

def scale(c, f):
    return (c[0] * f >> 8, c[1] * f >> 8, c[2] * f >> 8)

falling = []       # [x, y, Wobbel-Phase]
landed = []        # [x, Restzeit in Bildern]
wind = 0.0
gust = None        # x-Position der Windboee
frame = 0

while True:
    t = time.ticks_ms()
    frame += 1
    m.clear()
    # Sterne funkeln
    for x, y, ph in stars:
        m.set(x, y, scale((255, 255, 255), 20 + SIN[(frame * 3 + ph) & 255] // 4))
    for x, y in ground:
        m.set(x, y, GROUND)
    for x, y in trunk:
        m.set(x, y, TRUNK)
    # Blueten schimmern, Windboee hellt sie kurz auf
    for x, y, col, ph, sp in blossoms:
        f = 175 + SIN[(frame * sp + ph) & 255] * 80 // 255
        if gust is not None and abs(x - gust) < 2:
            f = min(255, f + 70)
        m.set(x, y, scale(col, f))
    # Wind aendert sich langsam, ab und zu eine Boee
    wind += random.uniform(-0.02, 0.02)
    wind = max(-0.4, min(0.4, wind))
    if gust is None and random.random() < 0.008:
        gust = -2.0
    if gust is not None:
        gust += 0.5
        if gust > W + 2:
            gust = None
    # neue Bluetenblaetter, bei einer Boee mehr
    rate = PETAL_RATE * (4 if gust is not None else 1)
    if len(falling) < PETALS and random.random() < rate:
        x, y, _, _, _ = random.choice(blossoms)
        falling.append([float(x), float(y), random.randrange(256)])
    for p in falling:
        p[2] = (p[2] + 9) & 255
        p[0] += wind * 0.3 + (SIN[p[2]] - 128) / 600
        p[1] += 0.12
    keep = []
    for p in falling:
        if p[1] >= H - 1:
            landed.append([int(p[0] + 0.5) % W, 75])
        elif -1 < p[0] < W:
            keep.append(p)
    falling = keep
    # liegende Blaetter verblassen
    for l in landed:
        l[1] -= 1
        f = min(255, l[1] * 6)
        base = TRUNK if ART[H - 1][l[0]] == "T" else GROUND
        m.set(l[0], H - 1, tuple(base[c] + ((PETAL[c] - base[c]) * f >> 8) for c in range(3)))
    landed = [l for l in landed if l[1] > 0]
    for x, y, _ in falling:
        m.set(int(x + 0.5), int(y + 0.5), PETAL)
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
