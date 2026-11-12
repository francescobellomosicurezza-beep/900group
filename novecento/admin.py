from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Articolo, Categoria, Ordine, RigaOrdine, Sede
from .notifiche import invia_ordine
from .pdf import genera_pdf_ordine, nome_file_pdf


class SedeAdminForm(forms.ModelForm):
    nuovo_pin = forms.CharField(
        label="Nuovo PIN",
        required=False,
        max_length=20,
        widget=forms.PasswordInput(render_value=False),
        help_text="Lasciare vuoto per non modificare il PIN attuale.",
    )
    rimuovi_pin = forms.BooleanField(
        label="Rimuovi PIN",
        required=False,
        help_text="Il punto vendita potrà ordinare senza PIN.",
    )

    class Meta:
        model = Sede
        fields = ["nome", "slug", "indirizzo", "email", "attiva", "ordine"]

    def save(self, commit=True):
        sede = super().save(commit=False)
        if self.cleaned_data.get("rimuovi_pin"):
            sede.imposta_pin("")
        elif self.cleaned_data.get("nuovo_pin"):
            sede.imposta_pin(self.cleaned_data["nuovo_pin"])
        if commit:
            sede.save()
        return sede


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    form = SedeAdminForm
    list_display = ["nome", "indirizzo", "email", "pin_impostato", "attiva", "ordine"]
    list_editable = ["attiva", "ordine"]
    prepopulated_fields = {"slug": ["nome"]}
    search_fields = ["nome", "indirizzo"]
    fieldsets = [
        (None, {"fields": ["nome", "slug", "indirizzo", "email", "attiva", "ordine"]}),
        ("Accesso", {"fields": ["nuovo_pin", "rimuovi_pin"]}),
    ]

    @admin.display(boolean=True, description="PIN")
    def pin_impostato(self, obj):
        return obj.richiede_pin


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
