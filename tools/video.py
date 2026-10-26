#!/usr/bin/env python3
"""Video-Sender: spielt eine Videodatei oder einen Link als 16x16-Video auf der Matrix ab.

ffmpeg dekodiert, schneidet quadratisch zu, verkleinert flaechengemittelt auf 16x16 und hebt
Farbe und Kontrast etwas an. Jedes Bild geht als "#" + 768 Zeichen '0'..'o' (6 Bit je Farbe)
+ Zeilenende an den Pico (demos/video.py) - nur druckbare Zeichen, nie Strg+C. Kommt der Pico
nicht hinterher, werden Bilder ausgelassen, damit das Video im Takt bleibt.

Aufruf:  python tools/video.py film.mp4
         python tools/video.py "https://www.youtube.com/watch?v=..."   (braucht yt-dlp)
         python tools/video.py film.mp4 --fps 20 --modus rand --schleife
Benoetigt: ffmpeg, pyserial; fuer Links yt-dlp
"""
import argparse
import signal
import subprocess
import sys
import time

import serial
from serial.tools import list_ports

N = 16
FRAME = N * N * 3
TABLE = bytes(48 + (v >> 2) for v in range(256))   # 8 Bit -> '0'..'o'


def find_port():
    for p in list_ports.comports():
        if p.vid == 0x2E8A:          # Raspberry Pi
            return p.device
    sys.exit("Kein Pico gefunden, bitte --port angeben")


def resolve(src):
    """Links von Videoseiten mit yt-dlp in eine direkte Video-Adresse umwandeln."""
    if not src.startswith(("http://", "https://")):
        return src
    try:
        out = subprocess.run(["yt-dlp", "-g", "-f", "worstvideo[height>=144]/worst[height>=144]/worst", src],
                             capture_output=True, text=True, check=True).stdout.split()
        return out[0]
    except FileNotFoundError:
        return src                   # ohne yt-dlp: vielleicht ist es schon eine Video-Adresse
    except subprocess.CalledProcessError as e:
        sys.exit("yt-dlp konnte den Link nicht oeffnen:\n" + e.stderr.strip())


def ffmpeg(src, fps, modus, loop, sat, contrast):
    if modus == "rand":          # ganzes Bild mit schwarzem Rand
        fit = f"scale={N}:{N}:force_original_aspect_ratio=decrease:flags=area,pad={N}:{N}:(ow-iw)/2:(oh-ih)/2"
    elif modus == "strecken":
        fit = f"scale={N}:{N}:flags=area"
    else:                        # quadratisch zuschneiden
        fit = f"crop='min(iw,ih)':'min(iw,ih)',scale={N}:{N}:flags=area"
    vf = f"fps={fps},{fit},eq=saturation={sat}:contrast={contrast}"
    cmd = ["ffmpeg", "-loglevel", "error"]
    if loop:
        cmd += ["-stream_loop", "-1"]
    cmd += ["-i", src, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    try:
        return subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except FileNotFoundError:
        sys.exit("ffmpeg ist nicht installiert")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("quelle", help="Videodatei oder Link")
    ap.add_argument("--port")
    ap.add_argument("--fps", type=float, default=25, help="Bilder pro Sekunde (Standard 25)")
    ap.add_argument("--modus", choices=("zuschneiden", "rand", "strecken"), default="zuschneiden",
                    help="an 16x16 anpassen: Mitte zuschneiden, ganzes Bild mit Rand oder strecken")
    ap.add_argument("--rand", action="store_true", help="kurz fuer --modus rand")
    ap.add_argument("--schleife", action="store_true", help="Video endlos wiederholen")
    ap.add_argument("--farbe", type=float, default=1.4, help="Farbsaettigung (1 = unveraendert)")
    ap.add_argument("--kontrast", type=float, default=1.15, help="Kontrast (1 = unveraendert)")
    args = ap.parse_args()

    # beim Beenden von aussen (z. B. durch die GUI) ffmpeg mit beenden
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    port = serial.Serial(args.port or find_port(), 115200, timeout=0, write_timeout=3)
    proc = ffmpeg(resolve(args.quelle), args.fps, "rand" if args.rand else args.modus, args.schleife,
                  args.farbe, args.kontrast)
    print(f"Sende {args.quelle} an {port.port}, Strg+C zum Beenden")
    step = 1 / args.fps
    t0 = time.monotonic()
    k = sent = dropped = 0
    last_report = t0
    try:
        while True:
            data = proc.stdout.read(FRAME)
            if len(data) < FRAME:
                break
            due = t0 + k * step
            k += 1
            now = time.monotonic()
            if now > due + step:
                dropped += 1         # zu spaet, Bild auslassen
                continue
            if due > now:
                time.sleep(due - now)
            port.write(b"#" + data.translate(TABLE) + b"\n")
            sent += 1
            back = port.read(256)    # Meldungen des Pico weitergeben
            if back:
                sys.stdout.write(back.decode(errors="replace"))
            if now - last_report > 10:
                print(f"PC: {sent / (now - last_report):.1f} Bilder/s gesendet, {dropped} ausgelassen")
                sent = dropped = 0
                last_report = now
    except KeyboardInterrupt:
        pass
    except serial.SerialTimeoutException:
        print("Pico nimmt keine Daten an - laeuft demos/video.py?")
    finally:
        proc.kill()
        port.close()
    print("Video zu Ende")


if __name__ == "__main__":
    main()
