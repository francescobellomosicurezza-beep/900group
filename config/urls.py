from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

admin.site.site_header = "Novecento – Amministrazione ordini"
admin.site.site_title = "Novecento"
admin.site.index_title = "Gestione sedi, catalogo e ordini"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accesso/",
        auth_views.LoginView.as_view(
            template_name="novecento/accesso.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("esci/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("novecento.urls")),
]
