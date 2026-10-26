# Demo: OS-Logo. Zeigt das Logo des Betriebssystems vom PC, so wie fastfetch es anzeigt: baut sich
# funkelnd auf, ein Glanzstreifen zieht darueber, dann zerfaellt es und baut sich neu auf.
# Das Logo kommt aus oslogo.bin, das tools/oslogo.py auf dem PC erzeugt und mit hochlaedt.
import time, random, micropython, array
import matrix as m

W, H = m.W, m.H
FRAME_MS = 30
FILE = "oslogo.bin"  # 768 Byte RGB, zeilenweise von oben links
BUILD_SPEED = 2      # Aufbau/Zerfall: Fortschritt pro Bild (alles in ca. 3,5 s)
HOLD = 600           # so viele Bilder bleibt das Logo stehen (ca. 18 s)
GLINT_EVERY = 160    # alle so vielen Bilder zieht ein Glanzstreifen darueber
PAUSE = 25           # dunkle Pause zwischen Zerfall und neuem Aufbau

# grosse Puffer zuerst anlegen
src = bytearray(W * H * 3)
appear = bytearray(W * H)            # Reihenfolge, in der die Pixel erscheinen (0..223)
IDX = array.array('H', [m.xy(i % W, i // W) * 3 for i in range(W * H)])

try:
    with open(FILE, "rb") as f:
        f.readinto(src)
except OSError:
    # kein Logo hochgeladen: weisses Fragezeichen
    Q = ("..XXXX..", ".XX..XX.", ".....XX.", "....XX..", "...XX...", "...XX...", "........", "...XX...")
    for y, row in enumerate(Q):
        for x, ch in enumerate(row):
            if ch == "X":
                for dy in (0, 1):
                    for dx in (0, 1):
                        j = ((y * 2 + dy) * W + x * 2 + dx) * 3
                        src[j] = src[j + 1] = src[j + 2] = 255
LIT = [i for i in range(W * H) if src[i * 3] | src[i * 3 + 1] | src[i * 3 + 2]]

def shuffle():
    # neue zufaellige Reihenfolge fuer die leuchtenden Pixel
    order = LIT[:]
    for i in range(len(order) - 1, 0, -1):
        j = random.randrange(i + 1)
        order[i], order[j] = order[j], order[i]
    n = max(1, len(order))
    for r, i in enumerate(order):
        appear[i] = r * 224 // n

@micropython.viper
def compose(src: ptr8, idx: ptr16, appear: ptr8, dst: ptr8, phase: int, rev: int, glint: int):
    for i in range(256):
        a = int(appear[i])
        if rev:
            v = (a - phase + 8) * 32
        else:
            v = (phase - a) * 32
        if v > 255:
            v = 255
        k = i * 3
        j = int(idx[i])
        r = int(src[k]); g = int(src[k + 1]); b = int(src[k + 2])
        if v <= 0 or (r | g | b) == 0:
            dst[j] = 0; dst[j + 1] = 0; dst[j + 2] = 0
            continue
        # Helligkeit, beim Erscheinen/Verschwinden kurz weiss aufblitzen
        bri = v * 2
        if bri > 255:
            bri = 255
        w = 255 - v
        d = (i & 15) + (i >> 4) - glint
        if d < 0:
            d = -d
        if d == 0:
            w += 170
        elif d == 1:
            w += 80
        if w > 255:
            w = 255
        r = r + ((255 - r) * w + 127) // 255
        g = g + ((255 - g) * w + 127) // 255
        b = b + ((255 - b) * w + 127) // 255
        dst[j] = (r * bri + 127) // 255
        dst[j + 1] = (g * bri + 127) // 255
        dst[j + 2] = (b * bri + 127) // 255

END = 224 + 8        # ab hier sind alle Pixel ganz da bzw. ganz weg
shuffle()
state = 0            # 0 Aufbau, 1 Stehen, 2 Zerfall, 3 Pause
phase = 0
timer = 0

while True:
    t = time.ticks_ms()
    glint = -100
    if state == 0:
        phase += BUILD_SPEED
        compose(src, IDX, appear, m.buf, phase, 0, glint)
        if phase >= END:
            state, timer = 1, 0
    elif state == 1:
        timer += 1
        g = timer % GLINT_EVERY
        if g < 80:
            glint = g // 2 - 4       # Streifen laeuft von oben links nach unten rechts
        compose(src, IDX, appear, m.buf, END, 0, glint)
        if timer >= HOLD:
            state, phase = 2, 0
            shuffle()
    elif state == 2:
        phase += BUILD_SPEED
        compose(src, IDX, appear, m.buf, phase, 1, glint)
        if phase >= END:
            state, timer = 3, 0
    else:
        timer += 1
        if timer == 1:
            m.clear()
        if timer >= PAUSE:
            state, phase = 0, 0
            shuffle()
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
