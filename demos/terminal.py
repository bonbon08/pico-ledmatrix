# Demo: Terminal. Altes Bernstein-Terminal: links tippt sich Text Zeile fuer Zeile, rechts druckt
# sich zu jeder Strophe ein Pixel-Symbol und ein Pegelmesser huepft im Takt des Tippens.
import time, random, gc
import matrix as m

W, H = m.W, m.H
FRAME_MS = 40
TYPE_FRAMES = 2      # Bilder pro getipptem Zeichen
LINE_PAUSE = 8       # Pause am Zeilenende (Bilder)
VERSE_LINES = (8, 14)  # so viele Zeilen hat eine Strophe (von, bis)
VERSE_PAUSE = 45     # Pause nach einer Strophe, dann wird der Schirm geloescht
TEXT_W = 9           # Breite des Textfensters (Spalten 0..8)
ROWS = (1, 3, 5, 7, 9, 11, 13)   # Textzeilen im linken Fenster

AMBER = (255, 140, 0)
FRESH = (255, 210, 80)   # gerade getippte Zeichen leuchten kurz heller
FRAME = (150, 55, 0)     # gestrichelte Rahmen

# Symbole fuer das rechte Fenster (6x6), X = Pixel
ICONS = (
    (".X..X.", "XXXXXX", "XXXXXX", ".XXXX.", "..XX..", "......"),   # Herz
    (".XXXX.", "X.XX.X", "XXXXXX", "X.XX.X", "XX..XX", ".XXXX."),   # Smiley
    (".XXXX.", "XXXXXX", "XXXXXX", ".XXXX.", "..XX..", "..XX.."),   # Gluehbirne
    (".....X", "....XX", "X..XX.", "XXXX..", ".XX...", "......"),   # Haken
    ("...XX.", "..XX..", ".XXXX.", "..XX..", ".XX...", ".X...."),   # Blitz
    ("..XX..", ".XXXX.", ".X..X.", ".XXXX.", "XXXXXX", "X.XX.X"),   # Rakete
    ("..XX..", "..XX..", "XXXXXX", ".XXXX.", ".X..X.", "X....X"),   # Stern
)
ICON_X, ICON_Y = 10, 2
BAR_TOP, BAR_BOTTOM = 10, 14     # Pegelmesser rechts unten

# Rahmen einmal zeichnen, danach pro Bild nur kopieren
m.clear()
for x in range(0, W, 2):
    m.set(x, 0, FRAME)
    m.set(x, 15, FRAME)
for y in range(0, H, 2):
    m.set(TEXT_W, y, FRAME)
for x in range(TEXT_W + 1, W, 2):
    m.set(x, 8, FRAME)
BG = bytes(m.buf)

def new_line():
    # eine Zeile aus Woertern (1-4 Zeichen) mit Luecken, als Liste von 0/1
    n = random.randrange(5, TEXT_W + 1)
    if random.random() < 0.08:
        return []                # Leerzeile
    out = []
    while len(out) < n:
        out += [1] * random.randrange(1, 5)
        out.append(0)
    out = out[:n]
    while out and out[-1] == 0:
        out.pop()
    return out

lines = []           # fertig getippte Zeilen (sichtbar)
cur = new_line()     # Zeile, die gerade getippt wird
pos = 0              # wie viele Zeichen davon schon da sind
wait = 0
left = random.randrange(*VERSE_LINES)
icon = random.randrange(len(ICONS))
icon_rows = 0        # wie viele Zeilen des Symbols schon gedruckt sind
bars = [0.0] * 6
frame = 0
typing = True

while True:
    t = time.ticks_ms()
    frame += 1

    # Tippen
    typing = False
    if wait > 0:
        wait -= 1
        if wait == 0 and left <= 0:
            # neue Strophe: Schirm leeren, anderes Symbol
            lines = []
            left = random.randrange(*VERSE_LINES)
            icon = (icon + random.randrange(1, len(ICONS))) % len(ICONS)
            icon_rows = 0
    elif frame % TYPE_FRAMES == 0:
        if pos < len(cur):
            pos += 1
            typing = cur[pos - 1] == 1
        else:
            lines.append(cur)
            if len(lines) >= len(ROWS):
                lines.pop(0)     # nach oben scrollen
            cur = new_line()
            pos = 0
            left -= 1
            wait = VERSE_PAUSE if left <= 0 else LINE_PAUSE
            if left <= 0:
                cur = new_line()
    if icon_rows < 6 and frame % 3 == 0:
        icon_rows += 1

    # Pegelmesser: springt beim Tippen hoch, faellt langsam
    for i in range(6):
        if typing and random.random() < 0.6:
            bars[i] = max(bars[i], random.uniform(1, 5))
        bars[i] = max(0.0, bars[i] - 0.25)

    # zeichnen
    m.buf[:] = BG
    for k, ln in enumerate(lines):
        y = ROWS[k]
        for x in range(len(ln)):
            if ln[x]:
                m.set(x, y, AMBER)
    y = ROWS[len(lines)] if left > 0 or wait == 0 else None
    if y is not None:
        for x in range(pos):
            if cur[x]:
                m.set(x, y, FRESH if x >= pos - 2 else AMBER)
        if (frame // 6) % 2 == 0 and pos < TEXT_W:
            m.set(pos, y, AMBER)     # Cursor
    art = ICONS[icon]
    for r in range(icon_rows):
        row = art[r]
        for c in range(6):
            if row[c] == "X":
                m.set(ICON_X + c, ICON_Y + r, AMBER)
    for i in range(6):
        h = int(bars[i] + 0.5)
        for j in range(h):
            m.set(TEXT_W + 1 + i, BAR_BOTTOM - j, FRESH if j == h - 1 else AMBER)
    m.show()
    if frame % 8 == 0:
        gc.collect()
    time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(time.ticks_ms(), t)))
