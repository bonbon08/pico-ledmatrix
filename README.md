# Pico LED-Matrix 16×16

Regenbogen-Animation für vier WS2812B-8×8-Matrizen (WS2812B-64) an einem Raspberry Pi Pico mit MicroPython.
Die vier Matrizen bilden zusammen eine Fläche von 16×16 Pixeln (256 LEDs). Sie sind so gedimmt, dass der Pico sie direkt über USB versorgen kann.

## Hardware

| Was | Details |
|---|---|
| Controller | Raspberry Pi Pico (RP2040) mit MicroPython |
| LEDs | 4 × WS2812B 8×8 (64 LEDs je Matrix), in Reihe geschaltet |
| Daten | **GP22** → DIN von Matrix 1, DOUT → DIN der nächsten Matrix usw. |
| Versorgung | 5 V von VBUS (USB) und GND gemeinsam mit dem Pico |

### Anordnung der Matrizen

Reihenfolge in der Datenkette (von vorne gesehen):

```
┌─────────┬─────────┐
│    1    │    3    │
│ (0–63)  │(128–191)│
├─────────┼─────────┤
│    2    │    4    │
│ (64–127)│(192–255)│
└─────────┴─────────┘
```

Innerhalb jeder Matrix laufen die LEDs zeilenweise von links nach rechts und dann von oben nach unten, also nicht im Zickzack.

### Koordinaten

`xy(x, y)` rechnet eine Koordinate in den LED-Index um. (0,0) ist oben links, (15,15) unten rechts:

```python
def xy(x, y):
    m = (x // 8) * 2 + (y // 8)          # welche Matrix (0–3)
    return m * 64 + (y % 8) * 8 + (x % 8)
```

## Stromverbrauch und Helligkeit

Bei voller Helligkeit zieht eine WS2812B in Weiß bis zu ca. 60 mA. 256 LEDs kämen damit auf über 15 A, viel zu viel für USB (500 mA).
Deshalb begrenzt `MAX` in `matrix.py` jeden Farbkanal auf **16 von 255**, also etwa 6 %.

Zusätzlich gibt es eine **Strombremse**: `show()` addiert alle Farbwerte. Liegt die Summe über `BUDGET`, wird das ganze Bild gleichmäßig gedimmt. `BUDGET` entspricht dem Regenbogen, bei dem jede LED zusammen 255 hat. Damit bleiben auch Demos mit vielen weißen oder gelben Pixeln im sicheren Bereich.

Grobe Schätzung:

| Verbraucher | Strom |
|---|---|
| Ruhestrom der LEDs (0,6–1 mA pro LED, auch wenn sie aus sind) | 150–250 mA |
| Leuchten bei `MAX = 16` (ca. 1,25 mA pro LED) | ca. 320 mA |
| Pico | ca. 25 mA |
| **Summe** | **ca. 500 mA** |

Das ist etwa die Grenze eines USB-2.0-Ports. Gemessen wurde VSYS über ADC3 (GP29): Die Spannung fiel von 4,71 V (alle LEDs aus) gleichmäßig auf 4,61 V (MAX 22), ohne Einbruch.

> Ohne externes 5-V-Netzteil `MAX` nicht über ca. 22 stellen. Bei Flackern oder Abstürzen auf 12 zurückgehen.
> Mit Netzteil die 5 V direkt an die Matrizen führen und GND mit dem Pico verbinden.

## Dateien

| Datei | Zweck |
|---|---|
| `matrix.py` | Gemeinsame Bibliothek: Koordinaten, Helligkeit, Helligkeitsausgleich, Strombremse |
| `demos/regenbogen.py` | Regenbogen-Ringe von der Mitte nach außen |
| `demos/tetris.py` | Zufällige Tetris-Steine fallen und stapeln sich, volle Reihen verschwinden |
| `demos/snake.py` | Snake, die von alleine spielt und meist das ganze Feld füllt |
| `demos/gameoflife.py` | Conways Game of Life mit Überblenden und Farbe nach Zellalter |
| `demos/feuer.py` | Lagerfeuer mit Flammenzungen, Wind und aufsteigenden Funken |
| `demos/uhr.py` | Uhr: oben Stunden, unten Minuten, Sekundenring am Rand (60 Pixel) |
| `demos/rennen_oben.py` | Autorennen von oben: 4 Autos auf einer 64×64-Strecke, Kamera fährt mit ([Vorschau](bilder/rennen_oben.png)) |
| `demos/rennen_hinten.py` | Autorennen von hinten (Pseudo-3D) mit Kurven, Sonnenuntergang, Palmen und Gegenverkehr ([Vorschau](bilder/rennen_hinten.png)) |
| `demos/shooter.py` | Ego-Shooter im 90er-Stil, der sich selbst spielt: Raycasting, eigenes Labyrinth, Schleimmonster ([Vorschau](bilder/shooter.png)) |
| `demos/visualizer.py` | Sound-Visualizer: 16 Frequenzbalken vom PC-Ton, braucht `tools/visualizer.py` auf dem PC |
| `demos/roboter.py` | Kleiner Roboter, der schaut, blinzelt, winkt, tanzt, sich verliebt und einschläft ([Vorschau](bilder/roboter.png)) |
| `demos/kopfstein.py` | Pflastersteinblock im Minecraft-Stil, der um alle drei Achsen taumelt ([Vorschau](bilder/kopfstein.png)) |
| `demos/matrixcode.py` | Grüner Matrix-Code-Regen mit flackernden Zeichen ([Vorschau](bilder/matrixcode.png)) |
| `demos/erdblock.py` | Rotierender 3D-Erdblock im Minecraft-Stil, optional als Grasblock ([Erde](bilder/erdblock.png), [Gras](bilder/grasblock.png)) |
| `demos/feuerwerk.py` | Feuerwerk mit Kugeln, Ringen, Goldregen und Glitzer, mit Nachleuchten ([Vorschau](bilder/feuerwerk.png)) |
| `demos/aquarium.py` | Aquarium mit Fischen, Seegras, Schatztruhe und Luftblasen ([Vorschau](bilder/aquarium.png)) |
| `demos/sternhimmel.py` | Funkelnde Sterne, Mondsichel und gelegentliche Sternschnuppen ([Vorschau](bilder/sternhimmel.png)) |
| `demos/kirschbaum.py` | Blauer Kirschblütenbaum bei Nacht mit fallenden Blütenblättern ([Vorschau](bilder/kirschbaum.png)) |
| `tools/testbild.py` | Testbild zum Prüfen der Ausrichtung |
| `tools/visualizer.py` | PC-Seite des Sound-Visualizers |
| `gehaeuse/` | 3D-Druck-Gehäuse (OpenSCAD + STL) |

## Installation

Benötigt wird [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html), z. B. über `uv`.
Zuerst einmal die Bibliothek hochladen, dann die gewünschte Demo als `main.py`:

```bash
uvx mpremote cp matrix.py :matrix.py
uvx mpremote cp demos/tetris.py :main.py + reset
```

`main.py` startet automatisch beim Einschalten. Der Treiber `neopixel` ist in MicroPython für den RP2040 schon enthalten.

### Uhr

Der Pico hat keine Uhr mit Batterie. Nach jedem Einstecken und nach jedem Hardware-Reset steht die Zeit auf dem 1.1.2021, die Uhr zeigt dann blinkend `-- --`.
Deshalb die Zeit beim Hochladen vom PC übernehmen und `main.py` ohne Reset starten:

```bash
uvx mpremote cp demos/uhr.py :main.py + rtc --set + exec --no-follow "import main"
```

### Sound-Visualizer

Der PC schneidet den Ton mit, der gerade abgespielt wird (PipeWire/PulseAudio, Monitor des Standard-Ausgangs). Daraus berechnet er 16 logarithmisch verteilte Frequenzbänder von 40 Hz bis 16 kHz und schickt sie etwa 40-mal pro Sekunde per USB an den Pico.
Die Lautstärke wird automatisch nachgeregelt. Kommen 2 Sekunden lang keine Daten an, zeigt der Pico eine blaue Warte-Welle.

```bash
uvx mpremote cp demos/visualizer.py :main.py + reset
python tools/visualizer.py          # benötigt parec, numpy, pyserial; Strg+C beendet
```

Solange `tools/visualizer.py` läuft, belegt es den USB-Port. `mpremote` funktioniert dann nicht.
Übertragen werden nur druckbare Zeichen (`'0'` + Pegel 0–64 je Band, dann ein Zeilenende). So landet nie versehentlich ein Strg+C beim Pico.

## Eigene Demos

```python
import matrix as m

m.clear()
m.set(0, 0, (255, 0, 0))      # Pixel oben links rot, Farben immer 0-255
m.set(15, 15, m.wheel(300))   # Farbe aus dem Farbrad (0-767)
m.show()                      # dimmt, korrigiert und sendet an die LEDs
```

`show()` braucht etwa 8 ms. Die Umrechnung läuft mit `@micropython.viper` als nativer Code, der Rest ist das Senden an die LEDs.

## Testbild

```bash
uvx mpremote run tools/testbild.py
```

Wenn die Zuordnung stimmt, siehst du:

- **Rot:** die komplette oberste Zeile (16 LEDs)
- **Grün:** die komplette linke Spalte (16 LEDs)
- **Gelb:** einen Punkt bei (1,1)
- **Blau:** einen Punkt ganz unten rechts (15,15)

Das Testbild bleibt nur bis zum nächsten Reset. Danach startet wieder `main.py`.

## Anpassen

- **Helligkeit:** `MAX` in `matrix.py`
- **Helligkeitsausgleich je Matrix und Farbe:** `GAIN` in `matrix.py`. Matrix 1 hat andere LEDs: Rot und Grün leuchten doppelt so hell, Blau etwa 1,45-mal. Sie läuft deshalb mit (0,5; 0,5; 0,69). Die Werte wurden per Auge mit einfarbigen Testbildern abgeglichen.
- **Regenbogen:** Die Geschwindigkeit stellt man über `off + 12` und `time.sleep_ms(20)` ein. Ein größerer Faktor in `int(d * 48)` ergibt schmalere Ringe.
- **Rennen von oben:** Die Strecke steht in `POINTS` als Eckpunkte einer geschlossenen Runde (Welt 64×64). `ROAD` und `CURB` sind die halbe Straßenbreite und die Breite der Randsteine. Die Autofarben stehen in `CARS`. Beim Start wird die Strecke etwa 4 Sekunden lang berechnet, solange ist ein Ladebalken zu sehen.
- **Rennen von hinten:** Die Strecke steht in `TRACK` als Abschnitte (Länge, Krümmung; negativ = links). `SPEED` ist das Tempo, `PX` die Straßenbreite.
- **Shooter:** Das Labyrinth steht in `MAP` (`#` Stein, `B` Ziegel, `T` Technik, `.` frei). `ENEMIES` ist die Anzahl der Gegner, `SHOOT_DIST` der Abstand, ab dem geschossen wird. `MOVE` und `TURN` bestimmen das Tempo.
- **Roboter:** Farben stehen oben in der Datei. Welche Zustände wie oft vorkommen, regelt `next_state()`.
- **Pflasterstein:** `SPIN` ist das Drehtempo um die drei Achsen, `STONES` das Steinmuster (8×8).
- **Matrix-Code:** `DROPS` ist die Anzahl der Spuren pro Spalte, `DECAY` die Schweiflänge, `GLYPH_FLIP` wie oft Zeichen wechseln.
- **Erdblock:** Mit `GRASS = True` wird daraus ein Grasblock. `SPIN` ist das Drehtempo, `TILT` die Neigung (negativ = von oben gesehen), `ZOOM` die Größe (kleiner = größer).
- **Feuerwerk:** `LAUNCH` ist die Häufigkeit der Raketen, `FINALE` die Häufigkeit eines Finales mit 4 Raketen. `TRAIL` bestimmt die Länge der Leuchtspuren. `MAX_SPARKS` begrenzt die Funken, damit der Pico flüssig bleibt.
- **Aquarium:** `FISH` ist die Anzahl der Fische (Farben in `FISH_COLS`), `BUBBLE_RATE` die Häufigkeit der Luftblasen. Die Fischform steht in `FISH_ART`, das Seegras in `WEEDS` als (x, Höhe).
- **Sternhimmel:** `STARS` ist die Anzahl der Sterne, `SHOOT` die Häufigkeit der Sternschnuppen (0,006 = etwa alle 7 Sekunden). Mit `MOON` lässt sich der Mond ein- und ausschalten.
- **Kirschbaum:** Die Form steht als Pixel-Art in `ART` (B = Blüte, T = Stamm, G = Boden, * = Stern), die Farben in `BLUES`. `PETALS` und `PETAL_RATE` steuern die Blütenblätter.
- **Feuer:** `COOL` bestimmt die Flammenhöhe (größer = niedriger). `EMBER` ist die Häufigkeit der Funken, `WIND` die Häufigkeit von Windwechseln.
- **Game of Life:** `FRAMES` und `FRAME_MS` bestimmen das Tempo (eine Generation = `FRAMES × FRAME_MS`, also ca. 190 ms). `DENSITY` ist die Startdichte beim Zufallsstart.
- **Snake:** `STEP_MS` ist die Zeit pro Schritt. Eine komplette Runde dauert bei 80 ms etwa 15 Minuten.
- **Tetris:** `FALL_MS` ist die Fallgeschwindigkeit. `SMART` ist der Anteil der Steine, die gut gelegt werden. Je höher der Wert, desto mehr Reihen werden voll.

## Fehlersuche

- **LEDs bleiben dunkel oder flackern:** Der 3,3-V-Datenpegel des Pico reicht bei 5-V-LEDs manchmal nicht ganz. Hilfreich sind dann ein Widerstand von 330 Ω in der Datenleitung, eine kurze Leitung oder ein Pegelwandler (z. B. 74AHCT125). Außerdem prüfen, ob GND gemeinsam verbunden ist.
- **Farben vertauscht:** Andere LED-Typen verwenden eine andere Kanalreihenfolge (z. B. RGB statt GRB).
- **Bild verdreht oder gespiegelt:** Mit dem Testbild prüfen und `xy()` anpassen.

## Gehäuse

Ein Gehäuse zum 3D-Drucken (Rahmen mit Pixelraster und Diffusor, Deckel mit Pico-Halter) liegt in [`gehaeuse/`](gehaeuse/README.md).
