import datetime
import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .admin import SedeAdminForm
from .models import Articolo, Categoria, Gruppo, Impostazioni, Ordine, Sede
from .pdf import genera_pdf_ordine

DESTINATARIO = "laboratorio@example.com"
PASSWORD = "Gelato-Novecento-2026"


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ORDINI_EMAIL_DESTINATARI=[DESTINATARIO],
)
class FlussoOrdineTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Articolo.objects.all().delete()
        Categoria.objects.all().delete()
        Sede.objects.all().delete()
        Utente = get_user_model()
        cls.account_spello = Utente.objects.create_user("spello", password=PASSWORD)
        cls.account_foligno = Utente.objects.create_user("foligno", password=PASSWORD)
        cls.sede = Sede.objects.create(
            nome="Spello", slug="spello", email="spello@example.com", account=cls.account_spello
        )
        cls.foligno = Sede.objects.create(
            nome="Foligno", slug="foligno", account=cls.account_foligno
        )
        cls.cat_gelato = Categoria.objects.create(numero=1, nome="Accessori gelateria")
        cls.cat_bar = Categoria.objects.create(numero=3, nome="Accessori bar")
        Categoria.objects.create(numero=9, nome="Vuota")
        cls.g_coni = Gruppo.objects.create(categoria=cls.cat_gelato, nome="Coni e cialde", ordine=1)
        cls.g_coppette = Gruppo.objects.create(categoria=cls.cat_gelato, nome="Coppette", ordine=2)
        cls.g_bicchieri = Gruppo.objects.create(categoria=cls.cat_bar, nome="Bicchieri")
        cls.coni = Articolo.objects.create(
            gruppo=cls.g_coni, codice="NOCC", nome="Cono cialda grande", unita="CT",
            pezzi_per_cartone=200,
        )
        cls.coppette = Articolo.objects.create(gruppo=cls.g_coppette, codice="ALC", nome="Coppette medie")
        cls.bicchieri = Articolo.objects.create(gruppo=cls.g_bicchieri, nome="Bicchiere caffè")
        Articolo.objects.create(gruppo=cls.g_bicchieri, nome="Disattivato", attivo=False)

    def _avvia(self, account=None):
        self.client.force_login(account or self.account_spello)
        r = self.client.get(reverse("novecento:scelta_sede"))
        self.assertRedirects(r, reverse("novecento:operatore"))
        r = self.client.post(reverse("novecento:operatore"), {"nome": "mario", "cognome": "rossi"})
        self.assertRedirects(r, reverse("novecento:categorie"))

    def _quantita(self, articolo, qta):
        return self.client.post(
            reverse("novecento:aggiorna_quantita"),
            data=json.dumps({"articolo": articolo.pk, "quantita": qta}),
            content_type="application/json",
        )

    def _ordina_e_invia(self):
        self._quantita(self.coni, 1)
        return self.client.post(reverse("novecento:riepilogo"), {})

    def test_anonimo_rimandato_al_login(self):
        for nome in ["scelta_sede", "operatore", "categorie", "riepilogo", "conferma"]:
            r = self.client.get(reverse(f"novecento:{nome}"))
            self.assertEqual(r.status_code, 302)
            self.assertTrue(r["Location"].startswith(reverse("login")))

    def test_login_con_credenziali_sede(self):
        r = self.client.post(reverse("login"), {"username": "spello", "password": "sbagliata"})
        self.assertContains(r, "non corretti")
        r = self.client.post(
            reverse("login"), {"username": "spello", "password": PASSWORD}, follow=True
        )
        self.assertRedirects(r, reverse("novecento:operatore"))
        self.assertContains(r, "900 Spello")

    def test_elenco_categorie_solo_con_articoli(self):
        self._avvia()
        r = self.client.get(reverse("novecento:categorie"))
        self.assertContains(r, "Accessori gelateria")
        self.assertContains(r, "Accessori bar")
        self.assertNotContains(r, "Vuota")

    def test_categoria_mostra_sottocategorie_e_varianti(self):
        self._avvia()
        r = self.client.get(reverse("novecento:categoria", args=[1]))
        self.assertContains(r, "Coni e cialde")
        self.assertContains(r, "Coppette")
        self.assertContains(r, "Cono cialda grande")
        self.assertContains(r, "cartone da 200 pz")
        self.assertContains(r, "NOCC")
        r = self.client.get(reverse("novecento:categoria", args=[3]))
        self.assertNotContains(r, "Disattivato")
        self.assertEqual(self.client.get(reverse("novecento:categoria", args=[9])).status_code, 404)

    def test_salvataggio_automatico_quantita(self):
        self._avvia()
        r = self._quantita(self.coni, 3)
        self.assertEqual(r.status_code, 200)
        dati = r.json()
        self.assertEqual(dati["articoli_selezionati"], 1)
        self.assertEqual(dati["per_gruppo"], {str(self.g_coni.pk): 1})
        self.assertEqual(self._quantita(self.coni, 0).json()["articoli_selezionati"], 0)
        self.assertEqual(self._quantita(self.coni, -1).status_code, 400)
        disattivato = Articolo.objects.get(nome="Disattivato")
        self.assertEqual(self._quantita(disattivato, 1).status_code, 404)

    def test_salvataggio_automatico_senza_ordine_avviato(self):
        self.client.force_login(self.account_spello)
        r = self._quantita(self.coni, 1)
        self.assertEqual(r.status_code, 409)

    def test_flusso_completo_invia_email_con_pdf(self):
        self._avvia()
        r = self.client.post(
            reverse("novecento:categoria", args=[1]),
            {f"art_{self.coni.pk}": "3", f"art_{self.coppette.pk}": "0", "vai": "3"},
        )
        self.assertRedirects(r, reverse("novecento:categoria", args=[3]))
        self._quantita(self.bicchieri, 2)

        r = self.client.get(reverse("novecento:riepilogo"))
        self.assertContains(r, "Coni e cialde")
        self.assertContains(r, "Bicchiere caffè")
        self.assertContains(r, 'value="3"')
        self.assertContains(r, 'data-carrello-totale>2<')

        r = self.client.post(reverse("novecento:riepilogo"), {"note": "Consegna entro le 10"})
        self.assertRedirects(r, reverse("novecento:conferma"))

        ordine = Ordine.objects.get()
        self.assertEqual(ordine.sede, self.sede)
        self.assertEqual(ordine.operatore, "Mario Rossi")
        self.assertEqual(ordine.stato_invio, Ordine.StatoInvio.INVIATO)
        self.assertEqual(
            list(ordine.righe.values_list("gruppo_nome", "codice", "articolo_nome", "quantita", "unita")),
            [
                ("Coni e cialde", "NOCC", "Cono cialda grande", 3, "cartone da 200 pz"),
                ("Bicchieri", "", "Bicchiere caffè", 2, "confezione"),
            ],
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [DESTINATARIO])
        self.assertEqual(email.cc, ["spello@example.com"])
        nome_file, contenuto, mimetype = email.attachments[0]
        self.assertTrue(nome_file.endswith(".pdf"))
        self.assertEqual(mimetype, "application/pdf")
        self.assertTrue(contenuto.startswith(b"%PDF"))

        self.assertNotIn("ordine_bozza", self.client.session)
        r = self.client.get(reverse("novecento:pdf_ordine"))
        self.assertEqual(r["Content-Type"], "application/pdf")

    def test_destinatari_da_impostazioni_admin(self):
        impostazioni = Impostazioni.corrente()
        impostazioni.email_destinatari = "lab1@example.com;\nlab2@example.com"
        impostazioni.save()
        self._avvia()
        self._ordina_e_invia()
        self.assertEqual(mail.outbox[0].to, ["lab1@example.com", "lab2@example.com"])

    def test_ricerca_articoli(self):
        self._avvia()
        r = self.client.get(reverse("novecento:cerca"), {"q": "cono"})
        self.assertContains(r, "Cono cialda grande")
        self.assertNotContains(r, "Coppette medie")
        r = self.client.get(reverse("novecento:cerca"), {"q": "alc"})
        self.assertContains(r, "Coppette medie")

    def test_operatori_recenti_e_ripeti_ultimo_ordine(self):
        self._avvia()
        self._quantita(self.coni, 4)
        self._quantita(self.bicchieri, 2)
        self.client.post(reverse("novecento:riepilogo"), {})

        r = self.client.get(reverse("novecento:scelta_sede"), follow=True)
        self.assertContains(r, "Mario Rossi")
        self.client.post(reverse("novecento:operatore"), {"nome": "Mario", "cognome": "Rossi"})

        r = self.client.get(reverse("novecento:categoria", args=[1]))
        self.assertContains(r, "ultima volta 4")

        r = self.client.post(reverse("novecento:ripeti_ultimo"))
        self.assertRedirects(r, reverse("novecento:riepilogo"))
        self.assertEqual(
            self.client.session["ordine_bozza"]["quantita"],
            {str(self.coni.pk): 4, str(self.bicchieri.pk): 2},
        )

    def test_sede_non_manomettibile_da_altro_account(self):
        self._avvia()
        sessione = self.client.session
        bozza = sessione["ordine_bozza"]
        bozza["sede_id"] = self.foligno.pk
        sessione["ordine_bozza"] = bozza
        sessione.save()
        r = self.client.get(reverse("novecento:categorie"))
        self.assertRedirects(r, reverse("novecento:scelta_sede"), fetch_redirect_response=False)

    def test_account_senza_sede(self):
        utente = get_user_model().objects.create_user("orfano", password=PASSWORD)
        self.client.force_login(utente)
        r = self.client.get(reverse("novecento:scelta_sede"))
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "non è collegato", status_code=403)

    def test_sede_disattivata_blocca_accesso(self):
        self.sede.attiva = False
        self.sede.save()
        self.client.force_login(self.account_spello)
        r = self.client.get(reverse("novecento:scelta_sede"))
        self.assertEqual(r.status_code, 403)

    def test_amministratore_sceglie_sede(self):
        admin = get_user_model().objects.create_superuser("admin", password=PASSWORD)
        self.client.force_login(admin)
        r = self.client.get(reverse("novecento:scelta_sede"))
        self.assertContains(r, "Foligno")
        r = self.client.post(reverse("novecento:scelta_sede"), {"sede": self.foligno.pk})
        self.assertRedirects(r, reverse("novecento:operatore"))

    def test_quantita_conservate_tra_categorie(self):
        self._avvia()
        self.client.post(
            reverse("novecento:categoria", args=[1]),
            {f"art_{self.coni.pk}": "5", "vai": ""},
        )
        r = self.client.get(reverse("novecento:categorie"))
        self.assertContains(r, "1 scelto")
        r = self.client.get(reverse("novecento:categoria", args=[1]))
        self.assertContains(r, 'value="5"')

    def test_ordine_vuoto_non_inviato(self):
        self._avvia()
        r = self.client.post(reverse("novecento:riepilogo"), {"note": ""})
        self.assertRedirects(r, reverse("novecento:categorie"))
        self.assertFalse(Ordine.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_conferma_non_visibile_ad_altra_sede(self):
        self._avvia()
        self._ordina_e_invia()
        ordine_id = self.client.session["ultimo_ordine_id"]
        self.client.force_login(self.account_foligno)
        sessione = self.client.session
        sessione["ultimo_ordine_id"] = ordine_id
        sessione.save()
        r = self.client.get(reverse("novecento:pdf_ordine"))
        self.assertEqual(r.status_code, 404)

    @override_settings(ORDINI_EMAIL_DESTINATARI=[])
    def test_senza_destinatari_ordine_in_errore(self):
        self._avvia()
        self._ordina_e_invia()
        ordine = Ordine.objects.get()
        self.assertEqual(ordine.stato_invio, Ordine.StatoInvio.ERRORE)
        r = self.client.get(reverse("novecento:conferma"))
        self.assertContains(r, "Riprova invio")

    def test_pdf_con_caratteri_speciali(self):
        ordine = Ordine.objects.create(sede=self.sede, nome="A", cognome="B", note="<b>&</b>")
        ordine.righe.create(
            categoria_nome="1 - Cat & co", gruppo_nome="Coni <grandi>", codice="X&Y",
            articolo_nome="Vaschette ½ kg", unita="cartone da 6 pz", quantita=1,
        )
        self.assertTrue(genera_pdf_ordine(ordine).startswith(b"%PDF"))


class ListinoTest(TestCase):
    def test_listino_900_caricato(self):
        self.assertEqual(Categoria.objects.count(), 7)
        self.assertEqual(Articolo.objects.count(), 57)
        self.assertEqual(
            list(Categoria.objects.values_list("numero", flat=True)), [1, 2, 3, 4, 5, 6, 7]
        )
        coni = Gruppo.objects.get(nome="Coni e cialde")
        self.assertEqual(coni.articoli.count(), 5)
        self.assertEqual(Articolo.objects.get(nome="Ghiaccio a cubetti 10 kg").codice, "SOT001")


class CredenzialiSedeTest(TestCase):
    def _dati(self, sede, **extra):
        dati = {
            "nome": sede.nome,
            "slug": sede.slug,
            "indirizzo": "",
            "email": "",
            "attiva": "on",
            "ordine": "0",
            "preavviso_minuti": "30",
        }
        dati.update(extra)
        return dati

    def test_admin_crea_e_aggiorna_account(self):
        sede = Sede.objects.create(nome="Assisi", slug="assisi")
        form = SedeAdminForm(self._dati(sede, username="assisi"), instance=sede)
        self.assertFalse(form.is_valid())
        self.assertIn("nuova_password", form.errors)

        form = SedeAdminForm(
            self._dati(sede, username="assisi", nuova_password=PASSWORD), instance=sede
        )
        self.assertTrue(form.is_valid(), form.errors)
        sede = form.save()
        self.assertTrue(sede.account.check_password(PASSWORD))

        form = SedeAdminForm(self._dati(sede, username="assisi900"), instance=sede)
        self.assertTrue(form.is_valid(), form.errors)
        sede = form.save()
        sede.account.refresh_from_db()
        self.assertEqual(sede.account.username, "assisi900")
        self.assertTrue(sede.account.check_password(PASSWORD))

        account = sede.account
        form = SedeAdminForm(self._dati(sede, disattiva_account="on"), instance=sede)
        self.assertTrue(form.is_valid(), form.errors)
        sede = form.save()
        account.refresh_from_db()
        self.assertIsNone(sede.account)
        self.assertFalse(account.is_active)

    def test_admin_rifiuta_username_duplicato_e_password_debole(self):
        get_user_model().objects.create_user("occupato", password=PASSWORD)
        sede = Sede.objects.create(nome="Assisi", slug="assisi")
        form = SedeAdminForm(
            self._dati(sede, username="Occupato", nuova_password="123"), instance=sede
        )
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)
        self.assertIn("nuova_password", form.errors)

    def test_comando_crea_accesso_sede(self):
        sede = Sede.objects.get(slug="spello")
        out = StringIO()
        call_command("crea_accesso_sede", "spello", "--password", PASSWORD, stdout=out)
        sede.refresh_from_db()
        self.assertEqual(sede.account.username, "spello")
        self.assertTrue(sede.account.check_password(PASSWORD))
        self.assertIn("creato", out.getvalue())

        with self.assertRaises(CommandError):
            call_command("crea_accesso_sede", "inesistente", "--password", PASSWORD)
        with self.assertRaises(CommandError):
            call_command("crea_accesso_sede", "bastia", "--password", "123")


class DatiDemoTest(TestCase):
    @override_settings(DEBUG=True)
    def test_crea_account_demo_idempotente(self):
        call_command("dati_demo", stdout=StringIO())
        call_command("dati_demo", stdout=StringIO())
        for sede in Sede.objects.filter(attiva=True):
            self.assertIsNotNone(sede.account)
        self.assertTrue(
            get_user_model().objects.get(username="admin").check_password("Demo-Admin-2026")
        )

    @override_settings(DEBUG=False)
    def test_bloccato_in_produzione(self):
        with self.assertRaises(CommandError):
            call_command("dati_demo", stdout=StringIO())


class PortaLiberaTest(TestCase):
    def test_salta_porta_occupata(self):
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupata:
            occupata.bind(("127.0.0.1", 0))
            occupata.listen()
            porta = occupata.getsockname()[1]
            out = StringIO()
            call_command("porta_libera", "--da", str(porta), stdout=out)
            self.assertNotEqual(int(out.getvalue()), porta)


class AvvisoOrdineTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account = get_user_model().objects.create_user("assisi", password=PASSWORD)
        cls.sede = Sede.objects.create(
            nome="Assisi",
            slug="assisi",
            account=cls.account,
            orario_ordine=datetime.time(10, 0),
            giorni_ordine="012345",
            preavviso_minuti=30,
        )

    def _alle(self, anno, mese, giorno, ora, minuto):
        return timezone.make_aware(datetime.datetime(anno, mese, giorno, ora, minuto))

    def test_stati_ordine(self):
        lunedi = (2026, 11, 16)
        stato = self.sede.stato_ordine(self._alle(*lunedi, 8, 0))
        self.assertEqual(stato["stato"], "da_fare")
        self.assertEqual(stato["minuti"], 120)
        self.assertFalse(stato["urgente"])
        self.assertTrue(self.sede.stato_ordine(self._alle(*lunedi, 9, 45))["urgente"])
        stato = self.sede.stato_ordine(self._alle(*lunedi, 10, 20))
        self.assertEqual((stato["stato"], stato["ritardo"]), ("in_ritardo", 20))
        domenica = (2026, 11, 15)
        self.assertIsNone(self.sede.stato_ordine(self._alle(*domenica, 9, 0)))

    def test_ordine_inviato_oggi(self):
        Ordine.objects.create(sede=self.sede, nome="Anna", cognome="Verdi")
        stato = self.sede.stato_ordine()
        self.assertEqual(stato["stato"], "inviato")

    def test_senza_orario_nessun_avviso(self):
        self.sede.orario_ordine = None
        self.assertIsNone(self.sede.stato_ordine(self._alle(2026, 11, 16, 9, 0)))

    def test_avviso_mostrato_in_app(self):
        self.client.force_login(self.account)
        r = self.client.get(reverse("novecento:scelta_sede"), follow=True)
        oggi_previsto = self.sede.ordina_il(timezone.localdate())
        if oggi_previsto:
            self.assertContains(r, "10:00")
        Ordine.objects.create(sede=self.sede, nome="Anna", cognome="Verdi")
        r = self.client.get(reverse("novecento:operatore"))
        self.assertContains(r, "Ordine inviato alle")

    def test_promemoria_calendario(self):
        self.client.force_login(self.account)
        r = self.client.get(reverse("novecento:promemoria"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/calendar", r["Content-Type"])
        testo = r.content.decode()
        self.assertIn("RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR,SA", testo)
        self.assertIn("T093000", testo)
        self.assertIn("T100000", testo)
        self.assertIn("BEGIN:VALARM", testo)
        self.assertIn("Ordine 900 Assisi entro le 10:00", testo)
        for riga in testo.split("\r\n"):
            self.assertLessEqual(len(riga.encode()), 75)

    def test_promemoria_senza_orario(self):
        self.sede.orario_ordine = None
        self.sede.save()
        self.client.force_login(self.account)
        r = self.client.get(reverse("novecento:promemoria"))
        self.assertEqual(r.status_code, 302)

    def test_admin_salva_giorni(self):
        form = SedeAdminForm(
            {
                "nome": "Assisi",
                "slug": "assisi",
                "indirizzo": "",
                "email": "",
                "attiva": "on",
                "ordine": "0",
                "orario_ordine": "09:30",
                "preavviso_minuti": "15",
                "giorni": ["0", "2", "4"],
                "username": "assisi",
            },
            instance=self.sede,
        )
        self.assertTrue(form.is_valid(), form.errors)
        sede = form.save()
        self.assertEqual(sede.giorni_ordine, "024")
        self.assertEqual(sede.giorni_display(), "Lun, Mer, Ven")
        self.assertEqual(sede.orario_ordine, datetime.time(9, 30))


class ConfigurazioneTest(TestCase):
    def test_lettura_file_env(self):
        import os
        import tempfile
        from pathlib import Path

        from config.settings import _carica_env

        with tempfile.TemporaryDirectory() as cartella:
            percorso = Path(cartella) / ".env"
            percorso.write_text(
                "# commento\nNV_PROVA_A=uno\nNV_PROVA_B=\"due tre\"\nriga senza uguale\n",
                encoding="utf-8",
            )
            os.environ["NV_PROVA_A"] = "gia-impostata"
            try:
                _carica_env(percorso)
                self.assertEqual(os.environ["NV_PROVA_A"], "gia-impostata")
                self.assertEqual(os.environ["NV_PROVA_B"], "due tre")
            finally:
                os.environ.pop("NV_PROVA_A", None)
                os.environ.pop("NV_PROVA_B", None)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_di_prova(self):
        out = StringIO()
        call_command("invia_email_prova", "lab@example.com", stdout=out)
        self.assertEqual(mail.outbox[0].to, ["lab@example.com"])
        self.assertIn("inviata", out.getvalue())

    @override_settings(ORDINI_EMAIL_DESTINATARI=[])
    def test_email_di_prova_senza_destinatari(self):
        with self.assertRaises(CommandError):
            call_command("invia_email_prova", stdout=StringIO())


class ListinoExcelTest(TestCase):
    def _file(self, modifica):
        from io import BytesIO

        from openpyxl import load_workbook

        from .listino_excel import esporta_listino

        libro = load_workbook(BytesIO(esporta_listino()))
        foglio = libro["Listino"]
        modifica(foglio)
        buffer = BytesIO()
        libro.save(buffer)
        buffer.seek(0)
        buffer.name = "listino.xlsx"
        return buffer

    def _riga(self, foglio, descrizione):
        for riga in foglio.iter_rows(min_row=2):
            if riga[5].value == descrizione:
                return riga
        raise AssertionError(descrizione)

    def test_esportazione_contiene_listino(self):
        from io import BytesIO

        from openpyxl import load_workbook

        from .listino_excel import esporta_listino

        libro = load_workbook(BytesIO(esporta_listino()))
        self.assertEqual(libro.sheetnames, ["Listino", "Istruzioni"])
        self.assertEqual(libro["Listino"].max_row, 1 + Articolo.objects.count())

    def test_importazione_aggiorna_e_crea(self):
        from .listino_excel import importa_listino

        def modifica(foglio):
            riga = self._riga(foglio, "Cono wafer 091")
            riga[4].value = "NOCC-091"
            riga[7].value = 6
            riga[8].value = "0,045"
            riga[9].value = 27.5
            riga[10].value = 22
            self._riga(foglio, "Sfere classiche")[11].value = "NO"
            foglio.append([None, 1, "", "Coni speciali", "X1", "Cono al cacao", "CT", 4, None, None, 10, "SI"])
            foglio.append([None, 8, "Bevande", "Acque", "", "Acqua naturale 0,5 l", "CT", 24, None, None, None, ""])

        esito = importa_listino(self._file(modifica))
        self.assertTrue(esito.riuscita, esito.errori)
        self.assertEqual((esito.creati, esito.aggiornati), (2, 2))
        wafer = Articolo.objects.get(nome="Cono wafer 091")
        self.assertEqual(wafer.codice, "NOCC-091")
        self.assertEqual(wafer.pezzi_per_cartone, 6)
        self.assertEqual(str(wafer.prezzo_pezzo), "0.045")
        self.assertEqual(str(wafer.prezzo_cartone), "27.50")
        self.assertEqual(wafer.iva, 22)
        self.assertEqual(wafer.confezione, "cartone da 6 pz")
        self.assertFalse(Articolo.objects.get(nome="Sfere classiche").attivo)
        nuovo = Articolo.objects.get(nome="Cono al cacao")
        self.assertEqual(nuovo.gruppo.nome, "Coni speciali")
        self.assertEqual(nuovo.gruppo.categoria.numero, 1)
        self.assertEqual(Categoria.objects.get(numero=8).nome, "Bevande")

    def test_errore_annulla_tutto(self):
        from .listino_excel import importa_listino

        def modifica(foglio):
            self._riga(foglio, "Cono wafer 091")[4].value = "CAMBIATO"
            self._riga(foglio, "Sacher")[6].value = "KG"
            foglio.append([None, 99, "", "X", "", "Senza categoria", "CF", None, None, None, None, "SI"])

        esito = importa_listino(self._file(modifica))
        self.assertFalse(esito.riuscita)
        self.assertEqual(len(esito.errori), 2)
        self.assertIn("unità «KG» non valida", esito.errori[0])
        self.assertIn("categoria 99 non esiste", esito.errori[1])
        self.assertEqual(Articolo.objects.get(nome="Cono wafer 091").codice, "NOCC")

    def test_file_non_valido(self):
        from io import BytesIO

        from .listino_excel import importa_listino

        esito = importa_listino(BytesIO(b"non sono un excel"))
        self.assertFalse(esito.riuscita)

    def test_pagine_admin(self):
        admin = get_user_model().objects.create_superuser("admin", password=PASSWORD)
        self.client.force_login(admin)
        r = self.client.get(reverse("admin:novecento_articolo_changelist"))
        self.assertContains(r, "Esporta in Excel")
        self.assertContains(r, "Importa da Excel")
        self.assertContains(r, reverse("admin:novecento_articolo_importa"))
        r = self.client.get(reverse("admin:novecento_articolo_esporta"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])

        def modifica(foglio):
            self._riga(foglio, "Sacher")[4].value = "SAC01"

        r = self.client.post(
            reverse("admin:novecento_articolo_importa"), {"file": self._file(modifica)}, follow=True
        )
        self.assertContains(r, "Listino importato")
        self.assertEqual(Articolo.objects.get(nome="Sacher").codice, "SAC01")

    def test_operatore_sede_non_accede(self):
        utente = get_user_model().objects.create_user("spello2", password=PASSWORD)
        self.client.force_login(utente)
        r = self.client.get(reverse("admin:novecento_articolo_esporta"))
        self.assertEqual(r.status_code, 302)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class GmailDaAdminTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("capo", password=PASSWORD)
        self.client.force_login(self.admin)
        self.url = reverse("admin:novecento_impostazioni_change", args=[Impostazioni.corrente().pk])

    def _dati(self, **extra):
        dati = {"email_destinatari": "lab@example.com", "email_mittente": "", "nuova_password_app": ""}
        dati.update(extra)
        return dati

    def test_salva_password_e_la_mantiene(self):
        r = self.client.post(
            self.url,
            self._dati(email_mittente="prova@gmail.com", nuova_password_app="abcd efgh ijkl mnop"),
        )
        self.assertEqual(r.status_code, 302)
        impostazioni = Impostazioni.corrente()
        self.assertEqual(impostazioni.email_password_app, "abcdefghijklmnop")
        self.assertTrue(impostazioni.gmail_configurato)

        self.client.post(self.url, self._dati(email_mittente="prova@gmail.com"))
        self.assertEqual(Impostazioni.corrente().email_password_app, "abcdefghijklmnop")

        r = self.client.get(self.url)
        self.assertNotContains(r, "abcdefghijklmnop")
        self.assertContains(r, "Password per le app salvata")

    def test_password_errata_o_mancante(self):
        r = self.client.post(
            self.url, self._dati(email_mittente="prova@gmail.com", nuova_password_app="corta")
        )
        self.assertContains(r, "16 lettere")
        r = self.client.post(self.url, self._dati(email_mittente="prova@gmail.com"))
        self.assertContains(r, "Inserisci la password per le app")
        self.assertFalse(Impostazioni.corrente().gmail_configurato)

    def test_scollega_gmail(self):
        self.client.post(
            self.url,
            self._dati(email_mittente="prova@gmail.com", nuova_password_app="abcdefghijklmnop"),
        )
        self.client.post(self.url, self._dati(email_mittente="prova@gmail.com", rimuovi_gmail="on"))
        impostazioni = Impostazioni.corrente()
        self.assertEqual((impostazioni.email_mittente, impostazioni.email_password_app), ("", ""))

    def test_pulsante_email_di_prova_usa_gmail(self):
        r = self.client.post(
            self.url,
            self._dati(
                email_mittente="prova@gmail.com",
                nuova_password_app="abcdefghijklmnop",
                _email_prova="1",
            ),
            follow=True,
        )
        self.assertContains(r, "Email di prova inviata a: lab@example.com")
        self.assertEqual(mail.outbox[0].from_email, "Ordini Novecento <prova@gmail.com>")
        self.assertEqual(mail.outbox[0].to, ["lab@example.com"])

    def test_ordine_inviato_dal_gmail_di_admin(self):
        impostazioni = Impostazioni.corrente()
        impostazioni.email_destinatari = "lab@example.com"
        impostazioni.email_mittente = "prova@gmail.com"
        impostazioni.email_password_app = "abcdefghijklmnop"
        impostazioni.save()
        sede = Sede.objects.get(slug="spello")
        ordine = Ordine.objects.create(sede=sede, nome="A", cognome="B")
        ordine.righe.create(categoria_nome="1 - X", articolo_nome="Y", unita="pezzo", quantita=1)
        from .notifiche import invia_ordine

        self.assertTrue(invia_ordine(ordine))
        self.assertEqual(mail.outbox[0].from_email, "Ordini Novecento <prova@gmail.com>")


class VariantiTest(TestCase):
    def _nomi(self, *nomi):
        from types import SimpleNamespace

        from .views import _segna_varianti

        return [(a.base, a.variante) for a in _segna_varianti(SimpleNamespace(nome=n) for n in nomi)]

    def test_parte_comune_iniziale(self):
        self.assertEqual(
            self._nomi("Coppette cartone baby", "Coppette cartone piccole", "Coppette cartone grandi"),
            [("Coppette cartone", "baby"), ("Coppette cartone", "piccole"), ("Coppette cartone", "grandi")],
        )

    def test_nessuna_parte_comune_o_un_solo_articolo(self):
        self.assertEqual(self._nomi("Sacher", "Torta soffice"), [("", ""), ("", "")])
        self.assertEqual(self._nomi("Box palette"), [("", "")])

    def test_nome_contenuto_in_altro(self):
        self.assertEqual(self._nomi("Cornetto", "Cornetto vuoto"), [("", ""), ("", "")])

    def test_mostrato_in_categoria(self):
        Articolo.objects.all().delete()
        Categoria.objects.all().delete()
        account = get_user_model().objects.create_user("perugia", password=PASSWORD)
        Sede.objects.create(nome="Perugia", slug="perugia", account=account)
        cat = Categoria.objects.create(numero=1, nome="Gelateria")
        gruppo = Gruppo.objects.create(categoria=cat, nome="Coppette")
        for taglia in ["piccole", "medie"]:
            Articolo.objects.create(gruppo=gruppo, nome=f"Coppette cartone {taglia}")
        self.client.force_login(account)
        self.client.get(reverse("novecento:scelta_sede"))
        self.client.post(reverse("novecento:operatore"), {"nome": "A", "cognome": "B"})
        r = self.client.get(reverse("novecento:categoria", args=[1]))
        self.assertContains(r, '<span class="articolo-base">Coppette cartone</span>', html=True)
        self.assertContains(r, ">Medie</label>")


class SalutoTest(TestCase):
    def test_saluto_in_base_all_ora(self):
        from .context_processors import saluto_del_momento

        def alle(ora):
            return timezone.make_aware(datetime.datetime(2026, 11, 16, ora, 30))

        self.assertEqual(saluto_del_momento(alle(8)), "Buongiorno")
        self.assertEqual(saluto_del_momento(alle(12)), "Buongiorno")
        self.assertEqual(saluto_del_momento(alle(13)), "Buon pomeriggio")
        self.assertEqual(saluto_del_momento(alle(17)), "Buon pomeriggio")
        self.assertEqual(saluto_del_momento(alle(18)), "Buonasera")
        self.assertEqual(saluto_del_momento(alle(2)), "Buonasera")

    def test_saluto_nella_pagina_di_accesso(self):
        from .context_processors import saluto_del_momento

        r = self.client.get(reverse("login"))
        self.assertContains(r, f'<h1 class="titolo">{saluto_del_momento()}</h1>', html=True)
        self.assertNotContains(r, "Ciao")
