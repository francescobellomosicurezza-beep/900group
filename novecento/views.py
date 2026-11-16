import json
from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Prefetch, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CategoriaForm, OperatoreForm, RiepilogoForm, SedeForm
from .models import Articolo, Categoria, Gruppo, Ordine, RigaOrdine, Sede
from .notifiche import invia_ordine
from .pdf import genera_pdf_ordine, nome_file_pdf
from .promemoria import calendario_promemoria

CHIAVE_BOZZA = "ordine_bozza"
CHIAVE_ULTIMO = "ultimo_ordine_id"
QUANTITA_MASSIMA = 9999


# --------------------------------------------------------------------------- #
# Supporto
# --------------------------------------------------------------------------- #


def _bozza(request):
    return request.session.get(CHIAVE_BOZZA)


def _salva_bozza(request, bozza):
    request.session[CHIAVE_BOZZA] = bozza
    request.session.modified = True


def _puo_scegliere_sede(utente):
    return utente.is_staff or utente.is_superuser


def _sede_bozza(request, bozza):
    """Sede della bozza, solo se coerente con l'account collegato."""
    if not bozza:
        return None
    sede = Sede.objects.filter(pk=bozza.get("sede_id"), attiva=True).first()
    if sede is None:
        return None
    if _puo_scegliere_sede(request.user):
        return sede
    sede_account = Sede.per_utente(request.user)
    return sede if sede_account and sede_account.pk == sede.pk else None


def _contesto_ordine(request):
    """Restituisce (bozza, sede) oppure una redirect se il flusso non è iniziato."""
    bozza = _bozza(request)
    sede = _sede_bozza(request, bozza)
    if sede is None:
        return None, None, redirect("novecento:scelta_sede")
    if not bozza.get("nome"):
        return None, None, redirect("novecento:operatore")
    bozza.setdefault("quantita", {})
    return bozza, sede, None


def _articoli_ordinabili():
    return Articolo.objects.filter(
        attivo=True, gruppo__attivo=True, gruppo__categoria__attiva=True
    ).select_related("gruppo", "gruppo__categoria")


def _categorie_ordinabili():
    articoli = Articolo.objects.filter(attivo=True)
    gruppi = (
        Gruppo.objects.filter(attivo=True, articoli__attivo=True)
        .distinct()
        .prefetch_related(Prefetch("articoli", queryset=articoli, to_attr="attivi"))
    )
    return list(
        Categoria.objects.filter(attiva=True, gruppi__in=gruppi)
        .distinct()
        .prefetch_related(Prefetch("gruppi", queryset=gruppi, to_attr="attivi"))
    )


def _ultimo_ordine_sede(sede):
    ordine = sede.ordini.order_by("-creato_il").first()
    if ordine is None:
        return None, {}
    quantita = {
        str(articolo_id): qta
        for articolo_id, qta in ordine.righe.filter(articolo__isnull=False).values_list(
            "articolo_id", "quantita"
        )
    }
    return ordine, quantita


def _conteggi(bozza):
    """Numero di articoli selezionati per categoria e per sottocategoria."""
    quantita = bozza.get("quantita", {})
    per_categoria, per_gruppo = {}, {}
    for gruppo_id, categoria_id in _articoli_ordinabili().filter(
        pk__in=quantita.keys()
    ).values_list("gruppo_id", "gruppo__categoria_id"):
        per_categoria[categoria_id] = per_categoria.get(categoria_id, 0) + 1
        per_gruppo[gruppo_id] = per_gruppo.get(gruppo_id, 0) + 1
    return per_categoria, per_gruppo


def _righe_bozza(bozza):
    """Righe ordinate per categoria > sottocategoria > articolo."""
    quantita = bozza.get("quantita", {})
    articoli = _articoli_ordinabili().filter(pk__in=quantita.keys())
    return [(a, quantita[str(a.pk)]) for a in articoli]


def _segna_varianti(articoli, max_parole=5):
    """Per articoli dello stesso gruppo che iniziano con le stesse parole imposta
    `base` (la parte comune) e `variante` (la parte che li distingue).

    Esempio: «Coppette cartone baby/piccole/medie/grandi» -> base «Coppette cartone»,
    varianti «baby», «piccole», «medie», «grandi».
    """
    articoli = list(articoli)
    for articolo in articoli:
        articolo.base, articolo.variante = "", ""
    if len(articoli) < 2:
        return articoli
    parole = [a.nome.split() for a in articoli]
    corta = min(len(p) for p in parole)
    comuni = 0
    while comuni < corta and len({p[comuni].lower() for p in parole}) == 1:
        comuni += 1
    resti = [p[comuni:] for p in parole]
    if not comuni or any(not r or len(r) > max_parole for r in resti):
        return articoli
    for articolo, p, resto in zip(articoli, parole, resti):
        articolo.base = " ".join(p[:comuni])
        articolo.variante = " ".join(resto)
    return articoli


def _raggruppa(righe):
    """{categoria: {gruppo: [(articolo, qta), ...]}} mantenendo l'ordine."""
    albero = OrderedDict()
    for articolo, qta in righe:
        categoria = articolo.gruppo.categoria
        albero.setdefault(categoria, OrderedDict()).setdefault(articolo.gruppo, []).append(
            (articolo, qta, articolo.unita_per_quantita(qta))
        )
    return albero


# --------------------------------------------------------------------------- #
# Passo 1 – Punto vendita
# --------------------------------------------------------------------------- #


@login_required
def scelta_sede(request):
    """Avvio ordine: sede dall'account, oppure scelta libera per gli amministratori."""
    sede_account = Sede.per_utente(request.user)
    if sede_account is not None:
        _salva_bozza(request, {"sede_id": sede_account.pk, "quantita": {}})
        return redirect("novecento:operatore")

    if not _puo_scegliere_sede(request.user):
        return render(request, "novecento/nessuna_sede.html", status=403)

    if request.method == "POST":
        form = SedeForm(request.POST)
        if form.is_valid():
            sede = form.cleaned_data["sede"]
            _salva_bozza(request, {"sede_id": sede.pk, "quantita": {}})
            return redirect("novecento:operatore")
    else:
        form = SedeForm()
    return render(
        request,
        "novecento/scelta_sede.html",
        {"form": form, "sedi": list(form.fields["sede"].queryset), "passo": 1},
    )


# --------------------------------------------------------------------------- #
# Passo 2 – Operatore
# --------------------------------------------------------------------------- #


@login_required
def operatore(request):
    bozza = _bozza(request)
    sede = _sede_bozza(request, bozza)
    if sede is None:
        return redirect("novecento:scelta_sede")

    if request.method == "POST":
        form = OperatoreForm(request.POST)
        if form.is_valid():
            bozza["nome"] = form.cleaned_data["nome"]
            bozza["cognome"] = form.cleaned_data["cognome"]
            _salva_bozza(request, bozza)
            return redirect("novecento:categorie")
    else:
        form = OperatoreForm(
            initial={"nome": bozza.get("nome", ""), "cognome": bozza.get("cognome", "")}
        )

    recenti = (
        sede.ordini.filter(creato_il__gte=timezone.now() - timezone.timedelta(days=60))
        .values("nome", "cognome")
        .annotate(ultimo=Max("creato_il"))
        .order_by("-ultimo")[:6]
    )
    ordini_oggi = sede.ordini.filter(creato_il__date=timezone.localdate()).count()
    return render(
        request,
        "novecento/operatore.html",
        {
            "form": form,
            "sede": sede,
            "ordini_oggi": ordini_oggi,
            "operatori_recenti": list(recenti),
            "passo": 2,
        },
    )


# --------------------------------------------------------------------------- #
# Passo 3 – Ordine guidato
# --------------------------------------------------------------------------- #


@login_required
def categorie(request):
    bozza, sede, uscita = _contesto_ordine(request)
    if uscita:
        return uscita
    elenco = _categorie_ordinabili()
    per_categoria, _ = _conteggi(bozza)
    for categoria in elenco:
        categoria.selezionati = per_categoria.get(categoria.pk, 0)
        categoria.totale_articoli = sum(len(g.attivi) for g in categoria.attivi)
    ultimo, _ = _ultimo_ordine_sede(sede)
    return render(
        request,
        "novecento/categorie.html",
        {
            "sede": sede,
            "bozza": bozza,
            "categorie": elenco,
            "articoli_selezionati": len(bozza["quantita"]),
            "ultimo_ordine": ultimo,
            "passo": 3,
        },
    )


@login_required
def categoria(request, numero):
    bozza, sede, uscita = _contesto_ordine(request)
    if uscita:
        return uscita
    elenco = _categorie_ordinabili()
    corrente = next((c for c in elenco if c.numero == numero), None)
    if corrente is None:
        raise Http404("Categoria non trovata.")

    articoli = [a for g in corrente.attivi for a in g.attivi]
    quantita = bozza["quantita"]

    if request.method == "POST":
        form = CategoriaForm(request.POST, articoli=articoli)
        if form.is_valid():
            for articolo in articoli:
                quantita.pop(str(articolo.pk), None)
            quantita.update(form.quantita())
            _salva_bozza(request, bozza)
            destinazione = request.POST.get("vai")
            if destinazione == "riepilogo":
                return redirect("novecento:riepilogo")
            if destinazione and destinazione.isdigit():
                return redirect("novecento:categoria", numero=int(destinazione))
            return redirect("novecento:categorie")
    else:
        form = CategoriaForm(
            initial={
                CategoriaForm.nome_campo(a): quantita[str(a.pk)]
                for a in articoli
                if str(a.pk) in quantita
            },
            articoli=articoli,
        )

    _, ultime = _ultimo_ordine_sede(sede)
    _, per_gruppo = _conteggi(bozza)
    campi = dict(form.righe())
    gruppi = []
    for gruppo in corrente.attivi:
        _segna_varianti(gruppo.attivi)
        confezioni = {a.confezione for a in gruppo.attivi}
        unita_comune = ""
        if len(confezioni) == 1 and not any(a.codice for a in gruppo.attivi):
            unita_comune = confezioni.pop()
            for articolo in gruppo.attivi:
                articolo.nascondi_confezione = True
        gruppo.unita_comune = unita_comune
        gruppi.append(
            {
                "gruppo": gruppo,
                "selezionati": per_gruppo.get(gruppo.pk, 0),
                "righe": [(a, campi[a], ultime.get(str(a.pk))) for a in gruppo.attivi],
            }
        )

    indice = elenco.index(corrente)
    return render(
        request,
        "novecento/categoria.html",
        {
            "form": form,
            "sede": sede,
            "bozza": bozza,
            "categoria": corrente,
            "gruppi": gruppi,
            "precedente": elenco[indice - 1] if indice > 0 else None,
            "successiva": elenco[indice + 1] if indice + 1 < len(elenco) else None,
            "articoli_selezionati": len(quantita),
            "passo": 3,
        },
    )


@login_required
def cerca(request):
    bozza, sede, uscita = _contesto_ordine(request)
    if uscita:
        return uscita
    testo = request.GET.get("q", "").strip()
    risultati = []
    if len(testo) >= 2:
        filtro = Q()
        for parola in testo.split():
            filtro &= (
                Q(nome__icontains=parola)
                | Q(codice__icontains=parola)
                | Q(gruppo__nome__icontains=parola)
            )
        risultati = list(_articoli_ordinabili().filter(filtro)[:40])
    _, ultime = _ultimo_ordine_sede(sede)
    quantita = bozza["quantita"]
    righe = [(a, quantita.get(str(a.pk), 0), ultime.get(str(a.pk))) for a in risultati]
    return render(
        request,
        "novecento/cerca.html",
        {
            "sede": sede,
            "bozza": bozza,
            "testo": testo,
            "righe": righe,
            "articoli_selezionati": len(quantita),
            "passo": 3,
        },
    )


@login_required
@require_POST
def aggiorna_quantita(request):
    """Salvataggio automatico di una quantità (chiamata dal browser)."""
    bozza, sede, uscita = _contesto_ordine(request)
    if uscita:
        return JsonResponse({"errore": "sessione scaduta", "redirect": uscita.url}, status=409)
    try:
        dati = json.loads(request.body or b"{}")
        articolo_id = int(dati["articolo"])
        qta = int(dati["quantita"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return JsonResponse({"errore": "dati non validi"}, status=400)
    if not 0 <= qta <= QUANTITA_MASSIMA:
        return JsonResponse({"errore": "quantità non valida"}, status=400)
    if not _articoli_ordinabili().filter(pk=articolo_id).exists():
        return JsonResponse({"errore": "articolo non disponibile"}, status=404)

    if qta:
        bozza["quantita"][str(articolo_id)] = qta
    else:
        bozza["quantita"].pop(str(articolo_id), None)
    _salva_bozza(request, bozza)
    per_categoria, per_gruppo = _conteggi(bozza)
    return JsonResponse(
        {
            "articoli_selezionati": len(bozza["quantita"]),
            "per_categoria": per_categoria,
            "per_gruppo": per_gruppo,
        }
    )


@login_required
@require_POST
def ripeti_ultimo(request):
    bozza, sede, uscita = _contesto_ordine(request)
    if uscita:
        return uscita
    ultimo, quantita = _ultimo_ordine_sede(sede)
    disponibili = {
        str(pk)
        for pk in _articoli_ordinabili().filter(pk__in=quantita.keys()).values_list("pk", flat=True)
    }
    copiati = {k: v for k, v in quantita.items() if k in disponibili}
    if not copiati:
        messages.info(request, "Non c'è un ordine precedente da ripetere.")
        return redirect("novecento:categorie")
    bozza["quantita"].update(copiati)
    _salva_bozza(request, bozza)
    messages.success(
        request,
        f"Inserite le quantità dell'ordine del {timezone.localtime(ultimo.creato_il):%d/%m/%Y}: "
        "controllale e modificale dove serve.",
    )
    return redirect("novecento:riepilogo")


# --------------------------------------------------------------------------- #
# Passo 4 – Riepilogo e invio
# --------------------------------------------------------------------------- #


@login_required
def riepilogo(request):
    bozza, sede, uscita = _contesto_ordine(request)
    if uscita:
        return uscita

    righe = _righe_bozza(bozza)

    if request.method == "POST":
        form = RiepilogoForm(request.POST)
        if not righe:
            messages.error(request, "L'ordine è vuoto: seleziona almeno un articolo.")
            return redirect("novecento:categorie")
        if form.is_valid():
            with transaction.atomic():
                ordine = Ordine.objects.create(
                    sede=sede,
                    nome=bozza["nome"],
                    cognome=bozza["cognome"],
                    note=form.cleaned_data["note"],
                )
                RigaOrdine.objects.bulk_create(
                    RigaOrdine(
                        ordine=ordine,
                        articolo=articolo,
                        categoria_nome=str(articolo.gruppo.categoria),
                        gruppo_nome=articolo.gruppo.nome,
                        codice=articolo.codice,
                        articolo_nome=articolo.nome,
                        unita=articolo.confezione,
                        quantita=qta,
                    )
                    for articolo, qta in righe
                )
            invia_ordine(ordine)
            request.session.pop(CHIAVE_BOZZA, None)
            request.session[CHIAVE_ULTIMO] = ordine.pk
            return redirect("novecento:conferma")
    else:
        form = RiepilogoForm()

    return render(
        request,
        "novecento/riepilogo.html",
        {
            "form": form,
            "sede": sede,
            "bozza": bozza,
            "albero": _raggruppa(righe),
            "totale_righe": len(righe),
            "passo": 4,
        },
    )


# --------------------------------------------------------------------------- #
# Conferma, PDF, reinvio, annullamento
# --------------------------------------------------------------------------- #


def _ultimo_ordine(request):
    ordine_id = request.session.get(CHIAVE_ULTIMO)
    if not ordine_id:
        raise Http404("Nessun ordine recente.")
    ordini = Ordine.objects.select_related("sede")
    if not _puo_scegliere_sede(request.user):
        ordini = ordini.filter(sede__account=request.user)
    return get_object_or_404(ordini, pk=ordine_id)


@login_required
def conferma(request):
    try:
        ordine = _ultimo_ordine(request)
    except Http404:
        return redirect("novecento:scelta_sede")
    return render(
        request,
        "novecento/conferma.html",
        {"ordine": ordine, "righe": ordine.righe.all(), "passo": 5},
    )


@login_required
def pdf_ordine(request):
    ordine = _ultimo_ordine(request)
    risposta = HttpResponse(genera_pdf_ordine(ordine), content_type="application/pdf")
    risposta["Content-Disposition"] = f'inline; filename="{nome_file_pdf(ordine)}"'
    return risposta


@login_required
@require_POST
def reinvia(request):
    ordine = _ultimo_ordine(request)
    if ordine.stato_invio == Ordine.StatoInvio.INVIATO:
        messages.info(request, "L'ordine risulta già inviato.")
    elif invia_ordine(ordine):
        messages.success(request, "Ordine inviato correttamente.")
    else:
        messages.error(request, "Invio non riuscito. Riprova o avvisa il responsabile.")
    return redirect("novecento:conferma")


@login_required
@require_POST
def annulla(request):
    request.session.pop(CHIAVE_BOZZA, None)
    messages.info(request, "Ordine annullato.")
    return redirect("novecento:scelta_sede")


@login_required
def promemoria_calendario(request):
    """Scarica il promemoria ricorrente da aggiungere al calendario del telefono."""
    sede = Sede.per_utente(request.user)
    if sede is None and _puo_scegliere_sede(request.user):
        sede = _sede_bozza(request, _bozza(request))
    if sede is None:
        return redirect("novecento:scelta_sede")
    if not sede.orario_ordine or not sede.giorni_ordine:
        messages.info(request, "Per questa sede non è impostato un orario d'ordine.")
        return redirect("novecento:categorie")
    contenuto = calendario_promemoria(sede, request.build_absolute_uri("/"))
    risposta = HttpResponse(contenuto, content_type="text/calendar; charset=utf-8")
    risposta["Content-Disposition"] = f'attachment; filename="promemoria-ordine-{sede.slug}.ics"'
    return risposta


def manifest(request):
    """Manifest dell'app installabile (schermata Home del telefono)."""
    icona = static("novecento/icone/icona-192.png")
    dati = {
        "name": "Novecento Ordini",
        "short_name": "Novecento",
        "description": "Ordini dei punti vendita Gelateria Novecento",
        "lang": "it",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#F6F1EA",
        "theme_color": "#F6F1EA",
        "icons": [
            {"src": icona, "sizes": "192x192", "type": "image/png"},
            {"src": static("novecento/icone/icona-512.png"), "sizes": "512x512", "type": "image/png"},
            {
                "src": static("novecento/icone/icona-maskable-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    return JsonResponse(dati, content_type="application/manifest+json")
