from fastapi import HTTPException, status


class ErreurMetier(HTTPException):
    statut: int = status.HTTP_400_BAD_REQUEST
    code: str = "ERROR"
    message_defaut: str = "Erreur."

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(
            status_code=self.statut,
            detail={"error": self.code, "message": message or self.message_defaut},
            headers=headers,
        )


class PasDeSortie(ErreurMetier):
    statut, code = status.HTTP_400_BAD_REQUEST, "NO_EXIT"
    message_defaut = "Il n'y a pas de passage dans cette direction."


class NonAuthentifie(ErreurMetier):
    statut, code = status.HTTP_401_UNAUTHORIZED, "NOT_AUTHENTICATED"
    message_defaut = "Token manquant, invalide ou expiré."

    def __init__(self, message: str | None = None):
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class IdentifiantsInvalides(NonAuthentifie):
    code = "BAD_CREDENTIALS"
    message_defaut = "Nom d'utilisateur ou mot de passe incorrect."


class PasTonHeros(ErreurMetier):
    statut, code = status.HTTP_403_FORBIDDEN, "NOT_YOUR_HERO"
    message_defaut = "Ce héros appartient à un autre joueur."


class HerosIntrouvable(ErreurMetier):
    statut, code = status.HTTP_404_NOT_FOUND, "HERO_NOT_FOUND"
    message_defaut = "Aucun héros ne porte cet identifiant."


class EnCombat(ErreurMetier):
    statut, code = status.HTTP_409_CONFLICT, "IN_COMBAT"
    message_defaut = "Action impossible pendant un combat."


class PasDeMonstre(ErreurMetier):
    statut, code = status.HTTP_409_CONFLICT, "NO_MONSTER"
    message_defaut = "Il n'y a aucun monstre à attaquer ici."


class HerosMort(ErreurMetier):
    statut, code = status.HTTP_409_CONFLICT, "HERO_DEAD"
    message_defaut = "Ce héros est mort : il ne peut plus agir."


class PseudoPris(ErreurMetier):
    statut, code = status.HTTP_409_CONFLICT, "USERNAME_TAKEN"
    message_defaut = "Ce nom d'utilisateur est déjà pris."
