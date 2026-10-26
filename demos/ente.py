# Demo: Tipp-Ente. Eine Ente pickt bei jedem Tastendruck am PC mit dem Schnabel auf ihre Tastatur.
# Der PC (tools/tastatur.py) schickt pro Tastendruck die Reihe der Taste ("q" oben, "a" Mitte,
# "y" unten, "k" sonstige), beim Loslassen ein "l" und jede Sekunde ein Lebenszeichen ("." wenn
# keine Taste gehalten wird, sonst "h"). Solange eine Taste gehalten wird, bleibt der Schnabel unten. Ohne PC pickt sie im Demo-Modus von selbst, nach langer Pause schlaeft sie ein.
import sys, time, select, random
import matrix as m

W, H = m.W, m.H
FRAME_MS = 30
AUTO_AFTER = 5000    # ms ohne Lebenszeichen vom PC -> Demo-Modus
SLEEP_AFTER = 30000  # ms ohne Tastendruck -> einschlafen
# Ablauf eines Picks: Kopfhaltung pro Bild (1 = halb unten, 2 = unten auf der Taste)
PECK = (1, 2, 2, 1)

# Stockente nach Vorlage des Benutzers (9x10 Pixel), hier nur der Koerper ohne Kopf und Hals.
# G = Gefieder, T = Schwanz, D = Fluegellinie, F = Fuesse, d = Tisch, K/k = Tastatur
ART = (
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    ".T..............",
    ".TTTDGGG........",
    ".TTDGGGGG.......",
    ".TGGDDGGG.......",
    "..GGGGGG..KKKKKK",
    ".....F.F.KkKkKkK",
    "dddddddddddddddd",
    "dddddddddddddddd",
    "dddddddddddddddd",
)
# Kopf und Hals je Haltung, "." = durchsichtig; W/B = Auge (weiss ueber blau), O = Schnabel
HEAD = (
    (   # 0: aufrecht, wie in der Vorlage
        "................",
        "................",
        "................",
        ".....GG.........",
        "....GGWG........",
        "....GGBGO.......",
        "....GGGG........",
        ".....GG.........",
    ),
    (   # 1: halb unten
        "................",
        "................",
        "................",
        "................",
        "................",
        "........GG......",
        ".......GGWG.....",
        "......GGGBGO....",
        ".......GGGG.....",
    ),
    (   # 2: unten auf der hinteren Taste (obere Tastaturreihe), duenner Hals
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "...........GG...",
        "........GGGGWG..",
        "..........GGBGO.",
        "..........GGGGO.",
    ),
    (   # 3: schlafend, Kopf nach hinten gedreht, Auge zu
        "................",
        "................",
        "................",
        "................",
        "....GG..........",
        "...GGGG.........",
        "..ODGGG.........",
        "...GGGG.........",
    ),
    (   # 4: unten auf der mittleren Taste (mittlere Tastaturreihe)
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        ".........GG.....",
        "........GGWG....",
        "..........BGO...",
        "..........GGO...",
    ),
    (   # 5: unten auf der vorderen Taste (untere Reihe und Leertaste), Schnabel nach unten
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "........GGG.....",
        "........GGWG....",
        "..........BG....",
        "..........OO....",
    ),
)
COL = {"G": (60, 190, 40), "T": (255, 175, 95), "D": (165, 95, 20), "F": (255, 110, 20),
       "W": (255, 255, 255), "B": (70, 110, 255), "O": (255, 110, 20),
       "d": (120, 60, 20), "K": (60, 60, 70), "k": (110, 110, 125)}
# Drei Tasten von hinten nach vorne, wie die Reihen der echten Tastatur: Kopfhaltung,
# Pixel der Taste und Mitte fuer die Funken
KEYS = ((2, ((14, 11), (15, 11), (14, 12), (15, 12)), 14.5),
        (4, ((12, 11), (13, 11), (12, 12), (13, 12)), 12.5),
        (5, ((10, 11), (11, 11), (10, 12), (11, 12)), 10.5))
HIT_COL = (255, 230, 80)

# Tisch, Koerper und Tastatur einmal zeichnen, danach pro Bild nur kopieren
m.clear()
for y, row in enumerate(ART):
    for x, ch in enumerate(row):
        if ch != ".":
            m.set(x, y, COL[ch])
BG = bytes(m.buf)
# Kopfhaltungen als Pixellisten vorberechnen
POSES = []
for art in HEAD:
    POSES.append([(x, y, COL[ch]) for y, row in enumerate(art) for x, ch in enumerate(row) if ch != "."])

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
inp = sys.stdin.buffer

ROWS = {b"q": 0, b"a": 1, b"y": 2}

def read_input():
    # neue Tastendruecke als Liste der Tasten (0-2), Anzahl losgelassener, ob ein Lebenszeichen kam
    # und ob der PC meldet, dass gar nichts mehr gehalten wird
    hits = []
    released = 0
    alive = False
    idle = False
    while poll.poll(0):
        c = inp.read(1)
        if not c:
            break
        if c in ROWS:
            hits.append(ROWS[c])
        elif c == b"k":
            hits.append(random.randrange(3))
        elif c == b"l":
            released += 1
        elif c == b".":
            idle = True
        elif c != b"h":
            continue
        alive = True
    return hits, released, alive, idle

step = len(PECK)       # Position im Pick-Ablauf, len(PECK) = Ruhe
queue = []             # Tasten, die noch gepickt werden muessen
key = 0                # Taste des aktuellen Picks
held = 0               # gerade gehaltene Tasten am PC
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
    hits, released, alive, idle = read_input()
    if alive:
        last_alive = t
    held = max(0, held + len(hits) - released)
    if idle:
        held = 0
    if time.ticks_diff(t, last_alive) > AUTO_AFTER:
        held = 0
        # Demo-Modus: mal schnelle Pick-Salven, mal Pause
        if auto_burst > 0:
            auto_burst -= 1
            if random.random() < 0.3:
                hits.append(random.randrange(3))
        elif random.random() < 0.01:
            auto_burst = random.randrange(20, 120)
    queue = (queue + hits)[:6]
    if hits or held:
        last_hit = t
    asleep = time.ticks_diff(t, last_hit) > SLEEP_AFTER

    # naechster Pick; bei schnellem Tippen gleich wieder runter, ohne ganz aufzurichten,
    # bei gehaltener Taste kurz halb hoch und auf die neue Taste
    if queue and (step >= len(PECK) - 1 or (held and step == 2)):
        key = queue.pop(0)
        step = 1 if step == len(PECK) - 1 else 0
    pose = 3 if asleep else (PECK[step] if step < len(PECK) else 0)
    if pose == 2:
        pose = KEYS[key][0]
        if PECK[step - 1] != 2:
            for _ in range(3):
                sparks.append([KEYS[key][2] + random.uniform(-1, 1), 10.5,
                               random.uniform(-0.3, 0.3), random.uniform(-0.4, -0.15), 6])

    # zeichnen
    m.buf[:] = BG
    if step < len(PECK) and PECK[step] == 2:
        for x, y in KEYS[key][1]:
            m.set(x, y, HIT_COL)
    if blink == 0 and random.random() < 0.01:
        blink = 4
    blink = max(0, blink - 1)
    # gehaltene Taste: unten bleiben, bis sie losgelassen wird
    if step < len(PECK) and not (held and step == 2):
        step += 1
    for s in sparks:
        s[0] += s[2]; s[1] += s[3]; s[4] -= 1
        f = s[4] * 42
        m.set(int(s[0]), int(s[1]), (255 * f >> 8, 220 * f >> 8, 60 * f >> 8))
    sparks = [s for s in sparks if s[4] > 0]
    for x, y, c in POSES[pose]:
        m.set(x, y, c)
    if blink and pose == 0:          # blinzeln: Auge zu
        m.set(6, 4, COL["G"]); m.set(6, 5, COL["D"])
    # schlafen: Z steigen auf
    if asleep and frame % 40 == 0:
        zs.append([5.0, 3.0])
    for z in zs:
        z[1] -= 0.06
        z[0] += 0.02
        m.set(int(z[0]), int(z[1]), (120, 140, 255))
        m.set(int(z[0]) + 1, int(z[1]), (120, 140, 255))
    zs = [z for z in zs if z[1] > -1]
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
