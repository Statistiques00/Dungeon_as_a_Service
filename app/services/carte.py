from dataclasses import dataclass

from app.services import dungeon_map

# vue typée de la carte : le reste du code ne lit jamais le json brut

DEPART: str = dungeon_map.START_ROOM
ARRIVEE: str = dungeon_map.FINAL_ROOM


@dataclass(frozen=True)
class Salle:
    id: str
    nom: str
    description: str
    sorties: dict[str, str]


@dataclass(frozen=True)
class FicheMonstre:
    nom: str
    pv_max: int
    attaque: int
    recompense: int


def salle(room_id: str) -> Salle | None:
    brut = dungeon_map.get_room(room_id)
    if brut is None:
        return None
    return Salle(id=room_id, nom=brut["name"], description=brut["description"], sorties=dict(brut["exits"]))


def monstre_de(room_id: str) -> FicheMonstre | None:
    brut = dungeon_map.get_monster_of_room(room_id)
    if brut is None:
        return None
    return FicheMonstre(nom=brut["name"], pv_max=brut["hp"], attaque=brut["attack"], recompense=brut["gold"])


def nombre_de_salles() -> int:
    vues, a_visiter = set(), [DEPART]
    while a_visiter:
        courante = a_visiter.pop()
        if courante in vues or (s := salle(courante)) is None:
            continue
        vues.add(courante)
        a_visiter.extend(s.sorties.values())
    return len(vues)
