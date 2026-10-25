# Demo: Kleiner Roboter. Er schaut sich um, blinzelt, winkt, tanzt, verliebt sich und schlaeft
# zwischendurch ein. Die Zustaende wechseln zufaellig.
import time, random
import matrix as m

W, H = m.W, m.H
FRAME_MS = 50

METAL = (150, 165, 190)
DARK = (80, 90, 115)
SCREEN = (8, 10, 30)
EYE = (0, 220, 255)
PINK = (255, 40, 140)
LEG = (70, 75, 95)

def rect(x0, y0, x1, y1, c, dy=0):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            m.set(x, y + dy, c)

def draw_robot(dy, eyes, look, arms, antenna, chest, legs):
    # Antenne
    m.set(7, 1 + dy, DARK)
    m.set(7, 0 + dy, antenna)
    # Kopf mit Bildschirm und Schrauben an der Seite
    rect(3, 2, 12, 7, METAL, dy)
    rect(4, 3, 11, 6, SCREEN, dy)
    m.set(2, 4 + dy, DARK); m.set(2, 5 + dy, DARK)
    m.set(13, 4 + dy, DARK); m.set(13, 5 + dy, DARK)
    # Augen (je 2x2): offen, zu, froh, Herz
    for ex in (5 + look, 9 + look):
        if eyes == "auf":
            rect(ex, 4, ex + 1, 5, EYE, dy)
        elif eyes == "zu":
            rect(ex, 5, ex + 1, 5, EYE, dy)
        elif eyes == "froh":
            m.set(ex, 5 + dy, EYE); m.set(ex + 1, 4 + dy, EYE)
            m.set(ex + 1, 5 + dy, SCREEN)
        elif eyes == "herz":
            rect(ex, 4, ex + 1, 5, PINK, dy)
    if eyes == "froh":
        # Mund
        rect(7, 6, 8, 6, EYE, dy)
    # Hals und Koerper
    rect(7, 8, 8, 8, DARK, dy)
    rect(4, 9, 11, 13, METAL, dy)
    rect(5, 10, 10, 12, DARK, dy)
    m.set(7, 11 + dy, chest); m.set(8, 11 + dy, chest)
    m.set(6, 10 + dy, (255, 200, 0)); m.set(9, 10 + dy, (0, 255, 80))
    # Arme: "unten", "links_hoch", "rechts_hoch", "beide_hoch"
    for side, up in ((-1, arms in ("links_hoch", "beide_hoch")), (1, arms in ("rechts_hoch", "beide_hoch"))):
        x = 3 if side < 0 else 12
        if up:
            m.set(x, 9 + dy, METAL)
            m.set(x + side, 8 + dy, METAL)
            m.set(x + 2 * side, 7 + dy, METAL)
            m.set(x + 2 * side, 6 + dy, METAL)
            m.set(x + 2 * side, 5 + dy, DARK)  # Hand
        else:
            for y in (9, 10, 11):
                m.set(x, y + dy, METAL)
            m.set(x, 12 + dy, DARK)
    # Beine
    l0, l1 = legs
    rect(5, 14, 6, 14 + l0, LEG, dy)
    rect(9, 14, 10, 14 + l1, LEG, dy)

hearts = []        # [x, y]
zs = []            # [x, y]
state = "schauen"
timer = 0
frame = 0
blink = 0
look = 0

def next_state():
    return random.choice(("schauen", "schauen", "winken", "tanzen", "verliebt", "schlafen"))

while True:
    t = time.ticks_ms()
    frame += 1
    timer += 1
    m.clear()
    dy = 0
    eyes = "auf"
    arms = "unten"
    legs = (1, 1)
    antenna = (255, 0, 0) if frame % 20 < 10 else (60, 0, 0)
    chest = (0, 255, 120) if (frame // 8) % 2 else (0, 90, 40)

    if state == "schauen":
        if random.random() < 0.02:
            look = random.choice((-1, 0, 0, 1))
        if blink == 0 and random.random() < 0.025:
            blink = 3
        if blink:
            eyes = "zu"
            blink -= 1
        if timer > 100:
            state, timer = next_state(), 0
    elif state == "winken":
        eyes = "froh"
        look = 0
        arms = "rechts_hoch" if (timer // 5) % 2 == 0 else "unten"
        if timer > 50:
            state, timer = "schauen", 0
    elif state == "tanzen":
        eyes = "froh"
        look = 0
        beat = (timer // 5) % 4
        dy = -1 if beat in (1, 3) else 0
        arms = ("links_hoch", "beide_hoch", "rechts_hoch", "beide_hoch")[beat]
        legs = ((1, 0), (1, 1), (0, 1), (1, 1))[beat]
        antenna = m.wheel(frame * 40)
        chest = m.wheel(frame * 40 + 384)
        if timer > 90:
            state, timer = "schauen", 0
    elif state == "verliebt":
        eyes = "herz"
        look = 0
        chest = PINK if (frame // 4) % 2 else (90, 10, 50)
        if timer % 12 == 1:
            hearts.append([random.choice((2.0, 13.0)), 6.0])
        if timer > 80:
            state, timer = "schauen", 0
    elif state == "schlafen":
        eyes = "zu"
        look = 0
        antenna = (0, 0, 80)
        chest = (0, 40, 20)
        dy = 1 if (timer // 20) % 2 else 0      # atmet langsam
        if timer % 25 == 1:
            zs.append([12.0, 3.0])
        if timer > 140:
            state, timer = "schauen", 0
            blink = 3

    draw_robot(dy, eyes, look, arms, antenna, chest, legs)
    for h in hearts:
        h[1] -= 0.15
        x, y = int(h[0]), int(h[1])
        m.set(x, y, PINK); m.set(x + 1, y, PINK)
        m.set(x, y - 1, (140, 20, 70)); m.set(x + 1, y - 1, (140, 20, 70))
    hearts = [h for h in hearts if h[1] > 0]
    for z in zs:
        z[1] -= 0.08
        z[0] += 0.03
        x, y = int(z[0]), int(z[1])
        c = (120, 120, 255)
        # kleines "Z" aus 3 Pixeln
        m.set(x, y - 1, c); m.set(x + 1, y - 1, c); m.set(x, y, c); m.set(x + 1, y + 1, c); m.set(x, y + 1, c)
    zs = [z for z in zs if z[1] > 0 and z[0] < W]
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
