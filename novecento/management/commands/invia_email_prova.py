from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from novecento.notifiche import invia_email_prova, mittente_e_connessione


class Command(BaseCommand):
    help = "Invia un'email di prova per verificare la configurazione dell'invio."

    def add_arguments(self, parser):
        parser.add_argument(
            "destinatario",
            nargs="?",
            help="Indirizzo di prova (predefinito: destinatari degli ordini).",
        )

    def handle(self, *args, **options):
        mittente, connessione = mittente_e_connessione()
        origine = "Admin > Impostazioni" if connessione else f"server {settings.EMAIL_HOST}"
        self.stdout.write(f"Mittente: {mittente} ({origine})")
        destinatari = [options["destinatario"]] if options["destinatario"] else None
        ok, messaggio = invia_email_prova(destinatari)
        if not ok:
            raise CommandError(messaggio)
        self.stdout.write(self.style.SUCCESS(messaggio))
