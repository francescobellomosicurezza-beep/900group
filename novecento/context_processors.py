from .models import Sede


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
