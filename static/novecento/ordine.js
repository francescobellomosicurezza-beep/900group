(function () {
  "use strict";

  var contenitore = document.getElementById("form-categoria");
  if (!contenitore) return;

  var urlQuantita = contenitore.dataset.urlQuantita;
  var tokenInput = contenitore.querySelector('input[name="csrfmiddlewaretoken"]');
  var csrf = tokenInput ? tokenInput.value : "";
  var inAttesa = {};
  var timer = {};
  var MASSIMO = 9999;

  function valore(input) {
    var n = parseInt(input.value, 10);
    return isNaN(n) ? 0 : Math.max(0, Math.min(MASSIMO, n));
  }

  function evidenzia(input) {
    var riga = input.closest(".nv-articolo");
    if (riga) riga.classList.toggle("selected", valore(input) > 0);
  }

  function aggiornaConteggi(dati) {
    document.querySelectorAll("[data-carrello-totale]").forEach(function (el) {
      el.textContent = dati.articoli_selezionati;
    });
    document.querySelectorAll("[data-conteggio-gruppo]").forEach(function (el) {
      var n = dati.per_gruppo[el.dataset.conteggioGruppo] || 0;
      el.textContent = n;
      el.hidden = n === 0;
    });
    var carrello = document.getElementById("nv-carrello");
    if (carrello) {
      carrello.classList.remove("pulse");
      void carrello.offsetWidth;
      carrello.classList.add("pulse");
    }
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
          aggiornaConteggi(dati);
        });
      })
      .catch(function () {
        inAttesa[articolo] = quantita;
        mostraErrore();
      });
  }

  function mostraErrore() {
    var avviso = document.getElementById("nv-avviso-rete");
    if (!avviso) {
      avviso = document.createElement("div");
      avviso.id = "nv-avviso-rete";
      avviso.className = "alert alert-warning small nv-avviso-rete";
      avviso.textContent = "Connessione assente: le quantità verranno salvate appena possibile.";
      document.body.appendChild(avviso);
    }
    avviso.hidden = false;
  }

  function salva(input) {
    var articolo = input.dataset.articolo;
    var quantita = valore(input);
    inAttesa[articolo] = quantita;
    clearTimeout(timer[articolo]);
    timer[articolo] = setTimeout(function () {
      invia(articolo, quantita);
    }, 350);
  }

  function svuotaCoda(keepalive) {
    Object.keys(inAttesa).forEach(function (articolo) {
      clearTimeout(timer[articolo]);
      invia(articolo, inAttesa[articolo], keepalive);
    });
  }

  contenitore.querySelectorAll(".nv-stepper").forEach(function (box) {
    var input = box.querySelector("input");
    box.querySelectorAll("button[data-step]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var nuovo = Math.max(0, Math.min(MASSIMO, valore(input) + parseInt(btn.dataset.step, 10)));
        input.value = nuovo || "";
        evidenzia(input);
        salva(input);
        if (navigator.vibrate) navigator.vibrate(8);
      });
    });
    input.addEventListener("input", function () {
      evidenzia(input);
      salva(input);
    });
    input.addEventListener("focus", function () { input.select(); });
  });

  window.addEventListener("online", function () {
    var avviso = document.getElementById("nv-avviso-rete");
    if (avviso) avviso.hidden = true;
    svuotaCoda(false);
  });
  window.addEventListener("pagehide", function () { svuotaCoda(true); });

  // Filtro testuale all'interno della categoria
  var filtro = document.querySelector("[data-filtro]");
  if (filtro) {
    filtro.addEventListener("input", function () {
      var testo = filtro.value.trim().toLowerCase();
      document.querySelectorAll(".nv-gruppo").forEach(function (gruppo) {
        var visibili = 0;
        var nomeGruppo = gruppo.querySelector(".nv-gruppo-nome").textContent.toLowerCase();
        gruppo.querySelectorAll(".nv-articolo").forEach(function (riga) {
          var ok = !testo || riga.dataset.nome.indexOf(testo) !== -1 || nomeGruppo.indexOf(testo) !== -1;
          riga.hidden = !ok;
          if (ok) visibili++;
        });
        gruppo.hidden = visibili === 0;
        if (testo && visibili) gruppo.open = true;
      });
    });
  }
})();
