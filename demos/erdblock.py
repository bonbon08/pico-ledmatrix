# Demo: Rotierender Erdblock im Minecraft-Stil. Jede sichtbare Wuerfelseite ist auf dem Bild
# ein Parallelogramm (orthografische Projektion), ihre Textur-Koordinaten haengen linear von der
# Pixelposition ab. Pro Bild werden je Seite 6 Koeffizienten berechnet, die Pixel-Schleife
# laeuft als viper-Code mit Ganzzahlen. Die 8x8-Textur wird beim Start selbst erzeugt.
import time, math, micropython, array
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
GRASS = False      # True = Grasblock (gruene Oberseite, gruener Rand an den Seiten)
SPIN = 0.045       # Drehung pro Bild (Bogenmass)
TILT = -0.5        # Neigung nach vorne, damit man die Oberseite sieht
ZOOM = 1.65        # halbe Bildbreite in Wuerfel-Einheiten (kleiner = groesserer Wuerfel)

# --- Textur 8x8, eigener Zufallsgenerator -> immer dieselbe Textur ---
_s = 1234
def rnd():
    global _s
    _s = (_s * 1103515245 + 12345) & 0x7FFFFFFF
    return (_s >> 8) / (1 << 23)

# Farben nutzen den vollen Bereich, weil matrix.py ohnehin stark herunterdimmt
DIRT = ((230, 150, 90), (195, 128, 75), (160, 102, 60), (130, 84, 48), (255, 180, 112))
GREEN = ((130, 220, 70), (105, 190, 55), (85, 160, 45))

def tex_dirt():
    t = []
    for i in range(64):
        r = rnd()
        t.append(DIRT[4] if r < 0.06 else DIRT[3] if r < 0.2 else DIRT[2] if r < 0.45
                 else DIRT[1] if r < 0.75 else DIRT[0])
    return t

def tex_green():
    return [GREEN[int(rnd() * 3)] for _ in range(64)]

T_DIRT = tex_dirt()
if GRASS:
    T_TOP = tex_green()
    T_SIDE = tex_dirt()
    for x in range(8):
        drip = 2 + (1 if rnd() < 0.5 else 0) + (1 if rnd() < 0.2 else 0)
        for y in range(drip):
            T_SIDE[y * 8 + x] = GREEN[int(rnd() * 3)]
else:
    T_TOP = T_SIDE = T_DIRT

# Licht von oben links vorne
LX, LY, LZ = -0.35, 0.85, -0.4
_l = math.sqrt(LX * LX + LY * LY + LZ * LZ)
LX, LY, LZ = LX / _l, LY / _l, LZ / _l

def rot(a, b):
    # Drehung um y (Winkel a), dann Neigung um x (Winkel b); liefert Zeilen der Matrix
    ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
    return ((ca, 0, sa), (sa * sb, cb, -ca * sb), (-sa * cb, sb, ca * cb))

# Texturen hintereinander in einem Puffer: 0 = Erde, 1 = Oberseite, 2 = Seite
TEX = bytearray()
for t in (T_DIRT, T_TOP, T_SIDE):
    for c in t:
        TEX.extend(bytes(c))
IDX = array.array('H', [m.xy(i % W, i // W) * 3 for i in range(W * H)])
FACES = array.array('i', [0] * 3 * 8)
FP = 1 << 12       # Festkomma: 12 Bit Nachkommastellen

@micropython.viper
def raster(faces: ptr32, nf: int, tex: ptr8, idx: ptr16, buf: ptr8):
    for py in range(16):
        for px in range(16):
            j = idx[py * 16 + px]
            r = 0
            g = 0
            b = 0
            f = 0
            while f < nf:
                o = f * 8
                tx = faces[o] * px + faces[o + 1] * py + faces[o + 2]
                ty = faces[o + 3] * px + faces[o + 4] * py + faces[o + 5]
                if tx >= 0 and tx < 32768 and ty >= 0 and ty < 32768:
                    t = faces[o + 7] + ((ty >> 12) * 8 + (tx >> 12)) * 3
                    s = faces[o + 6]
                    r = (tex[t] * s) >> 8
                    g = (tex[t + 1] * s) >> 8
                    b = (tex[t + 2] * s) >> 8
                    break
                f += 1
            buf[j] = r
            buf[j + 1] = g
            buf[j + 2] = b

# je Seite: Achse, Vorzeichen, Textur, Achse fuer u, Achse fuer v (Seiten: v zeigt nach unten)
SIDES = ((0, -1, 2, (0, 0, 1), (0, -1, 0)), (0, 1, 2, (0, 0, 1), (0, -1, 0)),
         (1, -1, 0, (1, 0, 0), (0, 0, 1)), (1, 1, 1, (1, 0, 0), (0, 0, 1)),
         (2, -1, 2, (1, 0, 0), (0, -1, 0)), (2, 1, 2, (1, 0, 0), (0, -1, 0)))

def render(a):
    R = rot(a, TILT)
    step = 2 * ZOOM / W

    def to_px(v, point):
        # Wuerfel-Koordinaten -> Pixel (Punkt oder Richtung)
        wx = R[0][0] * v[0] + R[0][1] * v[1] + R[0][2] * v[2]
        wy = R[1][0] * v[0] + R[1][1] * v[1] + R[1][2] * v[2]
        if point:
            return ((wx + ZOOM) / step - 0.5, (-wy + ZOOM) / step - 0.5)
        return (wx / step, -wy / step)

    nf = 0
    for axis, sign, texno, ua, va in SIDES:
        nz = R[2][axis] * sign
        if nz >= 0:               # zeigt vom Betrachter weg
            continue
        nx, ny = R[0][axis] * sign, R[1][axis] * sign
        shade = 0.55 + 0.45 * max(0.0, nx * LX + ny * LY + nz * LZ)
        cen = [0, 0, 0]
        cen[axis] = sign
        cx, cy = to_px(cen, True)
        ux, uy = to_px(ua, False)
        vx, vy = to_px(va, False)
        det = ux * vy - vx * uy
        if abs(det) < 1e-3:
            continue
        # u = ia*(px-cx) + ib*(py-cy), Texel-x = 4u + 4 (u, v laufen von -1 bis 1)
        ia, ib = vy / det, -vx / det
        ic, id_ = -uy / det, ux / det
        o = nf * 8
        FACES[o] = int(4 * ia * FP)
        FACES[o + 1] = int(4 * ib * FP)
        FACES[o + 2] = int((4 - 4 * ia * cx - 4 * ib * cy) * FP)
        FACES[o + 3] = int(4 * ic * FP)
        FACES[o + 4] = int(4 * id_ * FP)
        FACES[o + 5] = int((4 - 4 * ic * cx - 4 * id_ * cy) * FP)
        FACES[o + 6] = int(shade * 256)
        FACES[o + 7] = texno * 64 * 3
        nf += 1
    raster(FACES, nf, TEX, IDX, m.buf)

a = 0.0
while True:
    t = time.ticks_ms()
    render(a)
    m.show()
    a += SPIN
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
