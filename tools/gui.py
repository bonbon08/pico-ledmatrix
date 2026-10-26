#!/usr/bin/env python3
"""LED-Matrix-Steuerung: alles an einem Ort.

- Demos: Live-Vorschau auf dem PC, auf die Matrix laden, PC-Sender starten sich von selbst
- Bild / GIF: eigene Bilder und GIFs umrechnen und hochladen
- Video & Bildschirm: Videodatei, Link oder den Bildschirm live auf die Matrix streamen
- OS-Logo: Logo (wie bei fastfetch) waehlen, Kontrast einstellen, hochladen
- Werkzeuge: Testbild, Uhr stellen, Audioquelle, Tastatur-Rechte, Dateien auf dem Pico,
  Eintrag im Startmenue (startet ueber tools/starten.sh und holt vorher die neueste Version)

Die Sender (tools/visualizer.py, tastatur.py, video.py, bildschirm.py) bleiben eigene Programme
und laufen auch ohne GUI; die GUI startet sie mit den eingestellten Optionen.

Aufruf:  python tools/gui.py
Benoetigt: tkinter, Pillow, pyserial; mpremote (wird sonst ueber uvx gestartet);
je nach Funktion numpy + parec (Visualizer), ffmpeg (Video), fastfetch (OS-Logo),
python-gobject + gst-plugin-pipewire (Bildschirm unter Wayland).
"""
import os
import queue
import re
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

from PIL import Image, ImageOps, ImageSequence
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
DEMOS = ROOT / "demos"
BILDER = ROOT / "bilder"
MATRIX = ROOT / "matrix.py"
PLAYER = DEMOS / "_bild.py"
sys.path.insert(0, str(TOOLS))

# Demos, zu denen auf dem PC ein Sender laufen muss
SENDERS = {"visualizer": TOOLS / "visualizer.py",
           "bongocat": TOOLS / "tastatur.py",
           "ente": TOOLS / "tastatur.py"}
KEYBOARD_DEMOS = ("bongocat", "ente")

N = 16
MAX_FRAMES = 400           # 768 Byte je Bild -> ca. 300 KB im Flash des Pico

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
    "ente": ("Tipp-Ente", "Pickt bei jedem Tastendruck am PC mit dem Schnabel auf ihre Tastatur, je nach Tastaturreihe auf eine andere Taste, gehaltene Tasten hält sie gedrückt. Ohne PC pickt sie von selbst, nach 30 s Ruhe schläft sie ein."),
    "mampf": ("Mampf", "Ein runder Knubbel läuft über die Wiese, saugt herabfallendes Essen ein, kaut, rülpst Sterne und rennt nach einer Peperoni rot glühend herum."),
    "terminal": ("Terminal", "Altes Bernstein-Terminal: links tippt sich Text Zeile für Zeile, rechts drucken sich Pixel-Symbole und ein Pegel hüpft im Takt."),
    "oslogo": ("OS-Logo", "Das Logo des Betriebssystems, wie fastfetch es zeigt. Baut sich funkelnd auf, ein Glanzstreifen zieht darüber."),
    "elemente": ("Elemente", "Physik-Sandkasten: Sand rieselt, Wasser fließt, Lava wird an Wasser zu Stein und Dampf, Pflanzen wachsen und brennen ab."),
    "kikern": ("KI-Kern", "Rotierende 3D-Panzerkugel mit leuchtendem Auge und kreisendem Ring. Ab und zu hält sie an und starrt dich mit rotem Auge an."),
    "video": ("Video & Bildschirm", "Zeigt ein Video oder live den Bildschirm des PCs auf der Matrix, bis zu 50 Bilder pro Sekunde."),
    "roboter": ("Roboter", "Kleiner Roboter, der schaut, blinzelt, winkt, tanzt, sich verliebt und einschläft."),
    "erdblock": ("Erdblock", "Rotierender 3D-Erdblock im Minecraft-Stil."),
    "kopfstein": ("Pflasterstein", "Pflastersteinblock im Minecraft-Stil, der um alle drei Achsen taumelt."),
    "bloecke": ("Fallende Blöcke", "Zufällige Steine fallen und stapeln sich, volle Reihen verschwinden."),
    "snake": ("Snake", "Snake spielt von alleine und füllt meist das ganze Feld."),
    "gameoflife": ("Game of Life", "Conways Spiel des Lebens mit Überblenden und Farbe nach Zellalter."),
    "shooter": ("Ego-Shooter", "90er-Ego-Shooter, der sich selbst spielt: Labyrinth, Schleimmonster, Mündungsfeuer."),
    "rennen_oben": ("Rennen von oben", "Vier Autos fahren über eine Rennstrecke, die Kamera fährt mit. Start dauert ca. 4 s."),
    "rennen_hinten": ("Rennen von hinten", "Pseudo-3D-Rennen mit Kurven, Sonnenuntergang, Palmen und Überholen."),
}

# Hinweise je Demo unter der Beschreibung
HINTS = {
    "uhr": "Die Uhrzeit wird beim Hochladen vom PC übernommen (der Pico hat keine Batterie für die Uhr).",
    "visualizer": "Nach dem Hochladen startet der Ton-Sender von selbst. Die Audioquelle stellst du unter „Werkzeuge“ ein.",
    "oslogo": "Beim Hochladen wird das Logo aus dem Reiter „OS-Logo“ mitgeschickt (Standard: dieser PC).",
    "video": "Videos und den Bildschirm startest du im Reiter „Video & Bildschirm“.",
}

# Farben der Oberflaeche
BG = "#16181d"
PANEL = "#1f2229"
FIELD = "#2a2e37"
FG = "#e6e6e6"
DIM = "#9aa0aa"
ACCENT = "#ff9f1c"
OK = "#3ecf6e"
BAD = "#e5484d"


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
        title, desc = NAMES.get(path.stem, (title.rstrip(".") or path.stem, desc))
        demos.append({"path": path, "stem": path.stem, "title": title, "desc": desc})
    order = list(NAMES)
    demos.sort(key=lambda d: order.index(d["stem"]) if d["stem"] in order else len(order))
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
        top = max(max(f[1].getextrema(), key=lambda e: e[1])[1] for f in frames)
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


def keyboard_access():
    """(gefunden, lesbar): Tastaturen fuer die Bongo-Katze/Ente und ob der Benutzer sie lesen darf."""
    try:
        import tastatur
        paths = tastatur.keyboards()
    except Exception:
        return 0, 0
    return len(paths), sum(os.access(p, os.R_OK) for p in paths)


def audio_sources():
    try:
        out = subprocess.run(["pactl", "list", "sources", "short"], capture_output=True, text=True,
                             timeout=3).stdout
    except Exception:
        return []
    return [line.split("\t")[1] for line in out.splitlines() if "\t" in line]


class LedView(tk.Canvas):
    """16x16 runde LEDs; zeigt Bilder als 768 Byte RGB (zeilenweise) oder PIL-Bild."""

    def __init__(self, parent, cell=18):
        size = N * cell + 8
        super().__init__(parent, width=size, height=size, bg="#050505", highlightthickness=1,
                         highlightbackground="#333")
        self.leds = [self.create_oval(4 + x * cell + 2, 4 + y * cell + 2, 4 + x * cell + cell - 2,
                                      4 + y * cell + cell - 2, fill="#101010", width=0)
                     for y in range(N) for x in range(N)]
        self.last = None

    def show(self, data):
        if isinstance(data, Image.Image):
            data = data.convert("RGB").tobytes()
        if data == self.last:
            return
        self.last = data
        for i, item in enumerate(self.leds):
            r, g, b = data[i * 3:i * 3 + 3]
            # ganz dunkle LEDs leicht sichtbar lassen, damit das Raster erkennbar bleibt
            self.itemconfig(item, fill="#%02x%02x%02x" % (max(r, 16), max(g, 16), max(b, 16)))

    def clear(self):
        self.show(bytes(N * N * 3))


class LivePreview:
    """Laesst eine Demo auf dem PC laufen (tools/vorschau.py --live) und liefert das neueste Bild."""

    def __init__(self):
        self.proc = None
        self.frame = None
        self.lock = threading.Lock()

    def start(self, demo):
        self.stop()
        self.proc = subprocess.Popen([sys.executable, str(TOOLS / "vorschau.py"), str(demo), "--live"],
                                     stdout=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, cwd=ROOT)
        proc = self.proc
        threading.Thread(target=self.read, args=(proc,), daemon=True).start()

    def read(self, proc):
        size = N * N * 3
        while True:
            data = proc.stdout.read(size)
            if not data or len(data) < size:
                return
            with self.lock:
                if proc is self.proc:
                    self.frame = data

    def take(self):
        with self.lock:
            f, self.frame = self.frame, None
        return f

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.proc = None
        self.frame = None


class App(tk.Tk):
    def __init__(self):
        super().__init__(className="ledmatrix")       # Fensterklasse "Ledmatrix", passt zum Startmenue-Eintrag
        self.title("LED-Matrix")
        try:
            self.iconphoto(True, tk.PhotoImage(file=str(TOOLS / "symbol.png")))
        except tk.TclError:
            pass
        self.geometry("1060x800")
        self.minsize(900, 660)
        self.configure(bg=BG)
        self.style()
        self.log_q = queue.Queue()
        self.busy = False
        self.sender = None          # laufender PC-Sender
        self.sender_name = ""
        self.current = None         # was gerade auf der Matrix laeuft (soweit bekannt)
        self.frames = []
        self.anim = None
        self.demos = find_demos()
        self.preview = LivePreview()
        self.action_buttons = []

        self.build_top()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(4, 0))
        self.nb.add(self.build_demo_tab(), text="  Demos  ")
        self.nb.add(self.build_image_tab(), text="  Bild / GIF  ")
        self.nb.add(self.build_stream_tab(), text="  Video & Bildschirm  ")
        self.nb.add(self.build_logo_tab(), text="  OS-Logo  ")
        self.nb.add(self.build_tools_tab(), text="  Werkzeuge  ")
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.tab_changed())
        self.build_bottom()

        if os.environ.get("LEDMATRIX_UPDATE"):          # vom Startmenue-Starter
            self.log_q.put(os.environ["LEDMATRIX_UPDATE"])
        self.refresh_ports()
        self.after(100, self.pump_log)
        self.after(40, self.pump_preview)
        self.after(2000, self.watch_ports)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- Aussehen ----------
    def style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        base = ("TkDefaultFont", 10)
        s.configure(".", background=BG, foreground=FG, fieldbackground=FIELD, bordercolor="#333",
                    lightcolor=PANEL, darkcolor=PANEL, troughcolor=FIELD, font=base,
                    selectbackground=ACCENT, selectforeground="#111", insertcolor=FG)
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("Panel.TLabel", background=PANEL)
        s.configure("Dim.TLabel", foreground=DIM)
        s.configure("PanelDim.TLabel", background=PANEL, foreground=DIM)
        s.configure("Title.TLabel", font=("TkDefaultFont", 16, "bold"))
        s.configure("Hint.TLabel", background=PANEL, foreground=ACCENT)
        s.configure("TLabelframe", background=BG, bordercolor="#333")
        s.configure("TLabelframe.Label", background=BG, foreground=ACCENT, font=("TkDefaultFont", 10, "bold"))
        s.configure("TButton", background=FIELD, foreground=FG, padding=(10, 5), borderwidth=0)
        s.map("TButton", background=[("disabled", PANEL), ("active", "#3a3f4b")],
              foreground=[("disabled", "#555")])
        s.configure("Accent.TButton", background=ACCENT, foreground="#111", font=("TkDefaultFont", 10, "bold"))
        s.map("Accent.TButton", background=[("disabled", "#4a3f2c"), ("active", "#ffb54d")],
              foreground=[("disabled", "#9a8a6a")])
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 4, 0, 0))
        s.configure("TNotebook.Tab", background=PANEL, foreground=DIM, padding=(10, 6), borderwidth=0)
        s.map("TNotebook.Tab", background=[("selected", FIELD)], foreground=[("selected", ACCENT)])
        for w in ("TCheckbutton", "TRadiobutton"):
            s.configure(w, background=BG, foreground=FG, indicatorbackground=FIELD, indicatorforeground=ACCENT)
            s.map(w, background=[("active", BG)], indicatorbackground=[("selected", ACCENT)])
        s.configure("TCombobox", arrowcolor=FG, background=FIELD, foreground=FG)
        s.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", FG)])
        s.configure("TEntry", foreground=FG)
        s.configure("Horizontal.TScale", background=ACCENT, troughcolor=FIELD, bordercolor=BG,
                    lightcolor=ACCENT, darkcolor=ACCENT, gripcount=0, sliderthickness=14)
        self.option_add("*TCombobox*Listbox.background", FIELD)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)

    def build_top(self):
        top = ttk.Frame(self, style="Panel.TFrame", padding=(12, 8))
        top.pack(fill="x")
        self.dot = tk.Canvas(top, width=14, height=14, bg=PANEL, highlightthickness=0)
        self.dot_item = self.dot.create_oval(2, 2, 12, 12, fill=BAD, width=0)
        self.dot.pack(side="left")
        ttk.Label(top, text="Pico:", style="Panel.TLabel").pack(side="left", padx=(6, 4))
        self.port = tk.StringVar()
        self.port_box = ttk.Combobox(top, textvariable=self.port, width=30, state="readonly")
        self.port_box.pack(side="left")
        ttk.Button(top, text="Suchen", command=self.refresh_ports).pack(side="left", padx=6)
        self.now_lbl = ttk.Label(top, text="", style="PanelDim.TLabel")
        self.now_lbl.pack(side="left", padx=12)
        ttk.Button(top, text="Matrix aus", command=self.switch_off).pack(side="right")
        self.sender_btn = ttk.Button(top, text="Sender stoppen", command=self.stop_sender, state="disabled")
        self.sender_btn.pack(side="right", padx=6)
        self.sender_lbl = ttk.Label(top, text="", style="PanelDim.TLabel")
        self.sender_lbl.pack(side="right", padx=6)

    def build_bottom(self):
        bottom = ttk.Frame(self, padding=(12, 6))
        bottom.pack(fill="x")
        row = ttk.Frame(bottom)
        row.pack(fill="x")
        self.status = tk.StringVar(value="Bereit")
        ttk.Label(row, textvariable=self.status).pack(side="left")
        self.show_log = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text="Protokoll", variable=self.show_log,
                        command=lambda: self.log.pack(fill="x", pady=(4, 0)) if self.show_log.get()
                        else self.log.pack_forget()).pack(side="right")
        self.log = tk.Text(bottom, height=5, state="disabled", font=("monospace", 9), bg="#0e0f12",
                           fg=DIM, insertbackground=FG, relief="flat", highlightthickness=0)
        self.log.pack(fill="x", pady=(4, 0))

    def action(self, btn):
        """Knopf, der waehrend mpremote laeuft gesperrt wird."""
        self.action_buttons.append(btn)
        return btn

    # ---------- Demos ----------
    def build_demo_tab(self):
        f = ttk.Frame(self.nb, padding=12)
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self.fill_demo_list())
        ttk.Label(left, text="Suchen", style="Dim.TLabel").pack(anchor="w")
        ttk.Entry(left, textvariable=self.search, width=30).pack(fill="x", pady=(2, 8))
        self.demo_list = tk.Listbox(left, width=30, activestyle="none", exportselection=False, bg=PANEL,
                                    fg=FG, selectbackground=ACCENT, selectforeground="#111",
                                    highlightthickness=0, relief="flat", font=("TkDefaultFont", 11))
        self.demo_list.pack(fill="y", expand=True)
        self.demo_list.bind("<<ListboxSelect>>", lambda e: self.show_demo())
        self.demo_list.bind("<Double-Button-1>", lambda e: self.upload_demo())
        self.demo_list.bind("<Return>", lambda e: self.upload_demo())

        right = ttk.Frame(f, padding=(18, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)
        self.demo_title = ttk.Label(right, style="Title.TLabel")
        self.demo_title.pack(anchor="w")
        row = ttk.Frame(right)
        row.pack(anchor="w", fill="x", pady=10)
        self.demo_view = LedView(row, cell=20)
        self.demo_view.pack(side="left", anchor="n")
        info = ttk.Frame(row, padding=(16, 0, 0, 0))
        info.pack(side="left", fill="both", expand=True, anchor="n")
        ttk.Label(info, text="Live-Vorschau, auf dem PC gerechnet", style="Dim.TLabel").pack(anchor="w")
        self.demo_desc = ttk.Label(info, wraplength=380, justify="left")
        self.demo_desc.pack(anchor="w", pady=(8, 0))
        self.hint_box = ttk.Frame(info, style="Panel.TFrame", padding=10)
        self.hint = ttk.Label(self.hint_box, wraplength=320, justify="left", style="Hint.TLabel")
        self.hint.pack(anchor="w")
        self.hint_btn = ttk.Button(self.hint_box)
        self.demo_btn = self.action(ttk.Button(info, text="Auf die Matrix laden", style="Accent.TButton",
                                               command=self.upload_demo))
        self.demo_btn.pack(anchor="w", pady=14, side="bottom")
        self.shown = []
        self.fill_demo_list()
        return f

    def fill_demo_list(self):
        q = self.search.get().strip().lower()
        sel = self.selected_demo()
        self.shown = [d for d in self.demos if q in d["title"].lower() or q in d["desc"].lower()
                      or q in d["stem"]]
        self.demo_list.delete(0, "end")
        for d in self.shown:
            self.demo_list.insert("end", "  " + d["title"])
        if self.shown:
            i = self.shown.index(sel) if sel in self.shown else 0
            self.demo_list.selection_set(i)
            self.demo_list.see(i)
            self.after(10, self.show_demo)

    def selected_demo(self):
        sel = self.demo_list.curselection() if hasattr(self, "demo_list") else ()
        return self.shown[sel[0]] if sel and sel[0] < len(self.shown) else None

    def show_demo(self):
        d = self.selected_demo()
        if not d or d is getattr(self, "demo_shown", None):
            return
        self.demo_shown = d
        self.demo_title.config(text=d["title"])
        self.demo_desc.config(text=d["desc"])
        stem = d["stem"]
        hint, btn = HINTS.get(stem), None
        if stem in KEYBOARD_DEMOS:
            found, readable = keyboard_access()
            if readable:
                hint = "Nach dem Hochladen meldet die GUI jeden Tastendruck an den Pico (nur dass, nie welche Taste)."
            else:
                hint = ("Die Tastatur darf noch nicht mitgelesen werden. Einmalig im Terminal ausführen, "
                        "danach ab- und wieder anmelden:\nsudo usermod -aG input $USER\n"
                        "Bis dahin tippt die Figur im Demo-Modus von selbst.")
                btn = ("Befehl kopieren", lambda: self.copy("sudo usermod -aG input $USER"))
        if stem == "video":
            btn = ("Zu „Video & Bildschirm“", lambda: self.nb.select(2))
        if hint:
            self.hint.config(text=hint)
            if btn:
                self.hint_btn.config(text=btn[0], command=btn[1])
                self.hint_btn.pack(anchor="w", pady=(8, 0))
            else:
                self.hint_btn.pack_forget()
            self.hint_box.pack(anchor="w", fill="x", pady=(14, 0))
        else:
            self.hint_box.pack_forget()
        self.demo_view.clear()
        if self.nb.index("current") == 0:
            self.preview.start(d["path"])

    def pump_preview(self):
        f = self.preview.take()
        if f:
            self.demo_view.show(f)
        self.after(33, self.pump_preview)

    def tab_changed(self):
        # die Live-Vorschau kostet Rechenzeit, nur im Demo-Reiter laufen lassen
        if self.nb.index("current") == 0:
            self.demo_shown = None
            self.show_demo()
        else:
            self.preview.stop()

    def upload_demo(self, d=None):
        d = d or self.selected_demo()
        if not d:
            return
        stem = d["stem"]
        if stem == "video":
            self.nb.select(2)
            return
        if not self.check_ready():
            return
        cmd = ["cp", str(MATRIX), ":matrix.py", "+", "cp", str(d["path"]), ":main.py", "+"]
        sender, extra = SENDERS.get(stem), ()
        if stem == "visualizer":
            extra = ("--quelle", self.audio.get() or "@DEFAULT_MONITOR@")
        if stem == "oslogo":
            logo = Path(tempfile.mkdtemp(prefix="ledmatrix-")) / "oslogo.bin"
            try:
                logo.write_bytes(self.logo_image().tobytes())
            except SystemExit as e:
                messagebox.showerror("OS-Logo", str(e))
                return
            cmd += ["cp", str(logo), ":oslogo.bin", "+"]
        if stem == "uhr":
            # kein Reset, der wuerde die gerade gesetzte Uhrzeit wieder loeschen
            cmd += ["rtc", "--set", "+", "exec", "--no-follow", "import main"]
        else:
            cmd += ["reset"]
        after = (lambda: self.start_sender(sender, extra, d["title"])) if sender else None
        self.run(cmd, f"Lade „{d['title']}“ …", f"„{d['title']}“ läuft", after, current=d["title"])

    # ---------- Eigenes Bild ----------
    def build_image_tab(self):
        f = ttk.Frame(self.nb, padding=12)
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        ttk.Button(left, text="Bild oder GIF öffnen …", command=self.open_image).pack(anchor="w")
        self.img_info = ttk.Label(left, text="Noch keine Datei gewählt", wraplength=300, style="Dim.TLabel")
        self.img_info.pack(anchor="w", pady=(6, 14))

        box = ttk.LabelFrame(left, text="An 16 × 16 anpassen", padding=10)
        box.pack(anchor="w", fill="x")
        self.fit = tk.StringVar(value="einpassen")
        for val, txt in (("einpassen", "Einpassen (schwarze Ränder)"),
                         ("zuschneiden", "Zuschneiden (füllt alles)"),
                         ("strecken", "Strecken")):
            ttk.Radiobutton(box, text=txt, value=val, variable=self.fit, command=self.reconvert).pack(anchor="w")
        self.boost = tk.BooleanVar(value=True)
        ttk.Checkbutton(box, text="Helligkeit anheben", variable=self.boost,
                        command=self.reconvert).pack(anchor="w", pady=(8, 0))
        self.sharp = tk.BooleanVar(value=False)
        ttk.Checkbutton(box, text="Scharf skalieren (für Pixel-Art)", variable=self.sharp,
                        command=self.reconvert).pack(anchor="w")

        box = ttk.LabelFrame(left, text="GIF-Tempo", padding=10)
        box.pack(anchor="w", fill="x", pady=10)
        self.speed = tk.DoubleVar(value=1.0)
        self.slider(box, self.speed, 0.25, 3.0, "{:.2f}×", self.reconvert)
        self.img_btn = self.action(ttk.Button(left, text="Auf die Matrix laden", style="Accent.TButton",
                                              command=self.upload_image, state="disabled"))
        self.img_btn.pack(anchor="w", pady=10)

        self.img_view = LedView(f, cell=22)
        self.img_view.pack(side="left", padx=24, anchor="n")
        self.img_path = None
        return f

    def slider(self, parent, var, lo, hi, fmt, on_release=None):
        """Schieberegler mit Wertanzeige; on_release wird beim Loslassen aufgerufen."""
        row = ttk.Frame(parent)
        row.pack(fill="x")
        lbl = ttk.Label(row, text=fmt.format(var.get()), width=7)
        sc = ttk.Scale(row, from_=lo, to=hi, variable=var, length=200,
                       command=lambda v: lbl.config(text=fmt.format(float(v))))
        sc.pack(side="left", fill="x", expand=True)
        lbl.pack(side="left", padx=(6, 0))
        if on_release:
            sc.bind("<ButtonRelease-1>", lambda e: on_release())
        return sc

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
        if not self.busy:
            self.img_btn.config(state="normal")
        self.anim_i = 0
        if self.anim:
            self.after_cancel(self.anim)
        self.animate()

    def animate(self):
        if not self.frames:
            return
        dur, img = self.frames[self.anim_i % len(self.frames)]
        self.img_view.show(img)
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
        self.run(cmd, f"Lade {self.img_path.name} ({kb:.0f} KB) …", f"{self.img_path.name} läuft",
                 current=self.img_path.name)

    # ---------- Video & Bildschirm ----------
    def build_stream_tab(self):
        f = ttk.Frame(self.nb, padding=12)
        left = ttk.Frame(f)
        left.pack(side="left", fill="both", expand=True)

        box = ttk.LabelFrame(left, text="Quelle", padding=10)
        box.pack(fill="x")
        self.src = tk.StringVar(value="datei")
        self.file = tk.StringVar()
        self.url = tk.StringVar()
        r = ttk.Frame(box)
        r.pack(fill="x")
        ttk.Radiobutton(r, text="Videodatei", value="datei", variable=self.src,
                        command=self.stream_src_changed).pack(side="left")
        ttk.Entry(r, textvariable=self.file).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(r, text="Wählen …", command=self.pick_video).pack(side="left")
        r = ttk.Frame(box)
        r.pack(fill="x", pady=6)
        ttk.Radiobutton(r, text="Link        ", value="link", variable=self.src,
                        command=self.stream_src_changed).pack(side="left")
        ttk.Entry(r, textvariable=self.url).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(box, text="Links von Videoseiten (z. B. YouTube) werden mit yt-dlp aufgelöst.",
                  style="Dim.TLabel").pack(anchor="w")
        ttk.Radiobutton(box, text="Bildschirm dieses PCs (live)", value="bildschirm", variable=self.src,
                        command=self.stream_src_changed).pack(anchor="w", pady=(8, 0))

        box = ttk.LabelFrame(left, text="Bild", padding=10)
        box.pack(fill="x", pady=10)
        grid = ttk.Frame(box)
        grid.pack(fill="x")
        ttk.Label(grid, text="An 16 × 16 anpassen").grid(row=0, column=0, sticky="w")
        self.smode = tk.StringVar(value="zuschneiden")
        ttk.Combobox(grid, textvariable=self.smode, state="readonly", width=16,
                     values=("zuschneiden", "rand", "strecken")).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(grid, text="Bilder pro Sekunde").grid(row=1, column=0, sticky="w", pady=4)
        self.sfps = tk.DoubleVar(value=25)
        fr = ttk.Frame(grid)
        fr.grid(row=1, column=1, sticky="we", padx=8)
        self.slider(fr, self.sfps, 5, 50, "{:.0f}")
        ttk.Label(grid, text="Farbe").grid(row=2, column=0, sticky="w")
        self.sfarbe = tk.DoubleVar(value=1.4)
        fr = ttk.Frame(grid)
        fr.grid(row=2, column=1, sticky="we", padx=8)
        self.slider(fr, self.sfarbe, 0.5, 2.5, "{:.2f}")
        ttk.Label(grid, text="Kontrast").grid(row=3, column=0, sticky="w", pady=4)
        self.skontrast = tk.DoubleVar(value=1.15)
        fr = ttk.Frame(grid)
        fr.grid(row=3, column=1, sticky="we", padx=8)
        self.slider(fr, self.skontrast, 0.5, 2.0, "{:.2f}")
        grid.columnconfigure(1, weight=1)
        self.sloop = tk.BooleanVar(value=True)
        self.loop_btn = ttk.Checkbutton(box, text="Video endlos wiederholen", variable=self.sloop)
        self.loop_btn.pack(anchor="w", pady=(6, 0))

        self.screen_box = ttk.LabelFrame(left, text="Bildschirm", padding=10)
        r = ttk.Frame(self.screen_box)
        r.pack(fill="x")
        ttk.Label(r, text="Ausschnitt").pack(side="left")
        self.area = tk.StringVar(value="Ganzer Bildschirm")
        self.areas = {"Ganzer Bildschirm": None, "Linke Hälfte": "0,0,0.5,1", "Rechte Hälfte": "0.5,0,0.5,1",
                      "Mitte": "0.25,0.25,0.5,0.5", "Oben links": "0,0,0.5,0.5", "Oben rechts": "0.5,0,0.5,0.5",
                      "Unten links": "0,0.5,0.5,0.5", "Unten rechts": "0.5,0.5,0.5,0.5"}
        ttk.Combobox(r, textvariable=self.area, state="readonly", width=18,
                     values=list(self.areas)).pack(side="left", padx=8)
        self.renew = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.screen_box, text="Bildschirm neu auswählen (Freigabe-Dialog erneut zeigen)",
                        variable=self.renew).pack(anchor="w", pady=(6, 0))
        ttk.Label(self.screen_box, wraplength=460, style="Dim.TLabel", justify="left",
                  text="Unter Wayland fragt der Desktop beim ersten Mal, welcher Bildschirm geteilt wird. "
                       "Die Erlaubnis wird gespeichert.").pack(anchor="w", pady=(4, 0))

        r = ttk.Frame(left)
        r.pack(fill="x", side="bottom", pady=6)
        self.stream_btn = self.action(ttk.Button(r, text="▶  Starten", style="Accent.TButton",
                                                 command=self.start_stream))
        self.stream_btn.pack(side="left")
        ttk.Button(r, text="■  Stoppen", command=self.stop_sender).pack(side="left", padx=8)
        self.stream_info = ttk.Label(r, text="", style="Dim.TLabel")
        self.stream_info.pack(side="left", padx=8)

        right = ttk.Frame(f, padding=(18, 0, 0, 0))
        right.pack(side="left", anchor="n")
        ttk.Label(right, text="Tipps", style="TLabelframe.Label").pack(anchor="w")
        ttk.Label(right, text="Videos: 25 Bilder/s reichen meist.\n\nBei 16 × 16 wirken große, kräftige\n"
                              "Formen am besten: Zeichentrick,\nMusikvideos, Farbverläufe.\n\n"
                              "Dunkle Szenen: Kontrast höher.\nZu grell: Farbe auf 1,0.\n\n"
                              "Bildschirm: ein Ausschnitt\n(z. B. „Mitte“) zeigt mehr Details.",
                  style="Dim.TLabel", justify="left").pack(anchor="w", pady=6)
        self.stream_src_changed()
        return f

    def stream_src_changed(self):
        screen = self.src.get() == "bildschirm"
        if screen:
            self.screen_box.pack(fill="x", after=self.loop_btn.master)
            if self.smode.get() == "zuschneiden":
                self.smode.set("rand")
            if self.sfps.get() > 30:
                self.sfps.set(20)
        else:
            self.screen_box.pack_forget()
        self.loop_btn.config(state="disabled" if screen else "normal")

    def pick_video(self):
        path = filedialog.askopenfilename(title="Video auswählen", filetypes=[
            ("Videos", "*.mp4 *.mkv *.webm *.avi *.mov *.gif *.m4v"), ("Alle Dateien", "*")])
        if path:
            self.file.set(path)
            self.src.set("datei")
            self.stream_src_changed()

    def start_stream(self):
        src = self.src.get()
        common = ["--fps", f"{self.sfps.get():.0f}", "--modus", self.smode.get(),
                  "--farbe", f"{self.sfarbe.get():.2f}", "--kontrast", f"{self.skontrast.get():.2f}"]
        if src == "bildschirm":
            script, args, name = TOOLS / "bildschirm.py", common, "Bildschirm"
            if self.areas.get(self.area.get()):
                args = args + ["--bereich", self.areas[self.area.get()]]
            if self.renew.get():
                args = args + ["--neu"]
                self.renew.set(False)
        else:
            q = self.file.get().strip() if src == "datei" else self.url.get().strip()
            if not q:
                messagebox.showinfo("Video", "Bitte zuerst eine Videodatei wählen oder einen Link eintragen.")
                return
            if src == "datei" and not Path(q).exists():
                messagebox.showerror("Video", f"Datei nicht gefunden:\n{q}")
                return
            script, name = TOOLS / "video.py", ("Video: " + Path(q).name if src == "datei" else "Video-Link")
            args = [q] + common + (["--schleife"] if self.sloop.get() else [])
        if not self.check_ready():
            return
        self.stream_info.config(text="")
        if self.current == "Video & Bildschirm":
            # Empfaenger laeuft schon, nur den Sender (neu) starten
            self.stop_sender()
            self.start_sender(script, args, name, wait=False)
        else:
            cmd = ["cp", str(MATRIX), ":matrix.py", "+", "cp", str(DEMOS / "video.py"), ":main.py", "+", "reset"]
            self.run(cmd, "Lade den Video-Empfänger …", f"{name} läuft",
                     lambda: self.start_sender(script, args, name), current="Video & Bildschirm")

    # ---------- OS-Logo ----------
    def build_logo_tab(self):
        f = ttk.Frame(self.nb, padding=12)
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        box = ttk.LabelFrame(left, text="Logo", padding=10)
        box.pack(fill="x")
        self.logo = tk.StringVar(value="Dieser PC (automatisch)")
        self.logo_box = ttk.Combobox(box, textvariable=self.logo, width=30, values=["Dieser PC (automatisch)"])
        self.logo_box.pack(anchor="w")
        self.logo_box.bind("<<ComboboxSelected>>", lambda e: self.update_logo())
        self.logo_box.bind("<Return>", lambda e: self.update_logo())
        ttk.Label(box, text="Aus der Liste wählen oder Namen eintippen + Enter.\nAlle Namen: fastfetch --list-logos",
                  style="Dim.TLabel").pack(anchor="w", pady=(4, 0))
        box = ttk.LabelFrame(left, text="Umrechnen", padding=10)
        box.pack(fill="x", pady=10)
        ttk.Label(box, text="Schwache Randpixel weglassen").pack(anchor="w")
        self.logo_low = tk.DoubleVar(value=0.2)
        self.slider(box, self.logo_low, 0.0, 0.5, "{:.2f}", self.update_logo)
        ttk.Label(box, text="Ab hier volle Helligkeit").pack(anchor="w", pady=(8, 0))
        self.logo_high = tk.DoubleVar(value=0.55)
        self.slider(box, self.logo_high, 0.3, 1.0, "{:.2f}", self.update_logo)
        self.logo_btn = self.action(ttk.Button(left, text="Mit der Demo auf die Matrix laden",
                                               style="Accent.TButton", command=self.upload_logo))
        self.logo_btn.pack(anchor="w", pady=10)
        self.logo_msg = ttk.Label(left, text="", style="Dim.TLabel", wraplength=300)
        self.logo_msg.pack(anchor="w")
        self.logo_view = LedView(f, cell=22)
        self.logo_view.pack(side="left", padx=24, anchor="n")
        threading.Thread(target=self.load_logo_list, daemon=True).start()
        self.after(300, self.update_logo)
        return f

    def load_logo_list(self):
        try:
            import oslogo
            names = oslogo.list_logos()
        except Exception:
            names = []
        self.log_q.put(("call", lambda: self.logo_box.config(values=["Dieser PC (automatisch)"] + names)))

    def logo_image(self):
        import oslogo
        name = self.logo.get().strip()
        name = None if name.startswith("Dieser PC") or not name else name
        low, high = self.logo_low.get(), self.logo_high.get()
        return oslogo.render(oslogo.fastfetch_logo(name), low, max(high, low + 0.05))

    def update_logo(self):
        try:
            img = self.logo_image()
        except SystemExit as e:
            self.logo_msg.config(text=str(e))
            return
        except Exception as e:
            self.logo_msg.config(text=f"Fehler: {e}")
            return
        self.logo_msg.config(text="")
        self.logo_view.show(img)

    def upload_logo(self):
        for d in self.demos:
            if d["stem"] == "oslogo":
                self.upload_demo(d)
                return

    # ---------- Werkzeuge ----------
    def build_tools_tab(self):
        f = ttk.Frame(self.nb, padding=12)
        col1 = ttk.Frame(f)
        col1.pack(side="left", fill="both", expand=True, anchor="n")
        col2 = ttk.Frame(f, padding=(16, 0, 0, 0))
        col2.pack(side="left", fill="both", expand=True, anchor="n")

        box = ttk.LabelFrame(col1, text="Matrix", padding=10)
        box.pack(fill="x")
        self.tool_row(box, "Testbild", "Rote Zeile oben, grüne Spalte links, blau unten rechts, gelb "
                      "diagonal neben oben links. Zum Prüfen von Ausrichtung und Verkabelung.", self.testbild)
        self.tool_row(box, "Neu starten", "Startet main.py auf dem Pico neu (was zuletzt hochgeladen wurde).",
                      self.restart)
        self.tool_row(box, "Ausschalten", "Matrix dunkel, und beim nächsten Einstecken startet nichts.",
                      self.switch_off)

        box = ttk.LabelFrame(col1, text="Uhr", padding=10)
        box.pack(fill="x", pady=10)
        self.tool_row(box, "Uhrzeit stellen", "Übernimmt die Uhrzeit des PCs. Der Pico hat keine Batterie, "
                      "nach dem Ausstecken ist die Zeit weg. Startet die Uhr neu, falls sie läuft.", self.set_clock)

        box = ttk.LabelFrame(col1, text="Startmenü", padding=10)
        box.pack(fill="x")
        self.tool_row(box, "Ins Startmenü", "Legt „LED-Matrix“ im Startmenü an. Beim Start holt der Eintrag "
                      "jedes Mal die neueste Version von GitHub (git pull), ohne Netz startet die "
                      "vorhandene.", self.install_launcher)

        box = ttk.LabelFrame(col2, text="Sound-Visualizer", padding=10)
        box.pack(fill="x")
        ttk.Label(box, text="Audioquelle (Standard: was gerade abgespielt wird)").pack(anchor="w")
        r = ttk.Frame(box)
        r.pack(fill="x", pady=4)
        self.audio = tk.StringVar(value="@DEFAULT_MONITOR@")
        self.audio_box = ttk.Combobox(r, textvariable=self.audio, width=34)
        self.audio_box.pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="Aktualisieren", command=self.refresh_audio).pack(side="left", padx=6)
        self.refresh_audio()

        box = ttk.LabelFrame(col2, text="Tastatur (Bongo-Katze, Tipp-Ente)", padding=10)
        box.pack(fill="x", pady=10)
        self.kbd_lbl = ttk.Label(box, wraplength=420, justify="left")
        self.kbd_lbl.pack(anchor="w")
        r = ttk.Frame(box)
        r.pack(anchor="w", pady=(6, 0))
        ttk.Button(r, text="Erneut prüfen", command=self.check_keyboard).pack(side="left")
        ttk.Button(r, text="Befehl kopieren",
                   command=lambda: self.copy("sudo usermod -aG input $USER")).pack(side="left", padx=6)
        self.check_keyboard()

        box = ttk.LabelFrame(col2, text="Pico", padding=10)
        box.pack(fill="x")
        r = ttk.Frame(box)
        r.pack(anchor="w")
        self.action(ttk.Button(r, text="Dateien anzeigen", command=self.list_files)).pack(side="left")
        self.action(ttk.Button(r, text="Speicher", command=self.mem_info)).pack(side="left", padx=6)
        ttk.Label(box, text="Ausgabe erscheint im Protokoll unten.", style="Dim.TLabel").pack(anchor="w", pady=(4, 0))
        return f

    def tool_row(self, parent, text, desc, cmd):
        r = ttk.Frame(parent)
        r.pack(fill="x", pady=4)
        self.action(ttk.Button(r, text=text, width=16, command=cmd)).pack(side="left", anchor="n")
        ttk.Label(r, text=desc, wraplength=300, justify="left", style="Dim.TLabel").pack(side="left", padx=10)

    def refresh_audio(self):
        self.audio_box.config(values=["@DEFAULT_MONITOR@"] + audio_sources())

    def check_keyboard(self):
        found, readable = keyboard_access()
        if not found:
            text, col = "Keine Tastatur gefunden.", BAD
        elif readable:
            text, col = f"OK: {readable} Tastatur(en) lesbar. Gemeldet wird nur die Reihe der Taste, nie welche Taste.", OK
        else:
            text, col = ("Keine Berechtigung. Einmalig im Terminal ausführen, danach ab- und wieder anmelden:\n"
                         "sudo usermod -aG input $USER\nDanach dürfen alle Programme dieses Benutzers die "
                         "Tastatur mitlesen."), ACCENT
        self.kbd_lbl.config(text=text, foreground=col)

    def install_launcher(self):
        apps = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "applications"
        entry = apps / "ledmatrix.desktop"
        apps.mkdir(parents=True, exist_ok=True)
        entry.write_text("[Desktop Entry]\n"
                         "Type=Application\n"
                         "Name=LED-Matrix\n"
                         "Comment=Pico-LED-Matrix steuern: Demos, Bilder, Video\n"
                         f"Exec=\"{TOOLS / 'starten.sh'}\"\n"
                         f"Icon={TOOLS / 'symbol.png'}\n"
                         "Terminal=false\n"
                         "Categories=Utility;\n"
                         "StartupWMClass=Ledmatrix\n")
        if shutil.which("update-desktop-database"):
            subprocess.run(["update-desktop-database", str(apps)], capture_output=True)
        self.status.set("„LED-Matrix“ steht jetzt im Startmenü")
        self.log_q.put(f"Startmenü-Eintrag angelegt: {entry}")

    def testbild(self):
        if self.check_ready():
            self.run(["run", str(TOOLS / "testbild.py")], "Zeige Testbild …", "Testbild wird angezeigt",
                     current="Testbild")

    def restart(self):
        if self.check_ready():
            self.run(["reset"], "Starte neu …", "Neu gestartet")

    def set_clock(self):
        if self.check_ready():
            if self.current == "Uhr":
                self.run(["rtc", "--set", "+", "exec", "--no-follow", "import main"], "Stelle die Uhr …",
                         "Uhrzeit übernommen")
            else:
                self.run(["rtc", "--set"], "Stelle die Uhr …", "Uhrzeit übernommen (gilt bis zum Ausstecken)")

    def list_files(self):
        if self.check_ready():
            self.run(["fs", "ls", ":"], "Lese Dateien …", "Dateien siehe Protokoll", keep=True)

    def mem_info(self):
        if self.check_ready():
            code = ("import gc, os\ngc.collect()\ns = os.statvfs('/')\n"
                    "print('RAM frei: %d KB' % (gc.mem_free() // 1024))\n"
                    "print('Flash frei: %d KB von %d KB' % (s[0] * s[3] // 1024, s[0] * s[2] // 1024))")
            self.run(["exec", code], "Frage den Pico …", "Speicher siehe Protokoll", keep=True)

    def copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set(f"Kopiert: {text}")

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

    def run(self, args, status, done, after=None, current=None, keep=False):
        """mpremote im Hintergrund. current: was danach auf der Matrix laeuft; keep: reine Abfrage,
        die Anzeige "Auf der Matrix" bleibt."""
        self.stop_sender()
        self.busy = True
        self.set_buttons("disabled")
        self.status.set(status)
        cmd = mpremote() + ["connect", self.port_device()] + args

        def work():
            self.log_q.put("$ mpremote " + " ".join(a if len(a) < 60 else a[:57] + "…" for a in args[:6])
                           + (" …" if len(args) > 6 else ""))
            ok = False
            for attempt in range(5):
                try:
                    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                except Exception as e:
                    self.log_q.put(f"Fehler: {e}")
                    break
                out = (p.stdout + p.stderr).strip()
                retry = ("failed to access", "Input/output error", "could not enter raw repl",
                         "No such file or directory: '/dev/tty")
                if p.returncode != 0 and any(r in out for r in retry) and attempt < 4:
                    # Pico meldet sich nach einem Reset gerade neu an -> kurz warten
                    self.log_q.put("Pico noch nicht bereit, neuer Versuch …")
                    time.sleep(1.5)
                    continue
                if out and p.returncode != 0 and "Traceback" in out:
                    out = "\n".join(out.splitlines()[-3:])     # nur das Ende der Fehlermeldung
                if out:
                    self.log_q.put(out)
                ok = p.returncode == 0
                break
            self.log_q.put(("fertig", ok, done, after, current, keep))

        threading.Thread(target=work, daemon=True).start()

    def pump_log(self):
        while not self.log_q.empty():
            item = self.log_q.get()
            if isinstance(item, tuple) and item[0] == "call":
                item[1]()
                continue
            if isinstance(item, tuple) and item[0] == "sender_ende":
                if item[1] is self.sender:
                    self.sender = None
                    self.update_sender_lbl()
                continue
            if isinstance(item, tuple):
                _, ok, done, after, current, keep = item
                self.busy = False
                self.set_buttons("normal")
                self.status.set(done if ok else "Fehlgeschlagen, Details im Protokoll")
                if ok and not keep:
                    self.current = current
                    self.update_now()
                if ok and after:
                    after()
                continue
            m = re.match(r"Pico: ([\d.]+) Bilder/s", item)
            if m:
                self.stream_info.config(text=f"Pico zeigt {m.group(1)} Bilder/s")
            self.log.config(state="normal")
            self.log.insert("end", item + "\n")
            self.log.see("end")
            self.log.config(state="disabled")
        self.after(100, self.pump_log)

    def set_buttons(self, state):
        for b in self.action_buttons:
            b.config(state=state)
        if state == "normal" and not self.frames:
            self.img_btn.config(state="disabled")

    def update_now(self):
        self.now_lbl.config(text=f"Auf der Matrix: {self.current}" if self.current else "")

    def refresh_ports(self):
        # nur USB-Geraete, der Pico (Raspberry Pi, VID 2E8A) zuerst
        ports = sorted((p for p in list_ports.comports() if p.vid), key=lambda p: p.vid != 0x2E8A)
        self.port_map = {f"{p.device}  ({'Pico' if p.vid == 0x2E8A else p.description[:20]})": p.device
                         for p in ports}
        names = list(self.port_map)
        self.port_box["values"] = names
        if self.port.get() not in names:
            self.port.set(names[0] if names else "")
        self.update_dot(ports)

    def update_dot(self, ports=None):
        if ports is None:
            ports = [p for p in list_ports.comports() if p.vid]
        pico = any(p.vid == 0x2E8A for p in ports)
        self.dot.itemconfig(self.dot_item, fill=OK if pico else BAD)

    def watch_ports(self):
        # Pico ein-/ausgesteckt? Waehrend eines Resets nicht die Auswahl umwerfen
        if not self.busy:
            ports = [p for p in list_ports.comports() if p.vid]
            self.update_dot(ports)
            if not self.port.get() and ports:
                self.refresh_ports()
        self.after(2000, self.watch_ports)

    def port_device(self):
        return self.port_map.get(self.port.get(), self.port.get())

    def switch_off(self):
        if not self.check_ready():
            return
        code = ("import os, matrix\nmatrix.clear()\nmatrix.show()\n"
                "try:\n    os.remove('main.py')\nexcept OSError:\n    pass")
        self.run(["exec", code], "Schalte aus …", "Matrix aus (startet beim Einstecken nichts mehr)",
                 current="aus")

    # ---------- PC-Sender ----------
    def start_sender(self, script, extra=(), name="", wait=True):
        port = self.port_device()   # Tk-Variablen nur im Haupt-Thread lesen
        self.sender_name = name or script.stem

        def go():
            if wait:
                # der Pico meldet sich nach dem Reset kurz neu an
                time.sleep(1.5)
                t = time.time()
                while not Path(port).exists() and time.time() - t < 10:
                    time.sleep(0.3)
                time.sleep(1.0)
            proc = subprocess.Popen([sys.executable, "-u", str(script), "--port", port, *extra],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.sender = proc
            self.log_q.put(("call", self.update_sender_lbl))
            self.log_q.put(f"Sender {script.name} gestartet")
            for line in proc.stdout:
                self.log_q.put(line.rstrip())
            proc.wait()
            self.log_q.put(f"Sender {script.name} beendet")
            self.log_q.put(("sender_ende", proc))
        threading.Thread(target=go, daemon=True).start()

    def update_sender_lbl(self):
        running = self.sender is not None and self.sender.poll() is None
        self.sender_lbl.config(text=f"Sender: {self.sender_name}" if running else "",
                               foreground=OK if running else DIM)
        self.sender_btn.config(state="normal" if running else "disabled")

    def stop_sender(self):
        if self.sender and self.sender.poll() is None:
            self.sender.terminate()
            try:
                self.sender.wait(3)
            except subprocess.TimeoutExpired:
                self.sender.kill()
            self.log_q.put("Sender gestoppt")
        self.sender = None
        self.update_sender_lbl()
        if hasattr(self, "stream_info"):
            self.stream_info.config(text="")

    def on_close(self):
        self.preview.stop()
        self.stop_sender()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
