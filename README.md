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
Deshalb begrenzt `MAX` in `main.py` jeden Farbkanal auf **10 von 255**, also etwa 4 %. Außerdem leuchten nie alle drei Kanäle gleichzeitig, und zusammen ergeben sie höchstens `MAX`.

Grobe Schätzung:

| Verbraucher | Strom |
|---|---|
| Ruhestrom der LEDs (0,6–1 mA pro LED, auch wenn sie aus sind) | 150–250 mA |
| Leuchten bei `MAX = 10` (ca. 0,8 mA pro LED) | ca. 200 mA |
| Pico | ca. 25 mA |
| **Summe** | **ca. 375–475 mA** |

Das liegt knapp unter den 500 mA, die ein USB-2.0-Port liefert.

> Ohne externes 5-V-Netzteil `MAX` nicht weiter erhöhen.
> Mit Netzteil die 5 V direkt an die Matrizen führen und GND mit dem Pico verbinden.

## Dateien

| Datei | Zweck |
|---|---|
| `main.py` | Animation (Regenbogen-Ringe von der Mitte nach außen). Startet automatisch beim Einschalten. |
| `tools/testbild.py` | Testbild zum Prüfen der Ausrichtung |
| `gehaeuse/` | 3D-Druck-Gehäuse (OpenSCAD + STL) |

## Installation

Benötigt wird [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html), z. B. über `uv`:

```bash
uvx mpremote cp main.py :main.py + reset
```

Der Treiber `neopixel` ist in MicroPython für den RP2040 schon enthalten.

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

- **Helligkeit:** `MAX` in `main.py`
- **Geschwindigkeit:** `off + 12` (Schrittweite) und `time.sleep_ms(20)` (Pause zwischen den Bildern)
- **Ringbreite:** Faktor in `int(d * 48)`. Ein größerer Wert ergibt schmalere Ringe.

## Fehlersuche

- **LEDs bleiben dunkel oder flackern:** Der 3,3-V-Datenpegel des Pico reicht bei 5-V-LEDs manchmal nicht ganz. Hilfreich sind dann ein Widerstand von 330 Ω in der Datenleitung, eine kurze Leitung oder ein Pegelwandler (z. B. 74AHCT125). Außerdem prüfen, ob GND gemeinsam verbunden ist.
- **Farben vertauscht:** Andere LED-Typen verwenden eine andere Kanalreihenfolge (z. B. RGB statt GRB).
- **Bild verdreht oder gespiegelt:** Mit dem Testbild prüfen und `xy()` anpassen.

## Gehäuse

Ein Gehäuse zum 3D-Drucken (Rahmen mit Pixelraster und Diffusor, Deckel mit Pico-Halter) liegt in [`gehaeuse/`](gehaeuse/README.md).
