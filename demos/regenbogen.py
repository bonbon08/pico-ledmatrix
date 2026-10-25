# Demo: Regenbogen-Ringe, die von der Mitte nach aussen laufen
import time, math
import matrix as m

# Vorberechnet: Abstand zur Mitte je Pixel
pix = [(x, y, int(math.sqrt((x - 7.5) ** 2 + (y - 7.5) ** 2) * 48))
       for y in range(m.H) for x in range(m.W)]

off = 0
while True:
    for x, y, d in pix:
        m.set(x, y, m.wheel(d - off))
    m.show()
    off = (off + 12) % 768
    time.sleep_ms(20)
