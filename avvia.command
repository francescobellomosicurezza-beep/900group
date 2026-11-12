#!/usr/bin/env bash
# Avvio locale per macOS e Linux (doppio clic su macOS, oppure ./avvia.command).
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
else
    echo "Python 3 non trovato. Installalo da https://www.python.org/downloads/"
    read -r -p "Premi Invio per chiudere..."
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Preparazione ambiente, solo la prima volta..."
    "$PY" -m venv .venv
fi

.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
.venv/bin/python manage.py migrate -v 0
.venv/bin/python manage.py dati_demo

PORTA="$(.venv/bin/python manage.py porta_libera --da 8900)"
URL="http://127.0.0.1:${PORTA}"
echo "Novecento in avvio su $URL - premi CTRL+C per fermarla."
( sleep 3; if command -v open >/dev/null 2>&1; then open "$URL"; elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"; fi ) &
exec .venv/bin/python manage.py runserver "127.0.0.1:${PORTA}"
