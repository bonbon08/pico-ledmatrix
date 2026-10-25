# Demo: Sternhimmel. Sterne in verschiedenen Helligkeiten und Farben funkeln, verblassen
# und tauchen woanders neu auf. Ab und zu zieht eine Sternschnuppe mit Schweif vorbei.
import time, random, math
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
STARS = 35         # Anzahl Sterne
SHOOT = 0.006      # Chance pro Bild fuer eine Sternschnuppe
MOON = True        # Mondsichel oben rechts

SIN = [int(128 + 127 * math.sin(i * 2 * math.pi / 256)) for i in range(256)]
TINTS = ((170, 200, 255), (255, 255, 255), (255, 255, 255), (255, 230, 170), (255, 200, 140))

# Mondsichel: helle Pixel und etwas dunklere Kante
MOON_PIX = {(13, 1): 255, (14, 1): 200, (12, 2): 255, (12, 3): 255, (13, 4): 255,
            (14, 4): 200, (11, 2): 120, (11, 3): 120}
MOON_COL = (255, 235, 170)

def free_spot(stars):
    # nicht direkt neben einem anderen Stern und mit Abstand zum Mond
    for _ in range(200):
        x, y = random.randrange(W), random.randrange(H)
        if MOON and x >= 10 and y <= 6:
            continue
        if all(abs(x - s[0]) > 1 or abs(y - s[1]) > 1 for s in stars):
            return x, y
    return x, y

def new_star(stars):
    x, y = free_spot(stars)
    r = random.random()
    peak = 255 if r < 0.15 else 150 if r < 0.45 else 80
    # [x, y, Farbe, Spitzenhelligkeit, Funkel-Phase, Funkel-Tempo, Lebenszeit, Alter]
    return [x, y, random.choice(TINTS), peak, random.randrange(256), random.randrange(2, 7),
            random.randrange(400, 2000), 0]

stars = []
for _ in range(STARS):
    s = new_star(stars)
    s[7] = random.randrange(s[6])   # nicht alle gleichzeitig neu
    stars.append(s)

def scale(c, f):
    return (c[0] * f >> 8, c[1] * f >> 8, c[2] * f >> 8)

shooting = None    # [x, y, dx, dy, Spur]
frame = 0

while True:
    t = time.ticks_ms()
    frame += 1
    m.clear()
    if MOON:
        for (x, y), f in MOON_PIX.items():
            m.set(x, y, scale(MOON_COL, f))
    for i, s in enumerate(stars):
        x, y, col, peak, ph, sp, life, age = s
        s[7] = age = age + 1
        if age >= life:
            stars[i] = new_star(stars)
            continue
        # ein- und ausblenden ueber die ersten/letzten 60 Bilder, dazwischen funkeln
        fade = min(age, life - age, 60) * 255 // 60
        tw = 190 + SIN[(frame * sp + ph) & 255] * 65 // 255
        m.set(x, y, scale(col, peak * tw * fade >> 16))
    # Sternschnuppe
    if shooting is None and random.random() < SHOOT:
        dx = random.choice((-1, 1)) * random.uniform(0.5, 0.8)
        x = random.uniform(2, W - 2) if random.random() < 0.6 else (-1 if dx > 0 else W)
        y = -1 if x >= 0 and x < W else random.uniform(0, H / 2)
        shooting = [x, y, dx, random.uniform(0.3, 0.55), []]
    if shooting:
        sx, sy, dx, dy, trail = shooting
        trail.insert(0, (int(sx + 0.5), int(sy + 0.5)))
        del trail[6:]
        for k, (x, y) in enumerate(trail):
            m.set(x, y, scale((255, 245, 220), 255 - k * 42))
        shooting[0] += dx
        shooting[1] += dy
        if not (-6 < shooting[0] < W + 6 and shooting[1] < H + 6):
            shooting = None
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
