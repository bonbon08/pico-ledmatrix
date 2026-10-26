#!/usr/bin/env python3
"""OS-Logo fuer die Matrix: holt das Logo, das fastfetch anzeigt, und rechnet es auf 16x16 um.

Das farbige ASCII-Logo von fastfetch wird mit einer Monospace-Schrift gezeichnet, auf das Logo
zugeschnitten und flaechengemittelt auf 16x16 verkleinert. Ergebnis: oslogo.bin (768 Byte RGB,
zeilenweise von oben links) fuer demos/oslogo.py.

Aufruf:  python tools/oslogo.py                      # Logo dieses PCs, oslogo.bin + Vorschau
         python tools/oslogo.py --logo debian        # anderes Logo (fastfetch --list-logos)
         python tools/oslogo.py --upload             # zusammen mit der Demo auf den Pico laden
Benoetigt: fastfetch, Pillow
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
N = 16
LOW, HIGH = 0.2, 0.55      # Helligkeit unter LOW wird schwarz, ab HIGH voll

# ANSI-Grundfarben, kraeftig gewaehlt (die Matrix dimmt ohnehin stark)
ANSI = {30: (90, 90, 90), 31: (255, 40, 40), 32: (40, 230, 60), 33: (255, 200, 0),
        34: (40, 90, 255), 35: (230, 50, 230), 36: (20, 160, 255), 37: (230, 230, 230)}


def xterm256(n):
    if n < 16:
        return ANSI[30 + n % 8]
    if n < 232:
        n -= 16
        return tuple((0, 95, 135, 175, 215, 255)[v] for v in (n // 36, n // 6 % 6, n % 6))
    v = 8 + (n - 232) * 10
    return (v, v, v)


def fastfetch_logo(logo):
    cmd = ["fastfetch", "-s", "none", "--pipe", "false"]
    if logo:
        cmd += ["--logo", logo]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("fastfetch ist nicht installiert")
    # in Zeilen aus (Zeichen, Farbe) zerlegen
    rows = []
    col = ANSI[37]
    for line in out.split("\n"):
        row = []
        for part in re.split(r"(\x1b\[[0-9;]*m)", line):
            if part.startswith("\x1b["):
                codes = [int(c) for c in part[2:-1].split(";") if c]
                i = 0
                while i < len(codes):
                    c = codes[i]
                    if c in ANSI:
                        col = ANSI[c]
                    elif 90 <= c <= 97:
                        col = ANSI[c - 60]
                    elif c == 38 and i + 2 < len(codes) and codes[i + 1] == 5:
                        col = xterm256(codes[i + 2]); i += 2
                    elif c == 38 and i + 4 < len(codes) and codes[i + 1] == 2:
                        col = tuple(codes[i + 2:i + 5]); i += 4
                    i += 1
            else:
                row += [(ch, col) for ch in part]
        rows.append(row)
    while rows and not any(ch.strip() for ch, _ in rows[-1]):
        rows.pop()
    if not rows:
        sys.exit("fastfetch hat kein Logo geliefert")
    return rows


def list_logos():
    """Namen der eingebauten fastfetch-Logos."""
    out = subprocess.run(["fastfetch", "--list-logos"], capture_output=True, text=True).stdout
    return [m.group(1) for m in re.finditer(r'^\s*\d+\)\s+"([^"]+)"', out, re.M)]


def render(rows, low=LOW, high=HIGH):
    font_path = subprocess.run(["fc-match", "-f", "%{file}", "monospace"], capture_output=True,
                               text=True).stdout or None
    font = ImageFont.truetype(font_path, 40) if font_path else ImageFont.load_default()
    cw = int(font.getlength("M"))
    ascent, descent = font.getmetrics()
    ch_h = ascent + descent
    width = max(len(r) for r in rows)
    img = Image.new("RGB", (width * cw, len(rows) * ch_h))
    d = ImageDraw.Draw(img)
    for y, row in enumerate(rows):
        for x, (ch, col) in enumerate(row):
            if ch.strip():
                d.text((x * cw, y * ch_h), ch, font=font, fill=col)
    img = img.crop(img.getbbox())
    # quadratisch auffuellen, dann flaechengemittelt verkleinern
    side = max(img.size)
    sq = Image.new("RGB", (side, side))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    small = sq.resize((N, N), Image.BOX)
    # Helligkeit spreizen: Farbton bleibt, schwache Randpixel fallen weg, Kern wird voll
    pix = small.load()
    top = max(max(pix[x, y]) for y in range(N) for x in range(N)) or 1
    for y in range(N):
        for x in range(N):
            p = pix[x, y]
            f = min(1.0, max(0.0, (max(p) / top - low) / (high - low)))
            m = max(p) or 1
            pix[x, y] = tuple(round(c / m * 255 * f) for c in p)
    return small


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--logo", help="Logo-Name fuer fastfetch, sonst das des PCs")
    ap.add_argument("--out", default=str(ROOT / "oslogo.bin"))
    ap.add_argument("--png", help="Vorschau als PNG speichern (vergroessert)")
    ap.add_argument("--upload", action="store_true", help="mit demos/oslogo.py auf den Pico laden")
    args = ap.parse_args()

    img = render(fastfetch_logo(args.logo))
    Path(args.out).write_bytes(img.tobytes())
    print("Logo gespeichert:", args.out)
    if args.png:
        img.resize((N * 20, N * 20), Image.NEAREST).save(args.png)
    if args.upload:
        mp = [shutil.which("mpremote")] if shutil.which("mpremote") else ["uvx", "mpremote"]
        subprocess.run(mp + ["cp", str(ROOT / "matrix.py"), ":matrix.py", "+",
                             "cp", args.out, ":oslogo.bin", "+",
                             "cp", str(ROOT / "demos" / "oslogo.py"), ":main.py", "+", "reset"],
                       check=True)


if __name__ == "__main__":
    main()
