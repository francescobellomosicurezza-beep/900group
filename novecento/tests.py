from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Articolo, Categoria, Ordine, Sede
from .pdf import genera_pdf_ordine

DESTINATARIO = "laboratorio@example.com"


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
        cls.sede = Sede.objects.create(nome="Spello", slug="spello", email="spello@example.com")
        cls.cat_gelato = Categoria.objects.create(nome="Accessori gelato", ordine=1)
        cls.cat_bar = Categoria.objects.create(nome="Accessori bar", ordine=2)
        Categoria.objects.create(nome="Vuota", ordine=3)
        cls.coni = Articolo.objects.create(categoria=cls.cat_gelato, nome="Coni", unita="cartoni")
        cls.coppette = Articolo.objects.create(categoria=cls.cat_gelato, nome="Coppette")
        cls.bicchieri = Articolo.objects.create(categoria=cls.cat_bar, nome="Bicchieri")
        Articolo.objects.create(categoria=cls.cat_bar, nome="Disattivato", attivo=False)

    def _avvia(self):
        self.client.post(reverse("novecento:scelta_sede"), {"sede": self.sede.pk})
        self.client.post(
            reverse("novecento:operatore"), {"nome": "mario", "cognome": "rossi"}
        )

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

    def test_pin_obbligatorio(self):
        self.sede.imposta_pin("1234")
        self.sede.save()
        r = self.client.post(reverse("novecento:scelta_sede"), {"sede": self.sede.pk, "pin": "0000"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "PIN non corretto")
        r = self.client.post(reverse("novecento:scelta_sede"), {"sede": self.sede.pk, "pin": "1234"})
        self.assertRedirects(r, reverse("novecento:operatore"))

    def test_accesso_diretto_senza_sede(self):
        r = self.client.get(reverse("novecento:categoria", args=[1]))
        self.assertRedirects(r, reverse("novecento:scelta_sede"))

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
