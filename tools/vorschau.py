#!/usr/bin/env python3
"""Vorschaubild einer Demo auf dem PC erzeugen, ohne Pico.

Ersetzt matrix.py, micropython und die Zeitfunktionen durch Attrappen, laesst die Demo
laufen und speichert die gewuenschten Bilder nebeneinander als PNG.

Aufruf:  python tools/vorschau.py demos/feuer.py bilder/feuer.png 30,60,90 [--seed 4]
         python tools/vorschau.py demos/feuer.py --live    # Bilder in Echtzeit als Rohdaten
                                                           # auf stdout (768 Byte je Bild, fuer die GUI)
"""
import argparse
import builtins
import random
import sys
import time
import types

from PIL import Image, ImageDraw

N = 16
CELL = 22


def fake_modules(frames, live=False):
    m = types.ModuleType("matrix")
    m.W = m.H = N
    m.N = N * N
    m.buf = bytearray(N * N * 3)
    m.xy = lambda x, y: y * N + x                 # Vorschau: einfach zeilenweise

    def set_(x, y, c):
        if 0 <= x < N and 0 <= y < N:
            j = (y * N + x) * 3
            m.buf[j:j + 3] = bytes(max(0, min(255, int(v))) for v in c)

    def show():
        b = m.buf
        if live:
            out = bytearray(N * N * 3)
            out[:] = b
            try:
                sys.stdout.buffer.write(out)
                sys.stdout.buffer.flush()
            except BrokenPipeError:
                sys.exit(0)
            return
        frames.append([[tuple(b[(y * N + x) * 3:(y * N + x) * 3 + 3]) for x in range(N)] for y in range(N)])

    def wheel(p):
        p %= 768
        if p < 256:
            return (255 - p, p, 0)
        p -= 256
        if p < 256:
            return (0, 255 - p, p)
        p -= 256
        return (p, 0, 255 - p)

    m.set = set_
    m.show = show
    m.wheel = wheel
    m.fill = lambda c: m.buf.__setitem__(slice(None), bytes(c) * (N * N))
    m.clear = lambda: m.fill((0, 0, 0))
    mp = types.ModuleType("micropython")
    mp.viper = mp.native = lambda f: f
    sys.modules["matrix"] = m
    sys.modules["micropython"] = mp
    # Typ-Annotationen der viper-Funktionen
    builtins.ptr8 = builtins.ptr16 = builtins.ptr32 = object


class Stop(Exception):
    pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("demo")
    ap.add_argument("ausgabe", nargs="?")
    ap.add_argument("bilder", nargs="?", help="Bildnummern, z. B. 30,60,90")
    ap.add_argument("--seed", type=int, default=4)
    ap.add_argument("--live", action="store_true", help="in Echtzeit laufen, Bilder roh auf stdout")
    args = ap.parse_args()
    if args.live:
        live(args.demo)
        return
    if not (args.ausgabe and args.bilder):
        ap.error("Ausgabe und Bildnummern fehlen")
    want = [int(a) for a in args.bilder.split(",")]

    frames = []
    fake_modules(frames)
    count = [0]

    def sleep_ms(ms):
        count[0] += 1
        if count[0] > max(want):
            raise Stop

    # Zeit laeuft pro Bild 40 ms weiter, unabhaengig von der echten Rechenzeit
    time.sleep_ms = sleep_ms
    time.ticks_ms = lambda: count[0] * 40
    time.ticks_diff = lambda a, b: a - b
    random.seed(args.seed)
    try:
        exec(compile(open(args.demo, encoding="utf-8").read(), args.demo, "exec"), {"__name__": "__main__"})
    except Stop:
        pass
    if len(frames) < max(want):
        sys.exit(f"Demo hat nur {len(frames)} Bilder gezeigt")
    out = Image.new("RGB", (len(want) * (N * CELL + 20) - 20, N * CELL), (30, 30, 30))
    d = ImageDraw.Draw(out)
    for k, f in enumerate(want):
        fr = frames[f - 1]
        ox = k * (N * CELL + 20)
        d.rectangle([ox, 0, ox + N * CELL - 1, N * CELL - 1], fill=(0, 0, 0))
        for y in range(N):
            for x in range(N):
                d.rectangle([ox + x * CELL + 1, y * CELL + 1, ox + x * CELL + CELL - 2, y * CELL + CELL - 2],
                            fill=fr[y][x])
    out.save(args.ausgabe)


def live(demo):
    """Demo mit echter Zeit laufen lassen; jedes show() schreibt das Bild auf stdout."""
    fake_modules(None, live=True)
    t0 = time.monotonic()
    time.sleep_ms = lambda ms: time.sleep(max(0, ms) / 1000)
    time.ticks_ms = lambda: int((time.monotonic() - t0) * 1000)
    time.ticks_us = lambda: int((time.monotonic() - t0) * 1000000)
    time.ticks_diff = lambda a, b: a - b
    time.ticks_add = lambda a, b: a + b
    try:
        exec(compile(open(demo, encoding="utf-8").read(), demo, "exec"), {"__name__": "__main__"})
    except (BrokenPipeError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
