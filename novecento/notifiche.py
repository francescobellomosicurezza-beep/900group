import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.utils import timezone

from .models import Impostazioni, Ordine
from .pdf import genera_pdf_ordine, nome_file_pdf

logger = logging.getLogger(__name__)


def destinatari_ordini():
    """Indirizzi da Admin > Impostazioni, altrimenti da ORDINI_EMAIL_DESTINATARI."""
    return Impostazioni.corrente().destinatari() or list(settings.ORDINI_EMAIL_DESTINATARI)


def mittente_e_connessione():
    """(mittente, connessione): Gmail da Admin > Impostazioni se presente, altrimenti server."""
    impostazioni = Impostazioni.corrente()
    if not impostazioni.gmail_configurato:
        return settings.DEFAULT_FROM_EMAIL, None
    connessione = get_connection(
        host="smtp.gmail.com",
        port=587,
        username=impostazioni.email_mittente,
        password=impostazioni.email_password_app,
        use_tls=True,
        use_ssl=False,
        timeout=20,
    )
    return f"Ordini Novecento <{impostazioni.email_mittente}>", connessione


def invia_ordine(ordine):
    """Invia il PDF dell'ordine al laboratorio. Restituisce True se l'invio riesce."""
    destinatari = destinatari_ordini()
    if not destinatari:
        ordine.stato_invio = Ordine.StatoInvio.ERRORE
        ordine.errore_invio = (
            "Nessun destinatario configurato: impostalo in Admin > Impostazioni."
        )
        ordine.save(update_fields=["stato_invio", "errore_invio"])
        return False

    creato = timezone.localtime(ordine.creato_il)
    oggetto = f"Ordine {ordine.sede.nome} del {creato:%d/%m/%Y} – n. {ordine.numero}"
    corpo = (
        f"Nuovo ordine dal punto vendita {ordine.sede.nome}.\n\n"
        f"Numero ordine: {ordine.numero}\n"
        f"Operatore: {ordine.operatore}\n"
        f"Data: {creato:%d/%m/%Y %H:%M}\n"
        f"Righe d'ordine: {ordine.righe.count()}\n"
    )
    if ordine.note:
        corpo += f"\nNote:\n{ordine.note}\n"
    corpo += "\nIl dettaglio è nel PDF allegato.\n"

    mittente, connessione = mittente_e_connessione()
    messaggio = EmailMessage(
        subject=oggetto,
        body=corpo,
        from_email=mittente,
        to=destinatari,
        connection=connessione,
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


def invia_email_prova(destinatari=None):
    """Invia un'email di prova. Restituisce (ok, messaggio)."""
    destinatari = destinatari or destinatari_ordini()
    if not destinatari:
        return False, "Nessun destinatario: compila «email che ricevono gli ordini»."
    mittente, connessione = mittente_e_connessione()
    messaggio = EmailMessage(
        subject="Prova invio ordini Novecento",
        body="Se leggi questa email, l'invio degli ordini è configurato correttamente.",
        from_email=mittente,
        to=destinatari,
        connection=connessione,
    )
    try:
        messaggio.send(fail_silently=False)
    except (smtplib.SMTPException, OSError) as errore:
        logger.warning("Email di prova non inviata: %s", errore)
        return False, f"Invio non riuscito: {errore}"
    return True, f"Email di prova inviata a: {', '.join(destinatari)}"
