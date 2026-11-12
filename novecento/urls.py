from django.urls import path

from . import views

app_name = "novecento"

urlpatterns = [
    path("", views.scelta_sede, name="scelta_sede"),
    path("ordine/operatore/", views.operatore, name="operatore"),
    path("ordine/categoria/<int:indice>/", views.categoria, name="categoria"),
    path("ordine/riepilogo/", views.riepilogo, name="riepilogo"),
    path("ordine/conferma/", views.conferma, name="conferma"),
    path("ordine/conferma/pdf/", views.pdf_ordine, name="pdf_ordine"),
    path("ordine/conferma/reinvia/", views.reinvia, name="reinvia"),
    path("ordine/annulla/", views.annulla, name="annulla"),
]
