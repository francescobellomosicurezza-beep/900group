# Stato del progetto – Novecento Ordini

Ultimo aggiornamento: 16/11/2026

## Cosa c'è e funziona
- **Sito online**: https://novecento900.pythonanywhere.com (PythonAnywhere, piano gratuito Beginner).
- **Accessi creati** (le password NON sono qui: stanno nel gestore password del cliente):
  - amministratore `/admin/`: utente `novecento900`;
  - sedi: `spello`, `bastia`, `foligno`.
- **Flusso ordine**: accesso sede → chi sei (operatori recenti) → 7 categorie del listino →
  sottocategorie a fisarmonica con salvataggio automatico → riepilogo → PDF via email.
- **Aiuti**: ricerca, "ultimo ordine: N", ripeti ultimo ordine, barra carrello.
- **Orario d'ordine per sede** (admin → Sedi): avviso in app giallo/rosso/verde e
  promemoria ricorrente da aggiungere al calendario del telefono (.ics).
- **Listino 900**: 7 categorie, 17 sottocategorie, 57 articoli. Codici e prezzi provvisori.
  Gestione massiva da admin → Articoli → Esporta/Importa Excel.
- **Destinatari email e Gmail mittente** da admin → Impostazioni (con «Salva e invia email di prova»).
- **Interfaccia premium** (16/11/2026): barra compatta, home a griglia con nomi brevi delle
  categorie, sottocategorie a etichette scorrevoli, "+" che diventa "− n +", carrello flottante,
  riepilogo modificabile, conferma animata, app installabile sulla schermata Home (manifest + icone).
- **Identità del marchio** (dal sito gelaterianovecento.it): logo originale in barra, accesso e
  icona dell'app; colori esatti del logo (#53352A, #BC9944); foto "onde" del sito come sfondo;
  icone disegnate per categoria (scelta da admin → Categorie → «icona nell'app»).

## Da fare (prossimi passi)
1. **Email** (la fa il titolare, account dell'azienda). Due opzioni:
   - consigliata: Gmail nuovo solo per l'invio (es. ordini.novecento@gmail.com, recupero sul
     Gmail aziendale);
   - alternativa: il Gmail di Novecento già in uso.
   In entrambi i casi: verifica in due passaggi + "password per le app" (16 lettere).
   Servono: indirizzo mittente, 16 lettere, email del laboratorio che riceve.
   Si inseriscono da **admin → Impostazioni** (anche da telefono) → «Salva e invia email di prova».
   In alternativa da console: `bash 900group/deploy/configura_email.sh`.
   - ✅ Verificato il 16/11/2026: l'invio via Gmail funziona sul piano gratuito
     (prova fatta con un Gmail personale di Francesco; da sostituire con quello di Novecento
     e poi revocare la password per le app personale).
2. Impostare **orario e giorni d'ordine** di Spello, Bastia e Foligno (admin → Sedi).
3. Caricare **codici veri** (e poi prezzi/IVA) con Esporta/Importa Excel.
4. Sui telefoni delle sedi: "Aggiungi alla schermata Home" + "Ricevi il promemoria sul telefono".
5. Correggere se confermato: "Bicchiere granita 0,3 cl" / "frappè 0,4 cl" (probabilmente litri).

## Partenza consigliata
- Ordine di prova completo e controllo del PDF con chi legge gli ordini in laboratorio.
- Una sede pilota (es. Foligno) per una settimana, poi Bastia e Spello.
- Formazione di 10 minuti per sede: icona su schermata Home, promemoria nel calendario, ordine guidato.
- Proposta commerciale e nomina GDPR (art. 28) firmate prima della partenza ufficiale.

## Manutenzione
- **Ogni 3 mesi**: PythonAnywhere → Web → "Run until 3 months from today".
- **Aggiornare il sito** dopo modifiche su GitHub: `bash 900group/deploy/aggiorna.sh`
  (backup del database incluso).
- Prova locale: scaricare lo ZIP da GitHub e avviare `avvia.bat` / `avvia.command`
  (credenziali demo nel README, solo in locale).

## Idee per le fasi successive
- Promemoria automatici via email/Telegram (richiedono operazioni programmate: piano Developer).
- Ruoli (sede, laboratorio, titolare, consulente).
- HACCP e scadenze sicurezza (registro temperature, pulizie, lotti, formazione).
- Magazzino e ordini ai fornitori; chiusure di cassa e cruscotto del titolare.
- Listino diverso per sede.
