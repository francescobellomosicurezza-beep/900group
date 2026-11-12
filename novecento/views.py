from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CategoriaForm, OperatoreForm, RiepilogoForm, SedeForm
from .models import Articolo, Categoria, Ordine, RigaOrdine, Sede
from .notifiche import invia_ordine
from .pdf import genera_pdf_ordine, nome_file_pdf

CHIAVE_BOZZA = "ordine_bozza"
CHIAVE_ULTIMO = "ultimo_ordine_id"


# --------------------------------------------------------------------------- #
# Supporto
# --------------------------------------------------------------------------- #


def _bozza(request):
    return request.session.get(CHIAVE_BOZZA)


def _salva_bozza(request, bozza):
    request.session[CHIAVE_BOZZA] = bozza
    request.session.modified = True


def _categorie_ordinabili():
    articoli_attivi = Articolo.objects.filter(attivo=True)
    return list(
        Categoria.objects.filter(attiva=True)
        .annotate(n_articoli=Count("articoli", filter=Q(articoli__attivo=True)))
        .filter(n_articoli__gt=0)
        .prefetch_related(Prefetch("articoli", queryset=articoli_attivi, to_attr="attivi"))
    )


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


def _righe_bozza(bozza):
    """Righe d'ordine raggruppate per categoria a partire dalla bozza in sessione."""
    quantita = bozza.get("quantita", {})
    articoli = (
        Articolo.objects.filter(pk__in=quantita.keys(), attivo=True, categoria__attiva=True)
        .select_related("categoria")
        .order_by("categoria__ordine", "categoria__nome", "ordine", "nome")
    )
    return [(a, quantita[str(a.pk)]) for a in articoli]


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
            return redirect("novecento:categoria", indice=1)
    else:
        form = OperatoreForm(
            initial={"nome": bozza.get("nome", ""), "cognome": bozza.get("cognome", "")}
        )

    oggi = timezone.localdate()
    ordini_oggi = Ordine.objects.filter(sede=sede, creato_il__date=oggi).count()
    return render(
        request,
        "novecento/operatore.html",
        {"form": form, "sede": sede, "ordini_oggi": ordini_oggi, "passo": 2},
    )


# --------------------------------------------------------------------------- #
# Passo 3 – Scelta guidata per categoria
# --------------------------------------------------------------------------- #


@login_required
def categoria(request, indice):
    bozza = _bozza(request)
    sede = _sede_bozza(request, bozza)
    if sede is None:
        return redirect("novecento:scelta_sede")
    if not bozza.get("nome"):
        return redirect("novecento:operatore")

    categorie = _categorie_ordinabili()
    if not categorie:
        messages.error(request, "Non ci sono articoli ordinabili. Contatta l'amministratore.")
        return redirect("novecento:scelta_sede")
    if indice < 1 or indice > len(categorie):
        raise Http404("Categoria non trovata.")

    corrente = categorie[indice - 1]
    quantita = bozza.setdefault("quantita", {})

    if request.method == "POST":
        form = CategoriaForm(request.POST, articoli=corrente.attivi)
        if form.is_valid():
            for articolo in corrente.attivi:
                quantita.pop(str(articolo.pk), None)
            quantita.update(form.quantita())
            _salva_bozza(request, bozza)
            if request.POST.get("azione") == "indietro":
                if indice > 1:
                    return redirect("novecento:categoria", indice=indice - 1)
                return redirect("novecento:operatore")
            if indice < len(categorie):
                return redirect("novecento:categoria", indice=indice + 1)
            return redirect("novecento:riepilogo")
    else:
        iniziali = {
            CategoriaForm.nome_campo(a): quantita[str(a.pk)]
            for a in corrente.attivi
            if str(a.pk) in quantita
        }
        form = CategoriaForm(initial=iniziali, articoli=corrente.attivi)

    return render(
        request,
        "novecento/categoria.html",
        {
            "form": form,
            "sede": sede,
            "bozza": bozza,
            "categoria": corrente,
            "categorie": categorie,
            "indice": indice,
            "totale_categorie": len(categorie),
            "ultima": indice == len(categorie),
            "articoli_selezionati": len(quantita),
            "passo": 3,
        },
    )


# --------------------------------------------------------------------------- #
# Passo 4 – Riepilogo e invio
# --------------------------------------------------------------------------- #


@login_required
def riepilogo(request):
    bozza = _bozza(request)
    sede = _sede_bozza(request, bozza)
    if sede is None:
        return redirect("novecento:scelta_sede")
    if not bozza.get("nome"):
        return redirect("novecento:operatore")

    righe = _righe_bozza(bozza)
    totale_categorie = len(_categorie_ordinabili())

    if request.method == "POST":
        form = RiepilogoForm(request.POST)
        if not righe:
            messages.error(request, "L'ordine è vuoto: seleziona almeno un articolo.")
            return redirect("novecento:categoria", indice=1)
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
                        categoria_nome=articolo.categoria.nome,
                        articolo_nome=articolo.nome,
                        unita=articolo.get_unita_display(),
                        quantita=qta,
                    )
                    for articolo, qta in righe
                )
            invia_ordine(ordine)
            request.session.pop(CHIAVE_BOZZA, None)
            request.session[CHIAVE_ULTIMO] = ordine.pk
            return redirect("novecento:conferma")
    else:
        form = RiepilogoForm(initial={"note": bozza.get("note", "")})

    return render(
        request,
        "novecento/riepilogo.html",
        {
            "form": form,
            "sede": sede,
            "bozza": bozza,
            "righe": righe,
            "totale_categorie": totale_categorie,
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
