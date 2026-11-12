from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from novecento.models import Sede

PASSWORD_ADMIN = "Demo-Admin-2026"


def password_sede(sede):
    return f"Demo-{sede.nome.replace(' ', '')}-2026"


class Command(BaseCommand):
    help = "Crea account di prova per le sedi e l'amministratore (solo con DEBUG attivo)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Comando disponibile solo in sviluppo (DJANGO_DEBUG=1).")

        Utente = get_user_model()
        righe = []
        with transaction.atomic():
            admin, creato = Utente.objects.get_or_create(
                username="admin",
                defaults={"is_staff": True, "is_superuser": True, "email": "admin@example.com"},
            )
            if creato:
                admin.set_password(PASSWORD_ADMIN)
                admin.save()
            righe.append(("Amministratore", "admin", PASSWORD_ADMIN if creato else "(invariata)"))

            for sede in Sede.objects.filter(attiva=True):
                if sede.account_id:
                    righe.append((sede.nome, sede.account.username, "(invariata)"))
                    continue
                if Utente.objects.filter(username__iexact=sede.slug).exists():
                    righe.append((sede.nome, sede.slug, "username già usato, saltata"))
                    continue
                account = Utente(username=sede.slug)
                account.set_password(password_sede(sede))
                account.save()
                sede.account = account
                sede.save(update_fields=["account"])
                righe.append((sede.nome, sede.slug, password_sede(sede)))

        self.stdout.write(self.style.SUCCESS("\nCredenziali di prova:"))
        for nome, username, password in righe:
            self.stdout.write(f"  {nome:<15} username: {username:<10} password: {password}")
        self.stdout.write("")
