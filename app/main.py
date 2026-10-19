from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  enregistre les tables
from app.core.journal import configurer_journal
from app.database import create_db_and_tables
from app.routes import auth, heroes, public

DESCRIPTION = """
Moteur de jeu de **Dungeon as a Service**, le rpg rétro du studio *Pixel Crypt*.

1. créez un compte (`/auth/register`) puis cliquez sur **Authorize** ;
2. créez un héros, explorez le donjon salle par salle ;
3. survivez jusqu'à la salle du trône et terrassez la Liche.

Toutes les erreurs métier suivent le format `{"detail": {"error": "CODE", "message": "..."}}`.
"""

TAGS = [
    {"name": "Authentification", "description": "Comptes joueurs et tokens JWT."},
    {"name": "Héros", "description": "Création et consultation de vos héros."},
    {"name": "Exploration", "description": "Salles, déplacements et carte du donjon."},
    {"name": "Combat", "description": "Tours de combat et repos."},
    {"name": "Classement", "description": "Le panthéon de Pixel Crypt."},
    {"name": "Système", "description": "Santé du serveur."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    configurer_journal()
    create_db_and_tables()
    yield


app = FastAPI(
    title="Dungeon as a Service",
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=TAGS,
    lifespan=lifespan,
)

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(heroes.router)
