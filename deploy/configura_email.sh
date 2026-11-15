#!/usr/bin/env bash
# Configura (o cambia) l'account Gmail che invia gli ordini.
# Uso, dalla console Bash di PythonAnywhere:
#   bash 900group/deploy/configura_email.sh
set -euo pipefail

CARTELLA="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CARTELLA"
if [ ! -f .env ]; then
    echo "File .env assente: esegui prima deploy/installa_pythonanywhere.sh"
    exit 1
fi

echo "Configurazione email (account Gmail che INVIA gli ordini)."
read -r -p "Indirizzo Gmail mittente: " GMAIL
read -r -s -p "Password per le app (16 lettere, non si vede mentre scrivi): " GMAIL_PWD
echo
GMAIL_PWD="${GMAIL_PWD// /}"
read -r -p "Email del laboratorio che RICEVE gli ordini (Invio per lasciare quella attuale): " DESTINATARIO

if [ -z "$GMAIL" ] || [ -z "$GMAIL_PWD" ]; then
    echo "Gmail e password per le app sono obbligatori. Nessuna modifica fatta."
    exit 1
fi

NV_GMAIL="$GMAIL" NV_PWD="$GMAIL_PWD" NV_DEST="$DESTINATARIO" .venv/bin/python -I - <<'PY'
import os
from pathlib import Path

percorso = Path(".env")
valori = {
    "DJANGO_EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "DJANGO_EMAIL_HOST": "smtp.gmail.com",
    "DJANGO_EMAIL_PORT": "587",
    "DJANGO_EMAIL_USE_TLS": "1",
    "DJANGO_EMAIL_HOST_USER": os.environ["NV_GMAIL"].strip(),
    "DJANGO_EMAIL_HOST_PASSWORD": os.environ["NV_PWD"],
    "DJANGO_DEFAULT_FROM_EMAIL": f"Ordini Novecento <{os.environ['NV_GMAIL'].strip()}>",
}
if os.environ["NV_DEST"].strip():
    valori["ORDINI_EMAIL_DESTINATARI"] = os.environ["NV_DEST"].strip()

righe, presenti = [], set()
for riga in percorso.read_text(encoding="utf-8").splitlines():
    chiave = riga.split("=", 1)[0].strip()
    if chiave in valori:
        righe.append(f"{chiave}={valori[chiave]}")
        presenti.add(chiave)
    else:
        righe.append(riga)
righe += [f"{k}={v}" for k, v in valori.items() if k not in presenti]
percorso.write_text("\n".join(righe) + "\n", encoding="utf-8")
percorso.chmod(0o600)
PY
echo "-> Email salvata nel file .env"

WSGI="/var/www/$(whoami)_pythonanywhere_com_wsgi.py"
if [ -f "$WSGI" ]; then
    touch "$WSGI"
    echo "-> Sito ricaricato."
fi

read -r -p "Invio un'email di prova adesso? [s/N] " PROVA
if [[ "$PROVA" =~ ^[sS]$ ]]; then
    .venv/bin/python manage.py invia_email_prova || echo "!! Email non partita: controlla indirizzo e password per le app."
fi
