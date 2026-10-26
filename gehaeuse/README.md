# Gehäuse zum 3D-Drucken

Gehäuse für die vier Matrizen und den Pico, parametrisch in OpenSCAD (`gehaeuse.scad`).
Die vier Matrizen liegen stumpf aneinander. Davor sitzt ein Pixelraster mit 16×16 Zellen und ein dünner Diffusor, so ergibt sich ein durchgehendes Bild.

> **Stand nach dem ersten Druck:**
> - **Halter:** Die Halter im Deckel stießen gegen die Kabel hinter den Matrizen. Der Deckel ist jetzt 1 cm tiefer, statt Haltenasen an den Seitenmitten und einer Mittelstütze gibt es nur noch kleine Eckhalter.
> - **LED-Abstand:** Das Raster passte nicht, ab der Hälfte jeder Matrix lagen die LEDs neben den Löchern. Der LED-Abstand ist also nicht 8 mm. **Vor dem nächsten Druck des Frontrahmens bitte mit der Messlehre (`lehre.stl`) ausmessen** und `pitch_x` / `pitch_y` eintragen.

| Front (Raster) | Deckel (innen) |
|---|---|
| ![Front](bilder/front.png) | ![Deckel](bilder/deckel.png) |

## Aufbau, von vorne nach hinten

1. **Frontrahmen** (`front.stl`)
   - 0,6 mm Diffusor als Sichtfläche
   - dahinter das Pixelraster: 8 mm tief, 0,8 mm dicke Wände
   - Die Rasterwände sitzen jeweils mittig zwischen zwei LEDs und damit auch genau auf den Stoßkanten der Matrizen.
2. **Die 4 Matrizen**
   - liegen mit den LEDs zum Raster
   - Anordnung von vorne gesehen: 1 links oben, 2 links unten, 3 rechts oben, 4 rechts unten
3. **Deckel** (`deckel.stl`)
   - 38 mm Innenraum, genug Platz für die Kabel hinter den Matrizen (ca. 1 cm)
   - Kleine L-förmige Eckhalter drücken die Platinen an den äußeren Ecken ans Raster. In den Seitenmitten und in der Mitte laufen die Kabel zwischen den Matrizen, dort ist nichts.
   - Die Ecke links oben ist frei für das Eingangskabel von Matrix 1. Welche Ecken Halter bekommen, steht in `corner_tabs`.
   - Zwei Schlüssellöcher zum Aufhängen

**Pico:**
- sitzt links oben hinter Matrix 1, also nah am Eingangskabel
- liegt **umgedreht** auf 4 Abstandshaltern (6 mm): Die Bauteilseite zeigt zum Deckelboden, die nach unten angelöteten Stiftleisten zeigen zu den Matrizen.
- Die Dupont-Stecker haben dadurch nach oben Platz.
- Die Micro-USB-Buchse liegt in einem Durchbruch in der linken Wand.

## Maße (Standardwerte)

| | |
|---|---|
| Außenmaß | 148,6 × 152,6 mm |
| Tiefe | 50 mm (10 mm Front + 40 mm Deckel) |
| Matrix | 65 mm breit × 67 mm hoch, Platine ca. 3 mm mit LEDs |

## Material

- 4 × M3×16, selbstschneidend. Sie werden von hinten in die Deckelecken gesteckt, die Köpfe sitzen versenkt, und greifen in den Rahmen. Höchstens 17 mm lang, sonst drücken sie vorne durch.
- 4 × M2×6, selbstschneidend, für den Pico. Sie werden von der Pin-Seite durch die Pico-Löcher in die Abstandshalter gedreht.

## LED-Abstand ausmessen (Messlehre)

`lehre.stl` ist eine 1 mm dünne Platte mit sechs Lochreihen zu je 8 Löchern. Die Reihen haben die Abstände 8,0 bis 8,5 mm, jede ist mit ihrem Wert beschriftet. Der Druck dauert etwa 10 Minuten.

1. Die Lehre waagerecht auf eine Matrix legen, so dass die erste LED einer Zeile im ersten Loch einer Reihe sitzt.
2. Die Reihe suchen, in der alle 8 LEDs mittig in ihren Löchern sitzen. Ihr Wert kommt in `pitch_x`.
3. Das Gleiche senkrecht für `pitch_y`.
4. Danach `front.stl` neu erzeugen.

```bash
openscad -o lehre.stl -D 'teil="lehre"' gehaeuse.scad
```

## Drucken

| Teil | Lage | Hinweise |
|---|---|---|
| `front.stl` | Sichtseite nach unten | Die ersten 0,6 mm in **Weiß** drucken, dann Filamentwechsel auf **Schwarz** (M600 auf 0,6 mm Höhe). Dann leuchtet keine Zelle in die Nachbarzelle. 0,2 mm Schichthöhe, keine Stützen. |
| `deckel.stl` | Boden nach unten | Keine Stützen nötig. Der USB-Durchbruch überbrückt 12 mm. |

Den Diffusor kann man auch weglassen (`diff_t = 0`) und stattdessen eine Streuscheibe davorsetzen, z. B. aus satiniertem Acryl oder Transparentpapier.

## Zusammenbau

1. Den Frontrahmen mit der Sichtseite nach unten hinlegen.
2. Die Matrizen mit den LEDs nach unten einlegen. Matrix 1 kommt dabei, von vorne gesehen, nach links oben. Weil der Rahmen umgedreht liegt, ist das jetzt **rechts oben**.
3. Den Pico in den Deckel schrauben, das LED-Kabel aufstecken und den Deckel aufsetzen.
4. Mit den 4 M3-Schrauben verschrauben.

## Anpassen

Alle Maße stehen oben in `gehaeuse.scad`. Die wichtigsten:

- `board_x`, `board_y`, `pitch_x`, `pitch_y`: Maße der Matrix und LED-Abstand. Bitte nachmessen.
- `grid_h`: Raster-Tiefe. Höher heißt weichere, gleichmäßigere Pixel.
- `cav`: Tiefe des Innenraums.
- `corner_tabs`: Ecken mit Haltern (`"lo"`, `"ro"`, `"lu"`, `"ru"`).
- `tol`: Spiel um die Matrizen, falls sie zu stramm oder zu locker sitzen.

STL neu erzeugen:

```bash
openscad -o front.stl  -D 'teil="front"'  gehaeuse.scad
openscad -o deckel.stl -D 'teil="deckel"' gehaeuse.scad
```

## Offene Punkte

- **LED-Abstand:** noch nicht gemessen, siehe Messlehre oben. Die Rasterwände sitzen immer mittig zwischen zwei LEDs, auch an den Nähten zwischen den Matrizen.
  Das setzt voraus, dass die LEDs mittig auf dem Board sitzen. Falls nicht, bitte den Abstand vom Board-Rand zur ersten LED messen.
- **Pico-Maße:** Die Maße kommen aus dem Datenblatt (51 × 21 mm, Löcher 47 × 11,4 mm). Die Lage der USB-Buchse ist geschätzt.
