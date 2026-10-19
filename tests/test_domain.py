import pytest

from app.domain import Guerrier, Heros, Issue, Mage, Monstre, Voleur, tour_de_combat
from app.schemas.hero import Classe
from app.services import carte

JAMAIS = lambda: 0.99
TOUJOURS = lambda: 0.0


def test_heros_est_abstrait():
    with pytest.raises(TypeError):
        Heros(force=4, agilite=3, intelligence=3)


@pytest.mark.parametrize(
    ("heros", "degats", "pv_max"),
    [
        (Guerrier(force=6, agilite=2, intelligence=2), 14, 32),
        (Mage(force=2, agilite=2, intelligence=6), 19, 24),
        (Voleur(force=2, agilite=6, intelligence=2, de=JAMAIS), 14, 24),
    ],
)
def test_exemples_du_sujet(heros, degats, pv_max):
    assert heros.calculer_degats().degats == degats
    assert heros.pv_max == pv_max


def test_voleur_critique():
    coup = Voleur(force=2, agilite=6, intelligence=2, de=TOUJOURS).calculer_degats()
    assert coup.degats == 28 and coup.critique


def test_armure_du_guerrier():
    guerrier = Guerrier(force=6, agilite=2, intelligence=2)
    assert guerrier.subir_degats(7) == 6
    assert guerrier.subir_degats(1) == 1
    assert Mage(force=2, agilite=2, intelligence=6).subir_degats(7) == 7


def test_registre_aligne_sur_le_schema():
    assert set(Heros.classes()) == {c.value for c in Classe}


def test_tour_avec_riposte():
    heros = Mage(force=2, agilite=2, intelligence=2)
    monstre = Monstre("Ogre", 30, 6, 40)
    tour = tour_de_combat(heros, monstre)
    assert (tour.degats_infliges, tour.degats_subis, tour.issue) == (7, 6, Issue.EN_COURS)
    assert (heros.pv, monstre.pv) == (18, 23)


def _combat(heros, monstre) -> bool:
    while heros.est_vivant and monstre.est_vivant:
        tour_de_combat(heros, monstre)
    return heros.est_vivant


@pytest.mark.parametrize(
    "classe,stats",
    [
        ("guerrier", {"force": 6, "agilite": 2, "intelligence": 2}),
        ("mage", {"force": 2, "agilite": 2, "intelligence": 6}),
        ("voleur", {"force": 2, "agilite": 6, "intelligence": 2}),
    ],
)
def test_chaque_classe_peut_vaincre_la_liche(classe, stats):
    # pire cas : aucun critique, chemin réel couloir → antichambre, repos, puis trône
    heros = Heros.incarner(classe, **stats, de=JAMAIS)
    for salle in ("couloir", "antichambre"):
        assert _combat(heros, _monstre(salle))
    heros.pv = heros.pv_max
    assert _combat(heros, _monstre(carte.ARRIVEE))


def _monstre(room_id: str) -> Monstre:
    fiche = carte.monstre_de(room_id)
    return Monstre(fiche.nom, fiche.pv_max, fiche.attaque, fiche.recompense)


def test_carte_fournie():
    assert carte.nombre_de_salles() == 8
    assert carte.salle(carte.DEPART).sorties == {"nord": "hall"}
    assert carte.monstre_de("bibliotheque") == carte.FicheMonstre("Gobelin", 12, 3, 10)
