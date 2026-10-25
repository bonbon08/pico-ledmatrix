# Demo: Sound-Visualizer. Der PC (tools/visualizer.py) schickt ueber USB pro Bild eine Zeile mit
# 16 Zeichen: Pegel 0-64 je Frequenzband als '0' + Pegel (nur druckbare Zeichen, damit nie
# ein Strg+C dabei ist). Hier werden daraus 16 Balken mit fallenden Spitzenpunkten.
# Kommt nichts an, laeuft eine ruhige Warte-Animation.
import sys, time, select, math
import matrix as m

W, H = m.W, m.H
FRAME_MS = 25
FALL = 1.6         # wie schnell die Balken fallen (Pegel-Stufen pro Bild, 4 Stufen = 1 Pixel)
PEAK_HOLD = 18     # so viele Bilder bleibt der Spitzenpunkt stehen
PEAK_FALL = 0.5

# Farbe je Zeile: unten gruen, Mitte gelb, oben rot
ROW_COL = []
for y in range(H):
    f = (H - 1 - y) / (H - 1)
    ROW_COL.append((int(255 * min(1, f * 2)), int(255 * min(1, (1 - f) * 2)), 0))

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
inp = sys.stdin.buffer

line = bytearray()
target = [0] * W
level = [0.0] * W
peak = [0.0] * W
hold = [0] * W
last_rx = time.ticks_ms() - 10000

def read_input():
    global last_rx
    while poll.poll(0):
        c = inp.read(1)
        if not c:
            break
        c = c[0]
        if c == 10:
            if len(line) == W:
                for i in range(W):
                    target[i] = min(64, max(0, line[i] - 48))
                last_rx = time.ticks_ms()
            line[:] = b""
        elif len(line) < 64:
            line.append(c)

frame = 0
while True:
    t = time.ticks_ms()
    frame += 1
    read_input()
    idle = time.ticks_diff(t, last_rx) > 2000
    if idle:
        # Warte-Animation: sanfte Welle in Blau
        for i in range(W):
            target[i] = int(6 + 5 * math.sin(frame * 0.05 + i * 0.5))
    m.clear()
    for i in range(W):
        # steigt sofort, faellt langsam
        level[i] = target[i] if target[i] > level[i] else max(target[i], level[i] - FALL)
        if level[i] >= peak[i]:
            peak[i], hold[i] = level[i], PEAK_HOLD
        elif hold[i]:
            hold[i] -= 1
        else:
            peak[i] = max(0, peak[i] - PEAK_FALL)
        full = int(level[i]) // 4            # ganze Pixel
        part = int(level[i]) % 4             # angebrochenes Pixel oben (Viertel)
        for k in range(full):
            y = H - 1 - k
            m.set(i, y, (0, 60, 255) if idle else ROW_COL[y])
        if part and full < H:
            y = H - 1 - full
            c = (0, 60, 255) if idle else ROW_COL[y]
            m.set(i, y, (c[0] * part >> 2, c[1] * part >> 2, c[2] * part >> 2))
        if not idle and peak[i] >= 4:
            m.set(i, H - 1 - min(H - 1, int(peak[i]) // 4), (255, 255, 255))
    m.show()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
