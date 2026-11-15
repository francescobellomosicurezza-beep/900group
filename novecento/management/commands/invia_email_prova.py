import smtplib

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from novecento.notifiche import destinatari_ordini


class Command(BaseCommand):
    help = "Invia un'email di prova per verificare la configurazione SMTP."

    def add_arguments(self, parser):
        parser.add_argument(
            "destinatario",
            nargs="?",
            help="Indirizzo di prova (predefinito: destinatari degli ordini).",
        )

    def handle(self, *args, **options):
        destinatari = [options["destinatario"]] if options["destinatario"] else destinatari_ordini()
        if not destinatari:
            raise CommandError(
                "Nessun destinatario: passalo come argomento o impostalo in Admin > Impostazioni."
            )
        self.stdout.write(
            f"Server: {settings.EMAIL_HOST}:{settings.EMAIL_PORT} "
            f"utente: {settings.EMAIL_HOST_USER or '(nessuno)'}"
        )
        try:
            send_mail(
                "Prova invio ordini Novecento",
                "Se leggi questa email, l'invio degli ordini è configurato correttamente.",
                settings.DEFAULT_FROM_EMAIL,
                destinatari,
                fail_silently=False,
            )
        except (smtplib.SMTPException, OSError) as errore:
            raise CommandError(f"Invio non riuscito: {errore}") from errore
        self.stdout.write(self.style.SUCCESS(f"Email di prova inviata a: {', '.join(destinatari)}"))
