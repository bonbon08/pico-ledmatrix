# Demo: Uhr. Oben die Stunden, unten die Minuten, der Rand (genau 60 Pixel) zeigt die Sekunden.
# Der Pico hat keine Uhr mit Batterie: Die Zeit muss beim Hochladen vom PC gesetzt werden
# (mpremote rtc --set). Ohne gueltige Zeit blinkt "-- --".
import time
import matrix as m

W, H = m.W, m.H
HOUR_COL = (255, 110, 0)
MIN_COL = (0, 170, 255)

# Ziffern 4x6, jede Zeile 4 Bit (links = hoechstes Bit)
FONT = {
    "0": (0b0110, 0b1001, 0b1001, 0b1001, 0b1001, 0b0110),
    "1": (0b0010, 0b0110, 0b0010, 0b0010, 0b0010, 0b0111),
    "2": (0b0110, 0b1001, 0b0001, 0b0010, 0b0100, 0b1111),
    "3": (0b1110, 0b0001, 0b0110, 0b0001, 0b0001, 0b1110),
    "4": (0b0010, 0b0110, 0b1010, 0b1111, 0b0010, 0b0010),
    "5": (0b1111, 0b1000, 0b1110, 0b0001, 0b0001, 0b1110),
    "6": (0b0110, 0b1000, 0b1110, 0b1001, 0b1001, 0b0110),
    "7": (0b1111, 0b0001, 0b0010, 0b0100, 0b0100, 0b0100),
    "8": (0b0110, 0b1001, 0b0110, 0b1001, 0b1001, 0b0110),
    "9": (0b0110, 0b1001, 0b1001, 0b0111, 0b0001, 0b0110),
    "-": (0, 0, 0b1111, 0, 0, 0),
}

# Rand im Uhrzeigersinn, Sekunde 0 oben in der Mitte
RING = ([(x, 0) for x in range(W)] + [(W - 1, y) for y in range(1, H)] +
        [(x, H - 1) for x in range(W - 2, -1, -1)] + [(0, y) for y in range(H - 2, 0, -1)])
RING = RING[8:] + RING[:8]

def digit(ch, ox, oy, col):
    rows = FONT[ch]
    for y in range(6):
        bits = rows[y]
        for x in range(4):
            if bits & (8 >> x):
                m.set(ox + x, oy + y, col)

def two(text, oy, col):
    digit(text[0], 3, oy, col)
    digit(text[1], 9, oy, col)

def scale(c, f):
    return (c[0] * f >> 8, c[1] * f >> 8, c[2] * f >> 8)

last_sec = -1
sec_start = time.ticks_ms()
while True:
    t = time.localtime()
    valid = t[0] >= 2024
    if t[5] != last_sec:
        last_sec = t[5]
        sec_start = time.ticks_ms()
    frac = min(time.ticks_diff(time.ticks_ms(), sec_start), 999)   # 0-999 ms in der Sekunde
    m.clear()
    if valid:
        two("%02d" % t[3], 1, HOUR_COL)
        two("%02d" % t[4], 9, MIN_COL)
        s = t[5]
        ring_col = m.wheel(t[4] * 768 // 60)
        for i in range(s):
            x, y = RING[i]
            m.set(x, y, scale(ring_col, 70))
        # aktuelle Sekunde blendet ein
        x, y = RING[s]
        m.set(x, y, scale((255, 255, 255), 60 + frac * 196 // 1000))
    else:
        if frac < 600:
            two("--", 1, HOUR_COL)
            two("--", 9, MIN_COL)
        # Lauflicht am Rand, damit man sieht, dass der Pico laeuft
        p = time.ticks_ms() // 30 % 60
        for k in range(6):
            x, y = RING[(p - k) % 60]
            m.set(x, y, scale((255, 255, 255), 255 - k * 40))
    m.show()
    time.sleep_ms(40)
