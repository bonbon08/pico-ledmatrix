# Demo: Elemente. Physik-Sandkasten: ein Spender giesst Sand, Wasser, Lava und Samen aus. Lava und
# Wasser werden zu Stein und Dampf, Dampf regnet wieder ab, Pflanzen wachsen ins Wasser und brennen.
import time, random, micropython, array, gc
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
FULL = 165           # so viele belegte Pixel, dann oeffnet sich der Boden
KEEP = 30            # beim Ablaufen bleibt etwa so viel uebrig
DRAIN_MAX = 200      # laengstens so lange (Bilder) wird abgelassen
PHASE = (60, 160)    # Dauer einer Giess-Phase in Bildern (von, bis)
# Giess-Phasen: (Material, alle wie viele Bilder ein Pixel, Gewicht)
POUR = ((1, 2, 4),   # Sand
        (2, 2, 4),   # Wasser
        (3, 3, 3),   # Lava
        (8, 6, 3),   # Samen
        (9, 3, 2),   # Regen (Wasser an zufaelligen Stellen)
        (0, 1, 2))   # Pause

# Stoffe: 0 leer, 1 Sand, 2 Wasser, 3 Lava, 4 Stein, 5 Dampf, 6 Pflanze, 7 Feuer, 8 Samen
PAL = bytes((0, 0, 0,  255, 200, 60,  30, 90, 255,  255, 70, 0,  140, 140, 160,
             170, 180, 210,  40, 220, 40,  255, 160, 0,  170, 255, 80))
# Dichte als Bewegender (wer sinkt durch wen) und als Ziel (255 = feste Wand)
MD = bytes((0, 5, 2, 3, 5, 1, 0, 0, 5))
TD = bytes((0, 255, 2, 255, 255, 1, 255, 255, 255))
VAR = bytes((0, 30, 25, 90, 25, 30, 40, 120, 20))   # Farbschwankung je Stoff

# grosse Puffer zuerst
g = bytearray(W * H)                 # Stoff je Zelle
st = bytearray(W * H)                # Bildstempel: Zelle hat sich in diesem Bild schon bewegt
RND = bytearray(4096)
for i in range(4096):
    RND[i] = random.getrandbits(8)
IDX = array.array('H', [m.xy(i % W, i // W) * 3 for i in range(W * H)])
ri = array.array('i', [0])           # Lesezeiger in RND

@micropython.viper
def step(g: ptr8, st: ptr8, R: ptr8, rp: ptr32, md: ptr8, td: ptr8, fr: int) -> int:
    p = int(rp[0])
    stamp = fr % 255 + 1
    if stamp == 1:
        for i in range(256):
            st[i] = 0
    filled = 0
    y = 15
    while y >= 0:
        for k in range(16):
            x = k if ((fr + y) & 1) else 15 - k
            i = y * 16 + x
            t = int(g[i])
            if t == 0:
                continue
            filled += 1
            if int(st[i]) == stamp:
                continue
            p = (p + 1) & 4095
            r = int(R[p])
            # Reaktionen mit den vier Nachbarn
            if t == 3 or t == 6 or t == 7:
                for n in range(4):
                    if n == 0:
                        if y == 0:
                            continue
                        j = i - 16
                    elif n == 1:
                        if y == 15:
                            continue
                        j = i + 16
                    elif n == 2:
                        if x == 0:
                            continue
                        j = i - 1
                    else:
                        if x == 15:
                            continue
                        j = i + 1
                    u = int(g[j])
                    if t == 3:
                        if u == 2:
                            g[i] = 4; g[j] = 5; st[j] = stamp
                            t = 4
                        elif u == 6 or u == 8:
                            g[j] = 7; st[j] = stamp
                    elif t == 6:
                        if u == 2 and r < 2:
                            g[j] = 6; st[j] = stamp
                        elif u == 0 and n == 0 and r == 255:
                            g[j] = 6; st[j] = stamp     # selten nach oben ueber das Wasser
                    elif t == 7:
                        if (u == 6 or u == 8) and r < 110:
                            g[j] = 7; st[j] = stamp
                        elif u == 2:
                            g[j] = 5; st[j] = stamp     # Wasser loescht, wird zu Dampf
                            t = 0
                if t == 7 or t == 0:
                    if t == 0 or r < 14:
                        g[i] = 0
                    continue
                if t == 6:
                    continue
            if t == 5:
                # Dampf steigt, kondensiert oben zu Regen, verschwindet selten
                moved = 0
                if y > 0:
                    for n in range(3):
                        if n == 0:
                            j = i - 16
                        else:
                            s = 1 if ((r + n) & 1) else -1
                            if n == 2:
                                s = -s
                            if x + s < 0 or x + s > 15:
                                continue
                            j = i - 16 + s
                            if r & 2:
                                j = i + s           # auch seitlich treiben
                        u = int(g[j])
                        if u == 0 or u == 2:
                            g[j] = 5; g[i] = u; st[j] = stamp
                            moved = 1
                            break
                if moved == 0:
                    if y == 0 and r < 12:
                        g[i] = 2
                    elif r == 0:
                        g[i] = 0
                continue
            if t == 3 and r < 170:
                continue                            # Lava ist zaeh
            mt = int(md[t])
            moved = 0
            if y < 15:
                j = i + 16
                if int(td[int(g[j])]) < mt:
                    g[i] = g[j]; g[j] = t; st[j] = stamp
                    moved = 1
                else:
                    s = 1 if (r & 1) else -1
                    for n in range(2):
                        if x + s >= 0 and x + s <= 15:
                            j = i + 16 + s
                            if int(td[int(g[j])]) < mt:
                                g[i] = g[j]; g[j] = t; st[j] = stamp
                                moved = 1
                                break
                        s = -s
            if moved == 0 and (t == 2 or t == 3):
                # Fluessigkeit laeuft zur Seite
                s = 1 if (r & 4) else -1
                for n in range(2):
                    if x + s >= 0 and x + s <= 15:
                        j = i + s
                        if int(td[int(g[j])]) < mt:
                            g[i] = g[j]; g[j] = t; st[j] = stamp
                            moved = 1
                            break
                    s = -s
            if moved == 0 and t == 8:
                g[i] = 6                            # Samen keimt
        y -= 1
    rp[0] = p
    return filled

@micropython.viper
def draw(g: ptr8, pal: ptr8, var: ptr8, R: ptr8, rp: ptr32, idx: ptr16, dst: ptr8):
    p = int(rp[0])
    for i in range(256):
        t = int(g[i])
        j = int(idx[i])
        if t == 0:
            dst[j] = 0; dst[j + 1] = 0; dst[j + 2] = 0
            continue
        v = int(var[t])
        if t == 3 or t == 7 or t == 2:
            p = (p + 1) & 4095
            d = (int(R[p]) * v) >> 8                # flackert / schimmert
        else:
            d = ((((i * 7) ^ (i >> 4) * 13) & 7) * v) >> 3   # feste Koernung
        k = t * 3
        for c in range(3):
            val = int(pal[k + c]) - d
            if val < 0:
                val = 0
            dst[j + c] = val
    rp[0] = p

def pick():
    # viel Wasser oder viele Pflanzen machen Lava wahrscheinlicher, damit etwas passiert
    boost = 1 + (g.count(b"\x02") > 40) * 2 + (g.count(b"\x06") > 30) * 3
    ws = [w * boost if mat == 3 else w for mat, _, w in POUR]
    r = random.randrange(sum(ws))
    for (mat, every, _), w in zip(POUR, ws):
        if r < w:
            return mat, every
        r -= w

mat, every = pick()
left = random.randrange(*PHASE)
px = random.uniform(2, 13)
vx = random.choice((-0.15, 0.15))
drain = 0
frame = 0

while True:
    t = time.ticks_ms()
    frame += 1
    filled = step(g, st, RND, ri, MD, TD, frame)

    if drain:
        drain += 1
        if filled < KEEP or drain > DRAIN_MAX:
            drain = 0
        elif drain % 25 == 0:
            # haengengebliebene Pflanzen: eine faengt Feuer
            k = random.randrange(W * H)
            for n in range(W * H):
                if g[(k + n) % (W * H)] == 6:
                    g[(k + n) % (W * H)] = 7
                    break
        for x in range(W):
            if random.random() < 0.35:
                g[(H - 1) * W + x] = 0
    else:
        if filled > FULL:
            drain = 1
        # Spender wandert oben hin und her
        px += vx
        if px < 1 or px > W - 2:
            vx = -vx
        if random.random() < 0.01:
            vx = -vx
        if mat and frame % every == 0:
            if mat == 9:
                x = random.randrange(W)
                if g[x] == 0:
                    g[x] = 2
            else:
                x = int(px + 0.5)
                if g[x] == 0:
                    g[x] = mat
        left -= 1
        if left <= 0:
            mat, every = pick()
            left = random.randrange(*PHASE)

    draw(g, PAL, VAR, RND, ri, IDX, m.buf)
    m.show()
    if frame % 8 == 0:
        gc.collect()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
