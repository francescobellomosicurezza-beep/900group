#!/usr/bin/env bash
# Prima installazione su PythonAnywhere (piano gratuito).
# Uso, dalla console Bash di PythonAnywhere:
#   git clone https://github.com/francescobellomosicurezza-beep/900group.git
#   bash 900group/deploy/installa_pythonanywhere.sh
set -euo pipefail

CARTELLA="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CARTELLA"
UTENTE="$(whoami)"
DOMINIO="${UTENTE}.pythonanywhere.com"

echo "=============================================="
echo " Installazione Novecento Ordini"
echo " Cartella: $CARTELLA"
echo " Indirizzo del sito: https://$DOMINIO"
echo "=============================================="

# 1. Python e ambiente virtuale
PY=""
for candidato in python3.13 python3.12 python3.11 python3.10; do
    if command -v "$candidato" >/dev/null 2>&1; then PY="$candidato"; break; fi
done
if [ -z "$PY" ]; then echo "Python 3.10+ non trovato."; exit 1; fi
echo "-> Uso $PY"
if [ ! -x ".venv/bin/python" ]; then
    "$PY" -m venv .venv
fi
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt

# 2. File .env con le impostazioni riservate
if [ -f .env ]; then
    echo "-> File .env già presente: lo lascio invariato."
else
    echo
    echo "Configurazione email (account Gmail che INVIA gli ordini)."
    read -r -p "Indirizzo Gmail mittente: " GMAIL
    read -r -s -p "Password per le app Gmail (16 lettere, non si vede mentre scrivi): " GMAIL_PWD
    echo
    GMAIL_PWD="${GMAIL_PWD// /}"
    read -r -p "Email del laboratorio che RICEVE gli ordini: " DESTINATARIO
    CHIAVE="$(.venv/bin/python -c 'from django.core.management.utils import get_random_secret_key as g; print(g())')"
    umask 077
    cat > .env <<EOF
DJANGO_SECRET_KEY=$CHIAVE
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=$DOMINIO
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMINIO

DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.gmail.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USE_TLS=1
DJANGO_EMAIL_HOST_USER=$GMAIL
DJANGO_EMAIL_HOST_PASSWORD=$GMAIL_PWD
DJANGO_DEFAULT_FROM_EMAIL=Ordini Novecento <$GMAIL>

ORDINI_EMAIL_DESTINATARI=$DESTINATARIO
EOF
    chmod 600 .env
    echo "-> File .env creato (leggibile solo da te)."
fi

# 3. Database e file statici
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput -v 0
.venv/bin/python manage.py check --deploy --fail-level ERROR

# 4. Amministratore e credenziali delle sedi
echo
if .venv/bin/python manage.py shell -v 0 -c "from django.contrib.auth import get_user_model as g; import sys; sys.exit(0 if g().objects.filter(is_superuser=True).exists() else 1)"; then
    echo "-> Amministratore già presente."
else
    echo "Crea l'account AMMINISTRATORE (per /admin/):"
    .venv/bin/python manage.py createsuperuser
fi

for SEDE in spello bastia foligno; do
    if .venv/bin/python manage.py shell -v 0 -c "from novecento.models import Sede; import sys; sys.exit(0 if Sede.objects.filter(slug='$SEDE', account__isnull=False).exists() else 1)"; then
        echo "-> Credenziali di $SEDE già presenti."
    else
        echo
        echo "Password per la sede $SEDE (username: $SEDE):"
        .venv/bin/python manage.py crea_accesso_sede "$SEDE"
    fi
done

# 5. Email di prova
echo
read -r -p "Vuoi inviare un'email di prova al laboratorio adesso? [s/N] " PROVA
if [[ "$PROVA" =~ ^[sS]$ ]]; then
    .venv/bin/python manage.py invia_email_prova || echo "!! Email non partita: controlla Gmail e la password per le app."
fi

cat <<EOF

==============================================================
 FATTO. Ora apri la scheda "Web" di PythonAnywhere e imposta:

 Virtualenv:   $CARTELLA/.venv
 Static files: URL /static/   ->  Directory $CARTELLA/staticfiles
 Force HTTPS:  attivo

 Nel file WSGI (link "WSGI configuration file") cancella tutto e incolla:

import os, sys
path = "$CARTELLA"
if path not in sys.path:
    sys.path.insert(0, path)
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

 Poi premi il pulsante verde "Reload" e apri https://$DOMINIO
==============================================================
EOF
