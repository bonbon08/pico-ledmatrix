# 4x WS2812B 8x8 Matrizen als 16x16-Flaeche an GP22 - gedimmter Regenbogen-Ringe
# Anordnung: 1 links oben, 2 links unten, 3 rechts oben, 4 rechts unten
import machine, neopixel, time, math

PIN = 22
W = H = 16
MAX = 16  # max. Helligkeit pro Kanal (0-255) -> ca. 500 mA gesamt, VSYS gemessen stabil bis MAX 22
# Helligkeitsausgleich je Matrix (1, 2, 3, 4) und Farbkanal (R, G, B).
# Matrix 1 hat andere LEDs: Rot/Gruen doppelt so hell, Blau ca. 1,45x (per Auge abgeglichen)
GAIN = ((0.5, 0.5, 0.69), (1, 1, 1), (1, 1, 1), (1, 1, 1))

np = neopixel.NeoPixel(machine.Pin(PIN), W * H)

def xy(x, y):
    m = (x // 8) * 2 + (y // 8)
    return m * 64 + (y % 8) * 8 + (x % 8)

def wheel(p):
    # Farbrad 0..767 in voller Aufloesung (0-255), jeweils nur 2 Kanaele aktiv
    if p < 256:
        return (255 - p, p, 0)
    p -= 256
    if p < 256:
        return (0, 255 - p, p)
    p -= 256
    return (p, 0, 255 - p)

# Vorberechnet: LED-Index, Abstand zur Mitte und Maximalwert je Kanal und Pixel
pix = []
for y in range(H):
    for x in range(W):
        i = xy(x, y)
        d = math.sqrt((x - 7.5) ** 2 + (y - 7.5) ** 2)
        g = GAIN[i // 64]
        pix.append((i, int(d * 48), round(MAX * g[0]), round(MAX * g[1]), round(MAX * g[2])))

off = 0
while True:
    for i, d, mr, mg, mb in pix:
        r, g, b = wheel((d - off) % 768)
        # gerundet, damit Matrizen mit unterschiedlichem Maximum gleichzeitig umschalten
        np[i] = ((r * mr + 127) // 255, (g * mg + 127) // 255, (b * mb + 127) // 255)
    np.write()
    off = (off + 12) % 768
    time.sleep_ms(20)
