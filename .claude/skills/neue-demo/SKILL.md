---
name: neue-demo
description: Neue Animation/Demo für die 16x16-LED-Matrix bauen, von der Idee bis installiert und committet. Verwenden, wenn der Benutzer eine neue Demo, Animation oder ein neues Motiv für die Matrix möchte.
---

# Neue Demo für die LED-Matrix

Ziel: `$ARGUMENTS` als neue Demo in `demos/` – geprüft, schnell genug, dokumentiert, auf dem Pico installiert.

## 1. Planen
- In 2–4 Sätzen sagen, was zu sehen sein wird (Motiv, Bewegung, Farben). Bei Wünschen, die ein
  bestimmtes Spiel oder eine bekannte Figur nachbauen würden: eigene Version im Genre anbieten.
- Dateiname: kurz, deutsch, klein, ohne Umlaute (`demos/<name>.py`).

## 2. Schreiben
- Kopfkommentar `# Demo: <Name>. <Was passiert>` – daraus liest die GUI Name und Beschreibung.
- `import matrix as m`, einstellbare Konstanten in GROSSBUCHSTABEN oben mit Kommentar,
  `FRAME_MS` und Hauptschleife mit `time.sleep_ms(max(0, FRAME_MS - time.ticks_diff(...)))`.
- Stil der bestehenden Demos übernehmen (z. B. `demos/aquarium.py`, `demos/feuer.py`).

## 3. Vorschau auf dem PC
```bash
python tools/vorschau.py demos/<name>.py /tmp/<name>.png 30,90,200
```
Bild mit dem Read-Werkzeug ansehen. Form, Farben, Größen, Bewegung prüfen und so lange
verbessern, bis es stimmt. Für Spiele-KIs oder Simulationen zusätzlich auf dem PC viele Bilder
durchrechnen und Kennzahlen ausgeben (bleibt auf der Strecke, trifft, hängt nicht fest …).

## 4. Auf dem Pico messen
Kopie der Demo, deren Hauptschleife nach N Bildern endet und Durchschnitt und Maximum der
Bildzeit ausgibt, mit `uvx mpremote run` laufen lassen. Durchschnitt muss unter `FRAME_MS` liegen.
Zu langsam → vorberechneter Hintergrund (`m.buf[:] = BG`), viper-Schleifen, Tabellen statt
Fließkomma. Nach jeder Optimierung die Vorschau erneut rendern und mit der alten vergleichen
(`ImageChops.difference(...).getbbox() is None`).

## 5. Abschließen
1. `uvx mpremote cp matrix.py :matrix.py + cp demos/<name>.py :main.py + reset`
2. Vorschaubild nach `bilder/<name>.png` (3–5 aussagekräftige Bilder).
3. `README.md`: Zeile in der Dateitabelle (mit Vorschau-Link) und Punkt unter „Anpassen“.
4. `tools/gui.py`: Eintrag in `NAMES` (deutscher Name mit Umlauten, ein Satz Beschreibung).
   Braucht die Demo einen PC-Sender, auch in `SENDERS`.
5. Commit auf Deutsch („Demo: <Name>“), pushen.
6. Dem Benutzer sagen, was zu sehen sein sollte, was geprüft wurde (Vorschau, Bildzeit) und
   was nur er auf der echten Matrix beurteilen kann.
