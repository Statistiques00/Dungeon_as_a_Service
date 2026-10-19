from fastapi import APIRouter

from app.routes.deps import SessionDep
from app.schemas.classement import EntreeClassement, HealthRead
from app.services import classement_service

router = APIRouter()


@router.get("/health", response_model=HealthRead, tags=["Système"], summary="État du serveur")
def health():
    return HealthRead()


@router.get(
    "/leaderboard",
    response_model=list[EntreeClassement],
    tags=["Classement"],
    summary="Top 10 des héros",
    description="Route publique : les vainqueurs de la Liche d'abord, puis par or amassé.",
)
def leaderboard(session: SessionDep):
    return classement_service.classement(session)
