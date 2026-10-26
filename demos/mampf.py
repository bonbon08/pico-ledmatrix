# Demo: Mampf. Ein runder Knubbel laeuft ueber die Wiese, saugt herabfallendes Essen ein, kaut und
# freut sich. Nach einigen Happen ruelpst er Sterne, nach einer Peperoni rennt er rot gluehend herum.
import time, random, gc
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
MAX_ITEMS = 3        # so viel Essen liegt hoechstens gleichzeitig herum
SPAWN = 0.007        # Wahrscheinlichkeit pro Bild, dass neues Essen vom Himmel faellt
SPEED = 0.15         # Lauftempo in Pixel pro Bild
HOT_SPEED = 0.4      # Tempo nach einer Peperoni
HOT_FRAMES = 150     # so lange gluehen nach einer Peperoni
BURP_AFTER = 4       # nach so vielen Happen wird geruelpst
SUCK_RANGE = 5       # ab diesem Abstand vor dem Maul wird eingesaugt
GROUND = 14          # erste Bodenzeile

# Mampf nach rechts schauend, 8x6. B = Koerper, W/P = Augen, k = Wange, M = Mund, R = Maul offen,
# F = Fuesse. Der Mund (Zeile 3/4) und die Fuesse (Zeile 5) werden je nach Zustand ersetzt.
BODY = (
    ".B....B.",
    ".BBBBBB.",
    "BBBWPWPB",
    "BBBkBBMB",
    ".BBBBBB.",
)
MOUTH = {"zu": ("BBBkBBMB", ".BBBBBB."),
         "kau": ("BBBkBMMB", ".BBBBBB."),
         "auf": ("BBBkBRRR", ".BBBBRR.")}
FEET = ("..FF.FF.", ".FF...FF")
COL = {"B": (40, 220, 200), "W": (255, 255, 255), "P": (10, 10, 40), "k": (255, 110, 170),
       "M": (20, 60, 60), "R": (220, 0, 60), "F": (30, 90, 255)}
HOT = (255, 80, 30)  # Koerperfarbe nach der Peperoni

# Essen, 3x3: Apfel, Kirschen, Keks, Stern, Peperoni (selten)
ITEMS = (
    (".g.rrrrrr", 5),
    (".g.g.gr.r", 4),
    ("cccchcccc", 4),
    (".y.yyyy.y", 3),
    ("..g.r.r..", 1),
)
ICOL = {"r": (255, 30, 30), "g": (40, 220, 40), "c": (230, 150, 50), "h": (120, 60, 10),
        "y": (255, 220, 0)}
PEPERONI = 4

# Hintergrund: Wiese, Erde und zwei Wolken, einmal vorberechnet
m.clear()
for x in range(W):
    m.set(x, GROUND, (40, 200, 40) if x % 3 else (90, 240, 60))
    m.set(x, GROUND + 1, (140, 80, 20))
for cx, cy in ((2, 1), (10, 3)):
    for dx, dy in ((1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (3, 1)):
        m.set(cx + dx, cy + dy, (120, 130, 170))
BG = bytes(m.buf)

_cache = {}
def sprite(face, mouth, feet, eyes_shut, hot):
    # Pixelliste (dx, dy, Farbe) fuer eine Haltung, einmal berechnet und gemerkt
    key = (face, mouth, feet, eyes_shut, hot)
    if key in _cache:
        return _cache[key]
    rows = list(BODY[:3]) + list(MOUTH[mouth]) + [FEET[feet]]
    if eyes_shut:
        rows[2] = rows[2].replace("W", "P")
    px = []
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == ".":
                continue
            c = HOT if (hot and ch == "B") else COL[ch]
            px.append((dx if face > 0 else 7 - dx, dy, c))
    _cache[key] = px
    return px

def spawn():
    kinds = [k for k, (_, w) in enumerate(ITEMS) for _ in range(w)]
    return [random.randrange(0, W - 2), -3.0, 0.0, random.choice(kinds), False]  # x, y, vy, Art, liegt

x = 4.0              # linke Kante des Sprites
y = 0.0              # Hoehe ueber dem Boden (Huepfen)
vy = 0.0
face = 1
state = "laufen"
timer = 0
goal = None          # Ziel beim Herumschlendern
items = []
prey = None          # Essen, das gerade eingesaugt wird
eaten = 0
hot = 0
blink = 0
parts = []           # [x, y, dx, dy, Leben, Farbe]
frame = 0

while True:
    t = time.ticks_ms()
    frame += 1

    # Essen faellt vom Himmel
    if len(items) < MAX_ITEMS and random.random() < SPAWN:
        items.append(spawn())
    for it in items:
        if not it[4] and it is not prey:
            it[2] += 0.05
            it[1] += it[2]
            if it[1] >= GROUND - 3:
                it[1] = GROUND - 3
                it[4] = True

    mouth_x = x + 7.5 if face > 0 else x + 0.5
    speed = HOT_SPEED if hot else SPEED
    mouth = "zu"
    walking = False

    if state == "laufen":
        landed = [it for it in items if it[4]]
        if landed:
            # Standplatz kurz vor dem Essen suchen, von links (Blick nach rechts) oder von rechts
            best = None
            for it in landed:
                c = it[0] + 1.5
                for f, sx in ((1, c - 11.0), (-1, c + 3.0)):
                    sx = max(0.0, min(W - 8.0, sx))
                    if best is None or abs(sx - x) < abs(best[1] - x):
                        best = (f, sx, it)
            f, sx, it = best
            goal = None
            if abs(sx - x) <= speed and y == 0:
                x = sx
                face = f
                state = "saugen"
                prey = it
                prey[2] = 0.0
            else:
                face = 1 if sx > x else -1
                walking = True
        else:
            # nichts zu essen: herumschlendern, ab und zu huepfen
            if goal is None and random.random() < 0.02:
                goal = random.randrange(0, W - 7)
            if goal is not None:
                if abs(goal - x) < speed:
                    goal = None
                else:
                    face = 1 if goal > x else -1
                    walking = True
            if y == 0 and random.random() < 0.006:
                vy = 0.7
        if walking:
            x = max(0.0, min(W - 8.0, x + face * speed))
            if goal is not None and ((x <= 0 and face < 0) or (x >= W - 8 and face > 0)):
                goal = None
    elif state == "saugen":
        mouth = "auf"
        prey[2] += 0.012
        tx = mouth_x - 1.5
        prey[0] += prey[2] if tx > prey[0] else -prey[2]
        prey[1] += (GROUND - 4.5 - prey[1]) * 0.2
        # Windlinien zum Maul
        if random.random() < 0.6:
            wx = mouth_x + face * random.uniform(1, SUCK_RANGE)
            parts.append([wx, GROUND - 3.5 + random.uniform(-1.5, 1.5), -face * 0.5, 0.0, 6,
                          (200, 230, 255)])
        if abs(prey[0] + 1.5 - mouth_x) < 1.2:
            items.remove(prey)
            state = "kauen"
            timer = 25
            eaten += 1
            if prey[3] == PEPERONI:
                hot = HOT_FRAMES
            prey = None
    elif state == "kauen":
        mouth = "kau" if (timer // 4) % 2 else "zu"
        timer -= 1
        if timer == 0:
            state = "ruelpsen" if eaten >= BURP_AFTER else "freuen"
            timer = 20
    elif state == "freuen":
        timer -= 1
        if timer % 7 == 0:
            parts.append([x + 3.5 + random.uniform(-2, 2), GROUND - 7.0, 0.0, -0.15, 12, (255, 60, 140)])
        if timer == 0:
            state = "laufen"
    elif state == "ruelpsen":
        mouth = "auf"
        timer -= 1
        if timer > 8:
            parts.append([mouth_x, GROUND - 3.5, face * random.uniform(0.3, 0.7),
                          random.uniform(-0.5, 0.1), 10, (255, 230, 60)])
        if timer == 0:
            eaten = 0
            state = "laufen"

    # Huepfen
    if vy or y:
        y += vy
        vy -= 0.08
        if y <= 0:
            y = 0.0
            vy = 0.0

    if hot:
        hot -= 1
        if frame % 3 == 0:
            parts.append([x + 3.5 + random.uniform(-2, 2), GROUND - 7.0 - y, 0.0, -0.25, 6, (255, 140, 0)])

    # zeichnen
    m.buf[:] = BG
    for it in items:
        art = ITEMS[it[3]][0]
        ix, iy = int(it[0] + 0.5), int(it[1] + 0.5)
        for k in range(9):
            ch = art[k]
            if ch != ".":
                m.set(ix + k % 3, iy + k // 3, ICOL[ch])
    if blink == 0 and random.random() < 0.012:
        blink = 4
    shut = blink > 0 or state == "freuen" or state == "kauen"
    blink = max(0, blink - 1)
    feet = (int(x * 2) % 2) if walking else 0
    bob = 1 if state == "kauen" and (timer // 4) % 2 else 0     # beim Kauen wippt der Koerper
    sx = int(x + 0.5)
    sy = GROUND - 6 - int(y + 0.5) + bob
    for dx, dy, c in sprite(face, mouth, feet, shut, hot > 0):
        if dy == 5 and bob:
            continue            # Fuesse bleiben am Boden, der Koerper wippt
        m.set(sx + dx, sy + dy, c)
    if bob:
        for dx, dy, c in sprite(face, mouth, feet, shut, hot > 0):
            if dy == 5:
                m.set(sx + dx, GROUND - 1, c)
    for p in parts:
        p[0] += p[2]; p[1] += p[3]; p[4] -= 1
        f = min(255, p[4] * 40)
        c = p[5]
        m.set(int(p[0] + 0.5), int(p[1] + 0.5), (c[0] * f >> 8, c[1] * f >> 8, c[2] * f >> 8))
    parts = [p for p in parts if p[4] > 0]
    m.show()
    if frame % 8 == 0:
        gc.collect()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
