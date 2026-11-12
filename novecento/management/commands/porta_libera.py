import socket

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Stampa la prima porta TCP libera su 127.0.0.1 a partire da --da."

    def add_arguments(self, parser):
        parser.add_argument("--da", type=int, default=8900, help="Porta iniziale (8900).")
        parser.add_argument("--tentativi", type=int, default=50)

    def handle(self, *args, **options):
        for porta in range(options["da"], options["da"] + options["tentativi"]):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", porta))
                except OSError:
                    continue
            self.stdout.write(str(porta))
            return
        raise CommandError("Nessuna porta libera trovata.")
