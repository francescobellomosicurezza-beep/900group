from django import forms

from .models import Sede


class SedeForm(forms.Form):
    """Scelta della sede, usata solo dagli amministratori."""

    sede = forms.ModelChoiceField(
        queryset=Sede.objects.filter(attiva=True),
        empty_label=None,
        widget=forms.RadioSelect,
        label="Seleziona il punto vendita",
    )


class OperatoreForm(forms.Form):
    nome = forms.CharField(
        label="Nome",
        max_length=80,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-lg", "autocomplete": "given-name"}
        ),
    )
    cognome = forms.CharField(
        label="Cognome",
        max_length=80,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-lg", "autocomplete": "family-name"}
        ),
    )

    def clean_nome(self):
        return self.cleaned_data["nome"].strip().title()

    def clean_cognome(self):
        return self.cleaned_data["cognome"].strip().title()


class CategoriaForm(forms.Form):
    """Un campo quantità per ogni articolo attivo della categoria."""

    def __init__(self, *args, articoli, **kwargs):
        super().__init__(*args, **kwargs)
        self.articoli = list(articoli)
        for articolo in self.articoli:
            self.fields[self.nome_campo(articolo)] = forms.IntegerField(
                label=articolo.nome,
                min_value=0,
                max_value=9999,
                required=False,
                widget=forms.NumberInput(
                    attrs={
                        "class": "form-control text-center qty-input",
                        "inputmode": "numeric",
                        "min": "0",
                        "step": "1",
                    }
                ),
            )

    @staticmethod
    def nome_campo(articolo):
        return f"art_{articolo.pk}"

    def righe(self):
        """Coppie (articolo, bound field) per il template."""
        return [(a, self[self.nome_campo(a)]) for a in self.articoli]

    def quantita(self):
        """Dizionario {id_articolo: quantità} con le sole quantità > 0."""
        risultato = {}
        for articolo in self.articoli:
            valore = self.cleaned_data.get(self.nome_campo(articolo)) or 0
            if valore > 0:
                risultato[str(articolo.pk)] = valore
        return risultato


class RiepilogoForm(forms.Form):
    note = forms.CharField(
        label="Note per il laboratorio",
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
