from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model, password_validation
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone
from django.urls import path, reverse
from django.utils.html import format_html

from .models import GIORNI_SETTIMANA, Articolo, Categoria, Gruppo, Impostazioni, Ordine, RigaOrdine, Sede
from .listino_excel import esporta_listino, importa_listino
from .notifiche import invia_email_prova, invia_ordine
from .pdf import genera_pdf_ordine, nome_file_pdf


class SedeAdminForm(forms.ModelForm):
    username = forms.CharField(
        label="Username di accesso",
        required=False,
        max_length=150,
        help_text="Credenziale con cui il punto vendita entra nell'app (es. spello).",
    )
    nuova_password = forms.CharField(
        label="Nuova password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Obbligatoria alla creazione dell'account; vuota per non modificarla.",
    )
    disattiva_account = forms.BooleanField(
        label="Disattiva account",
        required=False,
        help_text="Scollega e disattiva l'account: il punto vendita non potrà più accedere.",
    )

    giorni = forms.MultipleChoiceField(
        label="Giorni dell'ordine",
        choices=GIORNI_SETTIMANA,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Sede
        fields = [
            "nome",
            "slug",
            "indirizzo",
            "email",
            "attiva",
            "ordine",
            "orario_ordine",
            "preavviso_minuti",
        ]
        widgets = {"orario_ordine": forms.TimeInput(attrs={"type": "time"}, format="%H:%M")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.account_id:
            self.fields["username"].initial = self.instance.account.username
        self.fields["giorni"].initial = list(self.instance.giorni_ordine or "")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("disattiva_account"):
            return cleaned
        username = (cleaned.get("username") or "").strip()
        password = cleaned.get("nuova_password") or ""
        account = self.instance.account if self.instance.pk else None
        if not username:
            if password:
                self.add_error("username", "Indica lo username per impostare la password.")
            return cleaned
        Utente = get_user_model()
        altro = Utente.objects.filter(username__iexact=username)
        if account:
            altro = altro.exclude(pk=account.pk)
        if altro.exists():
            self.add_error("username", "Username già in uso.")
        if account is None and not password:
            self.add_error("nuova_password", "Imposta una password per il nuovo account.")
        if password:
            utente_prova = account or Utente(username=username)
            try:
                password_validation.validate_password(password, utente_prova)
            except forms.ValidationError as errore:
                self.add_error("nuova_password", errore)
        cleaned["username"] = username
        return cleaned

    def save(self, commit=True):
        sede = super().save(commit=False)
        sede.giorni_ordine = "".join(sorted(self.cleaned_data.get("giorni") or []))
        Utente = get_user_model()
        account = sede.account if sede.account_id else None
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("nuova_password")

        if self.cleaned_data.get("disattiva_account"):
            if account:
                account.is_active = False
                account.save(update_fields=["is_active"])
            sede.account = None
        elif username:
            if account is None:
                account = Utente(username=username)
            account.username = username
            account.is_active = True
            if password:
                account.set_password(password)
            account.save()
            sede.account = account

        if commit:
            sede.save()
        return sede


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    form = SedeAdminForm
    list_display = [
        "nome",
        "username_accesso",
        "orario_ordine",
        "giorni_ordine_display",
        "email",
        "attiva",
        "ordine",
    ]
    list_editable = ["attiva", "ordine"]
    list_select_related = ["account"]
    prepopulated_fields = {"slug": ["nome"]}
    search_fields = ["nome", "indirizzo", "account__username"]
    fieldsets = [
        (None, {"fields": ["nome", "slug", "indirizzo", "email", "attiva", "ordine"]}),
        (
            "Orario dell'ordine",
            {
                "fields": ["orario_ordine", "giorni", "preavviso_minuti"],
                "description": "La sede vede un avviso nell'app e può aggiungere "
                "il promemoria al calendario del telefono.",
            },
        ),
        (
            "Credenziali del punto vendita",
            {"fields": ["username", "nuova_password", "disattiva_account"]},
        ),
    ]

    @admin.display(description="giorni")
    def giorni_ordine_display(self, obj):
        return obj.giorni_display()

    @admin.display(description="username accesso")
    def username_accesso(self, obj):
        if obj.account_id and obj.account.is_active:
            return obj.account.username
        return "—"


class ImportaListinoForm(forms.Form):
    file = forms.FileField(
        label="File Excel (.xlsx)",
        help_text="Usa il file scaricato con «Esporta in Excel», modificato e salvato.",
    )

    def clean_file(self):
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Carica un file Excel con estensione .xlsx")
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File troppo grande (massimo 5 MB).")
        return file


class GruppoInline(admin.TabularInline):
    model = Gruppo
    extra = 1
    fields = ["nome", "ordine", "attivo", "numero_articoli"]
    readonly_fields = ["numero_articoli"]
    show_change_link = True

    @admin.display(description="articoli")
    def numero_articoli(self, obj):
        return obj.articoli.count() if obj.pk else 0


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["numero", "nome", "icona", "numero_gruppi", "attiva"]
    list_display_links = ["nome"]
    list_editable = ["attiva"]
    search_fields = ["nome", "descrizione"]
    inlines = [GruppoInline]

    @admin.display(description="sottocategorie")
    def numero_gruppi(self, obj):
        return obj.gruppi.count()


class ArticoloInline(admin.TabularInline):
    model = Articolo
    extra = 1
    fields = [
        "codice",
        "nome",
        "unita",
        "pezzi_per_cartone",
        "prezzo_pezzo",
        "prezzo_cartone",
        "iva",
        "ordine",
        "attivo",
    ]


@admin.register(Gruppo)
class GruppoAdmin(admin.ModelAdmin):
    list_display = ["nome", "categoria", "ordine", "attivo"]
    list_editable = ["ordine", "attivo"]
    list_filter = ["categoria", "attivo"]
    search_fields = ["nome"]
    list_select_related = ["categoria"]
    inlines = [ArticoloInline]


@admin.register(Articolo)
class ArticoloAdmin(admin.ModelAdmin):
    list_display = [
        "codice",
        "nome",
        "gruppo",
        "unita",
        "pezzi_per_cartone",
        "prezzo_pezzo",
        "prezzo_cartone",
        "iva",
        "attivo",
    ]
    list_display_links = ["nome"]
    list_editable = ["codice", "unita", "pezzi_per_cartone", "prezzo_pezzo", "prezzo_cartone", "iva", "attivo"]
    list_filter = ["gruppo__categoria", "gruppo", "unita", "attivo"]
    search_fields = ["nome", "codice"]
    list_select_related = ["gruppo", "gruppo__categoria"]
    list_per_page = 100
    change_list_template = "admin/novecento/articolo/change_list.html"

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "puo_importare": self.has_change_permission(request)}
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        extra = [
            path(
                "esporta-excel/",
                self.admin_site.admin_view(self.esporta_excel),
                name="novecento_articolo_esporta",
            ),
            path(
                "importa-excel/",
                self.admin_site.admin_view(self.importa_excel),
                name="novecento_articolo_importa",
            ),
        ]
        return extra + super().get_urls()

    def esporta_excel(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        risposta = HttpResponse(
            esporta_listino(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        nome = f"listino-novecento-{timezone.localdate():%Y%m%d}.xlsx"
        risposta["Content-Disposition"] = f'attachment; filename="{nome}"'
        return risposta

    def importa_excel(self, request):
        if not self.has_change_permission(request):
            raise PermissionDenied
        esito = None
        if request.method == "POST":
            form = ImportaListinoForm(request.POST, request.FILES)
            if form.is_valid():
                esito = importa_listino(form.cleaned_data["file"])
                if esito.riuscita:
                    self.message_user(
                        request,
                        f"Listino importato: {esito.creati} nuovi, {esito.aggiornati} aggiornati, "
                        f"{esito.invariati} invariati.",
                        messages.SUCCESS,
                    )
                    for voce in esito.categorie_create:
                        self.message_user(request, f"Nuova categoria: {voce}", messages.INFO)
                    for voce in esito.gruppi_creati:
                        self.message_user(request, f"Nuova sottocategoria: {voce}", messages.INFO)
                    return redirect("admin:novecento_articolo_changelist")
        else:
            form = ImportaListinoForm()
        contesto = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Importa listino da Excel",
            "form": form,
            "esito": esito,
        }
        return render(request, "admin/novecento/articolo/importa_excel.html", contesto)


class ImpostazioniForm(forms.ModelForm):
    nuova_password_app = forms.CharField(
        label="Password per le app (Gmail)",
        required=False,
        strip=True,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
        help_text="Le 16 lettere create su myaccount.google.com/apppasswords. "
        "Lascia vuoto per mantenere quella salvata.",
    )
    rimuovi_gmail = forms.BooleanField(
        label="Scollega il Gmail",
        required=False,
        help_text="Cancella Gmail e password per le app: si torna alla configurazione del server.",
    )

    class Meta:
        model = Impostazioni
        fields = ["email_destinatari", "email_mittente"]
        widgets = {"email_destinatari": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("rimuovi_gmail"):
            return cleaned
        password = (cleaned.get("nuova_password_app") or "").replace(" ", "")
        cleaned["nuova_password_app"] = password
        if password and len(password) != 16:
            self.add_error(
                "nuova_password_app",
                "La password per le app di Google è di 16 lettere (gli spazi non contano).",
            )
        if password and not cleaned.get("email_mittente"):
            self.add_error("email_mittente", "Indica il Gmail a cui appartiene la password.")
        if (
            cleaned.get("email_mittente")
            and not password
            and not self.instance.email_password_app
        ):
            self.add_error("nuova_password_app", "Inserisci la password per le app di questo Gmail.")
        return cleaned

    def save(self, commit=True):
        impostazioni = super().save(commit=False)
        if self.cleaned_data.get("rimuovi_gmail"):
            impostazioni.email_mittente = ""
            impostazioni.email_password_app = ""
        elif self.cleaned_data.get("nuova_password_app"):
            impostazioni.email_password_app = self.cleaned_data["nuova_password_app"]
        if commit:
            impostazioni.save()
        return impostazioni


@admin.register(Impostazioni)
class ImpostazioniAdmin(admin.ModelAdmin):
    form = ImpostazioniForm
    change_form_template = "admin/novecento/impostazioni/change_form.html"
    fieldsets = [
        ("Chi riceve gli ordini", {"fields": ["email_destinatari"]}),
        (
            "Gmail che invia gli ordini",
            {
                "fields": ["email_mittente", "stato_gmail", "nuova_password_app", "rimuovi_gmail"],
                "description": "1) Sul Gmail attiva la verifica in due passaggi. "
                "2) Apri myaccount.google.com/apppasswords, crea una password chiamata "
                "«Novecento» e copia le 16 lettere. 3) Incollale qui, poi «Salva e invia "
                "email di prova».",
            },
        ),
    ]
    readonly_fields = ["stato_gmail"]

    @admin.display(description="Stato")
    def stato_gmail(self, obj):
        if obj and obj.gmail_configurato:
            return "✅ Password per le app salvata"
        return "— non configurato (si usa la configurazione del server)"

    def has_add_permission(self, request):
        return not Impostazioni.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        impostazioni = Impostazioni.corrente()
        return redirect("admin:novecento_impostazioni_change", impostazioni.pk)

    def response_change(self, request, obj):
        if "_email_prova" in request.POST:
            ok, messaggio = invia_email_prova()
            self.message_user(request, messaggio, messages.SUCCESS if ok else messages.ERROR)
            return redirect("admin:novecento_impostazioni_change", obj.pk)
        return super().response_change(request, obj)


class RigaOrdineInline(admin.TabularInline):
    model = RigaOrdine
    extra = 0
    can_delete = False
    fields = ["categoria_nome", "gruppo_nome", "codice", "articolo_nome", "quantita", "unita"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ordine)
class OrdineAdmin(admin.ModelAdmin):
    list_display = [
        "numero",
        "sede",
        "operatore",
        "creato_il",
        "totale_righe",
        "stato_invio",
        "link_pdf",
    ]
    list_filter = ["sede", "stato_invio", "creato_il"]
    search_fields = ["nome", "cognome", "note"]
    date_hierarchy = "creato_il"
    list_select_related = ["sede"]
    readonly_fields = [
        "sede",
        "nome",
        "cognome",
        "note",
        "creato_il",
        "stato_invio",
        "inviato_il",
        "errore_invio",
        "link_pdf",
    ]
    inlines = [RigaOrdineInline]
    actions = ["reinvia_email"]

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        extra = [
            path(
                "<int:pk>/pdf/",
                self.admin_site.admin_view(self.scarica_pdf),
                name="novecento_ordine_pdf",
            )
        ]
        return extra + super().get_urls()

    def scarica_pdf(self, request, pk):
        ordine = self.get_object(request, pk)
        if ordine is None:
            return HttpResponse(status=404)
        risposta = HttpResponse(genera_pdf_ordine(ordine), content_type="application/pdf")
        risposta["Content-Disposition"] = f'inline; filename="{nome_file_pdf(ordine)}"'
        return risposta

    @admin.display(description="PDF")
    def link_pdf(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("admin:novecento_ordine_pdf", args=[obj.pk])
        return format_html('<a href="{}" target="_blank">Apri PDF</a>', url)

    @admin.action(description="Reinvia email al laboratorio")
    def reinvia_email(self, request, queryset):
        riusciti = sum(1 for ordine in queryset.select_related("sede") if invia_ordine(ordine))
        falliti = queryset.count() - riusciti
        if riusciti:
            self.message_user(request, f"{riusciti} ordini inviati.", messages.SUCCESS)
        if falliti:
            self.message_user(
                request, f"{falliti} ordini non inviati: verifica la configurazione email.",
                messages.ERROR,
            )
