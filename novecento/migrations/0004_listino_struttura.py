import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def svuota_catalogo_demo(apps, schema_editor):
    """Rimuove il catalogo di esempio: gli ordini storici conservano i nomi copiati."""
    apps.get_model("novecento", "Articolo").objects.all().delete()
    apps.get_model("novecento", "Categoria").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("novecento", "0003_account_sede"),
    ]

    operations = [
        migrations.RunPython(svuota_catalogo_demo, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name="articolo", name="articolo_unico_per_categoria"),
        migrations.RemoveField(model_name="articolo", name="categoria"),
        migrations.RemoveField(model_name="articolo", name="descrizione"),
        migrations.RemoveField(model_name="categoria", name="ordine"),
        migrations.AddField(
            model_name="categoria",
            name="numero",
            field=models.PositiveSmallIntegerField(default=0, unique=True, verbose_name="numero"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="categoria",
            name="icona",
            field=models.CharField(
                blank=True, help_text="Un'emoji, es. 🍦", max_length=8, verbose_name="icona"
            ),
        ),
        migrations.AlterField(
            model_name="categoria",
            name="nome",
            field=models.CharField(max_length=120, unique=True, verbose_name="nome"),
        ),
        migrations.AlterField(
            model_name="categoria",
            name="descrizione",
            field=models.CharField(
                blank=True,
                help_text="Esempi di contenuto, mostrati sotto il nome.",
                max_length=255,
                verbose_name="descrizione",
            ),
        ),
        migrations.AlterModelOptions(
            name="categoria",
            options={
                "ordering": ["numero"],
                "verbose_name": "categoria",
                "verbose_name_plural": "categorie",
            },
        ),
        migrations.CreateModel(
            name="Gruppo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=120, verbose_name="nome")),
                ("ordine", models.PositiveSmallIntegerField(default=0, verbose_name="ordine di visualizzazione")),
                ("attivo", models.BooleanField(default=True, verbose_name="attivo")),
                (
                    "categoria",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gruppi",
                        to="novecento.categoria",
                        verbose_name="categoria",
                    ),
                ),
            ],
            options={
                "verbose_name": "sottocategoria",
                "verbose_name_plural": "sottocategorie",
                "ordering": ["categoria__numero", "ordine", "nome"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("categoria", "nome"), name="gruppo_unico_per_categoria"
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="articolo",
            name="gruppo",
            field=models.ForeignKey(
                default=0,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="articoli",
                to="novecento.gruppo",
                verbose_name="sottocategoria",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="articolo",
            name="codice",
            field=models.CharField(blank=True, max_length=30, verbose_name="codice"),
        ),
        migrations.AlterField(
            model_name="articolo",
            name="nome",
            field=models.CharField(max_length=150, verbose_name="descrizione"),
        ),
        migrations.AlterField(
            model_name="articolo",
            name="unita",
            field=models.CharField(
                choices=[("CT", "cartone"), ("CF", "confezione"), ("PZ", "pezzo")],
                default="CF",
                max_length=2,
                verbose_name="unità di vendita",
            ),
        ),
        migrations.AddField(
            model_name="articolo",
            name="pezzi_per_cartone",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="pezzi per cartone"),
        ),
        migrations.AddField(
            model_name="articolo",
            name="prezzo_pezzo",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=9,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="prezzo al pezzo (€)",
            ),
        ),
        migrations.AddField(
            model_name="articolo",
            name="prezzo_cartone",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=9,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="prezzo per cartone (€)",
            ),
        ),
        migrations.AddField(
            model_name="articolo",
            name="iva",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(4, "4%"), (5, "5%"), (10, "10%"), (22, "22%")],
                null=True,
                verbose_name="IVA",
            ),
        ),
        migrations.AlterModelOptions(
            name="articolo",
            options={
                "ordering": ["gruppo__categoria__numero", "gruppo__ordine", "ordine", "nome"],
                "verbose_name": "articolo",
                "verbose_name_plural": "articoli",
            },
        ),
        migrations.AddConstraint(
            model_name="articolo",
            constraint=models.UniqueConstraint(
                fields=("gruppo", "nome"), name="articolo_unico_per_gruppo"
            ),
        ),
        migrations.AlterField(
            model_name="rigaordine",
            name="categoria_nome",
            field=models.CharField(max_length=130, verbose_name="categoria"),
        ),
        migrations.AddField(
            model_name="rigaordine",
            name="gruppo_nome",
            field=models.CharField(blank=True, max_length=120, verbose_name="sottocategoria"),
        ),
        migrations.AddField(
            model_name="rigaordine",
            name="codice",
            field=models.CharField(blank=True, max_length=30, verbose_name="codice"),
        ),
        migrations.AlterField(
            model_name="rigaordine",
            name="unita",
            field=models.CharField(max_length=20, verbose_name="unità di vendita"),
        ),
        migrations.CreateModel(
            name="Impostazioni",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "email_destinatari",
                    models.TextField(
                        blank=True,
                        help_text="Uno o più indirizzi separati da virgola o a capo. "
                        "Se vuoto si usa la configurazione del server.",
                        verbose_name="email che ricevono gli ordini",
                    ),
                ),
            ],
            options={"verbose_name": "impostazioni", "verbose_name_plural": "impostazioni"},
        ),
    ]
