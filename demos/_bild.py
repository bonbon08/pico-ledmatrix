# Player fuer eigene Bilder und GIFs (wird von tools/gui.py zusammen mit bild.bin hochgeladen).
# bild.bin: b"LEDB", Anzahl Bilder (2 Byte), dann je Bild: Dauer in ms (2 Byte) + 768 Byte RGB,
# zeilenweise von oben links. Die Bilder werden einzeln aus dem Flash gelesen, damit auch
# lange GIFs nicht in den Arbeitsspeicher muessen.
import time, struct, micropython, array
import matrix as m

W, H = m.W, m.H
FILE = "bild.bin"
FRAME = W * H * 3

IDX = array.array('H', [m.xy(i % W, i // W) * 3 for i in range(W * H)])

@micropython.viper
def remap(src: ptr8, idx: ptr16, dst: ptr8, n: int):
    # zeilenweise RGB -> Reihenfolge der LED-Kette
    for i in range(n):
        j = idx[i]
        k = i * 3
        dst[j] = src[k]
        dst[j + 1] = src[k + 1]
        dst[j + 2] = src[k + 2]

frame = bytearray(FRAME)
head = bytearray(2)
with open(FILE, "rb") as f:
    if f.read(4) != b"LEDB":
        raise ValueError("bild.bin hat das falsche Format")
    count = struct.unpack("<H", f.read(2))[0]
    start = f.tell()
    while True:
        f.seek(start)
        for _ in range(count):
            t = time.ticks_ms()
            f.readinto(head)
            dur = head[0] | head[1] << 8
            f.readinto(frame)
            remap(frame, IDX, m.buf, W * H)
            m.show()
            if count == 1:
                # Standbild: einfach stehen lassen
                while True:
                    time.sleep(1)
            time.sleep_ms(max(0, dur - time.ticks_diff(time.ticks_ms(), t)))
