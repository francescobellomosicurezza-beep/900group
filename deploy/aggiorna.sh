#!/usr/bin/env bash
# Aggiorna il sito all'ultima versione su GitHub (console Bash di PythonAnywhere):
#   bash 900group/deploy/aggiorna.sh
set -euo pipefail

CARTELLA="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CARTELLA"

cp db.sqlite3 "db.backup-$(date +%Y%m%d-%H%M).sqlite3" 2>/dev/null || true
ls -1t db.backup-*.sqlite3 2>/dev/null | tail -n +6 | xargs -r rm --

git pull --ff-only
.venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput -v 0
.venv/bin/python manage.py check --deploy --fail-level ERROR

WSGI="/var/www/$(whoami)_pythonanywhere_com_wsgi.py"
if [ -f "$WSGI" ]; then
    touch "$WSGI"
    echo "Aggiornato e ricaricato: https://$(whoami).pythonanywhere.com"
else
    echo "Aggiornato. Premi \"Reload\" nella scheda Web di PythonAnywhere."
fi
