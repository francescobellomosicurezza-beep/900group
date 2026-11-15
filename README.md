# Novecento – Ordini punti vendita

Web app Django per gli ordini giornalieri dei punti vendita Gelateria Novecento
(900 Spello, 900 Bastia, 900 Foligno) verso il laboratorio.

## Flusso
1. Il dispositivo del punto vendita accede con le credenziali della sede
   (username e password); la sede viene riconosciuta automaticamente.
   Gli amministratori possono scegliere qualsiasi sede.
2. Il dipendente inserisce nome e cognome.
   Tocca il proprio nome se ha già ordinato da quella sede.
3. Ordine guidato:
   - sceglie una delle 7 macrocategorie del listino (con il numero di articoli già scelti);
   - dentro la categoria apre le sottocategorie a fisarmonica (es. Coni e cialde,
     Coppette, Contenitori asporto) e imposta le quantità con − / +;
   - le quantità si salvano da sole: può tornare indietro e cambiare categoria;
   - vede la quantità del suo ultimo ordine accanto a ogni articolo e può
     "ripetere l'ultimo ordine" come base;
   - ricerca veloce per descrizione o codice; barra carrello sempre visibile.
4. Riepilogo per categoria/sottocategoria, note e invio: viene generato un PDF
   (codice, articolo, quantità, unità) e spedito via email al laboratorio
   (in copia all'email della sede, se impostata). L'ordine resta nello storico.

## Orario dell'ordine e promemoria
In `/admin/` → Sedi, per ogni punto vendita si impostano **orario limite**, **giorni**
e **minuti di preavviso**. La sede vede in ogni pagina un avviso:
- giallo: ordine da inviare entro l'orario (lampeggia nel preavviso);
- rosso: ordine in ritardo;
- verde: ordine di oggi già inviato (ora e operatore).

Con «Ricevi il promemoria sul telefono» la sede scarica un evento ricorrente (.ics)
da aggiungere al calendario del telefono, con avviso prima dell'orario e alla scadenza:
funziona su iPhone e Android senza costi e senza servizi esterni.

## Amministrazione (`/admin/`)
- **Sedi**: aggiunta di nuovi punti vendita, email in copia, credenziali di accesso
  (username, nuova password, disattivazione account).
- **Categorie → Sottocategorie → Articoli**: listino 900 (7 categorie, 57 articoli).
  Per ogni articolo: codice, descrizione, unità di vendita (CT/CF/PZ), pezzi per
  cartone, prezzo al pezzo, prezzo per cartone, IVA. Gli articoli si modificano
  anche direttamente dall'elenco.
- **Listino in Excel**: Articoli → «Esporta in Excel» scarica tutto il listino; si
  modificano codici, prezzi, IVA o si aggiungono righe (ID vuoto) e si ricarica con
  «Importa da Excel». Se una riga ha un errore non viene modificato nulla.
- **Impostazioni**: indirizzi email che ricevono gli ordini.
- **Ordini**: storico, PDF, reinvio email.

## Provarla sul proprio computer (doppio clic)
Requisito: Python 3.12 o superiore (https://www.python.org/downloads/ — su Windows
spuntare "Add python.exe to PATH" durante l'installazione).

1. Su GitHub: **Code → Download ZIP**, poi estrai la cartella.
2. Avvia:
   - **Windows**: doppio clic su `avvia.bat`
   - **Mac**: tasto destro su `avvia.command` → Apri (la prima volta)
3. Si apre il browser su http://127.0.0.1:8900 (se occupata, la prima porta libera
   successiva, indicata nella finestra) con queste credenziali di prova:

| Accesso | Username | Password |
|---|---|---|
| Amministratore (`/admin/`) | admin | Demo-Admin-2026 |
| 900 Spello | spello | Demo-Spello-2026 |
| 900 Bastia | bastia | Demo-Bastia-2026 |
| 900 Foligno | foligno | Demo-Foligno-2026 |

Le email non partono davvero: compaiono nella finestra dello script.
Le credenziali di prova esistono solo in locale e il comando `dati_demo` è bloccato in produzione.

## Metterla online (gratis)
Guida passo passo per PythonAnywhere: [`deploy/GUIDA_PYTHONANYWHERE.md`](deploy/GUIDA_PYTHONANYWHERE.md).
In breve, dalla console Bash di PythonAnywhere:
```bash
git clone https://github.com/francescobellomosicurezza-beep/900group.git
bash 900group/deploy/installa_pythonanywhere.sh
```
Email (anche in un secondo momento): `bash 900group/deploy/configura_email.sh`.
Aggiornamenti successivi: `bash 900group/deploy/aggiorna.sh`.
Email di prova: `.venv/bin/python manage.py invia_email_prova`.

## Avvio in locale (manuale)
```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```
Credenziali dei punti vendita (in alternativa all'admin):
```bash
.venv/bin/python manage.py crea_accesso_sede spello
.venv/bin/python manage.py crea_accesso_sede bastia
.venv/bin/python manage.py crea_accesso_sede foligno
```
La password viene richiesta in modo interattivo.

In sviluppo le email vengono stampate in console. Per l'invio reale configurare le
variabili in `.env.example`.

## Test
```bash
.venv/bin/python manage.py test novecento
```

## Mappa del codice (Graphify)
In `graphify-out/` c'è il grafo del progetto: `graph.html` (visualizzazione interattiva),
`graph.json` e `GRAPH_REPORT.md`. Per aggiornarlo dopo modifiche al codice:
```bash
pip install graphifyy
graphify update .
```
