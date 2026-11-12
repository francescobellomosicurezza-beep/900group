from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model, password_validation
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Articolo, Categoria, Ordine, RigaOrdine, Sede
from .notifiche import invia_ordine
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

    class Meta:
        model = Sede
        fields = ["nome", "slug", "indirizzo", "email", "attiva", "ordine"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.account_id:
            self.fields["username"].initial = self.instance.account.username

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
    list_display = ["nome", "indirizzo", "email", "username_accesso", "attiva", "ordine"]
    list_editable = ["attiva", "ordine"]
    list_select_related = ["account"]
    prepopulated_fields = {"slug": ["nome"]}
    search_fields = ["nome", "indirizzo", "account__username"]
    fieldsets = [
        (None, {"fields": ["nome", "slug", "indirizzo", "email", "attiva", "ordine"]}),
        (
            "Credenziali del punto vendita",
            {"fields": ["username", "nuova_password", "disattiva_account"]},
        ),
    ]

    @admin.display(description="username accesso")
    def username_accesso(self, obj):
        if obj.account_id and obj.account.is_active:
            return obj.account.username
        return "—"


class ArticoloInline(admin.TabularInline):
    model = Articolo
    extra = 1
    fields = ["nome", "unita", "descrizione", "ordine", "attivo"]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nome", "numero_articoli", "ordine", "attiva"]
    list_editable = ["ordine", "attiva"]
    search_fields = ["nome"]
    inlines = [ArticoloInline]

    @admin.display(description="articoli")
    def numero_articoli(self, obj):
        return obj.articoli.count()


@admin.register(Articolo)
class ArticoloAdmin(admin.ModelAdmin):
    list_display = ["nome", "categoria", "unita", "ordine", "attivo"]
    list_editable = ["unita", "ordine", "attivo"]
    list_filter = ["categoria", "attivo", "unita"]
    search_fields = ["nome", "descrizione"]
    list_select_related = ["categoria"]


class RigaOrdineInline(admin.TabularInline):
    model = RigaOrdine
    extra = 0
    can_delete = False
    fields = ["categoria_nome", "articolo_nome", "quantita", "unita"]
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
