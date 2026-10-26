# Demo: KI-Kern. Eine gepanzerte 3D-Kugel mit leuchtendem Auge dreht sich, ein Ring kreist um sie.
# Ab und zu haelt sie an, starrt den Betrachter an und das Auge glueht rot.
import time, math, random, micropython, array, gc
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
RADIUS = 5.6         # Kugelradius in Pixeln
SPIN = 1.6           # Drehtempo in Grad pro Bild
TILT = 18            # wie weit sie nach vorn/hinten kippt (Grad)
STARE_EVERY = (300, 600)   # Bilder zwischen zwei Mal Anstarren (von, bis)
STARE = 70           # so lange (Bilder) wird gestarrt
ARMOR = (230, 230, 245)    # Panzer
SEAM = (50, 55, 70)        # Fugen
EYE = (0, 220, 255)        # Auge normal
ANGRY = (255, 20, 0)       # Auge beim Starren
RINGS = (  # (Neigung um x, Neigung um z in Grad, Radius, Tempo, Farbe); weitere Ringe moeglich
    (16, 22, 7.4, 3, (255, 140, 0)),
)

# feste Tabellen zuerst; Vorzeichen-Werte werden um 256 verschoben gespeichert (ptr16 ist ohne Vorzeichen)
NX = array.array('H', [0] * 256)
NY = array.array('H', [0] * 256)
NZ = array.array('H', [0] * 256)     # 0 = Pixel liegt nicht auf der Kugel
IDX = array.array('H', [m.xy(i % W, i // W) * 3 for i in range(W * H)])
COS = array.array('H', [int(256 + 256 * math.cos(k * math.pi / 128)) for k in range(256)])

# Normalen der Kugel sind bei Parallelprojektion fest, nur die Drehung aendert sich
for i in range(256):
    dx = (i % W) - 7.5
    dy = (i // W) - 7.5
    d2 = dx * dx + dy * dy
    if d2 < RADIUS * RADIUS:
        NX[i] = int(256 + 256 * dx / RADIUS)
        NY[i] = int(256 + 256 * dy / RADIUS)
        NZ[i] = int(256 + 256 * math.sqrt(RADIUS * RADIUS - d2) / RADIUS)

@micropython.viper
def core(nx: ptr16, ny: ptr16, nz: ptr16, idx: ptr16, dst: ptr8, c: int, s: int, ct: int, st: int,
         er: int, eg: int, eb: int, eye: int, pal: ptr8):
    for i in range(256):
        j = int(idx[i])
        z = int(nz[i])
        if z == 0:
            dst[j] = 0; dst[j + 1] = 0; dst[j + 2] = 0
            continue
        x = int(nx[i]) - 256
        y = int(ny[i]) - 256
        z -= 256
        # Licht von oben links vorn (Blickrichtung)
        lam = (-x * 100 - y * 120 + z * 200) >> 8
        if lam < 0:
            lam = 0
        sh = 85 + lam * 170 // 256
        if sh > 255:
            sh = 255
        # Blickrichtung zurueck in Kugel-Koordinaten drehen: erst kippen, dann drehen
        y1 = (y * ct + z * st) >> 8
        z1 = (z * ct - y * st) >> 8
        ox = (x * c - z1 * s) >> 8
        oz = (x * s + z1 * c) >> 8
        oy = y1
        # Auge zeigt in Kugel-Richtung +z
        if oz > 225 and eye:
            if oz > 248:
                dst[j] = 255; dst[j + 1] = 255; dst[j + 2] = 255
            else:
                dst[j] = er; dst[j + 1] = eg; dst[j + 2] = eb
            continue
        if oz > 205:
            dst[j] = 0; dst[j + 1] = 0; dst[j + 2] = 0      # Augenhoehle
            continue
        ax = ox if ox > 0 else -ox
        ay = oy if oy > 0 else -oy
        az = oz if oz > 0 else -oz
        k = 3 if (ax < 22 or ay < 22 or az < 22) else 0   # Fugen: zwei Meridiane und der Aequator
        r = int(pal[k]); g = int(pal[k + 1]); b = int(pal[k + 2])
        dst[j] = (r * sh + 127) // 255
        dst[j + 1] = (g * sh + 127) // 255
        dst[j + 2] = (b * sh + 127) // 255

@micropython.viper
def ring(cos: ptr16, idx: ptr16, dst: ptr8, ux: int, uy: int, uz: int, vx: int, vy: int, vz: int,
         spin: int, rr: int, cr: int, cg: int, cb: int, r2: int):
    # 64 Punkte auf einem Kreis, gestrichelt; hinter der Kugel versteckt
    for k in range(64):
        if ((k + (spin >> 2)) & 7) > 4:
            continue
        a = k * 4
        ca = int(cos[a]) - 256
        sa = int(cos[(a + 192) & 255]) - 256
        px = (ux * ca + vx * sa) >> 8
        py = (uy * ca + vy * sa) >> 8
        pz = (uz * ca + vz * sa) >> 8
        sx = (((px * rr) >> 8) + 128) >> 4   # rr = Radius*16, Mitte 7.5 = 120/16, +8 zum Runden
        sy = (((py * rr) >> 8) + 128) >> 4
        if sx < 0 or sx > 15 or sy < 0 or sy > 15:
            continue
        if pz < 0:
            dx = sx * 16 - 120
            dy = sy * 16 - 120
            if dx * dx + dy * dy < r2:
                continue                      # hinter der Kugel
            f = 120
        else:
            f = 255
        j = int(idx[sy * 16 + sx])
        dst[j] = (cr * f + 127) // 255
        dst[j + 1] = (cg * f + 127) // 255
        dst[j + 2] = (cb * f + 127) // 255

def ring_axes(ax, az):
    # zwei Achsen (x256) der Ringebene: Kreis in der x/z-Ebene, um x und z gekippt
    ax, az = math.radians(ax), math.radians(az)
    u = (1.0, 0.0, 0.0)
    v = (0.0, 0.0, 1.0)
    def rot(p):
        x, y, z = p
        y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
        x, y = x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az)
        return tuple(int(256 * q) for q in (x, y, z))
    return rot(u) + rot(v)

PAL = bytes(ARMOR + SEAM)
RING_AX = [ring_axes(a, b) for a, b, _, _, _ in RINGS]
R2 = int((RADIUS * 16) ** 2)

yaw = 0.0
speed = SPIN
frame = 0
next_stare = random.randrange(*STARE_EVERY)
stare = 0
blink = 0
spins = [0] * len(RINGS)

def cs(deg):
    k = int(deg * 256 / 360) & 255
    return COS[k] - 256, COS[(k + 192) & 255] - 256

while True:
    t = time.ticks_ms()
    frame += 1
    eye_col = EYE
    if stare:
        stare -= 1
        # Auge zum Betrachter (yaw = 0), rot pulsierend
        d = (-yaw + 180) % 360 - 180
        yaw += d * 0.15
        p = 0.6 + 0.4 * math.sin(frame * 0.4)
        eye_col = tuple(int(c * p) for c in ANGRY)
        if stare == 0:
            next_stare = frame + random.randrange(*STARE_EVERY)
            speed = 0.0
    else:
        speed = min(SPIN, speed + 0.05)
        yaw = (yaw + speed) % 360
        if frame >= next_stare and (yaw < 90 or yaw > 270):
            stare = STARE
    tilt = TILT * math.sin(frame * 0.015) if not stare else 0.0
    if blink == 0 and random.random() < 0.008:
        blink = 3
    blink = max(0, blink - 1)

    c, s = cs(yaw)
    ct, st = cs(tilt)
    core(NX, NY, NZ, IDX, m.buf, c, s, ct, st, eye_col[0], eye_col[1], eye_col[2], 0 if blink else 1, PAL)
    for n, (_, _, rad, sp, col) in enumerate(RINGS):
        spins[n] += sp
        ux, uy, uz, vx, vy, vz = RING_AX[n]
        ring(COS, IDX, m.buf, ux, uy, uz, vx, vy, vz, spins[n] & 0xFFFF, int(rad * 16), col[0], col[1], col[2], R2)
    m.show()
    if frame % 8 == 0:
        gc.collect()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
