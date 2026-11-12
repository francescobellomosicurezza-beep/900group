# Novecento – Ordini punti vendita

Web app Django per gli ordini giornalieri dei punti vendita Gelateria Novecento
(900 Spello, 900 Bastia, 900 Foligno) verso il laboratorio.

## Flusso
1. Il dipendente sceglie il proprio punto vendita (PIN opzionale per sede).
2. Inserisce nome e cognome.
3. Compila l'ordine guidato, una categoria alla volta.
4. Riepilogo, note e invio: viene generato un PDF e spedito via email al laboratorio
   (in copia all'email della sede, se impostata). L'ordine resta nello storico.

## Amministrazione (`/admin/`)
- **Sedi**: aggiunta di nuovi punti vendita, email in copia, PIN.
- **Categorie / Articoli**: catalogo ordinabile, ordine di visualizzazione, attivazione.
- **Ordini**: storico, PDF, reinvio email.

## Avvio in locale
```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```
In sviluppo le email vengono stampate in console. Per l'invio reale configurare le
variabili in `.env.example`.

## Test
```bash
.venv/bin/python manage.py test novecento
```
