# 4x WS2812B 8x8 Matrizen als 16x16-Flaeche an GP22 - gedimmter Regenbogen-Ringe
# Anordnung: 1 links oben, 2 links unten, 3 rechts oben, 4 rechts unten
import machine, neopixel, time, math

PIN = 22
W = H = 16
MAX = 16  # max. Helligkeit pro Kanal (0-255) -> ca. 500 mA gesamt, VSYS gemessen stabil bis MAX 22
# Helligkeitsausgleich je Matrix (1, 2, 3, 4) - Matrix 1 ist etwas heller als die anderen
GAIN = (0.63, 1.0, 1.0, 1.0)

np = neopixel.NeoPixel(machine.Pin(PIN), W * H)

def xy(x, y):
    m = (x // 8) * 2 + (y // 8)
    return m * 64 + (y % 8) * 8 + (x % 8)

def wheel(p, mx):
    # Farbrad 0..767, jeweils nur 2 Kanaele aktiv, Summe = mx
    if p < 256:
        return (mx * (255 - p) // 255, mx * p // 255, 0)
    p -= 256
    if p < 256:
        return (0, mx * (255 - p) // 255, mx * p // 255)
    p -= 256
    return (mx * p // 255, 0, mx * (255 - p) // 255)

# Vorberechnet: LED-Index, Abstand zur Mitte und Helligkeit je Pixel
pix = []
for y in range(H):
    for x in range(W):
        i = xy(x, y)
        d = math.sqrt((x - 7.5) ** 2 + (y - 7.5) ** 2)
        pix.append((i, int(d * 48), round(MAX * GAIN[i // 64])))

off = 0
while True:
    for i, d, mx in pix:
        np[i] = wheel((d - off) % 768, mx)
    np.write()
    off = (off + 12) % 768
    time.sleep_ms(20)
