from django.db import migrations

SEDI = [
    ("Spello", "spello", "", 1),
    ("Bastia", "bastia", "Piazza Luigi Pirandello – 06083 Bastia Umbra (PG)", 2),
    ("Foligno", "foligno", "", 3),
]

CATALOGO = [
    (
        "Accessori gelato",
        "Coni, coppette, vaschette e accessori per il banco gelato.",
        1,
        [
            ("Coni wafer", "cartoni"),
            ("Cialde piccole", "cartoni"),
            ("Cialde medie", "cartoni"),
            ("Cialde grandi", "cartoni"),
            ("Maxi cialde", "cartoni"),
            ("Coppette baby", "conf"),
            ("Coppette piccole", "conf"),
            ("Coppette medie", "conf"),
            ("Coppette grandi", "conf"),
            ("Vaschette ½ kg", "conf"),
            ("Vaschette 1 kg", "conf"),
            ("Palette / cucchiaini gelato", "conf"),
            ("Panna", "litri"),
        ],
    ),
    (
        "Accessori bar",
        "Materiale di consumo per la caffetteria.",
        2,
        [
            ("Bicchieri caffè da asporto", "conf"),
            ("Bicchieri plastica", "conf"),
            ("Cannucce", "conf"),
            ("Palette caffè", "conf"),
            ("Zucchero in bustine", "conf"),
            ("Tovaglioli", "conf"),
        ],
    ),
]


def carica(apps, schema_editor):
    Sede = apps.get_model("novecento", "Sede")
    Categoria = apps.get_model("novecento", "Categoria")
    Articolo = apps.get_model("novecento", "Articolo")

    for nome, slug, indirizzo, ordine in SEDI:
        Sede.objects.get_or_create(
            slug=slug, defaults={"nome": nome, "indirizzo": indirizzo, "ordine": ordine}
        )

    for nome_cat, descrizione, ordine_cat, articoli in CATALOGO:
        categoria, _ = Categoria.objects.get_or_create(
            nome=nome_cat, defaults={"descrizione": descrizione, "ordine": ordine_cat}
        )
        for posizione, (nome_art, unita) in enumerate(articoli, start=1):
            Articolo.objects.get_or_create(
                categoria=categoria,
                nome=nome_art,
                defaults={"unita": unita, "ordine": posizione},
            )


def rimuovi(apps, schema_editor):
    Articolo = apps.get_model("novecento", "Articolo")
    Categoria = apps.get_model("novecento", "Categoria")
    Sede = apps.get_model("novecento", "Sede")
    nomi_categorie = [c[0] for c in CATALOGO]
    Articolo.objects.filter(categoria__nome__in=nomi_categorie).delete()
    Categoria.objects.filter(nome__in=nomi_categorie).delete()
    Sede.objects.filter(slug__in=[s[1] for s in SEDI], ordini__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("novecento", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(carica, rimuovi),
    ]
