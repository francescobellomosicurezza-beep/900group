from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsernameSenzaMaiuscoleBackend(ModelBackend):
    """Accesso con username indipendente da maiuscole/minuscole (es. «Foligno» = «foligno»).

    La password resta sensibile alle maiuscole.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        Utente = get_user_model()
        if username is None:
            username = kwargs.get(Utente.USERNAME_FIELD)
        if username is None or password is None:
            return None
        username = username.strip()
        corrispondenti = list(
            Utente._default_manager.filter(**{f"{Utente.USERNAME_FIELD}__iexact": username})[:2]
        )
        if len(corrispondenti) != 1:
            # nessuno, oppure più account che differiscono solo per le maiuscole:
            # in quel caso vale solo la corrispondenza esatta
            return super().authenticate(request, username=username, password=password, **kwargs)
        utente = corrispondenti[0]
        if utente.check_password(password) and self.user_can_authenticate(utente):
            return utente
        Utente().set_password(password)  # tempo costante anche se la password è errata
        return None
