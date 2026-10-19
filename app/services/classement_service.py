from sqlmodel import Session, select

from app.models import Hero, Player
from app.schemas.classement import EntreeClassement

TAILLE = 10


def classement(session: Session) -> list[EntreeClassement]:
    lignes = session.exec(
        select(Hero, Player)
        .join(Player, Hero.owner_id == Player.id)
        .order_by(Hero.victoire.desc(), Hero.or_.desc(), Hero.id)
        .limit(TAILLE)
    ).all()
    return [
        EntreeClassement(
            rang=rang,
            nom=hero.nom,
            classe=hero.classe,
            joueur=joueur.username,
            or_=hero.or_,
            victoire=hero.victoire,
            est_vivant=hero.est_vivant,
        )
        for rang, (hero, joueur) in enumerate(lignes, start=1)
    ]
