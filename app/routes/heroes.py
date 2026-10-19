from fastapi import APIRouter, Depends, status

from app.routes.deps import HeroDuJoueur, JoueurCourant, SessionDep, joueur_courant
from app.schemas.combat import AttackResult
from app.schemas.erreur import documenter
from app.schemas.hero import HeroCreate, HeroRead
from app.schemas.salle import CarteRead, MoveRequest, SalleRead
from app.services import combat_service, hero_service

router = APIRouter(
    prefix="/heroes",
    dependencies=[Depends(joueur_courant)],
    responses=documenter(401),
)

PROPRIETAIRE = (403, 404)


@router.post(
    "",
    response_model=HeroRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Héros"],
    summary="Créer un héros",
    description="Le héros apparaît dans la salle de départ, PV au maximum. "
    "Les trois statistiques (1 à 8) doivent totaliser exactement 10.",
)
def create_hero(data: HeroCreate, session: SessionDep, joueur: JoueurCourant):
    return hero_service.creer(session, data, joueur)


@router.get("", response_model=list[HeroRead], tags=["Héros"], summary="Lister mes héros")
def list_heroes(session: SessionDep, joueur: JoueurCourant):
    return hero_service.lister(session, joueur)


@router.get(
    "/{hero_id}",
    response_model=HeroRead,
    tags=["Héros"],
    summary="Consulter un héros",
    responses=documenter(*PROPRIETAIRE),
)
def get_hero(hero: HeroDuJoueur):
    return hero_service.lire(hero)


@router.get(
    "/{hero_id}/room",
    response_model=SalleRead,
    tags=["Exploration"],
    summary="Décrire la salle du héros",
    responses=documenter(*PROPRIETAIRE),
)
def get_room(hero: HeroDuJoueur):
    return hero_service.decrire_salle(hero)


@router.post(
    "/{hero_id}/move",
    response_model=SalleRead,
    tags=["Exploration"],
    summary="Se déplacer",
    description="Entrer dans une salle hantée réveille son monstre (le donjon est maudit).",
    responses=documenter(400, *PROPRIETAIRE, 409),
)
def move(data: MoveRequest, hero: HeroDuJoueur, session: SessionDep):
    return hero_service.deplacer(session, hero, data.direction)


@router.get(
    "/{hero_id}/map",
    response_model=CarteRead,
    tags=["Exploration"],
    summary="Carte des salles découvertes",
    description="Brouillard de guerre : seules les salles visitées sont révélées.",
    responses=documenter(*PROPRIETAIRE),
)
def get_map(hero: HeroDuJoueur):
    return hero_service.cartographier(hero)


@router.post(
    "/{hero_id}/attack",
    response_model=AttackResult,
    tags=["Combat"],
    summary="Jouer un tour de combat",
    description="Le héros frappe en premier ; si le monstre survit, il riposte.",
    responses=documenter(*PROPRIETAIRE, 409),
)
def attack(hero: HeroDuJoueur, session: SessionDep):
    return combat_service.attaquer(session, hero)


@router.post(
    "/{hero_id}/rest",
    response_model=HeroRead,
    tags=["Combat"],
    summary="Se reposer (3 secondes)",
    description="Route asynchrone : le serveur continue de répondre pendant la sieste.",
    responses=documenter(*PROPRIETAIRE, 409),
)
async def rest(hero: HeroDuJoueur, session: SessionDep):
    return await hero_service.reposer(session, hero)
