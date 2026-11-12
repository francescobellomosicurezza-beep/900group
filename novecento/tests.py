from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin import SedeAdminForm
from .models import Articolo, Categoria, Ordine, Sede
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
        cls.cat_gelato = Categoria.objects.create(nome="Accessori gelato", ordine=1)
        cls.cat_bar = Categoria.objects.create(nome="Accessori bar", ordine=2)
        Categoria.objects.create(nome="Vuota", ordine=3)
        cls.coni = Articolo.objects.create(categoria=cls.cat_gelato, nome="Coni", unita="cartoni")
        cls.coppette = Articolo.objects.create(categoria=cls.cat_gelato, nome="Coppette")
        cls.bicchieri = Articolo.objects.create(categoria=cls.cat_bar, nome="Bicchieri")
        Articolo.objects.create(categoria=cls.cat_bar, nome="Disattivato", attivo=False)

    def _avvia(self, account=None):
        self.client.force_login(account or self.account_spello)
        r = self.client.get(reverse("novecento:scelta_sede"))
        self.assertRedirects(r, reverse("novecento:operatore"))
        self.client.post(reverse("novecento:operatore"), {"nome": "mario", "cognome": "rossi"})

    def test_anonimo_rimandato_al_login(self):
        for nome in ["scelta_sede", "operatore", "riepilogo", "conferma"]:
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

    def test_flusso_completo_invia_email_con_pdf(self):
        self._avvia()
        r = self.client.post(
            reverse("novecento:categoria", args=[1]),
            {f"art_{self.coni.pk}": "3", f"art_{self.coppette.pk}": "0", "azione": "avanti"},
        )
        self.assertRedirects(r, reverse("novecento:categoria", args=[2]))

        r = self.client.get(reverse("novecento:categoria", args=[2]))
        self.assertContains(r, "Bicchieri")
        self.assertNotContains(r, "Disattivato")

        r = self.client.post(
            reverse("novecento:categoria", args=[2]),
            {f"art_{self.bicchieri.pk}": "2", "azione": "avanti"},
        )
        self.assertRedirects(r, reverse("novecento:riepilogo"))

        r = self.client.post(reverse("novecento:riepilogo"), {"note": "Consegna entro le 10"})
        self.assertRedirects(r, reverse("novecento:conferma"))

        ordine = Ordine.objects.get()
        self.assertEqual(ordine.sede, self.sede)
        self.assertEqual(ordine.operatore, "Mario Rossi")
        self.assertEqual(ordine.stato_invio, Ordine.StatoInvio.INVIATO)
        self.assertEqual(
            sorted(ordine.righe.values_list("articolo_nome", "quantita")),
            [("Bicchieri", 2), ("Coni", 3)],
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

    def test_sede_non_manomettibile_da_altro_account(self):
        self._avvia()
        sessione = self.client.session
        bozza = sessione["ordine_bozza"]
        bozza["sede_id"] = self.foligno.pk
        sessione["ordine_bozza"] = bozza
        sessione.save()
        r = self.client.get(reverse("novecento:categoria", args=[1]))
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

    def test_indietro_conserva_quantita(self):
        self._avvia()
        self.client.post(
            reverse("novecento:categoria", args=[1]),
            {f"art_{self.coni.pk}": "5", "azione": "avanti"},
        )
        r = self.client.get(reverse("novecento:categoria", args=[1]))
        self.assertContains(r, 'value="5"')

    def test_ordine_vuoto_non_inviato(self):
        self._avvia()
        r = self.client.post(reverse("novecento:riepilogo"), {"note": ""})
        self.assertRedirects(r, reverse("novecento:categoria", args=[1]))
        self.assertFalse(Ordine.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_conferma_non_visibile_ad_altra_sede(self):
        self._avvia()
        self.client.post(
            reverse("novecento:categoria", args=[1]),
            {f"art_{self.coni.pk}": "1", "azione": "avanti"},
        )
        self.client.post(reverse("novecento:riepilogo"), {})
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
        self.client.post(
            reverse("novecento:categoria", args=[1]),
            {f"art_{self.coni.pk}": "1", "azione": "avanti"},
        )
        self.client.post(reverse("novecento:riepilogo"), {})
        ordine = Ordine.objects.get()
        self.assertEqual(ordine.stato_invio, Ordine.StatoInvio.ERRORE)
        r = self.client.get(reverse("novecento:conferma"))
        self.assertContains(r, "Riprova invio")

    def test_pdf_con_caratteri_speciali(self):
        ordine = Ordine.objects.create(sede=self.sede, nome="A", cognome="B", note="<b>&</b>")
        ordine.righe.create(
            categoria_nome="Cat & co", articolo_nome="Vaschette ½ kg", unita="pz", quantita=1
        )
        self.assertTrue(genera_pdf_ordine(ordine).startswith(b"%PDF"))


class CredenzialiSedeTest(TestCase):
    def _dati(self, sede, **extra):
        dati = {
            "nome": sede.nome,
            "slug": sede.slug,
            "indirizzo": "",
            "email": "",
            "attiva": "on",
            "ordine": "0",
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
