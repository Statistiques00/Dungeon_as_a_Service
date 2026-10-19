from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.routes.deps import JoueurCourant, SessionDep
from app.schemas.auth import PlayerCreate, PlayerRead, Token
from app.schemas.erreur import documenter
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post(
    "/register",
    response_model=PlayerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte joueur",
    responses=documenter(409),
)
def register(data: PlayerCreate, session: SessionDep):
    return auth_service.inscrire(session, data)


@router.post(
    "/login",
    response_model=Token,
    summary="Se connecter et obtenir un token JWT",
    responses=documenter(401),
)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    return auth_service.connecter(session, form.username, form.password)


@router.get("/me", response_model=PlayerRead, summary="Joueur connecté", responses=documenter(401))
def me(joueur: JoueurCourant):
    return joueur
