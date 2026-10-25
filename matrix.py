# Gemeinsame Bibliothek fuer alle Demos: 4x WS2812B 8x8 als 16x16-Flaeche an GP22
# Anordnung: 1 links oben, 2 links unten, 3 rechts oben, 4 rechts unten
# Farben werden immer in voller Aufloesung (0-255) angegeben, show() dimmt sie herunter.
import machine, neopixel, micropython, array

PIN = 22
W = H = 16
N = W * H
MAX = 16  # max. Helligkeit pro Kanal (0-255) -> ca. 500 mA gesamt, VSYS gemessen stabil bis MAX 22
# Helligkeitsausgleich je Matrix (1, 2, 3, 4) und Farbkanal (R, G, B).
# Matrix 1 hat andere LEDs: Rot/Gruen doppelt so hell, Blau ca. 1,45x (per Auge abgeglichen)
GAIN = ((0.5, 0.5, 0.69), (1, 1, 1), (1, 1, 1), (1, 1, 1))
# Strombremse: Summe aller Kanaele (0-255) darf das nicht ueberschreiten,
# sonst wird alles gleichmaessig gedimmt. 255 je LED = so viel wie der Regenbogen.
BUDGET = N * 255

_np = neopixel.NeoPixel(machine.Pin(PIN), N)
buf = bytearray(N * 3)  # R, G, B je LED, Index = LED-Nummer in der Kette

# Faktor je LED und Kanal in Festkomma (x1024), damit show() ohne Fliesskomma auskommt
_mul = array.array('H', [round(MAX * GAIN[i // 3 // 64][i % 3] * 1024 / 255) for i in range(N * 3)])

@micropython.viper
def _sum(src: ptr8, n: int) -> int:
    t = 0
    i = 0
    while i < n:
        t += src[i]
        i += 1
    return t

@micropython.viper
def _render(src: ptr8, dst: ptr8, mul: ptr16, n: int, k: int):
    # RGB (0-255) -> gedimmt, korrigiert, gerundet, in GRB-Reihenfolge fuer die WS2812B
    j = 0
    while j < n:
        dst[j + 1] = (src[j] * mul[j] * k + 524288) >> 20
        dst[j] = (src[j + 1] * mul[j + 1] * k + 524288) >> 20
        dst[j + 2] = (src[j + 2] * mul[j + 2] * k + 524288) >> 20
        j += 3

def xy(x, y):
    m = (x // 8) * 2 + (y // 8)
    return m * 64 + (y % 8) * 8 + (x % 8)

def set(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = xy(x, y) * 3
        buf[i] = c[0]; buf[i + 1] = c[1]; buf[i + 2] = c[2]

def get(x, y):
    i = xy(x, y) * 3
    return (buf[i], buf[i + 1], buf[i + 2])

def fill(c):
    for i in range(0, N * 3, 3):
        buf[i] = c[0]; buf[i + 1] = c[1]; buf[i + 2] = c[2]

def clear():
    fill((0, 0, 0))

def show():
    tot = _sum(buf, N * 3)
    k = 1024 if tot <= BUDGET else 1024 * BUDGET // tot
    _render(buf, _np.buf, _mul, N * 3, k)
    _np.write()

def wheel(p):
    # Farbrad 0..767, jeweils nur 2 Kanaele aktiv
    p %= 768
    if p < 256:
        return (255 - p, p, 0)
    p -= 256
    if p < 256:
        return (0, 255 - p, p)
    p -= 256
    return (p, 0, 255 - p)
