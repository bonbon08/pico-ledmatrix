import machine, neopixel
np = neopixel.NeoPixel(machine.Pin(22), 256)
# Matrix-Reihenfolge: 1 links oben, 2 links unten, 3 rechts oben, 4 rechts unten
def xy(x, y):
    m = (x // 8) * 2 + (y // 8)
    return m * 64 + (y % 8) * 8 + (x % 8)   # Annahme: zeilenweise, nicht Zickzack
np.fill((0, 0, 0))
for i in range(16):
    np[xy(i, 0)] = (6, 0, 0)    # oberste Zeile rot
    np[xy(0, i)] = (0, 6, 0)    # linke Spalte gruen
np[xy(15, 15)] = (0, 0, 8)      # Punkt rechts unten blau
np[xy(1, 1)] = (6, 6, 0)        # Punkt diagonal neben Ecke oben links gelb
np.write()
