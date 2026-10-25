# Demo: Pflastersteinblock (Cobblestone) im Minecraft-Stil, der um alle drei Achsen taumelt.
# Gleiche Technik wie erdblock.py: jede sichtbare Seite ist ein Parallelogramm, die Textur-
# Koordinaten haengen linear von der Pixelposition ab, die Pixel-Schleife laeuft in viper.
import time, math, micropython, array
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
SPIN = (0.041, 0.027, 0.017)   # Drehtempo um y, x und z (verschieden -> wirkt wie Taumeln)
ZOOM = 1.8         # halbe Bildbreite in Wuerfel-Einheiten; ab ca. 1.75 passt der Wuerfel immer ganz rein

# Steine 8x8: '.' = Fuge, 1-4 = Stein in verschiedenen Grautoenen
STONES = ("11.222.3",
          "11.22..3",
          "..333.44",
          "4.33.144",
          "4...11..",
          ".222.1.3",
          ".22..333",
          "1..44.33")
SHADES = {".": (70, 70, 78), "1": (200, 200, 205), "2": (160, 160, 165), "3": (130, 130, 138),
          "4": (230, 230, 235)}

# eigener Zufallsgenerator -> leichtes Rauschen, aber immer dieselbe Textur
_s = 4321
def rnd():
    global _s
    _s = (_s * 1103515245 + 12345) & 0x7FFFFFFF
    return (_s >> 8) / (1 << 23)

T_STONE = []
for row in STONES:
    for ch in row:
        f = 0.9 + 0.2 * rnd()
        T_STONE.append(tuple(min(255, int(v * f)) for v in SHADES[ch]))

# Licht von oben links vorne
LX, LY, LZ = -0.35, 0.85, -0.4
_l = math.sqrt(LX * LX + LY * LY + LZ * LZ)
LX, LY, LZ = LX / _l, LY / _l, LZ / _l

def mul(A, B):
    return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)) for i in range(3))

def rot(a, b, c):
    # Drehung um z (c), dann um y (a), dann um x (b)
    ca, sa = math.cos(a), math.sin(a)
    cb, sb = math.cos(b), math.sin(b)
    cc, sc = math.cos(c), math.sin(c)
    ry = ((ca, 0, sa), (0, 1, 0), (-sa, 0, ca))
    rx = ((1, 0, 0), (0, cb, -sb), (0, sb, cb))
    rz = ((cc, -sc, 0), (sc, cc, 0), (0, 0, 1))
    return mul(rx, mul(ry, rz))

TEX = bytearray()
for c in T_STONE:
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

# je Seite: Achse, Vorzeichen, Textur, Achse fuer u, Achse fuer v
SIDES = ((0, -1, 0, (0, 0, 1), (0, -1, 0)), (0, 1, 0, (0, 0, 1), (0, -1, 0)),
         (1, -1, 0, (1, 0, 0), (0, 0, 1)), (1, 1, 0, (1, 0, 0), (0, 0, 1)),
         (2, -1, 0, (1, 0, 0), (0, -1, 0)), (2, 1, 0, (1, 0, 0), (0, -1, 0)))

def render(R):
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
        shade = 0.5 + 0.5 * max(0.0, nx * LX + ny * LY + nz * LZ)
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

a = b = c = 0.0
while True:
    t = time.ticks_ms()
    render(rot(a, b, c))
    m.show()
    a += SPIN[0]
    b += SPIN[1]
    c += SPIN[2]
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
