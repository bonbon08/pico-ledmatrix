// Gehäuse für 4x WS2812B 8x8-Matrizen (16x16) + Raspberry Pi Pico
// Teile: "front" = Rahmen mit Diffusor und Pixelraster, "deckel" = Rückteil mit Pico-Halter
// Alle Maße in mm. Koordinaten wie von vorne gesehen: x nach rechts, y nach oben.
// Matrix 1 = links oben, 2 = links unten, 3 = rechts oben, 4 = rechts unten.

teil = "beide";        // "front", "deckel", "beide" (nebeneinander), "explosion"

/* [Matrizen] */
board_x = 65;          // Breite einer Matrix
board_y = 67;          // Höhe einer Matrix
pitch_x = 8;           // LED-Abstand waagerecht (Mitte zu Mitte)
pitch_y = 8;           // LED-Abstand senkrecht
pcb_t   = 1.6;         // Leiterplattendicke (ohne LEDs)
gap     = 0;           // Spalt zwischen den Matrizen (0 = stoßen aneinander)
tol     = 0.3;         // Spiel rundherum zwischen Matrizen und Rahmen

/* [Front] */
diff_t    = 0.6;       // Diffusor vorne (0 = offen, z. B. für eigene Streuscheibe)
grid_h    = 8;         // Raster-Tiefe = Abstand LED-Platine bis Diffusor
grid_wall = 0.8;       // Wandstärke des Pixelrasters (2 Bahnen bei 0,4er Düse)
wall      = 7;         // Rahmenbreite außen
press     = 0.2;       // Rahmen so viel flacher -> Deckel drückt Platinen leicht an

/* [Deckel] */
plate    = 2;          // Bodenstärke Deckel
cav      = 28;         // Tiefe des Innenraums (Pico mit Dupont-Steckern + Kabelbogen)
lip      = 2.5;        // wie weit die Haltenasen über die Platinen greifen
tab_len  = 12;         // Länge der Haltenasen
pillar_d = 8;          // Stütze in der Mitte (wo sich die 4 Matrizen treffen), 0 = keine
keyholes = true;       // Schlüssellöcher zum Aufhängen

/* [Schrauben] */
screw_pilot = 2.6;     // Kernloch im Rahmen (M3 selbstschneidend)
screw_clear = 3.4;     // Durchgangsloch im Deckel

/* [Pico] */
// Der Pico liegt umgedreht: Bauteilseite zum Deckelboden, Stiftleisten zeigen zu den Matrizen.
pico_so    = 6;        // Abstand Deckelboden -> Pico-Platine (Platz für USB-Buchse und Taster)
pico_hole  = 1.8;      // Loch in den Abstandshaltern (M2 selbstschneidend)

$fn = 40;

// ---------- abgeleitete Maße ----------
arr_x   = 2 * board_x + gap;
arr_y   = 2 * board_y + gap;
inner_x = arr_x + 2 * tol;
inner_y = arr_y + 2 * tol;
outer_x = inner_x + 2 * wall;
outer_y = inner_y + 2 * wall;
fh      = diff_t + grid_h + pcb_t - press;   // Höhe Frontrahmen
lh      = plate + cav;                        // Höhe Deckel
ax      = wall + tol;                         // Anfang des Matrix-Feldes

// LED-Mittelpunkte entlang einer Achse (LEDs mittig auf dem Board angenommen)
function led(i, b, p) = ax + floor(i / 8) * (b + gap) + (b - 7 * p) / 2 + (i % 8) * p;
// Rasterwände jeweils mittig zwischen zwei LEDs
grid_x = [for (i = [0:14]) (led(i, board_x, pitch_x) + led(i + 1, board_x, pitch_x)) / 2];
grid_y = [for (i = [0:14]) (led(i, board_y, pitch_y) + led(i + 1, board_y, pitch_y)) / 2];

corners = [[wall/2, wall/2], [outer_x - wall/2, wall/2],
           [wall/2, outer_y - wall/2], [outer_x - wall/2, outer_y - wall/2]];

// ---------- Frontrahmen (mit der Sichtseite nach unten drucken) ----------
module front() {
    difference() {
        cube([outer_x, outer_y, fh]);
        translate([wall, wall, diff_t]) cube([inner_x, inner_y, fh]);
        for (c = corners) translate([c[0], c[1], diff_t + 1]) cylinder(d = screw_pilot, h = fh);
    }
    // Pixelraster
    for (p = grid_x) translate([p - grid_wall/2, wall, diff_t]) cube([grid_wall, inner_y, grid_h]);
    for (p = grid_y) translate([wall, p - grid_wall/2, diff_t]) cube([inner_x, grid_wall, grid_h]);
}

// ---------- Deckel (mit dem Boden nach unten drucken) ----------
// Von oben in den offenen Deckel geschaut sieht man ihn wie von vorne durch das Bild:
// links oben = hinter Matrix 1. Dort sitzt der Pico, USB geht links raus.
pico_x0 = wall + 1.5;                    // Pico-Kante mit USB-Buchse
pico_yc = outer_y - wall - 4 - 10.5;     // Mitte des Pico (21 mm breit)
pico_holes = [for (dx = [2, 49], dy = [-5.7, 5.7]) [pico_x0 + dx, pico_yc + dy]];
usb_z = plate + pico_so - 1.3;           // Mitte der USB-Buchse (hängt unter der Platine)

module tab_at(x, y, sx, sy) translate([x, y, 0]) cube([sx, sy, lh]);

module deckel() {
    d = lip + tol;
    difference() {
        union() {
            difference() {
                cube([outer_x, outer_y, lh]);
                translate([wall, wall, plate]) cube([inner_x, inner_y, lh]);
            }
            // Haltenasen an Ecken und Seitenmitten (Lötpads in den Kantenmitten bleiben frei).
            // Ecke links oben bleibt frei für das Eingangskabel von Matrix 1.
            for (px = [wall, outer_x/2 - tab_len/2, outer_x - wall - tab_len]) {
                tab_at(px, wall, tab_len, d);                                   // unten
                if (px != wall) tab_at(px, outer_y - wall - d, tab_len, d);     // oben
            }
            for (py = [wall, outer_y/2 - tab_len/2, outer_y - wall - tab_len]) {
                tab_at(outer_x - wall - d, py, d, tab_len);                     // rechts
                if (py != outer_y - wall - tab_len) tab_at(wall, py, d, tab_len); // links
            }
            // Mittelstütze
            if (pillar_d > 0) translate([outer_x/2, outer_y/2, 0]) cylinder(d = pillar_d, h = lh);
            // Pico-Abstandshalter
            for (h = pico_holes) translate([h[0], h[1], 0]) cylinder(d = 3.6, h = plate + pico_so);  // schmal, damit die USB-Buchse vorbeipasst
        }
        // Schraubenlöcher
        for (c = corners) translate([c[0], c[1], -1]) cylinder(d = screw_clear, h = lh + 2);
        // Pico-Löcher
        for (h = pico_holes) translate([h[0], h[1], 1]) cylinder(d = pico_hole, h = lh);
        // USB-Durchbruch links (Micro-USB-Stecker)
        translate([-1, pico_yc - 6, max(plate, usb_z - 5)]) cube([wall + 2, 12, 10]);
        // Schlüssellöcher zum Aufhängen
        if (keyholes) for (kx = [outer_x/2 - 40, outer_x/2 + 40])
            translate([kx, outer_y/2 + 15, -1]) {
                cylinder(d = 8, h = plate + 2);
                translate([-2, 0, 0]) cube([4, 8, plate + 2]);
                translate([0, 8, 0]) cylinder(d = 4, h = plate + 2);
            }
    }
}

// ---------- Ausgabe ----------
if (teil == "front") front();
else if (teil == "deckel") deckel();
else if (teil == "beide") { front(); translate([outer_x + 10, 0, 0]) deckel(); }
else if (teil == "explosion") {
    color("white") translate([0, 0, lh + 30 + fh]) mirror([0, 0, 1]) front();
    color("gray") deckel();
}

echo(str("Außenmaß: ", outer_x, " x ", outer_y, " mm, Gesamttiefe: ", fh + lh, " mm"));
echo(str("Schrauben: 4x M3, max. Länge ", lh + fh - diff_t - 1, " mm (selbstschneidend), Pico: 4x M2 x 6"));
