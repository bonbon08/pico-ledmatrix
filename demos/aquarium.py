# Demo: Aquarium. Fische schwimmen hin und her, Seegras wiegt sich, aus einer Schatztruhe
# steigen Luftblasen auf, an der Oberflaeche flimmert Licht.
import time, random, math
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
FISH = 4           # Anzahl Fische
BUBBLE_RATE = 0.05 # Chance pro Bild fuer eine Luftblase

SIN = [math.sin(i * 2 * math.pi / 256) for i in range(256)]

# Fisch nach rechts schauend: T = Schwanzflosse, B = Koerper, E = Auge
FISH_ART = ("T.BBE.",
            "TBBBBB",
            "T.BBB.")
FW = len(FISH_ART[0])
FISH_COLS = ((255, 90, 0), (255, 200, 0), (255, 30, 120), (0, 255, 160), (120, 80, 255))

SAND = (150, 110, 40)
PEBBLES = {(3, H - 1): (90, 90, 80), (13, H - 1): (110, 100, 90), (8, H - 1): (80, 70, 60)}
CHEST = {(9, 13): (140, 70, 10), (10, 13): (200, 160, 0), (11, 13): (140, 70, 10),
         (9, 14): (110, 50, 5), (10, 14): (110, 50, 5), (11, 14): (110, 50, 5)}
WEEDS = [(1, 6), (5, 8), (14, 7), (12, 4)]      # (x, Hoehe)

def scale(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))

def new_fish(i):
    col = FISH_COLS[i % len(FISH_COLS)]
    d = random.choice((-1, 1))
    return {"x": random.uniform(0, W - FW), "y": random.uniform(1, 10), "ty": random.uniform(1, 10),
            "dir": d, "speed": random.uniform(0.05, 0.13), "col": col,
            "tail": scale(col, 0.55), "eye": scale(col, 0.2), "ph": random.randrange(256)}

def water(x, y, frame):
    # nach unten dunkler, in den obersten 3 Reihen flimmerndes Licht
    f = 0.22 - y * 0.012
    if y < 3:
        f += max(0, SIN[(x * 23 + frame * 4 + y * 40) & 255]) * (0.12 - y * 0.04)
    return (0, int(60 * f), int(255 * f))

# Unbewegter Hintergrund (Wasser ab Reihe 3, Sandboden) wird einmal vorberechnet
m.clear()
for y in range(3, H - 1):
    for x in range(W):
        m.set(x, y, water(x, y, 0))
for x in range(W):
    m.set(x, H - 1, PEBBLES.get((x, H - 1), SAND))
BG = bytes(m.buf)

fishes = [new_fish(i) for i in range(FISH)]
bubbles = []       # [x, y, Wobbel-Phase]
frame = 0

def draw_fish(f):
    ox, oy = int(f["x"] + 0.5), int(f["y"] + 0.5)
    for ry, row in enumerate(FISH_ART):
        for rx, ch in enumerate(row):
            if ch == ".":
                continue
            x = ox + (rx if f["dir"] > 0 else FW - 1 - rx)
            col = f["col"] if ch == "B" else f["tail"] if ch == "T" else f["eye"]
            m.set(x, oy + ry, col)

while True:
    t = time.ticks_ms()
    frame += 1
    m.buf[:] = BG
    for y in range(3):
        for x in range(W):
            m.set(x, y, water(x, y, frame))
    # Seegras wiegt sich, oben staerker
    for wx, wh in WEEDS:
        for k in range(wh):
            y = H - 2 - k
            sway = SIN[(frame * 2 + k * 18 + wx * 30) & 255] * k / wh * 1.4
            g = 120 + k * 15
            m.set(int(wx + sway + 0.5), y, (0, g, 20))
    for (x, y), c in CHEST.items():
        m.set(x, y, c)
    # Fische
    for f in fishes:
        f["x"] += f["dir"] * f["speed"]
        f["ph"] = (f["ph"] + 3) & 255
        if abs(f["ty"] - f["y"]) < 0.2 or random.random() < 0.003:
            f["ty"] = random.uniform(0, 10)
        f["y"] += (f["ty"] - f["y"]) * 0.01 + SIN[f["ph"]] * 0.02
        # am Rand oder einfach mal so umdrehen
        if (f["dir"] > 0 and f["x"] > W + 2) or (f["dir"] < 0 and f["x"] < -FW - 2) or random.random() < 0.002:
            f["dir"] = -f["dir"]
            f["speed"] = random.uniform(0.05, 0.13)
        draw_fish(f)
    # Luftblasen aus der Truhe
    if random.random() < BUBBLE_RATE:
        bubbles.append([10.0, 12.0, random.randrange(256)])
    for b in bubbles:
        b[1] -= 0.18
        b[2] = (b[2] + 12) & 255
        m.set(int(b[0] + SIN[b[2]] * 0.7 + 0.5), int(b[1] + 0.5), (140, 220, 255))
    bubbles = [b for b in bubbles if b[1] > -0.5]
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
