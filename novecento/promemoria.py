"""Promemoria ricorrente in formato calendario (iCalendar, RFC 5545)."""

import datetime

from django.utils import timezone

GIORNI_ICS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def _testo(valore):
    return (
        valore.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    )


def _piega(riga):
    """Righe al massimo di 75 ottetti, come richiesto dallo standard."""
    dati = riga.encode("utf-8")
    if len(dati) <= 75:
        return riga
    parti, corrente = [], b""
    for carattere in riga:
        codificato = carattere.encode("utf-8")
        limite = 75 if not parti else 74
        if len(corrente) + len(codificato) > limite:
            parti.append(corrente.decode("utf-8"))
            corrente = b""
        corrente += codificato
    parti.append(corrente.decode("utf-8"))
    return "\r\n ".join(parti)


def calendario_promemoria(sede, url_app):
    """File .ics con un evento ricorrente nei giorni d'ordine della sede.

    L'evento inizia `preavviso_minuti` prima dell'orario limite e ha un avviso
    all'inizio e uno all'orario limite. Gli orari sono "locali" (senza fuso),
    quindi seguono l'ora del telefono.
    """
    if not sede.orario_ordine or not sede.giorni_ordine:
        raise ValueError("La sede non ha orario o giorni d'ordine impostati.")

    oggi = timezone.localdate()
    giorni = sorted({int(g) for g in sede.giorni_ordine if g.isdigit() and int(g) < 7})
    inizio_giorno = next(
        oggi + datetime.timedelta(days=i) for i in range(7) if (oggi + datetime.timedelta(days=i)).weekday() in giorni
    )
    scadenza = datetime.datetime.combine(inizio_giorno, sede.orario_ordine)
    preavviso = max(sede.preavviso_minuti, 5)
    inizio = scadenza - datetime.timedelta(minutes=preavviso)
    formato = "%Y%m%dT%H%M%S"
    titolo = f"Ordine 900 {sede.nome} entro le {sede.orario_ordine:%H:%M}"
    descrizione = f"Invia l'ordine di oggi al laboratorio: {url_app}"

    righe = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Gelateria Novecento//Ordini//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:promemoria-ordine-{sede.slug}@novecento",
        f"DTSTAMP:{timezone.now().astimezone(datetime.timezone.utc):%Y%m%dT%H%M%SZ}",
        f"DTSTART:{inizio:{formato}}",
        f"DTEND:{scadenza:{formato}}",
        f"RRULE:FREQ=WEEKLY;BYDAY={','.join(GIORNI_ICS[g] for g in giorni)}",
        f"SUMMARY:{_testo(titolo)}",
        f"DESCRIPTION:{_testo(descrizione)}",
        f"URL:{url_app}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_testo(titolo)}",
        "TRIGGER:PT0M",
        "END:VALARM",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_testo('Scadenza ordine: ' + titolo)}",
        f"TRIGGER:PT{preavviso}M",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(_piega(r) for r in righe) + "\r\n"
