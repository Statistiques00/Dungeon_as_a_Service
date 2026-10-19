import asyncio

from sqlmodel import Session, select

from app.core.erreurs import EnCombat, HerosIntrouvable, HerosMort, PasDeSortie, PasTonHeros
from app.core.journal import journal
from app.domain import Heros
from app.models import Hero, Player
from app.schemas.hero import HeroCreate, HeroRead
from app.schemas.salle import CarteRead, Direction, MonstreRead, SalleCarte, SalleRead
from app.services import carte

DUREE_REPOS = 3

log = journal("exploration")


def creer(session: Session, data: HeroCreate, joueur: Player) -> HeroRead:
    stats = data.model_dump(include={"force", "agilite", "intelligence"})
    pv_max = Heros.incarner(data.classe.value, **stats).pv_max
    hero = Hero(
        nom=data.nom,
        classe=data.classe.value,
        **stats,
        pv=pv_max,
        pv_max=pv_max,
        salle_actuelle=carte.DEPART,
        salles_decouvertes=[carte.DEPART],
        owner_id=joueur.id,
    )
    session.add(hero)
    session.commit()
    session.refresh(hero)
    log.info(
        "%s le %s entre dans le donjon (#%s, joueur %s)", hero.nom, hero.classe, hero.id, joueur.username
    )
    return HeroRead.model_validate(hero)


def lister(session: Session, joueur: Player) -> list[HeroRead]:
    heros = session.exec(select(Hero).where(Hero.owner_id == joueur.id).order_by(Hero.id)).all()
    return [HeroRead.model_validate(h) for h in heros]


def obtenir(session: Session, hero_id: int, joueur: Player) -> Hero:
    hero = session.get(Hero, hero_id)
    if hero is None:
        raise HerosIntrouvable(f"Aucun héros avec l'identifiant {hero_id}.")
    if hero.owner_id != joueur.id:
        raise PasTonHeros(f"Le héros {hero_id} appartient à un autre joueur.")
    return hero


def lire(hero: Hero) -> HeroRead:
    return HeroRead.model_validate(hero)


def decrire_salle(hero: Hero) -> SalleRead:
    salle = carte.salle(hero.salle_actuelle)
    monstre = None
    if hero.en_combat and (fiche := carte.monstre_de(salle.id)):
        monstre = MonstreRead(nom=fiche.nom, pv=hero.monstre_pv, pv_max=fiche.pv_max, attaque=fiche.attaque)
    return SalleRead(
        id=salle.id,
        nom=salle.nom,
        description=salle.description,
        sorties=list(salle.sorties),
        monstre=monstre,
        salle_finale=salle.id == carte.ARRIVEE,
    )


def deplacer(session: Session, hero: Hero, direction: Direction) -> SalleRead:
    exiger_vivant(hero)
    exiger_hors_combat(hero, "Impossible de fuir : {monstre} vous barre la route.")

    depart = carte.salle(hero.salle_actuelle)
    destination = depart.sorties.get(direction.value)
    if destination is None:
        article = "l'" if direction.value[0] in "aeiou" else "le "
        raise PasDeSortie(f"Il n'y a pas de passage vers {article}{direction.value}.")

    hero.salle_actuelle = destination
    if destination not in hero.salles_decouvertes:
        hero.salles_decouvertes = [*hero.salles_decouvertes, destination]

    # donjon maudit : le monstre renaît à chaque entrée
    fiche = carte.monstre_de(destination)
    hero.monstre_pv = fiche.pv_max if fiche else None

    session.add(hero)
    session.commit()
    session.refresh(hero)
    log.info(
        "%s : %s --%s--> %s%s",
        hero.nom,
        depart.id,
        direction.value,
        destination,
        f" ⚔ {fiche.nom} surgit" if fiche else "",
    )
    return decrire_salle(hero)


def cartographier(hero: Hero) -> CarteRead:
    connues = set(hero.salles_decouvertes)
    salles = []
    for room_id in hero.salles_decouvertes:
        salle = carte.salle(room_id)
        salles.append(
            SalleCarte(
                id=salle.id,
                nom=salle.nom,
                hantee=carte.monstre_de(salle.id) is not None,
                sorties={d: (cible if cible in connues else None) for d, cible in salle.sorties.items()},
            )
        )
    return CarteRead(
        depart=carte.DEPART,
        position=hero.salle_actuelle,
        salles=salles,
        explorees=len(salles),
        total=carte.nombre_de_salles(),
    )


async def reposer(session: Session, hero: Hero) -> HeroRead:
    exiger_vivant(hero)
    exiger_hors_combat(hero, "Impossible de se reposer : {monstre} est encore là.")
    log.info("%s s'assoupit (%ss)…", hero.nom, DUREE_REPOS)

    await asyncio.sleep(DUREE_REPOS)

    # l'état a pu changer pendant la sieste : on revérifie
    session.refresh(hero)
    exiger_vivant(hero)
    exiger_hors_combat(hero, "Le repos a été interrompu par {monstre}.")
    hero.pv = hero.pv_max
    session.add(hero)
    session.commit()
    session.refresh(hero)
    log.info("%s se réveille, %s/%s PV", hero.nom, hero.pv, hero.pv_max)
    return HeroRead.model_validate(hero)


def exiger_vivant(hero: Hero) -> None:
    if not hero.est_vivant:
        raise HerosMort(f"{hero.nom} est mort : il ne peut plus agir.")


def exiger_hors_combat(hero: Hero, message: str) -> None:
    if hero.en_combat:
        fiche = carte.monstre_de(hero.salle_actuelle)
        raise EnCombat(message.format(monstre=fiche.nom if fiche else "un monstre"))
