from django.utils import timezone

from .models import Sede


def saluto_del_momento(adesso=None):
    """Buongiorno (5-12), Buon pomeriggio (13-17), Buonasera (18-4), ora italiana."""
    ora = timezone.localtime(adesso or timezone.now()).hour
    if 5 <= ora < 13:
        return "Buongiorno"
    if 13 <= ora < 18:
        return "Buon pomeriggio"
    return "Buonasera"


def saluto(request):
    return {"saluto": saluto_del_momento()}


def avviso_ordine(request):
    """Stato dell'ordine di oggi per la sede collegata, mostrato in ogni pagina."""
    utente = getattr(request, "user", None)
    if utente is None or not utente.is_authenticated:
        return {}
    sede = Sede.per_utente(utente)
    if sede is None and (utente.is_staff or utente.is_superuser):
        bozza = request.session.get("ordine_bozza") or {}
        sede = Sede.objects.filter(pk=bozza.get("sede_id"), attiva=True).first()
    if sede is None:
        return {}
    return {"avviso_sede": sede, "avviso_ordine": sede.stato_ordine()}
