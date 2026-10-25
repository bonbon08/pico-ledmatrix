# Demo: Zufaellige Tetris-Bloecke fallen herunter und stapeln sich.
# Volle Reihen blinken und verschwinden. Ist der Stapel oben angekommen,
# rutscht alles nach unten raus und es geht von vorne los.
import time, random
import matrix as m

W, H = m.W, m.H
FALL_MS = 70       # Zeit pro Fallschritt
SMART = 0.7        # Anteil der Steine, die gut gelegt werden (Rest landet zufaellig)

# Die 7 Steine (Zellen als (x, y)) mit ihren Farben
SHAPES = [
    ([(0, 0), (1, 0), (2, 0), (3, 0)], (0, 255, 255)),   # I
    ([(0, 0), (1, 0), (0, 1), (1, 1)], (255, 200, 0)),   # O
    ([(0, 0), (1, 0), (2, 0), (1, 1)], (170, 0, 255)),   # T
    ([(1, 0), (2, 0), (0, 1), (1, 1)], (0, 255, 0)),     # S
    ([(0, 0), (1, 0), (1, 1), (2, 1)], (255, 0, 0)),     # Z
    ([(0, 0), (0, 1), (1, 1), (2, 1)], (0, 60, 255)),    # J
    ([(2, 0), (0, 1), (1, 1), (2, 1)], (255, 90, 0)),    # L
]

def norm(cells):
    mx = min(c[0] for c in cells)
    my = min(c[1] for c in cells)
    return tuple(sorted((x - mx, y - my) for x, y in cells))

def rotations(cells):
    out = []
    c = norm(cells)
    for _ in range(4):
        if c not in out:
            out.append(c)
        c = norm([(y, -x) for x, y in c])
    return out

PIECES = [(rotations(cells), col) for cells, col in SHAPES]

board = [[None] * W for _ in range(H)]

def fits(cells, px, py):
    for x, y in cells:
        x += px; y += py
        if x < 0 or x >= W or y >= H:
            return False
        if y >= 0 and board[y][x] is not None:
            return False
    return True

def drop_y(cells, px):
    py = -4
    while fits(cells, px, py + 1):
        py += 1
    return py

def score(cells, px):
    # Bewertet eine Ablage: wenig Hoehe, wenig Loecher, glatte Oberflaeche, volle Reihen
    py = drop_y(cells, px)
    if py < 0 and any(y + py < 0 for _, y in cells):
        return -1e9
    filled = set((x + px, y + py) for x, y in cells)
    occ = lambda x, y: board[y][x] is not None or (x, y) in filled
    lines = sum(1 for y in range(H) if all(occ(x, y) for x in range(W)))
    heights = []
    holes = 0
    for x in range(W):
        h = 0
        seen = False
        for y in range(H):
            if occ(x, y):
                if not seen:
                    h = H - y
                    seen = True
            elif seen:
                holes += 1
        heights.append(h)
    bump = sum(abs(heights[i] - heights[i + 1]) for i in range(W - 1))
    return 0.76 * lines - 0.51 * sum(heights) - 1.4 * holes - 0.18 * bump

def choose(rots):
    if random.random() < SMART:
        best = None
        for r, cells in enumerate(rots):
            w = max(x for x, _ in cells) + 1
            for px in range(W - w + 1):
                s = score(cells, px) + random.random() * 0.3
                if best is None or s > best[0]:
                    best = (s, r, px)
        return best[1], best[2]
    r = random.randrange(len(rots))
    w = max(x for x, _ in rots[r]) + 1
    return r, random.randrange(W - w + 1)

def draw(cells=None, px=0, py=0, col=None):
    for y in range(H):
        row = board[y]
        for x in range(W):
            m.set(x, y, row[x] or (0, 0, 0))
    if cells:
        for x, y in cells:
            m.set(x + px, y + py, col)
    m.show()

def clear_lines():
    full = [y for y in range(H) if all(c is not None for c in board[y])]
    if not full:
        return
    for i in range(6):
        for y in full:
            for x in range(W):
                m.set(x, y, (255, 255, 255) if i % 2 == 0 else (0, 0, 0))
        m.show()
        time.sleep_ms(80)
    for y in full:
        del board[y]
        board.insert(0, [None] * W)
    draw()

def game_over():
    # Alles rutscht Reihe fuer Reihe unten raus
    for _ in range(H):
        board.pop()
        board.insert(0, [None] * W)
        draw()
        time.sleep_ms(60)
    time.sleep_ms(400)

while True:
    rots, col = random.choice(PIECES)
    r, tx = choose(rots)
    cells = rots[r]
    w = max(x for x, _ in cells) + 1
    px = random.randrange(W - w + 1)       # startet irgendwo und rutscht zum Ziel
    py = -max(y for _, y in cells) - 1
    if not fits(cells, tx, 0) or not fits(cells, px, py):
        game_over()
        continue
    while True:
        if px != tx:
            step = 1 if tx > px else -1
            if fits(cells, px + step, py):
                px += step
        if not fits(cells, px, py + 1):
            break
        py += 1
        draw(cells, px, py, col)
        time.sleep_ms(FALL_MS)
    if py < 0 and any(y + py < 0 for _, y in cells):
        game_over()
        continue
    for x, y in cells:
        board[y + py][x + px] = col
    clear_lines()
