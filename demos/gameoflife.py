# Demo: Conways Game of Life auf 16x16, Raender verbunden (was rechts rausgeht, kommt links rein).
# Zellen faden weich ein und aus, die Farbe zeigt das Alter einer Zelle.
# Stirbt alles aus oder wiederholt sich das Muster, startet eine neue Runde -
# zufaellig oder mit einem bekannten Muster.
import time, random
import matrix as m

W, H = m.W, m.H
N = W * H
FRAMES = 4         # Zwischenbilder pro Generation (Ueberblenden)
FRAME_MS = 45      # Zeit pro Zwischenbild
DENSITY = 0.35     # Anteil lebender Zellen beim zufaelligen Start
REPEAT_GENS = 40   # so lange darf ein Muster sich wiederholen, bevor neu gestartet wird
MAX_GENS = 1500    # spaetestens dann neue Runde

# Nachbarn je Zelle mit Umlauf an den Raendern
NB = []
for c in range(N):
    x, y = c % W, c // W
    NB.append(tuple(((y + dy) % H) * W + (x + dx) % W
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy))

PATTERNS = {
    "pulsar": [(x, y) for y in (0, 5, 7, 12) for x in (2, 3, 4, 8, 9, 10)] +
              [(x, y) for x in (0, 5, 7, 12) for y in (2, 3, 4, 8, 9, 10)],
    "glider": [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)],
    "r_pentomino": [(1, 0), (2, 0), (0, 1), (1, 1), (1, 2)],
    "acorn": [(1, 0), (3, 1), (0, 2), (1, 2), (4, 2), (5, 2), (6, 2)],
    "galaxy": [(x, y) for y, row in enumerate((
        "######.##", "######.##", ".......##", "##.....##", "##.....##",
        "##.....##", "##.......", "##.######", "##.######")) for x, ch in enumerate(row) if ch == "#"],
    "lwss": [(1, 0), (4, 0), (0, 1), (0, 2), (4, 2), (0, 3), (1, 3), (2, 3), (3, 3)],
}

def place(grid, cells, ox, oy):
    for x, y in cells:
        grid[((y + oy) % H) * W + (x + ox) % W] = 1

def seed():
    g = bytearray(N)
    r = random.random()
    if r < 0.5:
        for c in range(N):
            g[c] = 1 if random.random() < DENSITY else 0
    elif r < 0.6:
        place(g, PATTERNS["pulsar"], 1, 1)
    elif r < 0.65:
        place(g, PATTERNS["galaxy"], 3, 3)
    elif r < 0.7:
        # zwei Raumschiffe hintereinander
        place(g, PATTERNS["lwss"], 0, 2)
        place(g, PATTERNS["lwss"], 8, 10)
    elif r < 0.85:
        # mehrere Glider in verschiedene Richtungen
        for i in range(4):
            cells = PATTERNS["glider"]
            if i & 1:
                cells = [(2 - x, y) for x, y in cells]
            if i & 2:
                cells = [(x, 2 - y) for x, y in cells]
            place(g, cells, random.randrange(W), random.randrange(H))
    else:
        place(g, PATTERNS[random.choice(("r_pentomino", "acorn"))], 5, 6)
    return g

def step(cur):
    nxt = bytearray(N)
    for c in range(N):
        a, b, d, e, f, g, h, i = NB[c]
        n = cur[a] + cur[b] + cur[d] + cur[e] + cur[f] + cur[g] + cur[h] + cur[i]
        if n == 3 or (n == 2 and cur[c]):
            nxt[c] = 1
    return nxt

# Position jeder Zelle im Bildpuffer von matrix.py
IDX = [m.xy(c % W, c // W) * 3 for c in range(N)]

def palette(hue):
    # neue Zellen in der Grundfarbe, aeltere wandern im Farbrad weiter (bis max. 1/3 Runde)
    return [m.wheel(hue + a * 8) for a in range(33)]

def render(prev, cur, ages, old_ages, pal):
    buf = m.buf
    for f in range(1, FRAMES + 1):
        t = time.ticks_ms()
        fade_in = 255 * f // FRAMES
        for c in range(N):
            p, q = prev[c], cur[c]
            j = IDX[c]
            if not p and not q:
                buf[j] = buf[j + 1] = buf[j + 2] = 0
                continue
            if p and q:
                col = pal[min(ages[c], 32)]
                buf[j] = col[0]; buf[j + 1] = col[1]; buf[j + 2] = col[2]
                continue
            if q:
                lvl = fade_in
                col = pal[0]
            else:
                lvl = 255 - fade_in
                col = pal[min(old_ages[c], 32)]
            buf[j] = col[0] * lvl >> 8; buf[j + 1] = col[1] * lvl >> 8; buf[j + 2] = col[2] * lvl >> 8
        m.show()
        time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))

while True:
    pal = palette(random.randrange(768))
    empty = bytearray(N)
    cur = seed()
    ages = bytearray(N)
    render(empty, cur, ages, ages, pal)
    seen = {}
    repeat_since = None
    gen = 0
    while True:
        nxt = step(cur)
        old_ages = ages
        ages = bytearray(N)
        for c in range(N):
            if nxt[c]:
                ages[c] = min(old_ages[c] + 1, 255) if cur[c] else 0
        render(cur, nxt, ages, old_ages, pal)
        cur = nxt
        gen += 1
        key = bytes(cur)
        if repeat_since is None and key in seen:
            repeat_since = gen
        seen[key] = gen
        if len(seen) > 200:
            seen = {key: gen}
        if not any(cur) or gen > MAX_GENS or (repeat_since and gen - repeat_since > REPEAT_GENS):
            break
    # ausblenden, dann neue Runde
    time.sleep_ms(600)
    render(cur, empty, ages, ages, pal)
    time.sleep_ms(300)
