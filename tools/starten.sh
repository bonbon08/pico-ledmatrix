#!/bin/sh
# Starter fuer den Startmenue-Eintrag: holt vorher die neueste Version von GitHub und startet
# dann die GUI. Ohne Netz oder bei lokalen Aenderungen startet einfach die vorhandene Version.
# Den Eintrag legt die GUI unter Werkzeuge an ("Ins Startmenü").
cd "$(dirname "$0")/.." || exit 1
alt=$(git rev-parse --short HEAD 2>/dev/null)
if [ "$(git branch --show-current 2>/dev/null)" = main ] &&
   GIT_TERMINAL_PROMPT=0 timeout 10 git pull --ff-only --quiet >/dev/null 2>&1; then
    neu=$(git rev-parse --short HEAD)
    if [ "$alt" = "$neu" ]; then
        LEDMATRIX_UPDATE="Aktuell (Version $neu)"
    else
        LEDMATRIX_UPDATE="Aktualisiert: $alt → $neu"
    fi
else
    LEDMATRIX_UPDATE="Update nicht möglich (kein Netz, anderer Branch oder lokale Änderungen), starte Version $alt"
fi
export LEDMATRIX_UPDATE
exec python3 tools/gui.py "$@"
