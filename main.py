# 4x WS2812B 8x8 Matrizen als 16x16-Flaeche an GP22 - gedimmter Regenbogen-Ringe
# Anordnung: 1 links oben, 2 links unten, 3 rechts oben, 4 rechts unten
import machine, neopixel, time, math

PIN = 22
W = H = 16
MAX = 10  # max. Helligkeit pro Kanal (0-255) -> ca. 400 mA gesamt, Grenze fuer USB

np = neopixel.NeoPixel(machine.Pin(PIN), W * H)

def xy(x, y):
    m = (x // 8) * 2 + (y // 8)
    return m * 64 + (y % 8) * 8 + (x % 8)

def wheel(p):
    # Farbrad 0..767, jeweils nur 2 Kanaele aktiv
    if p < 256:
        return (MAX * (255 - p) // 255, MAX * p // 255, 0)
    p -= 256
    if p < 256:
        return (0, MAX * (255 - p) // 255, MAX * p // 255)
    p -= 256
    return (MAX * p // 255, 0, MAX * (255 - p) // 255)

# Vorberechnet: LED-Index und Abstand zur Mitte je Pixel
pix = []
for y in range(H):
    for x in range(W):
        d = math.sqrt((x - 7.5) ** 2 + (y - 7.5) ** 2)
        pix.append((xy(x, y), int(d * 48)))

off = 0
while True:
    for i, d in pix:
        np[i] = wheel((d - off) % 768)
    np.write()
    off = (off + 12) % 768
    time.sleep_ms(20)
