from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.core.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY
from app.core.erreurs import IdentifiantsInvalides, NonAuthentifie, PseudoPris
from app.core.journal import journal
from app.models import Player
from app.schemas.auth import PlayerCreate, Token

log = journal("auth")
_hasher = PasswordHash.recommended()
# hash factice : même temps de réponse que l'utilisateur existe ou non
_HASH_FANTOME = _hasher.hash("pixel-crypt-fantome")


def inscrire(session: Session, data: PlayerCreate) -> Player:
    if session.exec(select(Player).where(Player.username == data.username)).first():
        raise PseudoPris(f"Le nom « {data.username} » est déjà pris.")
    joueur = Player(username=data.username, hashed_password=_hasher.hash(data.password))
    session.add(joueur)
    session.commit()
    session.refresh(joueur)
    log.info("nouveau joueur : %s (#%s)", joueur.username, joueur.id)
    return joueur


def connecter(session: Session, username: str, password: str) -> Token:
    joueur = session.exec(select(Player).where(Player.username == username)).first()
    if joueur is None:
        _hasher.verify(password, _HASH_FANTOME)
        raise IdentifiantsInvalides()
    if not _hasher.verify(password, joueur.hashed_password):
        raise IdentifiantsInvalides()
    return Token(access_token=_emettre_token(joueur))


def joueur_du_token(session: Session, token: str | None) -> Player:
    if not token:
        raise NonAuthentifie("Authentification requise : envoyez un token Bearer.")
    try:
        charge = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        joueur_id = int(charge["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise NonAuthentifie() from None
    joueur = session.get(Player, joueur_id)
    if joueur is None:
        raise NonAuthentifie("Le joueur associé à ce token n'existe plus.")
    return joueur


def _emettre_token(joueur: Player) -> str:
    maintenant = datetime.now(timezone.utc)
    charge = {
        "sub": str(joueur.id),
        "name": joueur.username,
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(charge, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
