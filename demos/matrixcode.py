# Demo: Matrix-Code. Gruene Zeichenspuren regnen in jeder Spalte unterschiedlich schnell herunter.
# Jede Zelle hat eine Helligkeit, die langsam abklingt - der Kopf einer Spur setzt sie auf voll,
# dadurch entsteht der Schweif von selbst. Die "Zeichen" flackern zufaellig.
import time, random, micropython, array
import matrix as m

W, H = m.W, m.H
FRAME_MS = 35
DECAY = 225        # wie schnell der Schweif verblasst (0-255, groesser = laengerer Schweif)
GLYPH_FLIP = 0.06  # Chance pro Bild, dass ein Zeichen wechselt
DROPS = 1.3        # Spuren pro Spalte im Schnitt

level = bytearray(W * H)                          # Helligkeit je Zelle
glyph = bytearray(random.randrange(90, 256) for _ in range(W * H))   # Zeichen-Helligkeit
head = bytearray(W * H)                           # 1 = hier ist gerade ein Kopf

IDX = array.array('H', [m.xy(i % W, i // W) * 3 for i in range(W * H)])

@micropython.viper
def decay(level: ptr8, head: ptr8, n: int, f: int):
    for i in range(n):
        level[i] = (level[i] * f) >> 8
        head[i] = 0

@micropython.viper
def paint(level: ptr8, glyph: ptr8, head: ptr8, idx: ptr16, buf: ptr8, n: int):
    for i in range(n):
        j = idx[i]
        if head[i]:
            buf[j] = 190
            buf[j + 1] = 255
            buf[j + 2] = 190
        else:
            v = (level[i] * glyph[i]) >> 8
            buf[j] = 0
            buf[j + 1] = v
            buf[j + 2] = v >> 3

def new_drop(x, start_above=True):
    return [x, -random.uniform(0, H) if start_above else random.uniform(0, H),
            random.uniform(0.18, 0.55)]

drops = [new_drop(x % W, False) for x in range(int(W * DROPS))]

while True:
    t = time.ticks_ms()
    decay(level, head, W * H, DECAY)
    # Zeichen wechseln
    for _ in range(int(W * H * GLYPH_FLIP)):
        glyph[random.randrange(W * H)] = random.randrange(90, 256)
    # Spuren fallen
    for d in drops:
        d[1] += d[2]
        y = int(d[1])
        if y >= H + 2:
            d[:] = new_drop(random.randrange(W))
            continue
        if 0 <= y < H:
            i = y * W + d[0]
            level[i] = 255
            head[i] = 1
    paint(level, glyph, head, IDX, m.buf, W * H)
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
