# Demo: Feuer. Unter dem Bild liegen zwei unsichtbare Glutreihen, deren Waerme nach oben
# steigt und dabei abkuehlt. Die Waerme (0-255) wird ueber eine Palette in Farben umgesetzt.
import time, random, micropython, array
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40      # Zeit pro Bild
COOL = 45          # Abkuehlung beim Aufsteigen (groesser = kleinere Flammen)
EMBER = 0.04       # Chance pro Bild, dass ein Funke hochsteigt
WIND = 0.03        # wie oft der Wind die Richtung wechselt

# Waerme je Zelle, 2 unsichtbare Glutreihen unter dem Bild (Zeile H und H+1)
heat = bytearray(W * (H + 2))
IDX = array.array('H', [m.xy(c % W, c // W) * 3 for c in range(W * H)])

@micropython.viper
def rise(heat: ptr8, w: int, h: int, wind: int, cool: int, seed: int) -> int:
    # Mittel aus den Zellen darunter, minus zufaellige Abkuehlung (oben staerker).
    # Eigener Zufallsgenerator, weil random in viper nicht geht.
    s = seed
    for y in range(h):
        row = y * w
        below = row + w
        below2 = below + w
        for x in range(w):
            xs = (x + wind + w) % w
            v = (heat[below + (xs + w - 1) % w] + heat[below + xs] * 2
                 + heat[below + (xs + 1) % w] + heat[below2 + xs]) // 5
            s = (s * 25173 + 13849) & 0xFFFF
            v -= ((s >> 4) * cool >> 12) * (h - y) // h + 2
            heat[row + x] = v if v > 0 else 0
    return s

@micropython.viper
def paint(heat: ptr8, pal: ptr8, idx: ptr16, buf: ptr8, n: int):
    for c in range(n):
        j = idx[c]
        p = heat[c] * 3
        buf[j] = pal[p]
        buf[j + 1] = pal[p + 1]
        buf[j + 2] = pal[p + 2]

def make_palette():
    # schwarz -> dunkelrot -> rot -> orange -> gelb -> hellgelb
    pts = [(0, (0, 0, 0)), (40, (40, 0, 0)), (90, (200, 10, 0)), (140, (255, 70, 0)),
           (190, (255, 160, 0)), (230, (255, 230, 40)), (255, (255, 255, 120))]
    pal = bytearray(256 * 3)
    for i in range(256):
        for k in range(len(pts) - 1):
            a, ca = pts[k]
            b, cb = pts[k + 1]
            if a <= i <= b:
                t = (i - a) * 256 // (b - a)
                for ch in range(3):
                    pal[i * 3 + ch] = ca[ch] + ((cb[ch] - ca[ch]) * t >> 8)
                break
    return pal

PAL = make_palette()
embers = []        # aufsteigende Funken: [x, y, Waerme]
# Brennstoff je Spalte, schwankt langsam -> einzelne Flammenzungen
fuel = [random.randrange(120, 256) for _ in range(W)]
wind = 0
seed = random.randrange(65536)

while True:
    t = time.ticks_ms()
    # Glutreihen flackern
    base = W * H
    for x in range(W):
        f = fuel[x] + random.randrange(-25, 26)
        fuel[x] = 100 if f < 100 else 255 if f > 255 else f
        v = fuel[x] - random.randrange(60) if random.random() < 0.85 else random.randrange(30, 100)
        heat[base + x] = v
        heat[base + W + x] = (heat[base + W + x] + v) >> 1
    if random.random() < WIND:
        wind = random.choice((-1, 0, 0, 1))
    seed = rise(heat, W, H, wind, COOL, seed)
    # Funken
    if random.random() < EMBER:
        embers.append([random.randrange(W), H - 1, 255])
    for e in embers:
        e[1] -= 1
        e[0] = (e[0] + random.choice((-1, 0, 0, 1))) % W
        e[2] -= 18
    embers = [e for e in embers if e[1] >= 0 and e[2] > 60]
    # Zeichnen
    paint(heat, PAL, IDX, m.buf, W * H)
    for x, y, v in embers:
        m.set(x, y, (255, 200 * v // 255, 60 * v // 255))
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
