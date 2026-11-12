import getpass

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from novecento.models import Sede


class Command(BaseCommand):
    help = "Crea o aggiorna le credenziali di accesso di un punto vendita."

    def add_arguments(self, parser):
        parser.add_argument("sede", help="Slug della sede (es. spello, bastia, foligno).")
        parser.add_argument(
            "--username", help="Username di accesso (predefinito: slug della sede)."
        )
        parser.add_argument(
            "--password",
            help="Password. Se omessa viene richiesta in modo interattivo.",
        )

    def handle(self, *args, **options):
        try:
            sede = Sede.objects.select_related("account").get(slug=options["sede"])
        except Sede.DoesNotExist as errore:
            slugs = ", ".join(Sede.objects.values_list("slug", flat=True))
            raise CommandError(f"Sede inesistente. Sedi disponibili: {slugs}") from errore

        Utente = get_user_model()
        username = (options["username"] or sede.slug).strip()
        account = sede.account

        conflitto = Utente.objects.filter(username__iexact=username)
        if account:
            conflitto = conflitto.exclude(pk=account.pk)
        if conflitto.exists():
            raise CommandError(f"Lo username '{username}' è già in uso.")

        password = options["password"]
        if not password:
            password = getpass.getpass(f"Password per {sede.nome} ({username}): ")
            if password != getpass.getpass("Ripeti la password: "):
                raise CommandError("Le password non coincidono.")

        account = account or Utente(username=username)
        account.username = username
        try:
            password_validation.validate_password(password, account)
        except ValidationError as errore:
            raise CommandError(" ".join(errore.messages)) from errore

        with transaction.atomic():
            creato = account.pk is None
            account.is_active = True
            account.set_password(password)
            account.save()
            sede.account = account
            sede.save(update_fields=["account"])

        azione = "creato" if creato else "aggiornato"
        self.stdout.write(
            self.style.SUCCESS(f"Account '{username}' {azione} per la sede {sede.nome}.")
        )
