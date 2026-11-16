from django.db import migrations, models

NOMI_BREVI = {
    1: "Gelateria e yogurt",
    2: "Salse e granelle",
    3: "Bar",
    4: "Buste e asporto",
    5: "Torte gelato",
    6: "Crostate e torte",
    7: "Surgelati",
}


def imposta_nomi_brevi(apps, schema_editor):
    Categoria = apps.get_model("novecento", "Categoria")
    for numero, nome in NOMI_BREVI.items():
        Categoria.objects.filter(numero=numero, nome_breve="").update(nome_breve=nome)


class Migration(migrations.Migration):
    dependencies = [
        ("novecento", "0007_email_da_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="categoria",
            name="nome_breve",
            field=models.CharField(
                blank=True,
                help_text="Nome corto per la griglia dell'app (es. «Bar»). Se vuoto si usa il nome.",
                max_length=30,
                verbose_name="nome breve",
            ),
        ),
        migrations.RunPython(imposta_nomi_brevi, migrations.RunPython.noop),
    ]
