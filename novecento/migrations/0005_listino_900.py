"""Listino 900 (LISTINO_900_categorie_numerate.pdf).

Prezzi, pezzi per cartone e IVA non sono ancora presenti nel listino:
si completano dal pannello di amministrazione.
"""

from django.db import migrations

# (numero, nome, descrizione, icona, [(sottocategoria, [(codice, descrizione, unità)])])
LISTINO = [
    (
        1,
        "Accessori gelateria e yogurteria",
        "Coni, cialde, coppette, contenitori, palette",
        "🍦",
        [
            (
                "Coni e cialde",
                [
                    ("NOCC", "Cono cialda 1071 (grande)", "CT"),
                    ("NOCC", "Cono cialda 1070 (medio)", "CT"),
                    ("NOCC", "Cono cialda 1072 (piccolo)", "CT"),
                    ("NOCC", "Cono wafer 091", "CT"),
                    ("NOCC", "Dischetti cialda 027", "CT"),
                ],
            ),
            (
                "Coppette gelato in cartone",
                [
                    ("ALC", "Coppette cartone baby", "CF"),
                    ("ALC", "Coppette cartone piccole", "CF"),
                    ("ALC", "Coppette cartone medie", "CF"),
                    ("ALC", "Coppette cartone grandi", "CF"),
                ],
            ),
            (
                "Contenitori gelato da asporto",
                [
                    ("ALC", "Contenitori gelato asporto 500", "CF"),
                    ("ALC", "Contenitori gelato asporto 1000", "CF"),
                ],
            ),
            (
                "Yogurteria",
                [
                    ("", "Coppetta piccola per yogurt", "CF"),
                    ("", "Coppetta media per yogurt", "CF"),
                    ("", "Coppetta grande per yogurt", "CF"),
                    ("", "Cucchiaini per yogurt", "CF"),
                ],
            ),
            (
                "Bicchieri granita e frappè",
                [
                    ("ALC", "Bicchiere granita 0,3 cl", "CF"),
                    ("ALC", "Bicchiere frappè 0,4 cl", "CF"),
                ],
            ),
            ("Palette", [("ALC", "Box palette", "CF")]),
        ],
    ),
    (
        2,
        "Salse e granelle per yogurt, farciture per cornetti",
        "Salse yogurt, granelle, farciture croissant",
        "🍓",
        [
            (
                "Salse per yogurt",
                [
                    ("UNI", "Frutti di bosco 3 kg", "CF"),
                    ("UNI", "Brunella pistacchio 5 kg", "CF"),
                    ("AME", "Joycream white 5 kg", "CF"),
                    ("MEC", "Fiordifragola 3 kg", "CF"),
                    ("PRE", "Caramel fleur de sel 3 kg", "CF"),
                    ("LEA", "Choco speculoos (Lotus) 5 kg", "CF"),
                ],
            ),
            (
                "Granelle per yogurt",
                [
                    ("MEC", "Peanut ciuri ciuri 1 kg", "CF"),
                    ("DOL", "Granella nocciola 5 kg", "CF"),
                    ("AME", "Granella pistacchio 1 kg", "CF"),
                    ("MAI", "Granella meringa", "CF"),
                    ("MAI", "Granella extra dark", "CF"),
                    ("MET", "Granella Lotus 1,1 kg", "CF"),
                ],
            ),
            (
                "Farciture per croissant",
                [
                    ("SAI", "My Farcy albicocca 0,9 kg", "CT"),
                    ("SAI", "My Farcy frutti di bosco 0,9 kg", "CT"),
                    ("SAI", "My Farcy miele 0,9 kg", "CT"),
                ],
            ),
        ],
    ),
    (
        3,
        "Accessori bar",
        "Zuccheri, dolcificanti, bicchieri, tovaglioli",
        "☕",
        [
            (
                "Zuccheri e dolcificanti",
                [
                    ("PERS", "Zucchero di canna 10 kg", "CT"),
                    ("PERS", "Zucchero classico 10 kg", "CT"),
                    ("PERS", "Dolcificante 1,4 kg", "CT"),
                ],
            ),
            (
                "Bicchieri",
                [
                    ("ALC", "Bicchiere asporto cappuccino", "CF"),
                    ("ALC", "Bicchiere asporto caffè", "CF"),
                    ("ALC", "Bicchiere acqua", "CF"),
                ],
            ),
            ("Tovaglioli", [("PERS", "Tovaglioli carta bianchi bar", "CT")]),
        ],
    ),
    (
        4,
        "Buste, shopper e involucri per asporto",
        "Buste e shopper Novecento",
        "🛍️",
        [
            (
                "Buste asporto",
                [
                    ("STAMP", "Buste marroni Novecento", "CT"),
                    ("PERS", "Buste bianche asporto Novecento", "CT"),
                ],
            ),
        ],
    ),
    (
        5,
        "Torte gelato, semifreddi e monoporzioni",
        "Torte gelato, semifreddi, monoporzioni",
        "🍰",
        [("Monoporzioni", [("SFE", "Sfere classiche", "CT")])],
    ),
    (
        6,
        "Crostate e torte secche",
        "Crostate, torte da forno",
        "🥧",
        [
            (
                "Crostate",
                [
                    ("", "Crostata albicocca", "PZ"),
                    ("", "Crostata frutti di bosco", "PZ"),
                ],
            ),
            (
                "Torte",
                [
                    ("", "Sacher", "PZ"),
                    ("", "Torta soffice alle carote", "PZ"),
                    ("", "Ciambellone bianco e nero", "PZ"),
                ],
            ),
        ],
    ),
    (
        7,
        "Prodotti surgelati",
        "Cornetteria, forno, ghiaccio",
        "❄️",
        [
            (
                "Cornetteria",
                [
                    ("PDB", "Cornetto vuoto 30 pz", "CT"),
                    ("PDB", "Cornetto multicereali vuoto 30 pz", "CT"),
                    ("PDB", "Saccottino al cioccolato 30 pz", "CT"),
                    ("PAS", "Cornetto al cioccolato", "CT"),
                    ("PAS", "Cornetto vuoto burro", "CT"),
                    ("PAS", "Treccia noci pecan", "CT"),
                    ("GIA", "Croissant vegano all'arancia", "CT"),
                ],
            ),
            ("Forno", [("PAM001", "Torta al testo", "CT")]),
            ("Ghiaccio", [("SOT001", "Ghiaccio a cubetti 10 kg", "CT")]),
        ],
    ),
]


def carica(apps, schema_editor):
    Categoria = apps.get_model("novecento", "Categoria")
    Gruppo = apps.get_model("novecento", "Gruppo")
    Articolo = apps.get_model("novecento", "Articolo")
    for numero, nome, descrizione, icona, gruppi in LISTINO:
        categoria, _ = Categoria.objects.update_or_create(
            numero=numero,
            defaults={"nome": nome, "descrizione": descrizione, "icona": icona},
        )
        for ordine_gruppo, (nome_gruppo, articoli) in enumerate(gruppi, start=1):
            gruppo, _ = Gruppo.objects.update_or_create(
                categoria=categoria, nome=nome_gruppo, defaults={"ordine": ordine_gruppo}
            )
            for ordine_art, (codice, descrizione_art, unita) in enumerate(articoli, start=1):
                Articolo.objects.update_or_create(
                    gruppo=gruppo,
                    nome=descrizione_art,
                    defaults={"codice": codice, "unita": unita, "ordine": ordine_art},
                )


def rimuovi(apps, schema_editor):
    Categoria = apps.get_model("novecento", "Categoria")
    Articolo = apps.get_model("novecento", "Articolo")
    numeri = [c[0] for c in LISTINO]
    Articolo.objects.filter(gruppo__categoria__numero__in=numeri).delete()
    Categoria.objects.filter(numero__in=numeri).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("novecento", "0004_listino_struttura"),
    ]

    operations = [
        migrations.RunPython(carica, rimuovi),
    ]
