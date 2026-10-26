# Pico LED-Matrix 16×16

Raspberry Pi Pico (RP2040, MicroPython) steuert vier WS2812B-8×8-Matrizen an GP22 als 16×16-Fläche.
Dazu gehören Demos, eine PC-GUI zum Hochladen und ein 3D-Druck-Gehäuse. Mit dem Benutzer wird auf **Deutsch** kommuniziert, Doku und Commits sind ebenfalls auf Deutsch.

## Hardware, die man kennen muss

- **Anordnung von vorne:** Matrix 1 links oben, 2 links unten, 3 rechts oben, 4 rechts unten. Innerhalb einer Matrix laufen die LEDs zeilenweise, kein Zickzack. Die Umrechnung macht `matrix.xy(x, y)`, (0,0) ist oben links.
- **Strom:** Versorgt wird nur über USB, ca. 500 mA. Deshalb `MAX = 16` (von 255) in `matrix.py`, dazu die Strombremse `BUDGET`. Nicht über 22 erhöhen, ohne dass der Benutzer ein Netzteil hat.
- **Matrix 1 hat andere LEDs:** Sie ist heller als die anderen, Rot und Grün etwa ×2, Blau etwa ×1,45. Ausgeglichen wird das über `GAIN` in `matrix.py`, per Auge abgeglichen. Nicht ändern, ohne einfarbige Testbilder zu zeigen.
- **Gerundet wird überall mit `(x * f + 127) // 255`, nicht abgerundet.** Sonst wechseln die Farbstufen bei Matrix 1 zu anderen Zeitpunkten als bei den anderen Matrizen, und es sieht aus, als würde sie verzögert reagieren.
- **Uhr:** Der Pico hat keine RTC-Batterie. Ein Hard-Reset löscht die Zeit. Beim Hochladen der Uhr deshalb `rtc --set` und `exec --no-follow "import main"` statt `reset`.

## Aufbau

- `matrix.py`: die gemeinsame Bibliothek. Farben werden immer in 0–255 angegeben. Dazu gehören `set`, `get`, `fill`, `clear`, `show`, `wheel`, `xy` und `buf`, das ist RGB in LED-Ketten-Reihenfolge. `show()` dimmt, korrigiert und rundet per `@micropython.viper` und braucht etwa 8 ms.
- `demos/*.py`: eine Demo pro Datei, wird als `main.py` auf den Pico geladen. Dateien mit `_` am Anfang sind keine Demos, zum Beispiel `_bild.py`, der Player für eigene Bilder.
- `tools/gui.py`: Tkinter-GUI. Neue Demos tauchen automatisch auf, Name und Beschreibung kommen aus `NAMES`. Demos, die einen PC-Sender brauchen, stehen in `SENDERS`.
- `tools/visualizer.py` und `tools/tastatur.py`: PC-Sender. Sie schicken **nur druckbare Zeichen** über USB-Seriell, nie Byte 0x03 (Strg+C), sonst bricht der Pico das Programm ab.
- `tools/vorschau.py`: rendert eine Demo auf dem PC mit Attrappen für `matrix` und `micropython` als PNG.
- `gehaeuse/gehaeuse.scad`: parametrisches OpenSCAD-Gehäuse. `teil = "front" | "deckel" | "lehre"`.

## Befehle

```bash
uvx mpremote cp matrix.py :matrix.py + cp demos/X.py :main.py + reset    # Demo installieren
uvx mpremote run demos/X.py                                              # nur testen, ohne zu installieren
python tools/vorschau.py demos/X.py bilder/X.png 30,60,90                # Vorschau (Bildnummern)
openscad -o gehaeuse/front.stl -D 'teil="front"' gehaeuse/gehaeuse.scad  # STL erzeugen
python tools/gui.py
```

`mpremote` ist nicht installiert, immer `uvx mpremote` benutzen. Nach einem `reset` meldet sich der Pico 1–3 Sekunden lang neu am USB an. Direkt danach schlägt `mpremote` fehl, dann kurz warten.

## Regeln für neue Demos

Der Ablauf steht im Skill `/neue-demo`. Das Wichtigste:

1. **Kein Nachbau bestimmter Spiele oder Figuren.** Genres sind in Ordnung, also eigene Levels, eigene Grafik, eigene Namen. Bei Wünschen wie „Doom“ oder „OutRun“ das kurz sagen und eine eigene Version im Stil bauen.
2. **Immer zuerst eine Vorschau auf dem PC rendern und ansehen**, bevor die Demo auf den Pico geht. Die meisten Fehler sieht man dort: falsche Ausrichtung, Farben, Größen.
3. **Auf dem Pico messen.** Jede Demo hat `FRAME_MS`, und die gemessene Bildzeit muss darunter liegen. Typische Bremsen und was dagegen hilft:
   - Fließkomma und `m.set()` pro Pixel: unbewegten Hintergrund einmal vorberechnen und mit `m.buf[:] = BG` kopieren.
   - Schleifen über alle 256 Pixel: mit `@micropython.viper` und Festkomma rechnen.
   - Farben: Paletten oder Tabellen vorberechnen.
   - Speicher: alle 8 Bilder `gc.collect()` statt jedes Bild.
4. **Speicher:** Große `bytearray`s **am Anfang** anlegen, vor vielen kleinen Objekten. Der Heap fragmentiert sonst, und 4 KB am Stück sind trotz 190 KB freiem Speicher nicht mehr zu bekommen.
5. **viper-Einschränkungen:** keine verketteten Vergleiche (`0 <= x < 64` geht nicht), kein `random`, Integer sind 32 Bit.
6. **Farben im vollen Bereich wählen**, also mindestens ein Kanal nahe 255. Die Matrix dimmt ohnehin auf etwa 6 %, dunkle Töne verschwinden sonst.
7. Am Ende gehören dazu: Eintrag in `README.md` (Dateitabelle und Abschnitt „Anpassen“), Eintrag in `NAMES` in `tools/gui.py`, Vorschaubild unter `bilder/<name>.png`. Dann committen, pushen und die Demo auf dem Pico installieren.

## Ehrlich berichten

Der Benutzer sieht die Matrix, Claude nicht. Nie behaupten, etwas „sieht gut aus“ oder „funktioniert“, wenn nur die PC-Vorschau oder ein fehlerfreier Lauf geprüft wurde. Sagen, was geprüft wurde, und nachfragen, wie es auf der echten Matrix aussieht.

## Gehäuse: Stand

- Der Deckel ist nach dem ersten Druck um 1 cm vertieft, weil hinter den Matrizen Kabel liegen. Er hat nur noch Eckhalter (`corner_tabs`), Seitenmitten und Mitte bleiben frei.
- Der **LED-Abstand ist nicht 8 mm**, das Raster passte beim ersten Druck nicht. Der echte Wert ist noch offen. Den misst der Benutzer mit `lehre.stl` und trägt ihn dann in `pitch_x` und `pitch_y` ein.

## Git

Commits auf Deutsch, kurze Betreffzeile („Demo: …“, „Gehäuse: …“). Remote: privates GitHub-Repo `bonbon08/pico-ledmatrix`, Branch `main`.
