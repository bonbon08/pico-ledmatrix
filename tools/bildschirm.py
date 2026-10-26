#!/usr/bin/env python3
"""Bildschirm-Sender: zeigt den PC-Bildschirm live auf der Matrix (Pico-Seite: demos/video.py).

Unter Wayland laeuft die Aufnahme ueber die Bildschirmfreigabe des Desktops (xdg-desktop-portal
+ PipeWire). Beim ersten Mal fragt der Desktop in einem Dialog, welcher Bildschirm geteilt werden
soll; die Erlaubnis wird gespeichert, danach kommt kein Dialog mehr. Unter X11 nimmt ffmpeg auf.
Das Bild wird flaechengemittelt auf 16x16 verkleinert und im selben Format wie bei tools/video.py
geschickt (nur druckbare Zeichen).

Aufruf:  python tools/bildschirm.py                       # ganzer Bildschirm mit Rand
         python tools/bildschirm.py --modus zuschneiden   # Mitte quadratisch
         python tools/bildschirm.py --bereich 0,0,0.5,1   # linke Haelfte (x, y, Breite, Hoehe)
         python tools/bildschirm.py --neu                 # Bildschirm neu auswaehlen
Benoetigt: pyserial, Pillow; Wayland: python-gobject, gst-plugin-pipewire; X11: ffmpeg
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import serial
from PIL import Image, ImageEnhance

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video import TABLE, find_port   # noqa: E402  (gleiches Format wie der Video-Sender)

N = 16
GRAB_W = 320                      # Breite des Zwischenbilds; verkleinert wird auf dem PC
TOKEN = Path.home() / ".cache" / "ledmatrix-bildschirm.token"


class Portal:
    """Bildschirmfreigabe ueber xdg-desktop-portal, liefert Bilder ueber GStreamer/PipeWire."""

    def __init__(self, fresh):
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gio, GLib, Gst
        self.GLib = GLib
        Gst.init(None)
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION)
        self.proxy = Gio.DBusProxy.new_sync(self.bus, 0, None, "org.freedesktop.portal.Desktop",
                                            "/org/freedesktop/portal/desktop",
                                            "org.freedesktop.portal.ScreenCast", None)
        self.sender = self.bus.get_unique_name()[1:].replace(".", "_")
        self.n = 0
        V = GLib.Variant
        res = self.request("CreateSession", lambda tok: V("(a{sv})", ({
            "handle_token": V("s", tok), "session_handle_token": V("s", tok + "s")},)))
        session = res["session_handle"]
        opts = {"types": V("u", 1), "multiple": V("b", False), "persist_mode": V("u", 2)}
        modes = self.proxy.get_cached_property("AvailableCursorModes")
        if modes and modes.unpack() & 2:
            opts["cursor_mode"] = V("u", 2)          # Mauszeiger mit ins Bild
        if TOKEN.exists() and not fresh:
            opts["restore_token"] = V("s", TOKEN.read_text().strip())
        self.request("SelectSources", lambda tok: V("(oa{sv})", (session, dict(opts, handle_token=V("s", tok)))))
        print("Warte auf die Freigabe (beim ersten Mal fragt der Desktop in einem Dialog) ...")
        res = self.request("Start", lambda tok: V("(osa{sv})", (session, "", {"handle_token": V("s", tok)})))
        if "restore_token" in res:
            TOKEN.parent.mkdir(parents=True, exist_ok=True)
            TOKEN.write_text(res["restore_token"])
        node, props = res["streams"][0]
        w, h = props.get("size", (16, 9))
        ret, fds = self.proxy.call_with_unix_fd_list_sync(
            "OpenPipeWireRemote", V("(oa{sv})", (session, {})), 0, -1, None, None)
        fd = fds.get(ret.unpack()[0])
        gh = max(2, round(GRAB_W * h / w) // 2 * 2)
        self.size = (GRAB_W, gh)
        self.pipe = Gst.parse_launch(
            f"pipewiresrc fd={fd} path={node} always-copy=true ! videoconvert ! videoscale ! "
            f"video/x-raw,format=RGB,width={GRAB_W},height={gh} ! "
            "appsink name=sink max-buffers=1 drop=true sync=false")
        self.sink = self.pipe.get_by_name("sink")
        self.pipe.set_state(Gst.State.PLAYING)

    def request(self, method, params):
        # Portal-Aufrufe antworten ueber ein Signal am Request-Objekt
        self.n += 1
        tok = f"ledmatrix{os.getpid()}_{self.n}"
        path = f"/org/freedesktop/portal/desktop/request/{self.sender}/{tok}"
        loop = self.GLib.MainLoop()
        out = {}

        def on_response(_c, _s, _o, _i, _n, args):
            out["code"], out["res"] = args.unpack()
            loop.quit()
        sub = self.bus.signal_subscribe("org.freedesktop.portal.Desktop", "org.freedesktop.portal.Request",
                                        "Response", path, None, 0, on_response)
        self.proxy.call_sync(method, params(tok), 0, -1, None)
        loop.run()
        self.bus.signal_unsubscribe(sub)
        if out["code"] != 0:
            sys.exit("Bildschirmfreigabe abgebrochen" if out["code"] == 1 else f"Portal-Fehler bei {method}")
        return out["res"]

    def grab(self):
        """Neuestes Bild oder None, wenn sich nichts geaendert hat (PipeWire schickt nur Aenderungen)."""
        sample = self.sink.emit("try-pull-sample", 0)
        if sample is None:
            return None
        buf = sample.get_buffer()
        return Image.frombytes("RGB", self.size, buf.extract_dup(0, buf.get_size()))

    def close(self):
        from gi.repository import Gst
        self.pipe.set_state(Gst.State.NULL)


class X11:
    """Aufnahme unter X11 mit ffmpeg."""

    def __init__(self, fps):
        out = subprocess.run(["xdpyinfo"], capture_output=True, text=True).stdout
        dims = next((l.split()[1] for l in out.splitlines() if "dimensions:" in l), "1920x1080")
        w, h = (int(v) for v in dims.split("x"))
        gh = max(2, round(GRAB_W * h / w) // 2 * 2)
        self.size = (GRAB_W, gh)
        self.proc = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-f", "x11grab", "-framerate", str(fps),
             "-i", os.environ.get("DISPLAY", ":0"), "-vf", f"scale={GRAB_W}:{gh}:flags=area",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

    def grab(self):
        data = self.proc.stdout.read(self.size[0] * self.size[1] * 3)
        return Image.frombytes("RGB", self.size, data) if data else None

    def close(self):
        self.proc.kill()


def to_matrix(img, modus, bereich, farbe, kontrast):
    if bereich:
        x, y, w, h = bereich
        W, H = img.size
        img = img.crop((int(x * W), int(y * H), int((x + w) * W), int((y + h) * H)))
    if modus == "zuschneiden":
        s = min(img.size)
        img = img.crop(((img.width - s) // 2, (img.height - s) // 2, (img.width + s) // 2, (img.height + s) // 2))
        img = img.resize((N, N), Image.BOX)
    elif modus == "strecken":
        img = img.resize((N, N), Image.BOX)
    else:   # rand: ganzes Bild, oben/unten bzw. links/rechts schwarz
        k = N / max(img.size)
        small = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.BOX)
        img = Image.new("RGB", (N, N))
        img.paste(small, ((N - small.width) // 2, (N - small.height) // 2))
    img = ImageEnhance.Color(img).enhance(farbe)
    return ImageEnhance.Contrast(img).enhance(kontrast)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port")
    ap.add_argument("--fps", type=float, default=20, help="Bilder pro Sekunde (Standard 20)")
    ap.add_argument("--modus", choices=("rand", "zuschneiden", "strecken"), default="rand")
    ap.add_argument("--bereich", help="Ausschnitt x,y,Breite,Hoehe als Anteile 0..1, z. B. 0.25,0,0.5,1")
    ap.add_argument("--farbe", type=float, default=1.4, help="Farbsaettigung (1 = unveraendert)")
    ap.add_argument("--kontrast", type=float, default=1.15, help="Kontrast (1 = unveraendert)")
    ap.add_argument("--neu", action="store_true", help="gespeicherte Freigabe vergessen, neu auswaehlen")
    args = ap.parse_args()
    bereich = tuple(float(v) for v in args.bereich.split(",")) if args.bereich else None

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    port = serial.Serial(args.port or find_port(), 115200, timeout=0, write_timeout=3)
    wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or "WAYLAND_DISPLAY" in os.environ
    src = Portal(args.neu) if wayland else X11(args.fps)
    print(f"Sende Bildschirm an {port.port}, Strg+C zum Beenden")
    step = 1 / args.fps
    frame = None
    nxt = time.monotonic()
    try:
        while True:
            img = src.grab()
            if img is not None:
                frame = b"#" + to_matrix(img, args.modus, bereich, args.farbe, args.kontrast).tobytes().translate(TABLE) + b"\n"
            if frame:
                # auch bei unveraendertem Bild weiter senden, sonst zeigt der Pico das Play-Symbol
                port.write(frame)
            back = port.read(256)
            if back:
                sys.stdout.write(back.decode(errors="replace"))
            nxt += step
            time.sleep(max(0.0, nxt - time.monotonic()))
            if time.monotonic() - nxt > 1:
                nxt = time.monotonic()      # nach einer Haenger nicht hinterherhetzen
    except KeyboardInterrupt:
        pass
    except serial.SerialTimeoutException:
        print("Pico nimmt keine Daten an - laeuft demos/video.py?")
    finally:
        src.close()
        port.close()


if __name__ == "__main__":
    main()
