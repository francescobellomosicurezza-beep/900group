import datetime

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

GIORNI_SETTIMANA = [
    ("0", "Lunedì"),
    ("1", "Martedì"),
    ("2", "Mercoledì"),
    ("3", "Giovedì"),
    ("4", "Venerdì"),
    ("5", "Sabato"),
    ("6", "Domenica"),
]


class Sede(models.Model):
    nome = models.CharField("nome", max_length=100, unique=True)
    slug = models.SlugField("slug", max_length=100, unique=True)
    indirizzo = models.CharField("indirizzo", max_length=200, blank=True)
    email = models.EmailField(
        "email sede",
        blank=True,
        help_text="Se valorizzata, riceve in copia il PDF degli ordini della sede.",
    )
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="account di accesso",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sede",
    )
    orario_ordine = models.TimeField(
        "ordine da inviare entro le",
        null=True,
        blank=True,
        help_text="Lasciare vuoto per non mostrare avvisi.",
    )
    giorni_ordine = models.CharField(
        "giorni dell'ordine",
        max_length=7,
        default="0123456",
        blank=True,
        help_text="Giorni della settimana in cui la sede deve ordinare.",
    )
    preavviso_minuti = models.PositiveSmallIntegerField(
        "preavviso (minuti)",
        default=30,
        validators=[MaxValueValidator(720)],
        help_text="Quanto prima dell'orario suona il promemoria sul telefono.",
    )
    attiva = models.BooleanField("attiva", default=True)
    ordine = models.PositiveSmallIntegerField("ordine di visualizzazione", default=0)

    class Meta:
        verbose_name = "sede"
        verbose_name_plural = "sedi"
        ordering = ["ordine", "nome"]

    def __str__(self):
        return self.nome

    @classmethod
    def per_utente(cls, utente):
        """Sede collegata all'account, se attiva."""
        sede = getattr(utente, "sede", None)
        return sede if sede is not None and sede.attiva else None

    def ordina_il(self, data):
        return str(data.weekday()) in (self.giorni_ordine or "")

    def giorni_display(self):
        etichette = dict(GIORNI_SETTIMANA)
        giorni = [etichette[g][:3] for g in sorted(set(self.giorni_ordine or "")) if g in etichette]
        if len(giorni) == 7:
            return "tutti i giorni"
        return ", ".join(giorni) or "nessun giorno"

    def stato_ordine(self, adesso=None):
        """Stato dell'ordine di oggi per l'avviso in app, oppure None se non previsto."""
        adesso = timezone.localtime(adesso or timezone.now())
        oggi = adesso.date()
        inviato = (
            self.ordini.filter(creato_il__date=oggi).order_by("creato_il").first()
            if self.pk
            else None
        )
        if inviato:
            return {"stato": "inviato", "ordine": inviato, "ora": timezone.localtime(inviato.creato_il)}
        if not self.orario_ordine or not self.ordina_il(oggi):
            return None
        scadenza = timezone.make_aware(
            datetime.datetime.combine(oggi, self.orario_ordine), adesso.tzinfo
        )
        minuti = int((scadenza - adesso).total_seconds() // 60)
        if minuti < 0:
            return {"stato": "in_ritardo", "scadenza": scadenza, "ritardo": -minuti}
        return {
            "stato": "da_fare",
            "scadenza": scadenza,
            "minuti": minuti,
            "urgente": minuti <= self.preavviso_minuti,
        }


class Categoria(models.Model):
    """Macrocategoria del listino (es. 1 - Accessori gelateria e yogurteria)."""

    class Simbolo(models.TextChoices):
        GELATO = "gelato", "Cono gelato"
        SALSE = "salse", "Barattolo salse"
        BAR = "bar", "Tazza caffè"
        ASPORTO = "asporto", "Busta asporto"
        TORTE = "torte", "Torta"
        CROSTATE = "crostate", "Fetta di crostata"
        SURGELATI = "surgelati", "Fiocco di neve"
        CORNETTI = "cornetti", "Cornetto"
        BEVANDE = "bevande", "Bottiglia"
        PULIZIA = "pulizia", "Pulizia"
        GENERICO = "generico", "Scatola"

    numero = models.PositiveSmallIntegerField("numero", unique=True)
    nome = models.CharField("nome", max_length=120, unique=True)
    nome_breve = models.CharField(
        "nome breve",
        max_length=30,
        blank=True,
        help_text="Nome corto per la griglia dell'app (es. «Bar»). Se vuoto si usa il nome.",
    )
    descrizione = models.CharField(
        "descrizione",
        max_length=255,
        blank=True,
        help_text="Esempi di contenuto, mostrati sotto il nome.",
    )
    icona = models.CharField(
        "emoji", max_length=8, blank=True, help_text="Facoltativa, es. 🍦"
    )
    simbolo = models.CharField(
        "icona nell'app",
        max_length=20,
        choices=Simbolo.choices,
        default=Simbolo.GENERICO,
    )
    attiva = models.BooleanField("attiva", default=True)

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorie"
        ordering = ["numero"]

    def __str__(self):
        return f"{self.numero} - {self.nome}"

    @property
    def etichetta(self):
        return self.nome_breve or self.nome


class Gruppo(models.Model):
    """Sottocategoria che raggruppa le varianti di uno stesso prodotto (es. Coni)."""

    categoria = models.ForeignKey(
        Categoria,
        verbose_name="categoria",
        on_delete=models.CASCADE,
        related_name="gruppi",
    )
    nome = models.CharField("nome", max_length=120)
    ordine = models.PositiveSmallIntegerField("ordine di visualizzazione", default=0)
    attivo = models.BooleanField("attivo", default=True)

    class Meta:
        verbose_name = "sottocategoria"
        verbose_name_plural = "sottocategorie"
        ordering = ["categoria__numero", "ordine", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["categoria", "nome"], name="gruppo_unico_per_categoria"
            )
        ]

    def __str__(self):
        return f"{self.categoria.nome} › {self.nome}"


class Articolo(models.Model):
    class Unita(models.TextChoices):
        CARTONE = "CT", "cartone"
        CONFEZIONE = "CF", "confezione"
        PEZZO = "PZ", "pezzo"

    class Iva(models.IntegerChoices):
        QUATTRO = 4, "4%"
        CINQUE = 5, "5%"
        DIECI = 10, "10%"
        VENTIDUE = 22, "22%"

    gruppo = models.ForeignKey(
        Gruppo,
        verbose_name="sottocategoria",
        on_delete=models.PROTECT,
        related_name="articoli",
    )
    codice = models.CharField("codice", max_length=30, blank=True)
    nome = models.CharField("descrizione", max_length=150)
    unita = models.CharField(
        "unità di vendita", max_length=2, choices=Unita.choices, default=Unita.CONFEZIONE
    )
    pezzi_per_cartone = models.PositiveIntegerField("pezzi per cartone", null=True, blank=True)
    prezzo_pezzo = models.DecimalField(
        "prezzo al pezzo (€)",
        max_digits=9,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    prezzo_cartone = models.DecimalField(
        "prezzo per cartone (€)",
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    iva = models.PositiveSmallIntegerField("IVA", choices=Iva.choices, null=True, blank=True)
    attivo = models.BooleanField("attivo", default=True)
    ordine = models.PositiveSmallIntegerField("ordine di visualizzazione", default=0)

    class Meta:
        verbose_name = "articolo"
        verbose_name_plural = "articoli"
        ordering = ["gruppo__categoria__numero", "gruppo__ordine", "ordine", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["gruppo", "nome"], name="articolo_unico_per_gruppo")
        ]

    def __str__(self):
        return self.nome

    PLURALI = {"CT": "cartoni", "CF": "confezioni", "PZ": "pezzi"}

    def unita_per_quantita(self, quantita):
        """Unità concordata con la quantità: 1 cartone, 2 cartoni."""
        return self.get_unita_display() if quantita == 1 else self.PLURALI[self.unita]

    @property
    def confezione(self):
        """Descrizione breve della confezione, es. 'cartone da 6 pz'."""
        testo = self.get_unita_display()
        if self.unita == self.Unita.CARTONE and self.pezzi_per_cartone:
            testo += f" da {self.pezzi_per_cartone} pz"
        return testo


class Impostazioni(models.Model):
    """Impostazioni modificabili dal pannello admin (record unico)."""

    email_destinatari = models.TextField(
        "email che ricevono gli ordini",
        blank=True,
        help_text="Uno o più indirizzi separati da virgola o a capo. "
        "Se vuoto si usa la configurazione del server.",
    )
    email_mittente = models.EmailField(
        "Gmail che invia gli ordini",
        blank=True,
        help_text="Se vuoto si usa la configurazione del server.",
    )
    email_password_app = models.CharField(
        "password per le app (Gmail)",
        max_length=64,
        blank=True,
        help_text="Le 16 lettere generate da Google.",
    )

    class Meta:
        verbose_name = "impostazioni"
        verbose_name_plural = "impostazioni"

    def __str__(self):
        return "Impostazioni ordini"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def corrente(cls):
        impostazioni, _ = cls.objects.get_or_create(pk=1)
        return impostazioni

    def destinatari(self):
        testo = self.email_destinatari.replace("\n", ",").replace(";", ",")
        return [e.strip() for e in testo.split(",") if e.strip()]

    @property
    def gmail_configurato(self):
        return bool(self.email_mittente and self.email_password_app)


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
    categoria_nome = models.CharField("categoria", max_length=130)
    gruppo_nome = models.CharField("sottocategoria", max_length=120, blank=True)
    codice = models.CharField("codice", max_length=30, blank=True)
    articolo_nome = models.CharField("articolo", max_length=150)
    unita = models.CharField("unità di vendita", max_length=20)
    quantita = models.PositiveIntegerField("quantità", validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "riga d'ordine"
        verbose_name_plural = "righe d'ordine"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.articolo_nome} × {self.quantita} {self.unita}"
