from sqlmodel import Session

from app.core.erreurs import PasDeMonstre
from app.core.journal import journal
from app.domain import Heros, Issue, Monstre, tour_de_combat
from app.models import Hero
from app.schemas.combat import AttackResult
from app.services import carte
from app.services.hero_service import exiger_vivant

log = journal("combat")


def attaquer(session: Session, hero: Hero, **options) -> AttackResult:
    exiger_vivant(hero)
    fiche = carte.monstre_de(hero.salle_actuelle)
    if not hero.en_combat or fiche is None:
        raise PasDeMonstre(f"Rien à combattre dans cette salle, {hero.nom} frappe dans le vide.")

    # le service construit les objets métier puis leur délègue tout le calcul
    heros = Heros.incarner(
        hero.classe,
        force=hero.force,
        agilite=hero.agilite,
        intelligence=hero.intelligence,
        pv=hero.pv,
        **options,
    )
    monstre = Monstre(fiche.nom, fiche.pv_max, fiche.attaque, fiche.recompense, pv=hero.monstre_pv)
    tour = tour_de_combat(heros, monstre)

    hero.pv = heros.pv
    or_gagne = 0
    if tour.issue is Issue.MONSTRE_VAINCU:
        or_gagne = monstre.recompense
        hero.or_ += or_gagne
        hero.monstre_pv = None
        if hero.salle_actuelle == carte.ARRIVEE:
            hero.victoire = True
    elif tour.issue is Issue.HEROS_MORT:
        hero.monstre_pv = None
    else:
        hero.monstre_pv = monstre.pv

    session.add(hero)
    session.commit()
    session.refresh(hero)

    recit = tour.recit(hero.nom, fiche.nom)
    log.info(
        "%s [%s] pv héros %s · pv %s %s", recit, tour.issue.value, tour.pv_heros, fiche.nom, tour.pv_monstre
    )
    if tour.issue is Issue.MONSTRE_VAINCU and hero.victoire and hero.salle_actuelle == carte.ARRIVEE:
        log.info("👑 %s a vaincu %s ! le donjon est libéré.", hero.nom, fiche.nom)

    return AttackResult(
        degats_infliges=tour.degats_infliges,
        critique=tour.critique,
        degats_subis=tour.degats_subis,
        pv_heros=tour.pv_heros,
        pv_monstre=tour.pv_monstre,
        issue=tour.issue,
        or_gagne=or_gagne,
        victoire=hero.victoire,
        recit=recit,
    )
