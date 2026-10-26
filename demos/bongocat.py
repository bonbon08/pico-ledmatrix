# Demo: Bongo-Katze. Die Katze haut bei jedem Tastendruck am PC auf ihre Tastatur, abwechselnd
# links und rechts. Der PC (tools/tastatur.py) schickt pro Tastendruck einen Buchstaben fuer die
# Tastaturreihe ("k", "q", "a", "y") und jede Sekunde ein Lebenszeichen ("." oder "h") - welche
# Taste gedrueckt wurde, erfaehrt der Pico nie.
# Ohne PC tippt sie im Demo-Modus von selbst, nach langer Pause schlaeft sie ein.
import sys, time, select, random
import matrix as m

W, H = m.W, m.H
FRAME_MS = 30
PAW_FRAMES = 3     # so lange bleibt eine Pfote unten
AUTO_AFTER = 5000  # ms ohne Lebenszeichen vom PC -> Demo-Modus
SLEEP_AFTER = 30000  # ms ohne Tastendruck -> einschlafen

# W = Fell, P = Ohr innen, E = Auge, N = Nase, M = Mund, D = Tisch, K/k = Tastatur
ART = (
    "................",
    "................",
    "...W........W...",
    "...WW......WW...",
    "...WPWWWWWWPW...",
    "..WWWWWWWWWWWW..",
    "..WWEWWWWWWEWW..",
    "..WWWWWNNWWWWW..",
    "..WWWWMWWMWWWW..",
    "...WWWWWWWWWW...",
    "....WWWWWWWW....",
    "DDDDDDDDDDDDDDDD",
    "DKKKKKKKKKKKKKKD",
    "DKkKkKkKkKkKkKkD",
    "DDDDDDDDDDDDDDDD",
    "DDDDDDDDDDDDDDDD",
)
COL = {"W": (175, 175, 195), "P": (255, 120, 160), "E": (20, 20, 30), "N": (255, 110, 150),
       "M": (60, 40, 50), "D": (120, 60, 20), "K": (60, 60, 70), "k": (110, 110, 125)}
# Pfoten heller als das Fell, mit rosa Ballen; erhoben neben dem Koerper mit Luft zum Tisch
PAW = (255, 255, 255)
BEAN = (255, 120, 160)
PAW_UP = (((0, 8), (1, 8), (0, 9), (1, 9)), ((14, 8), (15, 8), (14, 9), (15, 9)))
PAW_DOWN = (((2, 10), (3, 10), (2, 11), (3, 11)), ((12, 10), (13, 10), (12, 11), (13, 11)))
BEAN_UP = ((1, 9), (14, 9))
KEYS_HIT = (((2, 12), (3, 12), (2, 13), (3, 13)), ((12, 12), (13, 12), (12, 13), (13, 13)))

# Katze, Tisch und Tastatur einmal zeichnen, danach pro Bild nur kopieren
m.clear()
for y, row in enumerate(ART):
    for x, ch in enumerate(row):
        if ch != ".":
            m.set(x, y, COL[ch])
BG = bytes(m.buf)

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
inp = sys.stdin.buffer

def read_input():
    # liefert Anzahl neuer Tastendruecke und ob ein Lebenszeichen kam
    hits = 0
    alive = False
    while poll.poll(0):
        c = inp.read(1)
        if not c:
            break
        if c in b"kqay":         # Tastendruck (Reihe ist der Katze egal)
            hits += 1
            alive = True
        elif c in b".hl":
            alive = True
    return hits, alive

paw = [0, 0]           # Restbilder, die die Pfote unten bleibt
next_paw = 0
pending = 0
sparks = []            # [x, y, dx, dy, Leben]
last_alive = time.ticks_ms() - AUTO_AFTER
last_hit = time.ticks_ms()
blink = 0
zs = []
frame = 0
auto_burst = 0

while True:
    t = time.ticks_ms()
    frame += 1
    hits, alive = read_input()
    if alive:
        last_alive = t
    auto = time.ticks_diff(t, last_alive) > AUTO_AFTER
    if auto:
        # Demo-Modus: mal schnelle Tipp-Salven, mal Pause
        if auto_burst > 0:
            auto_burst -= 1
            if random.random() < 0.45:
                hits += 1
        elif random.random() < 0.01:
            auto_burst = random.randrange(20, 120)
    pending = min(pending + hits, 6)
    if hits:
        last_hit = t
    asleep = time.ticks_diff(t, last_hit) > SLEEP_AFTER

    # freie Pfote nimmt den naechsten Tastendruck, abwechselnd links/rechts
    for _ in range(2):
        if pending and paw[next_paw] == 0:
            paw[next_paw] = PAW_FRAMES
            pending -= 1
            hx, hy = PAW_DOWN[next_paw][0]
            hy -= 1
            for _ in range(2):
                sparks.append([hx + 0.5 + random.uniform(-1, 1), hy - 0.5,
                               random.uniform(-0.25, 0.25), random.uniform(-0.35, -0.15), 6])
            next_paw ^= 1

    # zeichnen
    m.buf[:] = BG
    if blink == 0 and random.random() < 0.01:
        blink = 4
    if asleep or blink:
        for ex in (4, 11):
            m.set(ex, 6, COL["W"])
            if asleep:
                m.set(ex - 1, 6, COL["E"]); m.set(ex, 6, COL["E"])     # Augen zu: Strich
        blink = max(0, blink - 1)
    for side in (0, 1):
        if paw[side]:
            for x, y in PAW_DOWN[side]:
                m.set(x, y, PAW)
            for x, y in KEYS_HIT[side]:
                m.set(x, y, (255, 230, 80))
            paw[side] -= 1
        elif not asleep:
            for x, y in PAW_UP[side]:
                m.set(x, y, PAW)
            m.set(*BEAN_UP[side], BEAN)
    for s in sparks:
        s[0] += s[2]; s[1] += s[3]; s[4] -= 1
        f = s[4] * 42
        m.set(int(s[0]), int(s[1]), (255 * f >> 8, 220 * f >> 8, 60 * f >> 8))
    sparks = [s for s in sparks if s[4] > 0]
    # schlafen: Z steigen auf
    if asleep and frame % 40 == 0:
        zs.append([13.0, 4.0])
    for z in zs:
        z[1] -= 0.06
        z[0] += 0.02
        m.set(int(z[0]), int(z[1]), (120, 140, 255))
        m.set(int(z[0]) + 1, int(z[1]), (120, 140, 255))
    zs = [z for z in zs if z[1] > -1]
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
