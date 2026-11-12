import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .models import Ordine
from .pdf import genera_pdf_ordine, nome_file_pdf

logger = logging.getLogger(__name__)


def invia_ordine(ordine):
    """Invia il PDF dell'ordine al laboratorio. Restituisce True se l'invio riesce."""
    destinatari = list(settings.ORDINI_EMAIL_DESTINATARI)
    if not destinatari:
        ordine.stato_invio = Ordine.StatoInvio.ERRORE
        ordine.errore_invio = "Nessun destinatario configurato (ORDINI_EMAIL_DESTINATARI)."
        ordine.save(update_fields=["stato_invio", "errore_invio"])
        return False

    creato = timezone.localtime(ordine.creato_il)
    oggetto = f"Ordine {ordine.sede.nome} del {creato:%d/%m/%Y} – n. {ordine.numero}"
    corpo = (
        f"Nuovo ordine dal punto vendita {ordine.sede.nome}.\n\n"
        f"Numero ordine: {ordine.numero}\n"
        f"Operatore: {ordine.operatore}\n"
        f"Data: {creato:%d/%m/%Y %H:%M}\n"
        f"Articoli: {ordine.righe.count()}\n"
    )
    if ordine.note:
        corpo += f"\nNote:\n{ordine.note}\n"
    corpo += "\nIl dettaglio è nel PDF allegato.\n"

    messaggio = EmailMessage(
        subject=oggetto,
        body=corpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinatari,
        cc=[ordine.sede.email] if ordine.sede.email else [],
    )
    messaggio.attach(nome_file_pdf(ordine), genera_pdf_ordine(ordine), "application/pdf")

    try:
        messaggio.send(fail_silently=False)
    except (smtplib.SMTPException, OSError) as errore:
        logger.exception("Invio ordine %s fallito", ordine.pk)
        ordine.stato_invio = Ordine.StatoInvio.ERRORE
        ordine.errore_invio = str(errore)
        ordine.save(update_fields=["stato_invio", "errore_invio"])
        return False

    ordine.stato_invio = Ordine.StatoInvio.INVIATO
    ordine.inviato_il = timezone.now()
    ordine.errore_invio = ""
    ordine.save(update_fields=["stato_invio", "inviato_il", "errore_invio"])
    return True
