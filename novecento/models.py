from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MinValueValidator
from django.db import models


class Sede(models.Model):
    nome = models.CharField("nome", max_length=100, unique=True)
    slug = models.SlugField("slug", max_length=100, unique=True)
    indirizzo = models.CharField("indirizzo", max_length=200, blank=True)
    email = models.EmailField(
        "email sede",
        blank=True,
        help_text="Se valorizzata, riceve in copia il PDF degli ordini della sede.",
    )
    pin_hash = models.CharField("PIN (hash)", max_length=128, blank=True, editable=False)
    attiva = models.BooleanField("attiva", default=True)
    ordine = models.PositiveSmallIntegerField("ordine di visualizzazione", default=0)

    class Meta:
        verbose_name = "sede"
        verbose_name_plural = "sedi"
        ordering = ["ordine", "nome"]

    def __str__(self):
        return self.nome

    @property
    def richiede_pin(self):
        return bool(self.pin_hash)

    def imposta_pin(self, pin):
        self.pin_hash = make_password(pin) if pin else ""

    def verifica_pin(self, pin):
        if not self.pin_hash:
            return True
        return bool(pin) and check_password(pin, self.pin_hash)


class Categoria(models.Model):
    nome = models.CharField("nome", max_length=100, unique=True)
    descrizione = models.CharField("descrizione", max_length=255, blank=True)
    ordine = models.PositiveSmallIntegerField("ordine di visualizzazione", default=0)
    attiva = models.BooleanField("attiva", default=True)

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorie"
        ordering = ["ordine", "nome"]

    def __str__(self):
        return self.nome


class Articolo(models.Model):
    class Unita(models.TextChoices):
        PEZZI = "pz", "pezzi"
        CONFEZIONI = "conf", "confezioni"
        CARTONI = "cartoni", "cartoni"
        VASCHETTE = "vaschette", "vaschette"
        KG = "kg", "kg"
        LITRI = "litri", "litri"

    categoria = models.ForeignKey(
        Categoria,
        verbose_name="categoria",
        on_delete=models.PROTECT,
        related_name="articoli",
    )
    nome = models.CharField("nome", max_length=150)
    descrizione = models.CharField("descrizione", max_length=255, blank=True)
    unita = models.CharField(
        "unità di misura", max_length=20, choices=Unita.choices, default=Unita.PEZZI
    )
    attivo = models.BooleanField("attivo", default=True)
    ordine = models.PositiveSmallIntegerField("ordine di visualizzazione", default=0)

    class Meta:
        verbose_name = "articolo"
        verbose_name_plural = "articoli"
        ordering = ["categoria__ordine", "ordine", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["categoria", "nome"], name="articolo_unico_per_categoria"
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.get_unita_display()})"


class Ordine(models.Model):
    class StatoInvio(models.TextChoices):
        IN_ATTESA = "in_attesa", "In attesa"
        INVIATO = "inviato", "Inviato"
        ERRORE = "errore", "Errore di invio"

    sede = models.ForeignKey(
        Sede, verbose_name="sede", on_delete=models.PROTECT, related_name="ordini"
    )
    nome = models.CharField("nome", max_length=80)
    cognome = models.CharField("cognome", max_length=80)
    note = models.TextField("note", blank=True)
    creato_il = models.DateTimeField("creato il", auto_now_add=True)
    stato_invio = models.CharField(
        "stato invio",
        max_length=20,
        choices=StatoInvio.choices,
        default=StatoInvio.IN_ATTESA,
    )
    inviato_il = models.DateTimeField("inviato il", null=True, blank=True)
    errore_invio = models.TextField("dettaglio errore", blank=True)

    class Meta:
        verbose_name = "ordine"
        verbose_name_plural = "ordini"
        ordering = ["-creato_il"]

    def __str__(self):
        return f"Ordine n. {self.numero} – {self.sede}"

    @property
    def numero(self):
        return f"{self.creato_il:%Y}-{self.pk:05d}" if self.pk and self.creato_il else "-"

    @property
    def operatore(self):
        return f"{self.nome} {self.cognome}".strip()

    @property
    def totale_righe(self):
        return self.righe.count()


class RigaOrdine(models.Model):
    """Riga d'ordine con copia dei dati dell'articolo al momento dell'invio."""

    ordine = models.ForeignKey(
        Ordine, verbose_name="ordine", on_delete=models.CASCADE, related_name="righe"
    )
    articolo = models.ForeignKey(
        Articolo,
        verbose_name="articolo",
        on_delete=models.SET_NULL,
        null=True,
        related_name="righe_ordine",
    )
    categoria_nome = models.CharField("categoria", max_length=100)
    articolo_nome = models.CharField("articolo", max_length=150)
    unita = models.CharField("unità di misura", max_length=20)
    quantita = models.PositiveIntegerField("quantità", validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "riga d'ordine"
        verbose_name_plural = "righe d'ordine"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.articolo_nome} × {self.quantita} {self.unita}"
