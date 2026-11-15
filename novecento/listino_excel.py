"""Esportazione e importazione del listino in formato Excel (.xlsx)."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.db import transaction
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .models import Articolo, Categoria, Gruppo

FOGLIO = "Listino"
COLONNE = [
    ("ID", 8),
    ("N. categoria", 12),
    ("Categoria", 34),
    ("Sottocategoria", 30),
    ("Codice", 14),
    ("Descrizione", 44),
    ("Unità (CT/CF/PZ)", 16),
    ("Pezzi per cartone", 16),
    ("Prezzo al pezzo", 15),
    ("Prezzo per cartone", 17),
    ("IVA %", 8),
    ("Attivo (SI/NO)", 14),
]
UNITA_VALIDE = {u.value for u in Articolo.Unita}
IVA_VALIDE = {i.value for i in Articolo.Iva}
MARRONE = "4E2E22"
CREMA = "F2EEE9"

ISTRUZIONI = [
    "COME USARE QUESTO FILE",
    "",
    "1. Modifica le righe del foglio «Listino»: codice, descrizione, unità, pezzi per cartone, prezzi, IVA, attivo.",
    "2. Per AGGIUNGERE un articolo: nuova riga con la colonna ID VUOTA, numero categoria, sottocategoria e descrizione.",
    "   Se la sottocategoria non esiste viene creata. La categoria deve esistere (oppure scrivi anche il nome per crearla).",
    "3. Per TOGLIERE un articolo dagli ordini: scrivi NO in «Attivo». Non cancellare le righe.",
    "4. Non modificare la colonna ID delle righe esistenti: serve a riconoscere l'articolo.",
    "5. Unità: CT = cartone, CF = confezione, PZ = pezzo. IVA: 4, 5, 10 o 22. Prezzi con la virgola o il punto.",
    "6. Salva il file e caricalo da Admin › Articoli › «Importa da Excel».",
    "   Se una riga contiene un errore non viene modificato nulla e il sito indica la riga da correggere.",
]


@dataclass
class EsitoImportazione:
    creati: int = 0
    aggiornati: int = 0
    invariati: int = 0
    gruppi_creati: list = field(default_factory=list)
    categorie_create: list = field(default_factory=list)
    errori: list = field(default_factory=list)

    @property
    def riuscita(self):
        return not self.errori


def esporta_listino():
    """Restituisce il file .xlsx del listino completo."""
    libro = Workbook()
    foglio = libro.active
    foglio.title = FOGLIO
    intestazione_font = Font(bold=True, color="FFFFFF")
    intestazione_sfondo = PatternFill("solid", fgColor=MARRONE)

    for indice, (titolo, larghezza) in enumerate(COLONNE, start=1):
        cella = foglio.cell(row=1, column=indice, value=titolo)
        cella.font = intestazione_font
        cella.fill = intestazione_sfondo
        cella.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        foglio.column_dimensions[get_column_letter(indice)].width = larghezza
    foglio.row_dimensions[1].height = 30
    foglio.freeze_panes = "A2"

    articoli = Articolo.objects.select_related("gruppo", "gruppo__categoria").order_by(
        "gruppo__categoria__numero", "gruppo__ordine", "ordine", "nome"
    )
    riga = 2
    for articolo in articoli:
        categoria = articolo.gruppo.categoria
        foglio.append(
            [
                articolo.pk,
                categoria.numero,
                categoria.nome,
                articolo.gruppo.nome,
                articolo.codice,
                articolo.nome,
                articolo.unita,
                articolo.pezzi_per_cartone,
                float(articolo.prezzo_pezzo) if articolo.prezzo_pezzo is not None else None,
                float(articolo.prezzo_cartone) if articolo.prezzo_cartone is not None else None,
                articolo.iva,
                "SI" if articolo.attivo else "NO",
            ]
        )
        if categoria.numero % 2 == 0:
            for colonna in range(1, len(COLONNE) + 1):
                foglio.cell(row=riga, column=colonna).fill = PatternFill("solid", fgColor=CREMA)
        foglio.cell(row=riga, column=9).number_format = "#,##0.000 €"
        foglio.cell(row=riga, column=10).number_format = "#,##0.00 €"
        riga += 1

    ultima = max(riga + 500, 1000)
    for formula, colonna in [('"CT,CF,PZ"', "G"), ('"4,5,10,22"', "K"), ('"SI,NO"', "L")]:
        validazione = DataValidation(type="list", formula1=formula, allow_blank=True)
        validazione.add(f"{colonna}2:{colonna}{ultima}")
        foglio.add_data_validation(validazione)
    foglio.auto_filter.ref = f"A1:{get_column_letter(len(COLONNE))}{max(riga - 1, 1)}"

    istruzioni = libro.create_sheet("Istruzioni")
    istruzioni.column_dimensions["A"].width = 120
    for numero, testo in enumerate(ISTRUZIONI, start=1):
        cella = istruzioni.cell(row=numero, column=1, value=testo)
        if numero == 1:
            cella.font = Font(bold=True, size=13, color=MARRONE)

    buffer = BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def _testo(valore):
    if valore is None:
        return ""
    if isinstance(valore, float) and valore.is_integer():
        valore = int(valore)
    return str(valore).strip()


def _intero(valore, nome, minimo=0):
    testo = _testo(valore)
    if not testo:
        return None
    try:
        numero = int(Decimal(testo.replace(",", ".")))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{nome}: «{testo}» non è un numero intero") from None
    if numero < minimo:
        raise ValueError(f"{nome}: deve essere almeno {minimo}")
    return numero


def _decimale(valore, nome, cifre):
    testo = _testo(valore).replace("€", "").replace(" ", "")
    if not testo:
        return None
    if "," in testo:
        testo = testo.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(testo)
    except InvalidOperation:
        raise ValueError(f"{nome}: «{_testo(valore)}» non è un prezzo valido") from None
    if numero < 0:
        raise ValueError(f"{nome}: non può essere negativo")
    return numero.quantize(Decimal(1).scaleb(-cifre))


def _riga_vuota(valori):
    return all(_testo(v) == "" for v in valori)


def importa_listino(file):
    """Aggiorna e crea articoli dal file Excel. Tutto o niente."""
    esito = EsitoImportazione()
    try:
        libro = load_workbook(file, data_only=True, read_only=True)
    except Exception:  # file non leggibile come .xlsx
        esito.errori.append("Il file non è un Excel (.xlsx) valido.")
        return esito
    if FOGLIO not in libro.sheetnames:
        esito.errori.append(f"Nel file manca il foglio «{FOGLIO}».")
        return esito

    righe = list(libro[FOGLIO].iter_rows(min_row=1, values_only=True))
    if not righe or _testo(righe[0][0]).upper() != "ID":
        esito.errori.append("La prima riga deve contenere le intestazioni del file esportato.")
        return esito

    esistenti = {a.pk: a for a in Articolo.objects.select_related("gruppo", "gruppo__categoria")}
    categorie = {c.numero: c for c in Categoria.objects.all()}
    gruppi = {(g.categoria_id, g.nome.lower()): g for g in Gruppo.objects.all()}
    visti = set()

    try:
        with transaction.atomic():
            for numero_riga, valori in enumerate(righe[1:], start=2):
                valori = list(valori) + [None] * (len(COLONNE) - len(valori))
                if _riga_vuota(valori[: len(COLONNE)]):
                    continue
                try:
                    _importa_riga(valori, esito, esistenti, categorie, gruppi, visti)
                except ValueError as errore:
                    esito.errori.append(f"Riga {numero_riga}: {errore}")
            if esito.errori:
                raise _Annulla
    except _Annulla:
        esito.creati = esito.aggiornati = esito.invariati = 0
        esito.gruppi_creati, esito.categorie_create = [], []
    return esito


class _Annulla(Exception):
    pass


def _importa_riga(valori, esito, esistenti, categorie, gruppi, visti):
    (id_art, num_cat, nome_cat, nome_gruppo, codice, descrizione, unita, pezzi,
     prezzo_pz, prezzo_ct, iva, attivo) = valori[: len(COLONNE)]

    descrizione = _testo(descrizione)
    nome_gruppo = _testo(nome_gruppo)
    if not descrizione:
        raise ValueError("manca la descrizione")
    if len(descrizione) > 150:
        raise ValueError("descrizione troppo lunga (max 150 caratteri)")
    unita = (_testo(unita) or "CF").upper()
    if unita not in UNITA_VALIDE:
        raise ValueError(f"unità «{unita}» non valida (usa CT, CF o PZ)")
    iva = _intero(iva, "IVA")
    if iva is not None and iva not in IVA_VALIDE:
        raise ValueError(f"IVA {iva}% non valida (usa 4, 5, 10 o 22)")
    attivo_testo = (_testo(attivo) or "SI").upper()
    if attivo_testo not in {"SI", "SÌ", "NO"}:
        raise ValueError("«Attivo» deve essere SI o NO")
    codice = _testo(codice)
    if len(codice) > 30:
        raise ValueError("codice troppo lungo (max 30 caratteri)")

    campi = {
        "codice": codice,
        "nome": descrizione,
        "unita": unita,
        "pezzi_per_cartone": _intero(pezzi, "Pezzi per cartone", minimo=1),
        "prezzo_pezzo": _decimale(prezzo_pz, "Prezzo al pezzo", 3),
        "prezzo_cartone": _decimale(prezzo_ct, "Prezzo per cartone", 2),
        "iva": iva,
        "attivo": attivo_testo != "NO",
    }

    numero_cat = _intero(num_cat, "N. categoria", minimo=1)
    categoria = categorie.get(numero_cat) if numero_cat else None
    if numero_cat and categoria is None:
        nome_categoria = _testo(nome_cat)
        if not nome_categoria:
            raise ValueError(f"la categoria {numero_cat} non esiste: scrivi anche il nome per crearla")
        categoria = Categoria.objects.create(numero=numero_cat, nome=nome_categoria)
        categorie[numero_cat] = categoria
        esito.categorie_create.append(str(categoria))

    id_articolo = _intero(id_art, "ID", minimo=1)
    articolo = None
    if id_articolo:
        articolo = esistenti.get(id_articolo)
        if articolo is None:
            raise ValueError(f"ID {id_articolo} non trovato: per un articolo nuovo lascia vuoto l'ID")
        if id_articolo in visti:
            raise ValueError(f"ID {id_articolo} ripetuto due volte")
        visti.add(id_articolo)

    if categoria is None and articolo is None:
        raise ValueError("per un articolo nuovo indica il numero di categoria")
    categoria = categoria or articolo.gruppo.categoria

    if nome_gruppo:
        chiave = (categoria.pk, nome_gruppo.lower())
        gruppo = gruppi.get(chiave)
        if gruppo is None:
            gruppo = Gruppo.objects.create(
                categoria=categoria, nome=nome_gruppo, ordine=categoria.gruppi.count() + 1
            )
            gruppi[chiave] = gruppo
            esito.gruppi_creati.append(str(gruppo))
    elif articolo is not None:
        gruppo = articolo.gruppo
    else:
        raise ValueError("per un articolo nuovo indica la sottocategoria")

    duplicato = Articolo.objects.filter(gruppo=gruppo, nome__iexact=descrizione)
    if articolo is not None:
        duplicato = duplicato.exclude(pk=articolo.pk)
    if duplicato.exists():
        raise ValueError(f"«{descrizione}» esiste già in «{gruppo.nome}»")

    if articolo is None:
        Articolo.objects.create(
            gruppo=gruppo, ordine=gruppo.articoli.count() + 1, **campi
        )
        esito.creati += 1
        return

    campi["gruppo"] = gruppo
    modificati = [k for k, v in campi.items() if getattr(articolo, k) != v]
    if not modificati:
        esito.invariati += 1
        return
    for chiave in modificati:
        setattr(articolo, chiave, campi[chiave])
    articolo.save(update_fields=modificati)
    esito.aggiornati += 1
