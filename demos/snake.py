# Demo: Snake, die von alleine spielt.
# Die Schlange sucht den kuerzesten Weg zum Futter, nimmt ihn aber nur, wenn sie danach
# noch ihr Schwanzende erreicht (sonst sperrt sie sich ein). Sonst laeuft sie ihrem
# Schwanz hinterher, bis sich ein sicherer Weg auftut.
import time, random
import matrix as m

W, H = m.W, m.H
N = W * H
STEP_MS = 80       # Zeit pro Schritt (inkl. Rechenzeit)
STUCK = 3000       # so viele Schritte ohne Futter -> neue Runde

# Nachbarfelder je Feld (Feld = y * 16 + x)
NB = []
for c in range(N):
    x, y = c % W, c // W
    NB.append(tuple(n for n, ok in ((c - W, y > 0), (c + W, y < H - 1),
                                    (c - 1, x > 0), (c + 1, x < W - 1)) if ok))

def bfs(start, goal, occ):
    # kuerzester Weg von start nach goal (ohne start), None wenn keiner existiert
    prev = bytearray(N)
    seen = bytearray(N)
    seen[start] = 1
    q = [start]
    i = 0
    while i < len(q):
        c = q[i]; i += 1
        if c == goal:
            path = []
            while c != start:
                path.append(c)
                c = prev[c]
            path.reverse()
            return path
        for n in NB[c]:
            if not seen[n] and (not occ[n] or n == goal):
                seen[n] = 1
                prev[n] = c
                q.append(n)
    return None

def area(start, occ):
    # Groesse der freien Flaeche ab start
    seen = bytearray(N)
    seen[start] = 1
    q = [start]
    i = 0
    while i < len(q):
        for n in NB[q[i]]:
            if not seen[n] and not occ[n]:
                seen[n] = 1
                q.append(n)
        i += 1
    return len(q)

def occupancy(body):
    occ = bytearray(N)
    for c in body:
        occ[c] = 1
    return occ

def safe_after(body, path):
    # Schlange folgt dem Weg und frisst: kommt sie danach noch an ihr Schwanzende?
    nb = (list(reversed(path)) + body)[:len(body) + 1]
    return bfs(nb[0], nb[-1], occupancy(nb[:-1])) is not None

def next_move(body, food):
    head = body[0]
    occ = occupancy(body[:-1])           # Schwanzende ist im naechsten Schritt frei
    p = bfs(head, food, occ)
    if p and safe_after(body, p):
        return p[0]
    # Schwanz hinterherlaufen, dabei moeglichst weit weg vom Futter (Zeit schinden).
    # Etwas Zufall verhindert, dass sie ewig im selben Kreis laeuft.
    best = None
    for n in NB[head]:
        if occ[n]:
            continue
        nb = [n] + body[:-1]
        if len(body) < 3 or bfs(n, nb[-1], occupancy(nb[:-1])) is not None:
            d = abs(n % W - food % W) + abs(n // W - food // W) + random.random()
            if best is None or d > best[0]:
                best = (d, n)
    if best:
        return best[1]
    # Notloesung: Feld mit dem meisten Platz
    best = None
    for n in NB[head]:
        if not occ[n]:
            a = area(n, occ)
            if best is None or a > best[0]:
                best = (a, n)
    return best[1] if best else None

def place_food(body):
    occ = occupancy(body)
    free = [c for c in range(N) if not occ[c]]
    return random.choice(free) if free else None

def draw(body, food, hue):
    m.clear()
    n = len(body)
    for i, c in enumerate(body):
        if i == 0:
            col = (255, 255, 255)
        else:
            col = m.wheel(hue + i * 6)
            # zum Schwanz hin dunkler werden
            f = 255 - (i * 150) // max(n, 1)
            col = (col[0] * f // 255, col[1] * f // 255, col[2] * f // 255)
        m.set(c % W, c // W, col)
    if food is not None:
        m.set(food % W, food // W, (255, 0, 0))
    m.show()

def death(body, food, hue):
    for i in range(6):
        if i % 2:
            draw(body, food, hue)
        else:
            m.clear(); m.show()
        time.sleep_ms(150)
    # vom Schwanz her aufloesen
    while body:
        body.pop()
        draw(body, food, hue)
        time.sleep_ms(15)
    time.sleep_ms(400)

def win():
    for i in range(60):
        for c in range(N):
            m.set(c % W, c // W, m.wheel(c * 3 + i * 25))
        m.show()
        time.sleep_ms(20)

while True:
    c = (H // 2) * W + W // 2
    body = [c, c - 1, c - 2]
    food = place_food(body)
    hue = random.randrange(768)
    stuck = 0
    while True:
        t = time.ticks_ms()
        draw(body, food, hue)
        nxt = next_move(body, food)
        time.sleep_ms(max(0, STEP_MS - time.ticks_diff(time.ticks_ms(), t)))
        if nxt is None or stuck > STUCK:
            if len(body) >= N - 8:     # Feld praktisch voll, letzte Felder unerreichbar
                win()
            else:
                death(body, food, hue)
            break
        body.insert(0, nxt)
        if nxt == food:
            food = place_food(body)
            stuck = 0
            if food is None:
                win()
                break
        else:
            body.pop()
            stuck += 1
        hue = (hue + 2) % 768
