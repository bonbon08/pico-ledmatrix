#!/usr/bin/env python3
"""LED-Matrix-Steuerung: Demos auswaehlen und auf den Pico laden, eigene Bilder und GIFs
umrechnen und hochladen.

Aufruf:  python tools/gui.py
Benoetigt: tkinter, Pillow, pyserial; mpremote (wird sonst ueber uvx gestartet);
fuer den Sound-Visualizer zusaetzlich numpy und parec.
"""
import queue
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageSequence, ImageTk
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parent.parent
DEMOS = ROOT / "demos"
BILDER = ROOT / "bilder"
MATRIX = ROOT / "matrix.py"
PLAYER = DEMOS / "_bild.py"
# Demos, zu denen auf dem PC ein Sender laufen muss
SENDERS = {"visualizer": ROOT / "tools" / "visualizer.py",
           "bongocat": ROOT / "tools" / "tastatur.py",
           "ente": ROOT / "tools" / "tastatur.py"}

N = 16
MAX_FRAMES = 400           # 768 Byte je Bild -> ca. 300 KB im Flash des Pico
CELL = 22                  # Pixelgroesse in der Vorschau


# Anzeigenamen und Beschreibungen (Reihenfolge = Reihenfolge in der Liste). Demos ohne Eintrag
# erscheinen trotzdem, dann mit dem Text aus ihrem Kopfkommentar ("# Demo: Name. Text").
NAMES = {
    "regenbogen": ("Regenbogen", "Regenbogen-Ringe, die von der Mitte nach außen laufen."),
    "feuer": ("Feuer", "Lagerfeuer mit Flammenzungen, Wind und aufsteigenden Funken."),
    "feuerwerk": ("Feuerwerk", "Raketen explodieren als Kugel, Ring, Goldregen oder Glitzer, mit leuchtenden Spuren."),
    "sternhimmel": ("Sternhimmel", "Funkelnde Sterne, eine Mondsichel und ab und zu eine Sternschnuppe."),
    "kirschbaum": ("Kirschblütenbaum", "Blauer Kirschblütenbaum bei Nacht, Blütenblätter trudeln im Wind herab."),
    "aquarium": ("Aquarium", "Fische, Seegras, eine Schatztruhe mit Luftblasen und Licht von der Wasseroberfläche."),
    "matrixcode": ("Matrix-Code", "Grüner Code-Regen mit flackernden Zeichen."),
    "uhr": ("Uhr", "Oben Stunden, unten Minuten, der Rand zeigt als Ring die Sekunden."),
    "visualizer": ("Sound-Visualizer", "16 Frequenzbalken zu dem Ton, der gerade auf dem PC läuft."),
    "bongocat": ("Bongo-Katze", "Haut bei jedem Tastendruck am PC auf ihre Tastatur. Ohne PC trommelt sie von selbst, nach 30 s Ruhe schläft sie ein."),
    "ente": ("Tipp-Ente", "Pickt bei jedem Tastendruck am PC mit dem Schnabel auf ihre Tastatur. Ohne PC pickt sie von selbst, nach 30 s Ruhe schläft sie ein."),
    "mampf": ("Mampf", "Ein runder Knubbel läuft über die Wiese, saugt herabfallendes Essen ein, kaut, rülpst Sterne und rennt nach einer Peperoni rot glühend herum."),
    "terminal": ("Terminal", "Altes Bernstein-Terminal: links tippt sich Text Zeile für Zeile, rechts drucken sich Pixel-Symbole und ein Pegel hüpft im Takt."),
    "oslogo": ("OS-Logo", "Das Logo des Betriebssystems dieses PCs, wie fastfetch es zeigt. Baut sich funkelnd auf, ein Glanzstreifen zieht darüber."),
    "elemente": ("Elemente", "Physik-Sandkasten: Sand rieselt, Wasser fließt, Lava wird an Wasser zu Stein und Dampf, Pflanzen wachsen und brennen ab."),
    "roboter": ("Roboter", "Kleiner Roboter, der schaut, blinzelt, winkt, tanzt, sich verliebt und einschläft."),
    "erdblock": ("Erdblock", "Rotierender 3D-Erdblock im Minecraft-Stil."),
    "kopfstein": ("Pflasterstein", "Pflastersteinblock im Minecraft-Stil, der um alle drei Achsen taumelt."),
    "tetris": ("Fallende Blöcke", "Zufällige Steine fallen und stapeln sich, volle Reihen verschwinden."),
    "snake": ("Snake", "Snake spielt von alleine und füllt meist das ganze Feld."),
    "gameoflife": ("Game of Life", "Conways Spiel des Lebens mit Überblenden und Farbe nach Zellalter."),
    "shooter": ("Ego-Shooter", "90er-Ego-Shooter, der sich selbst spielt: Labyrinth, Schleimmonster, Mündungsfeuer."),
    "rennen_oben": ("Rennen von oben", "Vier Autos fahren über eine Rennstrecke, die Kamera fährt mit. Start dauert ca. 4 s."),
    "rennen_hinten": ("Rennen von hinten", "Pseudo-3D-Rennen mit Kurven, Sonnenuntergang, Palmen und Überholen."),
}


def mpremote():
    exe = shutil.which("mpremote")
    return [exe] if exe else ["uvx", "mpremote"]


def find_demos():
    """Liest Name und Beschreibung aus dem Kopfkommentar jeder Demo ("# Demo: Name. Text")."""
    demos = []
    for path in sorted(DEMOS.glob("*.py")):
        if path.name.startswith("_"):
            continue
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("#"):
                break
            lines.append(line.lstrip("#").strip())
        text = " ".join(lines)
        if text.startswith("Demo:"):
            text = text[5:].strip()
        title, _, desc = text.partition(". ")
        preview = BILDER / f"{path.stem}.png"
        title, desc = NAMES.get(path.stem, (title.rstrip(".") or path.stem, desc))
        demos.append({"path": path, "title": title, "desc": desc,
                      "preview": preview if preview.exists() else None})
    order = list(NAMES)
    demos.sort(key=lambda d: order.index(d["path"].stem) if d["path"].stem in order else len(order))
    return demos


def convert(path, mode, boost, sharp, speed):
    """Bild oder GIF -> Liste von (Dauer in ms, 16x16-RGB-Bild)."""
    src = Image.open(path)
    resample = Image.NEAREST if sharp else Image.LANCZOS
    frames = []
    for fr in ImageSequence.Iterator(src):
        dur = fr.info.get("duration", 100) or 100
        img = fr.convert("RGBA")
        bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        img = Image.alpha_composite(bg, img).convert("RGB")
        if mode == "zuschneiden":
            img = ImageOps.fit(img, (N, N), method=resample)
        elif mode == "strecken":
            img = img.resize((N, N), resample)
        else:
            img.thumbnail((N, N), resample)
            canvas = Image.new("RGB", (N, N))
            canvas.paste(img, ((N - img.width) // 2, (N - img.height) // 2))
            img = canvas
        frames.append([max(20, int(dur / speed)), img])
        if len(frames) >= MAX_FRAMES:
            break
    if boost:
        # gemeinsamer Faktor fuer alle Bilder, damit ein GIF nicht flackert
        top = max(max(max(px) for px in f[1].getdata()) for f in frames)
        if 0 < top < 255:
            k = 255 / top
            for f in frames:
                f[1] = f[1].point(lambda v: min(255, int(v * k)))
    return frames, getattr(src, "n_frames", 1)


def pack(frames):
    out = bytearray(b"LEDB" + struct.pack("<H", len(frames)))
    for dur, img in frames:
        out += struct.pack("<H", min(dur, 65535)) + img.tobytes()
    return bytes(out)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LED-Matrix")
        self.geometry("900x640")
        self.minsize(760, 560)
        self.log_q = queue.Queue()
        self.busy = False
        self.sender = None          # laufender Visualizer-Sender
        self.frames = []
        self.anim = None
        self.demos = find_demos()

        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="Pico:").pack(side="left")
        self.port = tk.StringVar()
        self.port_box = ttk.Combobox(top, textvariable=self.port, width=28, state="readonly")
        self.port_box.pack(side="left", padx=6)
        ttk.Button(top, text="Suchen", command=self.refresh_ports).pack(side="left")
        ttk.Button(top, text="Matrix ausschalten", command=self.switch_off).pack(side="right")
        self.sender_btn = ttk.Button(top, text="PC-Sender stoppen", command=self.stop_sender,
                                     state="disabled")
        self.sender_btn.pack(side="right", padx=6)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10)
        nb.add(self.build_demo_tab(nb), text="Demos")
        nb.add(self.build_image_tab(nb), text="Eigenes Bild / GIF")

        bottom = ttk.Frame(self, padding=(10, 6))
        bottom.pack(fill="x")
        self.status = tk.StringVar(value="Bereit")
        ttk.Label(bottom, textvariable=self.status).pack(anchor="w")
        self.log = tk.Text(bottom, height=7, state="disabled", font=("monospace", 9))
        self.log.pack(fill="x", pady=(4, 0))

        self.refresh_ports()
        self.after(100, self.pump_log)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- Demos ----------
    def build_demo_tab(self, parent):
        f = ttk.Frame(parent, padding=10)
        self.demo_list = tk.Listbox(f, width=28, activestyle="none", exportselection=False)
        for d in self.demos:
            self.demo_list.insert("end", d["title"])
        self.demo_list.pack(side="left", fill="y")
        self.demo_list.bind("<<ListboxSelect>>", lambda e: self.show_demo())
        self.demo_list.bind("<Double-Button-1>", lambda e: self.upload_demo())
        right = ttk.Frame(f, padding=(12, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)
        self.demo_title = ttk.Label(right, font=("TkDefaultFont", 14, "bold"))
        self.demo_title.pack(anchor="w")
        self.demo_img = ttk.Label(right)
        self.demo_img.pack(anchor="w", pady=8)
        self.demo_desc = ttk.Label(right, wraplength=520, justify="left")
        self.demo_desc.pack(anchor="w")
        self.demo_btn = ttk.Button(right, text="Auf die Matrix laden", command=self.upload_demo)
        self.demo_btn.pack(anchor="w", pady=12)
        if self.demos:
            self.demo_list.selection_set(0)
            self.after(50, self.show_demo)
        return f

    def selected_demo(self):
        sel = self.demo_list.curselection()
        return self.demos[sel[0]] if sel else None

    def show_demo(self):
        d = self.selected_demo()
        if not d:
            return
        self.demo_title.config(text=d["title"])
        extra = ""
        if d["path"].stem == "uhr":
            extra = "\n\nDie Uhrzeit wird beim Hochladen vom PC übernommen."
        elif d["path"].stem == "visualizer":
            extra = "\n\nNach dem Hochladen startet die GUI das Senden des PC-Tons automatisch."
        elif d["path"].stem == "oslogo":
            extra = "\n\nBeim Hochladen wird das Logo mit fastfetch von diesem PC geholt und mitgeschickt."
        elif d["path"].stem in ("bongocat", "ente"):
            extra = ("\n\nNach dem Hochladen meldet die GUI jeden Tastendruck an den Pico (nur dass, nie welche "
                     "Taste). Dafür muss dein Benutzer in der Gruppe „input“ sein: "
                     "sudo usermod -aG input $USER, danach ab- und wieder anmelden.")
        self.demo_desc.config(text=d["desc"] + extra)
        if d["preview"]:
            img = Image.open(d["preview"])
            img.thumbnail((560, 200))
            self.demo_photo = ImageTk.PhotoImage(img)
            self.demo_img.config(image=self.demo_photo, text="")
        else:
            self.demo_img.config(image="", text="(keine Vorschau)")

    def upload_demo(self):
        d = self.selected_demo()
        if not d or not self.check_ready():
            return
        stem = d["path"].stem
        cmd = ["cp", str(MATRIX), ":matrix.py", "+", "cp", str(d["path"]), ":main.py", "+"]
        if stem == "oslogo":
            logo = Path(tempfile.mkdtemp(prefix="ledmatrix-")) / "oslogo.bin"
            r = subprocess.run([sys.executable, str(ROOT / "tools" / "oslogo.py"), "--out", str(logo)],
                               capture_output=True, text=True)
            if r.returncode:
                messagebox.showerror("OS-Logo", r.stderr.strip() or r.stdout.strip())
                return
            cmd += ["cp", str(logo), ":oslogo.bin", "+"]
        if stem == "uhr":
            # kein Reset, der wuerde die gerade gesetzte Uhrzeit wieder loeschen
            cmd += ["rtc", "--set", "+", "exec", "--no-follow", "import main"]
        else:
            cmd += ["reset"]
        after = (lambda: self.start_sender(SENDERS[stem])) if stem in SENDERS else None
        self.run(cmd, f"Lade „{d['title']}“ …", f"„{d['title']}“ läuft", after)

    # ---------- Eigenes Bild ----------
    def build_image_tab(self, parent):
        f = ttk.Frame(parent, padding=10)
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        ttk.Button(left, text="Bild oder GIF öffnen …", command=self.open_image).pack(anchor="w")
        self.img_info = ttk.Label(left, text="Noch keine Datei gewählt", wraplength=300)
        self.img_info.pack(anchor="w", pady=(6, 12))

        ttk.Label(left, text="Anpassen an 16 × 16:").pack(anchor="w")
        self.fit = tk.StringVar(value="einpassen")
        for val, txt in (("einpassen", "Einpassen (schwarze Ränder)"),
                         ("zuschneiden", "Zuschneiden (füllt alles)"),
                         ("strecken", "Strecken")):
            ttk.Radiobutton(left, text=txt, value=val, variable=self.fit,
                            command=self.reconvert).pack(anchor="w")
        self.boost = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="Helligkeit anheben", variable=self.boost,
                        command=self.reconvert).pack(anchor="w", pady=(10, 0))
        self.sharp = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Scharf skalieren (für Pixel-Art)", variable=self.sharp,
                        command=self.reconvert).pack(anchor="w")
        ttk.Label(left, text="GIF-Tempo:").pack(anchor="w", pady=(10, 0))
        self.speed = tk.DoubleVar(value=1.0)
        sp = ttk.Frame(left)
        sp.pack(anchor="w", fill="x")
        ttk.Scale(sp, from_=0.25, to=3.0, variable=self.speed,
                  command=lambda v: self.speed_lbl.config(text=f"{float(v):.2f}×")).pack(side="left", fill="x", expand=True)
        self.speed_lbl = ttk.Label(sp, text="1.00×", width=6)
        self.speed_lbl.pack(side="left")
        ttk.Button(left, text="Tempo übernehmen", command=self.reconvert).pack(anchor="w", pady=(4, 0))
        self.img_btn = ttk.Button(left, text="Auf die Matrix laden", command=self.upload_image,
                                  state="disabled")
        self.img_btn.pack(anchor="w", pady=16)

        size = N * CELL
        self.canvas = tk.Canvas(f, width=size, height=size, bg="#111", highlightthickness=0)
        self.canvas.pack(side="left", padx=24, anchor="n")
        self.cells = [[self.canvas.create_rectangle(x * CELL + 1, y * CELL + 1, x * CELL + CELL - 1,
                                                    y * CELL + CELL - 1, fill="#000", width=0)
                       for x in range(N)] for y in range(N)]
        self.img_path = None
        return f

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Bild oder GIF wählen",
            filetypes=[("Bilder", "*.png *.gif *.jpg *.jpeg *.bmp *.webp"), ("Alle Dateien", "*")])
        if not path:
            return
        self.img_path = Path(path)
        try:
            with Image.open(path) as im:
                small = max(im.size) <= 32
        except Exception as e:
            messagebox.showerror("Datei", f"Kann die Datei nicht öffnen:\n{e}")
            return
        self.sharp.set(small)       # kleine Bilder sind meist Pixel-Art
        self.reconvert()

    def reconvert(self):
        if not self.img_path:
            return
        try:
            self.frames, total = convert(self.img_path, self.fit.get(), self.boost.get(),
                                         self.sharp.get(), self.speed.get())
        except Exception as e:
            messagebox.showerror("Umrechnen", f"Fehler beim Umrechnen:\n{e}")
            return
        n = len(self.frames)
        info = f"{self.img_path.name}\n{n} Bild" + ("er" if n != 1 else "")
        if total > n:
            info += f" (von {total}, gekürzt auf {MAX_FRAMES})"
        if n > 1:
            info += f", {sum(d for d, _ in self.frames) / 1000:.1f} s"
        self.img_info.config(text=info)
        self.img_btn.config(state="normal")
        self.anim_i = 0
        if self.anim:
            self.after_cancel(self.anim)
        self.animate()

    def animate(self):
        if not self.frames:
            return
        dur, img = self.frames[self.anim_i % len(self.frames)]
        px = img.load()
        for y in range(N):
            for x in range(N):
                self.canvas.itemconfig(self.cells[y][x], fill="#%02x%02x%02x" % px[x, y])
        self.anim_i += 1
        self.anim = self.after(dur, self.animate) if len(self.frames) > 1 else None

    def upload_image(self):
        if not self.frames or not self.check_ready():
            return
        tmp = Path(tempfile.mkdtemp(prefix="ledmatrix-")) / "bild.bin"
        tmp.write_bytes(pack(self.frames))
        cmd = ["cp", str(MATRIX), ":matrix.py", "+", "cp", str(tmp), ":bild.bin", "+",
               "cp", str(PLAYER), ":main.py", "+", "reset"]
        kb = tmp.stat().st_size / 1024
        self.run(cmd, f"Lade {self.img_path.name} ({kb:.0f} KB) …", f"{self.img_path.name} läuft")

    # ---------- Ausfuehren ----------
    def check_ready(self):
        if self.busy:
            return False
        if not self.port.get():
            self.refresh_ports()
            if not self.port.get():
                messagebox.showwarning("Pico", "Kein Pico gefunden. Ist er eingesteckt?")
                return False
        return True

    def run(self, args, status, done, after=None):
        self.stop_sender()
        self.busy = True
        self.set_buttons("disabled")
        self.status.set(status)
        cmd = mpremote() + ["connect", self.port_device()] + args

        def work():
            self.log_q.put("$ " + " ".join(cmd[:3]) + " …")
            ok = False
            for attempt in range(5):
                try:
                    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                except Exception as e:
                    self.log_q.put(f"Fehler: {e}")
                    break
                out = (p.stdout + p.stderr).strip()
                if p.returncode != 0 and "failed to access" in out and attempt < 4:
                    # Pico meldet sich nach einem Reset gerade neu an -> kurz warten
                    self.log_q.put("Pico noch nicht bereit, neuer Versuch …")
                    time.sleep(1.5)
                    continue
                if out:
                    self.log_q.put(out)
                ok = p.returncode == 0
                break
            self.log_q.put(("fertig", ok, done, after))

        threading.Thread(target=work, daemon=True).start()

    def pump_log(self):
        while not self.log_q.empty():
            item = self.log_q.get()
            if isinstance(item, tuple):
                _, ok, done, after = item
                self.busy = False
                self.set_buttons("normal")
                self.status.set(done if ok else "Fehlgeschlagen, Details im Protokoll")
                if ok and after:
                    after()
                continue
            self.log.config(state="normal")
            self.log.insert("end", item + "\n")
            self.log.see("end")
            self.log.config(state="disabled")
        self.after(100, self.pump_log)

    def set_buttons(self, state):
        self.demo_btn.config(state=state)
        if self.frames:
            self.img_btn.config(state=state)

    def refresh_ports(self):
        # nur USB-Geraete, der Pico (Raspberry Pi, VID 2E8A) zuerst
        ports = sorted((p for p in list_ports.comports() if p.vid), key=lambda p: p.vid != 0x2E8A)
        self.port_map = {f"{p.device}  {p.description}": p.device for p in ports}
        names = list(self.port_map)
        self.port_box["values"] = names
        self.port.set(names[0] if names else "")

    def port_device(self):
        return self.port_map.get(self.port.get(), self.port.get())

    def switch_off(self):
        if not self.check_ready():
            return
        code = ("import os, matrix\nmatrix.clear()\nmatrix.show()\n"
                "try:\n    os.remove('main.py')\nexcept OSError:\n    pass")
        self.run(["exec", code], "Schalte aus …", "Matrix aus (startet beim Einstecken nichts mehr)")

    # ---------- PC-Sender (Sound-Visualizer, Bongo-Katze) ----------
    def start_sender(self, script):
        port = self.port_device()   # Tk-Variablen nur im Haupt-Thread lesen

        def go():
            # der Pico meldet sich nach dem Reset kurz neu an
            time.sleep(1.5)
            t = time.time()
            while not Path(port).exists() and time.time() - t < 10:
                time.sleep(0.3)
            time.sleep(1.0)
            self.sender = subprocess.Popen([sys.executable, "-u", str(script), "--port", port],
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.log_q.put(f"PC-Sender {script.name} gestartet")
            for line in self.sender.stdout:
                self.log_q.put(line.rstrip())
        threading.Thread(target=go, daemon=True).start()
        self.sender_btn.config(state="normal")

    def stop_sender(self):
        if self.sender and self.sender.poll() is None:
            self.sender.terminate()
            try:
                self.sender.wait(3)
            except subprocess.TimeoutExpired:
                self.sender.kill()
            self.log_q.put("PC-Sender gestoppt")
        self.sender = None
        self.sender_btn.config(state="disabled")

    def on_close(self):
        self.stop_sender()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
