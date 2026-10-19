from typing import Annotated

from fastapi import Depends, Path
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.database import get_session
from app.models import Hero, Player
from app.services import auth_service, hero_service

# auto_error=False : le 401 garde notre format d'erreur
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

SessionDep = Annotated[Session, Depends(get_session)]


def joueur_courant(session: SessionDep, token: Annotated[str | None, Depends(oauth2)]) -> Player:
    return auth_service.joueur_du_token(session, token)


JoueurCourant = Annotated[Player, Depends(joueur_courant)]


def hero_du_joueur(
    hero_id: Annotated[int, Path(description="Identifiant du héros", ge=1)],
    session: SessionDep,
    joueur: JoueurCourant,
) -> Hero:
    return hero_service.obtenir(session, hero_id, joueur)


HeroDuJoueur = Annotated[Hero, Depends(hero_du_joueur)]
