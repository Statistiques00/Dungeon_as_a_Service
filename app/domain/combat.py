from dataclasses import dataclass
from enum import Enum

from app.domain.heros import Heros
from app.domain.monstre import Monstre


class Issue(str, Enum):
    EN_COURS = "en_cours"
    MONSTRE_VAINCU = "monstre_vaincu"
    HEROS_MORT = "heros_mort"


@dataclass(frozen=True)
class Tour:
    degats_infliges: int
    critique: bool
    degats_subis: int
    pv_heros: int
    pv_monstre: int
    issue: Issue

    def recit(self, nom_heros: str, nom_monstre: str) -> str:
        coup = "coup critique ! " if self.critique else ""
        lignes = [f"{nom_heros} frappe {nom_monstre} : {coup}{self.degats_infliges} dégâts."]
        if self.issue is Issue.MONSTRE_VAINCU:
            lignes.append(f"{nom_monstre} s'effondre.")
        else:
            lignes.append(f"{nom_monstre} riposte : {self.degats_subis} dégâts.")
        if self.issue is Issue.HEROS_MORT:
            lignes.append(f"{nom_heros} tombe au combat.")
        return " ".join(lignes)


def tour_de_combat(heros: Heros, monstre: Monstre) -> Tour:
    coup = heros.calculer_degats()
    monstre.encaisser(coup.degats)

    if not monstre.est_vivant:
        return Tour(coup.degats, coup.critique, 0, heros.pv, 0, Issue.MONSTRE_VAINCU)

    subis = heros.subir_degats(monstre.attaque)
    heros.encaisser(subis)
    issue = Issue.EN_COURS if heros.est_vivant else Issue.HEROS_MORT
    return Tour(coup.degats, coup.critique, subis, heros.pv, monstre.pv, issue)
