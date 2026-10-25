#!/usr/bin/env python3
"""Sound-Visualizer, PC-Seite: schneidet den Ton mit, der gerade auf dem PC laeuft
(PipeWire/PulseAudio, Monitor des Standard-Ausgangs), berechnet 16 Frequenzbaender und
schickt sie an den Pico. Dort muss demos/visualizer.py als main.py laufen.

Aufruf:  python tools/visualizer.py [--port /dev/ttyACM0] [--fps 40]
Benoetigt: parec (pipewire-pulse), numpy, pyserial
"""
import argparse
import subprocess
import sys
import time

import numpy as np
import serial
from serial.tools import list_ports

RATE = 44100
BANDS = 16
FMIN, FMAX = 40, 16000
FFT = 2048


def find_port():
    for p in list_ports.comports():
        if p.vid == 0x2E8A:          # Raspberry Pi
            return p.device
    sys.exit("Kein Pico gefunden, bitte --port angeben")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port")
    ap.add_argument("--fps", type=int, default=40)
    ap.add_argument("--quelle", default="@DEFAULT_MONITOR@",
                    help="PulseAudio-Quelle (Standard: was gerade abgespielt wird)")
    args = ap.parse_args()

    port = serial.Serial(args.port or find_port(), 115200, timeout=0)
    hop = RATE // args.fps
    rec = subprocess.Popen(
        ["parec", "-d", args.quelle, "--format=s16le", f"--rate={RATE}", "--channels=1",
         "--latency-msec=20"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    # logarithmisch verteilte Baender, jedes mindestens ein FFT-Bin breit
    freqs = np.fft.rfftfreq(FFT, 1 / RATE)
    edges = np.geomspace(FMIN, FMAX, BANDS + 1)
    bins = [(max(1, np.searchsorted(freqs, lo)), max(np.searchsorted(freqs, lo) + 1, np.searchsorted(freqs, hi)))
            for lo, hi in zip(edges[:-1], edges[1:])]
    window = np.hanning(FFT)
    buf = np.zeros(FFT)
    gain = 1e-3                      # automatische Verstaerkung: folgt dem lautesten Band
    print(f"Sende an {port.port}, Strg+C zum Beenden")
    try:
        while True:
            raw = rec.stdout.read(hop * 2)
            if not raw:
                break
            buf = np.roll(buf, -hop)
            buf[-hop:] = np.frombuffer(raw, dtype="<i2") / 32768
            spec = np.abs(np.fft.rfft(buf * window))
            bands = np.array([spec[a:b].mean() for a, b in bins])
            # hohe Frequenzen haben weniger Energie -> etwas anheben
            bands *= np.linspace(1, 3, BANDS)
            gain = max(gain * 0.995, bands.max(), 1e-3)
            db = 20 * np.log10(bands / gain + 1e-9)            # 0 dB = lautestes Band
            lv = np.clip((db + 40) / 40 * 64, 0, 64).astype(int)  # -40..0 dB -> 0..64
            if bands.max() < 2e-3:                             # Stille
                lv[:] = 0
            port.write(bytes(48 + v for v in lv) + b"\n")
    except KeyboardInterrupt:
        pass
    finally:
        rec.terminate()
        port.close()


if __name__ == "__main__":
    main()
