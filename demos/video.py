# Demo: Video. Zeigt ein Video oder den Bildschirm, das der PC (tools/video.py oder tools/bildschirm.py)
# Bild fuer Bild ueber USB schickt.
# Ohne PC pulsiert ein Play-Symbol. Pro Bild kommt "#", dann 768 Zeichen '0'..'o' (6 Bit je Farbe,
# zeilenweise RGB) und ein Zeilenende - nur druckbare Zeichen, damit nie ein Strg+C dabei ist.
import sys, time, select, micropython, array
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40        # Takt des Play-Symbols; das Video gibt der PC vor
TIMEOUT = 1500       # ms ohne Bild -> Play-Symbol
STATS_MS = 5000      # so oft meldet der Pico dem Sender seine Bildrate
LEN = W * H * 3

frame = bytearray(LEN + 1)           # 768 Zeichen + Zeilenende
mv = memoryview(frame)
IDX = array.array('H', [m.xy(i % W, i // W) * 3 for i in range(W * H)])

@micropython.viper
def decode(src: ptr8, idx: ptr16, dst: ptr8):
    for i in range(256):
        j = int(idx[i])
        k = i * 3
        for c in range(3):
            v = int(src[k + c]) - 48
            if v < 0:
                v = 0
            if v > 63:
                v = 63
            dst[j + c] = (v * 255 + 31) // 63

PLAY = ("X.....", "XXX...", "XXXXX.", "XXXXXX", "XXXXX.", "XXX...", "X.....")
PLAY_PX = [(5 + x, 4 + y) for y, row in enumerate(PLAY) for x, ch in enumerate(row) if ch == "X"]

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
inp = sys.stdin.buffer

def read_frame():
    # auf "#" warten, dann ein ganzes Bild lesen; False bei Stoerung oder wenn nichts kommt
    while True:
        if not poll.poll(200):
            return False
        c = inp.read(1)
        if not c:
            return False
        if c == b"#":
            break
    got = 0
    while got < LEN + 1:
        if not poll.poll(200):
            return False
        n = inp.readinto(mv[got:])
        if not n:
            return False
        got += n
    return frame[LEN] == 10

last = time.ticks_ms() - TIMEOUT
stats_t = time.ticks_ms()
shown = 0
tick = 0

while True:
    t = time.ticks_ms()
    if poll.poll(0) and read_frame():
        decode(frame, IDX, m.buf)
        m.show()
        last = t
        shown += 1
        if time.ticks_diff(t, stats_t) >= STATS_MS:
            # nur melden, solange ein Sender da ist, der das liest
            print("Pico: %.1f Bilder/s" % (shown * 1000 / time.ticks_diff(t, stats_t)))
            stats_t = t
            shown = 0
        continue
    if time.ticks_diff(t, last) > TIMEOUT:
        # kein Sender: Play-Symbol pulsiert
        tick += 1
        f = 140 + int(115 * (1 - abs((tick % 50) - 25) / 25))
        m.clear()
        for x, y in PLAY_PX:
            m.set(x, y, (f, f, f))
        m.show()
        stats_t = t
        shown = 0
        time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
    else:
        time.sleep_ms(1)
