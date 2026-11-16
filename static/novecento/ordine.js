(function () {
  "use strict";

  var contenitore = document.querySelector("[data-url-quantita]");
  if (!contenitore) return;

  var urlQuantita = contenitore.dataset.urlQuantita;
  var tokenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
  var csrf = tokenInput ? tokenInput.value : "";
  var MASSIMO = 9999;
  var inAttesa = {};
  var timer = {};

  function valore(input) {
    var n = parseInt(input.value, 10);
    return isNaN(n) ? 0 : Math.max(0, Math.min(MASSIMO, n));
  }

  function aggiornaRiga(input) {
    var riga = input.closest(".articolo");
    if (riga) riga.classList.toggle("attivo", valore(input) > 0);
  }

  function rimbalza(el) {
    if (!el) return;
    el.classList.remove("salto");
    void el.offsetWidth;
    el.classList.add("salto");
  }

  function aggiornaConteggi(dati) {
    var totale = dati.articoli_selezionati;
    document.querySelectorAll("[data-carrello-totale]").forEach(function (el) {
      if (el.textContent !== String(totale)) {
        el.textContent = totale;
        rimbalza(el);
      }
    });
    document.querySelectorAll("[data-carrello-etichetta]").forEach(function (el) {
      el.textContent = (totale === 1 ? "articolo" : "articoli") + " nell'ordine";
    });
    var carrello = document.getElementById("nv-carrello");
    if (carrello) carrello.classList.toggle("visibile", totale > 0);
    var vuoto = document.querySelector("[data-ordine-vuoto]");
    if (vuoto) vuoto.hidden = totale > 0;
    var invia = document.getElementById("btn-invia");
    if (invia) invia.disabled = totale === 0;
    document.querySelectorAll("[data-conteggio-gruppo]").forEach(function (el) {
      var n = dati.per_gruppo[el.dataset.conteggioGruppo] || 0;
      el.textContent = n;
      el.hidden = n === 0;
    });
  }

  function mostraAvviso(testo) {
    var avviso = document.getElementById("nv-avviso-rete");
    if (!avviso) {
      avviso = document.createElement("div");
      avviso.id = "nv-avviso-rete";
      avviso.className = "messaggio warning";
      avviso.style.cssText = "position:fixed;top:calc(70px + env(safe-area-inset-top));left:12px;right:12px;z-index:60;max-width:536px;margin:0 auto";
      document.body.appendChild(avviso);
    }
    avviso.textContent = testo;
    avviso.hidden = false;
  }

  function invia(articolo, quantita, keepalive) {
    delete inAttesa[articolo];
    return fetch(urlQuantita, {
      method: "POST",
      credentials: "same-origin",
      keepalive: !!keepalive,
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify({ articolo: articolo, quantita: quantita })
    })
      .then(function (r) {
        return r.json().then(function (dati) {
          if (r.status === 409 && dati.redirect) {
            window.location.href = dati.redirect;
            return;
          }
          if (!r.ok) throw new Error(dati.errore || "Errore");
          var avviso = document.getElementById("nv-avviso-rete");
          if (avviso) avviso.hidden = true;
          aggiornaConteggi(dati);
        });
      })
      .catch(function () {
        inAttesa[articolo] = quantita;
        mostraAvviso("Connessione assente: le quantità verranno salvate appena torna la rete.");
      });
  }

  function salva(input) {
    var articolo = input.dataset.articolo;
    inAttesa[articolo] = valore(input);
    clearTimeout(timer[articolo]);
    timer[articolo] = setTimeout(function () {
      invia(articolo, inAttesa[articolo]);
    }, 300);
  }

  function svuotaCoda(keepalive) {
    Object.keys(inAttesa).forEach(function (articolo) {
      clearTimeout(timer[articolo]);
      invia(articolo, inAttesa[articolo], keepalive);
    });
  }

  document.querySelectorAll(".qta").forEach(function (box) {
    var input = box.querySelector("input");
    box.querySelectorAll("button[data-step]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var nuovo = Math.max(0, Math.min(MASSIMO, valore(input) + parseInt(btn.dataset.step, 10)));
        input.value = nuovo || "";
        aggiornaRiga(input);
        rimbalza(box);
        salva(input);
        if (navigator.vibrate) navigator.vibrate(nuovo ? 8 : [6, 30, 6]);
      });
    });
    input.addEventListener("input", function () {
      aggiornaRiga(input);
      salva(input);
    });
    input.addEventListener("focus", function () { input.select(); });
  });

  window.addEventListener("online", function () { svuotaCoda(false); });
  window.addEventListener("pagehide", function () { svuotaCoda(true); });
  document.querySelectorAll("a[href]").forEach(function (link) {
    link.addEventListener("click", function () { svuotaCoda(true); });
  });

  // Etichette delle sottocategorie: evidenzia quella visibile durante lo scorrimento
  var schede = document.querySelectorAll("[data-scheda]");
  if (schede.length && "IntersectionObserver" in window) {
    var barra = document.querySelector(".schede");
    var attiva = function (id) {
      schede.forEach(function (s) {
        var on = s.dataset.scheda === id;
        s.classList.toggle("attiva", on);
        if (on && barra) {
          barra.scrollTo({ left: s.offsetLeft - 16, behavior: "smooth" });
        }
      });
    };
    var osservatore = new IntersectionObserver(function (voci) {
      voci.forEach(function (v) {
        if (v.isIntersecting) attiva(v.target.dataset.sezione);
      });
    }, { rootMargin: "-35% 0px -60% 0px" });
    document.querySelectorAll("[data-sezione]").forEach(function (s) { osservatore.observe(s); });
    schede.forEach(function (s) {
      s.addEventListener("click", function () { attiva(s.dataset.scheda); });
    });
  }
})();
