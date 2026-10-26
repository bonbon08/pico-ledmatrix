#!/usr/bin/env python3
"""Tastatur-Sender fuer Bongo-Katze und Tipp-Ente: meldet dem Pico jeden Tastendruck am PC.

Gesendet wird nie, welche Taste gedrueckt wurde, nur ihre Reihe auf der Tastatur: "q" fuer die
oberen Reihen (Ziffern, QWERTZ, F-Tasten), "a" fuer die mittlere, "y" fuer die untere mit Leertaste,
"k" fuer alles andere. Beim Loslassen kommt ein "l", jede Sekunde ein Lebenszeichen: "." wenn keine
Taste mehr gehalten wird, sonst "h". Gelesen wird direkt aus /dev/input, das funktioniert auch
unter Wayland und egal welches Fenster aktiv ist. Dafuer muss der Benutzer in der Gruppe "input" sein:

    sudo usermod -aG input $USER     (danach ab- und wieder anmelden)

Aufruf:  python tools/tastatur.py [--port /dev/ttyACM0]
Benoetigt: pyserial
"""
import argparse
import os
import select
import struct
import sys
import time

import serial
from serial.tools import list_ports

EVENT = struct.Struct("llHHi")       # struct input_event: Zeit (2x long), Typ, Code, Wert
EV_KEY = 1
# Linux-Tastencodes je Reihe (gelten fuer QWERTZ und QWERTY gleich, es sind Positionen)
ROW = {}
for c in [1, *range(2, 28), *range(59, 69), 87, 88]:         # Esc, Ziffern, Q-Reihe, F1-F12
    ROW[c] = b"q"
for c in [28, *range(30, 42), 43, 58]:           # Enter, A-Reihe, #, Feststell
    ROW[c] = b"a"
for c in [29, 42, *range(44, 58), 86, 97, 100, 125, 126]:    # Strg, Umschalt, Y-Reihe, Alt, Leertaste, <>, Super
    ROW[c] = b"y"


def find_port():
    for p in list_ports.comports():
        if p.vid == 0x2E8A:          # Raspberry Pi
            return p.device
    sys.exit("Kein Pico gefunden, bitte --port angeben")


def keyboards():
    """Pfade aller Geraete, die wie eine echte Tastatur aussehen (viele Tasten)."""
    found = []
    for block in open("/proc/bus/input/devices").read().split("\n\n"):
        handlers = keys = ""
        for line in block.splitlines():
            if line.startswith("H: Handlers="):
                handlers = line[12:]
            elif line.startswith("B: KEY="):
                keys = line[7:]
        if "kbd" not in handlers or not keys:
            continue
        nkeys = sum(bin(int(w, 16)).count("1") for w in keys.split())
        if nkeys < 60:               # Lautstaerke-Tasten, Power-Knopf usw. aussortieren
            continue
        for h in handlers.split():
            if h.startswith("event"):
                found.append("/dev/input/" + h)
    return found


def open_keyboards():
    fds = {}
    denied = []
    for path in keyboards():
        try:
            fds[os.open(path, os.O_RDONLY | os.O_NONBLOCK)] = path
        except PermissionError:
            denied.append(path)
    return fds, denied


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port")
    args = ap.parse_args()

    fds, denied = open_keyboards()
    if not fds:
        if denied:
            sys.exit("Keine Berechtigung fuer die Tastatur (" + ", ".join(denied) + ").\n"
                     "Einmalig ausfuehren:  sudo usermod -aG input $USER\n"
                     "und danach ab- und wieder anmelden.")
        sys.exit("Keine Tastatur gefunden")
    port = serial.Serial(args.port or find_port(), 115200, timeout=0)
    print(f"Lese {len(fds)} Tastatur(en), sende an {port.port}, Strg+C zum Beenden")
    last_beat = 0.0
    held = set()
    try:
        while True:
            ready, _, _ = select.select(list(fds), [], [], 0.5)
            out = b""
            for fd in ready:
                try:
                    data = os.read(fd, EVENT.size * 64)
                except OSError:            # Tastatur abgezogen
                    os.close(fd)
                    del fds[fd]
                    continue
                for i in range(0, len(data) - EVENT.size + 1, EVENT.size):
                    _, _, typ, code, value = EVENT.unpack_from(data, i)
                    if typ != EV_KEY or code >= 0x100:   # Maustasten u. a. nicht mitzaehlen
                        continue
                    if value == 1 and (fd, code) not in held:           # gedrueckt
                        held.add((fd, code))
                        out += ROW.get(code, b"k")
                    elif value == 0 and (fd, code) in held:             # losgelassen
                        held.discard((fd, code))
                        out += b"l"
                    # value 2 = automatische Wiederholung beim Halten, ignorieren
            now = time.monotonic()
            if now - last_beat > 1:
                held = {k for k in held if k[0] in fds}
                out += b"h" if held else b"."
                last_beat = now
                if not fds:                # neu eingesteckte Tastaturen finden
                    fds, _ = open_keyboards()
            if out:
                port.write(out)
    except KeyboardInterrupt:
        pass
    finally:
        port.close()


if __name__ == "__main__":
    main()
