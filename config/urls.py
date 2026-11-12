from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Novecento – Amministrazione ordini"
admin.site.site_title = "Novecento"
admin.site.index_title = "Gestione sedi, catalogo e ordini"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("novecento.urls")),
]
