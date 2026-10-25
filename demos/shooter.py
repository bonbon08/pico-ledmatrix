# Demo: Ego-Shooter im Stil der 90er, der sich selbst spielt. Raycasting mit 16 Strahlen
# (einer pro Spalte), eigenes Labyrinth, Gegner sind einaeugige Schleimmonster.
# Die KI laeuft zu zufaelligen Zielen, sucht Gegner, dreht sich zu ihnen und schiesst.
import time, random, math, gc
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
FOV = 0.66          # halbe Bildbreite der Kamera (tan des halben Blickwinkels)
ENEMIES = 3
SHOOT_DIST = 3.2   # erst so nah herangehen, dann schiessen
MOVE = 0.055        # Laufgeschwindigkeit pro Bild
TURN = 0.07         # Drehgeschwindigkeit pro Bild

# '#' = Stein, 'B' = Ziegel, 'T' = Technik, '.' = frei
MAP = (
    "################",
    "#......#.......#",
    "#.BB...#..TTT..#",
    "#.B....#....T..#",
    "#.B..###....T..#",
    "#..............#",
    "####..BBBB..####",
    "#.....B..B.....#",
    "#.TT..B..B..TT.#",
    "#.T..........T.#",
    "#.T..######..T.#",
    "#....#....#....#",
    "#.BB.#....#.BB.#",
    "#....#....#....#",
    "#..............#",
    "################",
)
MW, MH = len(MAP[0]), len(MAP)
WALL_COL = {"#": (150, 150, 165), "B": (200, 90, 50), "T": (60, 200, 170)}
# 4x4-Muster je Wandart (Helligkeit in 1/8): Fugen, Ziegel, Paneele
WALL_TEX = {
    "#": ((8, 8, 8, 6), (8, 7, 8, 6), (6, 6, 6, 6), (8, 6, 8, 8)),
    "B": ((8, 8, 8, 5), (5, 5, 5, 5), (8, 5, 8, 8), (5, 5, 5, 5)),
    "T": ((8, 8, 8, 8), (8, 5, 5, 8), (8, 5, 5, 8), (8, 8, 8, 8)),
}
MONSTER = (".PPP.",
           "PPWPP",
           "PWKWP",
           "PPPPP",
           "P.P.P")
MONSTER_COL = {"P": (170, 30, 255), "W": (255, 255, 255), "K": (20, 0, 0)}

# Pufferposition je Pixel, spaltenweise
COLIDX = [[m.xy(x, y) * 3 for y in range(H)] for x in range(W)]

def solid(x, y):
    return MAP[int(y)][int(x)] != "."

FREE = [(x, y) for y in range(MH) for x in range(MW) if MAP[y][x] == "."]

# Hintergrund: Decke dunkelgrau, Boden braun, beide zur Mitte hin dunkler
m.clear()
for y in range(H):
    d = abs(y - 7.5) / 7.5
    col = (int(30 * d), int(30 * d), int(38 * d)) if y < 8 else (int(110 * d), int(70 * d), int(40 * d))
    for x in range(W):
        m.set(x, y, col)
BG = bytes(m.buf)

def scale(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))

def los(x0, y0, x1, y1):
    # freie Sichtlinie zwischen zwei Punkten?
    dx, dy = x1 - x0, y1 - y0
    n = int(math.sqrt(dx * dx + dy * dy) * 6) + 1
    for i in range(1, n):
        if solid(x0 + dx * i / n, y0 + dy * i / n):
            return False
    return True

OPEN = bytearray(1 if MAP[i // MW][i % MW] == "." else 0 for i in range(MW * MH))

def bfs(start, goal):
    # kuerzester Weg auf dem Raster, Felder als y * MW + x
    s, g = start[1] * MW + start[0], goal[1] * MW + goal[0]
    prev = bytearray(MW * MH)
    seen = bytearray(MW * MH)
    seen[s] = 1
    q = [s]
    i = 0
    while i < len(q):
        c = q[i]
        i += 1
        if c == g:
            path = []
            while c != s:
                path.append((c % MW, c // MW))
                c = prev[c]
            return path[::-1]
        for n in (c + 1, c - 1, c + MW, c - MW):
            if OPEN[n] and not seen[n]:
                seen[n] = 1
                prev[n] = c
                q.append(n)
    return []

def angle_diff(a, b):
    d = (a - b) % (2 * math.pi)
    return d - 2 * math.pi if d > math.pi else d

class Enemy:
    def __init__(self):
        self.spawn()

    def spawn(self):
        while True:
            x, y = random.choice(FREE)
            if abs(x + 0.5 - px) + abs(y + 0.5 - py) > 6:
                break
        self.x, self.y = x + 0.5, y + 0.5
        self.state = "alive"   # alive, dying, dead
        self.timer = 0

px, py, pa = 1.5, 1.5, 0.0
enemies = [Enemy() for _ in range(ENEMIES)]
path = []
target = None
cooldown = 0
flash = 0           # Muendungsfeuer
hurt = 0            # roter Bildschirm, wenn ein Gegner zu nah ist
bob = 0.0
frame = 0

def render():
    m.buf[:] = BG
    dx, dy = math.cos(pa), math.sin(pa)
    plx, ply = -dy * FOV, dx * FOV
    zbuf = [0.0] * W
    for x in range(W):
        cam = 2 * (x + 0.5) / W - 1
        rx, ry = dx + plx * cam, dy + ply * cam
        mx, my = int(px), int(py)
        ddx = abs(1 / rx) if rx else 1e9
        ddy = abs(1 / ry) if ry else 1e9
        if rx < 0:
            sx, sdx = -1, (px - mx) * ddx
        else:
            sx, sdx = 1, (mx + 1 - px) * ddx
        if ry < 0:
            sy, sdy = -1, (py - my) * ddy
        else:
            sy, sdy = 1, (my + 1 - py) * ddy
        while True:
            if sdx < sdy:
                sdx += ddx
                mx += sx
                side = 0
            else:
                sdy += ddy
                my += sy
                side = 1
            if MAP[my][mx] != ".":
                break
        dist = (sdx - ddx) if side == 0 else (sdy - ddy)
        dist = max(dist, 0.05)
        zbuf[x] = dist
        wall = MAP[my][mx]
        hit = (py + dist * ry) if side == 0 else (px + dist * rx)
        tu = int((hit - int(hit)) * 4) & 3
        col = WALL_COL[wall]
        shade = 1 / (1 + dist * 0.15) * (0.75 if side else 1.0)
        hgt = H / dist
        top = 8 - hgt / 2
        bot = 8 + hgt / 2
        y0 = max(0, int(top))
        y1 = min(H, int(bot) + 1)
        tex = WALL_TEX[wall]
        cr, cg, cb = int(col[0] * shade), int(col[1] * shade), int(col[2] * shade)
        cidx = COLIDX[x]
        buf = m.buf
        # Texturzeile in Festkomma (x256) mitzaehlen statt pro Pixel neu rechnen
        tstep = int(1024 / hgt)
        tv = int((y0 + 0.5 - top) * 1024 / hgt)
        for y in range(y0, y1):
            f = tex[(tv >> 8) & 3][tu]
            tv += tstep
            if y == y0 or y == y1 - 1:
                # Randpixel nur anteilig -> weichere Kanten
                cover = min(y + 1, bot) - max(y, top)
                if cover <= 0:
                    continue
                if cover < 1:
                    f = int(f * cover)
            j = cidx[y]
            buf[j] = cr * f >> 3
            buf[j + 1] = cg * f >> 3
            buf[j + 2] = cb * f >> 3
    # Gegner, von hinten nach vorne
    inv = 1 / (plx * dy - dx * ply)
    order = sorted(enemies, key=lambda e: -((e.x - px) ** 2 + (e.y - py) ** 2))
    for e in order:
        if e.state == "dead":
            continue
        ex, ey = e.x - px, e.y - py
        tx = inv * (dy * ex - dx * ey)
        tz = inv * (-ply * ex + plx * ey)
        if tz < 0.2:
            continue
        cx = W / 2 * (1 + tx / tz)
        size = H / tz * 0.8
        bottom = 8 + H / tz / 2
        if e.state == "dying":
            size *= max(0.1, 1 - e.timer / 12)
        top = bottom - size
        left = cx - size / 2
        shade = int(256 / (1 + tz * 0.2))
        pal = {}
        for ch, c in MONSTER_COL.items():
            if e.state == "dying":
                c = (255, 255, 255) if e.timer < 3 else (255, 40, 0)
            pal[ch] = (c[0] * shade >> 8, c[1] * shade >> 8, c[2] * shade >> 8)
        buf = m.buf
        sscale = 5 / size
        for x in range(max(0, int(left)), min(W, int(left + size) + 1)):
            if tz >= zbuf[x]:
                continue
            u = int((x + 0.5 - left) * sscale)
            if not 0 <= u < 5:
                continue
            cidx = COLIDX[x]
            for y in range(max(0, int(top)), min(H, int(bottom) + 1)):
                v = int((y + 0.5 - top) * sscale)
                if not 0 <= v < 5:
                    continue
                ch = MONSTER[v][u]
                if ch == ".":
                    continue
                c = pal[ch]
                j = cidx[y]
                buf[j] = c[0]
                buf[j + 1] = c[1]
                buf[j + 2] = c[2]
    # Waffe, wackelt beim Laufen
    b = 1 if math.sin(bob) > 0.6 else 0
    for x, y in ((7, 12), (8, 12), (7, 13), (8, 13)):
        m.set(x, y + b, (90, 90, 100))
    for x, y in ((6, 14), (7, 14), (8, 14), (9, 14), (6, 15), (7, 15), (8, 15), (9, 15)):
        m.set(x, y + b, (140, 140, 150))
    if flash:
        for x, y, c in ((7, 11, (255, 255, 200)), (8, 11, (255, 255, 200)), (6, 11, (255, 140, 0)),
                        (9, 11, (255, 140, 0)), (7, 10, (255, 200, 0)), (8, 10, (255, 200, 0))):
            m.set(x, y + b, c)
    if hurt:
        b = m.buf
        for i in range(0, len(b), 3):
            b[i] = min(255, b[i] + 90)

def try_move(nx, ny):
    global px, py
    r = 0.25
    if not solid(nx + (r if nx > px else -r), py):
        px = nx
    if not solid(px, ny + (r if ny > py else -r)):
        py = ny

while True:
    t = time.ticks_ms()
    frame += 1
    cooldown = max(0, cooldown - 1)
    flash = max(0, flash - 1)
    hurt = max(0, hurt - 1)
    # Gegner aktualisieren
    foe = None
    best = 99
    for e in enemies:
        if e.state == "dying":
            e.timer += 1
            if e.timer > 12:
                e.state, e.timer = "dead", 0
        elif e.state == "dead":
            e.timer += 1
            if e.timer > 120:
                e.spawn()
        else:
            dx, dy = e.x - px, e.y - py
            d = math.sqrt(dx * dx + dy * dy)
            if d < 8 and los(px, py, e.x, e.y):
                if d < best:
                    foe, best = e, d
                # kommt langsam naeher
                if d > 1.4:
                    nx, ny = e.x - dx / d * 0.015, e.y - dy / d * 0.015
                    if not solid(nx, ny):
                        e.x, e.y = nx, ny
                elif frame % 25 == 0:
                    hurt = 3
    moving = False
    if foe:
        # Kampf: zum Gegner drehen und schiessen
        want = math.atan2(foe.y - py, foe.x - px)
        diff = angle_diff(want, pa)
        pa += max(-TURN, min(TURN, diff))
        if best > SHOOT_DIST and abs(diff) < 0.4:
            try_move(px + math.cos(pa) * MOVE, py + math.sin(pa) * MOVE)
            moving = True
        elif abs(diff) < 0.08 and cooldown == 0:
            flash, cooldown = 3, 14
            if random.random() < 0.8:
                foe.state, foe.timer = "dying", 0
        path = []
    else:
        # zu einem zufaelligen Ziel laufen
        if not path:
            # meist den naechsten Gegner jagen, sonst irgendwohin
            alive = [e for e in enemies if e.state == "alive"]
            if alive and random.random() < 0.7:
                e = min(alive, key=lambda e: abs(e.x - px) + abs(e.y - py))
                goal = (int(e.x), int(e.y))
            else:
                goal = random.choice(FREE)
            path = bfs((int(px), int(py)), goal)[:6]   # nach ein paar Feldern neu planen
        if path:
            wx, wy = path[0][0] + 0.5, path[0][1] + 0.5
            if abs(wx - px) < 0.15 and abs(wy - py) < 0.15:
                path.pop(0)
            else:
                want = math.atan2(wy - py, wx - px)
                diff = angle_diff(want, pa)
                pa += max(-TURN, min(TURN, diff))
                if abs(diff) < 0.5:
                    try_move(px + math.cos(pa) * MOVE, py + math.sin(pa) * MOVE)
                    moving = True
    if moving:
        bob += 0.35
    render()
    m.show()
    if frame % 8 == 0:
        gc.collect()  # regelmaessig kurz aufraeumen statt seltener langer Pausen
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
