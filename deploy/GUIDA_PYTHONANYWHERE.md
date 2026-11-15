# Mettere online Novecento Ordini su PythonAnywhere (gratis)

Tempo: circa 20 minuti. Costo: 0 €.

## Account Gmail per l'invio (si può fare anche dopo l'installazione)

1. Crea un Gmail dedicato, es. `ordini.novecento@gmail.com`.
2. Attiva la **Verifica in due passaggi**: Account Google → Sicurezza.
3. Crea una **Password per le app**: Account Google → Sicurezza → Password per le app
   (oppure cerca "password per le app"). Nome: `Novecento`.
   Google mostra 16 lettere: **copiale**.
   Non sono la password del Gmail e funzionano solo per l'invio.
4. Dalla console Bash di PythonAnywhere:
   `bash 900group/deploy/configura_email.sh`
   (chiede Gmail, password per le app ed email del laboratorio, poi manda un'email di prova).

## 1. Account PythonAnywhere

1. Vai su https://www.pythonanywhere.com → **Pricing & signup** →
   **Create a Beginner account** (gratuito).
2. Lo **username** diventa l'indirizzo del sito: `USERNAME.pythonanywhere.com`.
   Esempio: `novecento900` → `https://novecento900.pythonanywhere.com`.
3. Conferma l'email.

## 2. Installazione (console)

1. Nella Dashboard apri **Consoles → Bash**.
2. Incolla, una riga alla volta:

```bash
git clone https://github.com/francescobellomosicurezza-beep/900group.git
```

```bash
bash 900group/deploy/installa_pythonanywhere.sh
```

3. Lo script chiede:
   - username, email e password dell'**amministratore**
     (mentre scrivi le password non si vede nulla, è normale);
   - una password per ciascuna sede (**spello**, **bastia**, **foligno**);
   - se configurare subito l'email: rispondi `n` se il Gmail non è ancora pronto,
     lo farai dopo con `configura_email.sh`.

   Alla fine stampa le impostazioni per la scheda Web: **lascia aperta la console**.

## 3. Scheda Web

1. Menu in alto → **Web** → **Add a new web app** → Next →
   **Manual configuration** (non "Django") → scegli la versione di Python più alta → Next.
2. Nella pagina della web app compila:
   - **Virtualenv**: `/home/USERNAME/900group/.venv`
   - **Static files**: URL `/static/` → Directory `/home/USERNAME/900group/staticfiles`
   - **Force HTTPS**: attivo
3. Clicca il link **WSGI configuration file**, cancella tutto il contenuto e incolla
   il blocco stampato dallo script. Salva.
4. In alto clicca il pulsante verde **Reload**.
5. Apri `https://USERNAME.pythonanywhere.com`: compare la pagina di accesso.

## 4. Ultime impostazioni (dal sito)

Entra in `https://USERNAME.pythonanywhere.com/admin/` con l'amministratore:

- **Sedi**: per ogni 900 imposta l'orario e i giorni dell'ordine e, se vuoi, l'email della sede.
- **Impostazioni**: verifica l'email del laboratorio; puoi aggiungerne altre.
- **Articoli**: completa codici, prezzi, pezzi per cartone e IVA quando li hai.

Poi su ogni telefono o tablet delle sedi:
1. apri il sito ed entra con le credenziali della sede;
2. **iPhone**: Condividi → *Aggiungi alla schermata Home*;
   **Android**: menu ⋮ → *Aggiungi a schermata Home*;
3. nella pagina delle categorie tocca **Ricevi il promemoria sul telefono**.

## 5. Ogni 3 mesi (importante)

Il piano gratuito spegne il sito se nessuno lo rinnova:
**Web** → pulsante **Run until 3 months from today**.
Metti subito un promemoria nel tuo calendario.
PythonAnywhere manda anche un'email prima della scadenza.

## Aggiornare il sito a una nuova versione

Quando ci sono modifiche su GitHub, dalla console Bash:

```bash
bash 900group/deploy/aggiorna.sh
```

Lo script fa un backup del database (tiene gli ultimi 5), scarica la nuova
versione, aggiorna il database e ricarica il sito.

## Problemi frequenti

| Sintomo | Soluzione |
|---|---|
| "Something went wrong" o errore 500 | Web → **Error log**: l'ultima riga indica la causa |
| Bad Request (400) | Nel file `.env` controlla `DJANGO_ALLOWED_HOSTS=USERNAME.pythonanywhere.com` |
| Pagina senza grafica | Controlla la riga **Static files** e premi Reload |
| Email non partite | In console: `cd 900group && .venv/bin/python manage.py invia_email_prova` e leggi l'errore; di solito è la password per le app |
| Ho perso una password delle sedi | Admin → Sedi → apri la sede → **Nuova password** |

Il file `/home/USERNAME/900group/.env` contiene le password: non condividerlo e non caricarlo su GitHub (è già escluso).
