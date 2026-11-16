from django.urls import path

from . import views

app_name = "novecento"

urlpatterns = [
    path("", views.scelta_sede, name="scelta_sede"),
    path("ordine/operatore/", views.operatore, name="operatore"),
    path("ordine/", views.categorie, name="categorie"),
    path("ordine/categoria/<int:numero>/", views.categoria, name="categoria"),
    path("ordine/cerca/", views.cerca, name="cerca"),
    path("ordine/quantita/", views.aggiorna_quantita, name="aggiorna_quantita"),
    path("ordine/ripeti-ultimo/", views.ripeti_ultimo, name="ripeti_ultimo"),
    path("ordine/riepilogo/", views.riepilogo, name="riepilogo"),
    path("ordine/conferma/", views.conferma, name="conferma"),
    path("ordine/conferma/pdf/", views.pdf_ordine, name="pdf_ordine"),
    path("ordine/conferma/reinvia/", views.reinvia, name="reinvia"),
    path("ordine/annulla/", views.annulla, name="annulla"),
    path("promemoria.ics", views.promemoria_calendario, name="promemoria"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
]
