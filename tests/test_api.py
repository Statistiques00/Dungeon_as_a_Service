import asyncio
import time

import httpx
import pytest

from app.main import app
from app.services import hero_service
from tests.conftest import GUERRIER, entete


def erreur(reponse) -> str:
    return reponse.json()["detail"]["error"]


# palier 1


def test_creation_nominale(client, alice):
    r = client.post("/heroes", json=GUERRIER, headers=alice)
    assert r.status_code == 201
    corps = r.json()
    assert corps["salle_actuelle"] == "entree"
    assert corps["pv"] == corps["pv_max"] == 32
    assert "monstre_pv" not in corps and "owner_id" not in corps


@pytest.mark.parametrize(
    "modif",
    [
        {"force": 6, "agilite": 5, "intelligence": 4},
        {"nom": "Al"},
        {"nom": "x" * 21},
        {"classe": "paladin"},
        {"force": 9, "agilite": 0, "intelligence": 1},
        {"force": "6"},
    ],
)
def test_creation_invalide_422(client, alice, modif):
    assert client.post("/heroes", json={**GUERRIER, **modif}, headers=alice).status_code == 422


def test_heros_inconnu_404(client, alice):
    r = client.get("/heroes/9999", headers=alice)
    assert r.status_code == 404
    assert set(r.json()["detail"]) == {"error", "message"}


# palier 2 et 3


def test_pas_de_sortie_400(client, alice, heros):
    r = client.post(f"/heroes/{heros['id']}/move", json={"direction": "est"}, headers=alice)
    assert r.status_code == 400 and erreur(r) == "NO_EXIT"


def test_direction_invalide_422(client, alice, heros):
    r = client.post(f"/heroes/{heros['id']}/move", json={"direction": "haut"}, headers=alice)
    assert r.status_code == 422


def test_partie_complete_contre_le_gobelin(client, alice, heros):
    hid = heros["id"]
    move = lambda d: client.post(f"/heroes/{hid}/move", json={"direction": d}, headers=alice)

    assert client.post(f"/heroes/{hid}/attack", headers=alice).json()["detail"]["error"] == "NO_MONSTER"
    assert move("nord").json()["id"] == "hall"
    salle = move("ouest").json()
    assert salle["monstre"]["nom"] == "Gobelin"

    r = move("est")
    assert r.status_code == 409 and erreur(r) == "IN_COMBAT"
    assert erreur(client.post(f"/heroes/{hid}/rest", headers=alice)) == "IN_COMBAT"

    tour = client.post(f"/heroes/{hid}/attack", headers=alice).json()
    assert tour["issue"] == "monstre_vaincu" and tour["or_gagne"] == 10
    assert client.get(f"/heroes/{hid}", headers=alice).json()["or"] == 10

    # donjon maudit : le gobelin revient
    move("est")
    assert move("ouest").json()["monstre"]["pv"] == 12


def test_repos_restaure_les_pv(client, alice, heros):
    hid = heros["id"]
    for d in ("nord", "est"):
        client.post(f"/heroes/{hid}/move", json={"direction": d}, headers=alice)
    # squelette de la crypte : une riposte, puis victoire au second coup
    blesse = client.post(f"/heroes/{hid}/attack", headers=alice).json()
    assert blesse["issue"] == "en_cours" and blesse["pv_heros"] == 29
    assert client.post(f"/heroes/{hid}/attack", headers=alice).json()["or_gagne"] == 15
    r = client.post(f"/heroes/{hid}/rest", headers=alice)
    assert r.status_code == 200 and r.json()["pv"] == r.json()["pv_max"]


def test_heros_mort_reste_consultable(client, alice, engine):
    from sqlmodel import Session

    from app.models import Hero

    hid = client.post("/heroes", json=GUERRIER, headers=alice).json()["id"]
    with Session(engine) as session:
        hero = session.get(Hero, hid)
        hero.pv = 0
        session.add(hero)
        session.commit()

    assert client.get(f"/heroes/{hid}", headers=alice).json()["est_vivant"] is False
    assert client.get(f"/heroes/{hid}/room", headers=alice).status_code == 200
    for action, corps in (("move", {"direction": "nord"}), ("attack", None), ("rest", None)):
        r = client.post(f"/heroes/{hid}/{action}", json=corps, headers=alice)
        assert r.status_code == 409 and erreur(r) == "HERO_DEAD"


# palier 4


def test_sans_token_401(client):
    r = client.get("/heroes")
    assert r.status_code == 401 and erreur(r) == "NOT_AUTHENTICATED"
    assert client.get("/heroes", headers={"Authorization": "Bearer faux"}).status_code == 401


def test_heros_d_un_autre_403(client, alice, heros):
    bob = entete(client, "bob")
    r = client.post(f"/heroes/{heros['id']}/move", json={"direction": "nord"}, headers=bob)
    assert r.status_code == 403 and erreur(r) == "NOT_YOUR_HERO"
    assert client.get("/heroes", headers=bob).json() == []


def test_mot_de_passe_hache_et_login(client, engine):
    from sqlmodel import Session, select

    from app.models import Player

    entete(client, "carol", "tres-secret")
    with Session(engine) as session:
        assert session.exec(select(Player)).one().hashed_password != "tres-secret"
    r = client.post("/auth/login", data={"username": "carol", "password": "mauvais"})
    assert r.status_code == 401 and erreur(r) == "BAD_CREDENTIALS"
    assert client.post("/auth/register", json={"username": "carol", "password": "xxxxxx"}).status_code == 409


def test_classement_public(client, alice, heros):
    r = client.get("/leaderboard")
    assert r.status_code == 200 and r.json()[0]["nom"] == "Aragorn"


# le serveur reste disponible pendant un repos


@pytest.mark.anyio
async def test_repos_non_bloquant(client, alice, heros, monkeypatch):
    monkeypatch.setattr(hero_service, "DUREE_REPOS", 0.5)
    fins: dict[str, float] = {}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as ac:

        async def appel(nom, methode, url):
            await ac.request(methode, url, headers=alice)
            fins[nom] = time.perf_counter()

        await asyncio.gather(
            appel("repos", "POST", f"/heroes/{heros['id']}/rest"),
            appel("health", "GET", "/health"),
        )

    assert fins["health"] < fins["repos"]


def test_victoire_contre_la_liche(client, alice, heros):
    hid = heros["id"]
    move = lambda d: client.post(f"/heroes/{hid}/move", json={"direction": d}, headers=alice)

    def combattre():
        while (tour := client.post(f"/heroes/{hid}/attack", headers=alice).json())["issue"] == "en_cours":
            pass
        return tour

    # entree → hall → couloir (rat) → antichambre (ogre) → repos → salle du trône
    move("nord")
    assert move("nord").json()["monstre"]["nom"] == "Rat géant"
    assert combattre()["issue"] == "monstre_vaincu"
    assert move("nord").json()["monstre"]["nom"] == "Ogre"
    assert combattre()["issue"] == "monstre_vaincu"
    client.post(f"/heroes/{hid}/rest", headers=alice)
    assert move("nord").json()["salle_finale"] is True
    tour = combattre()
    assert tour["issue"] == "monstre_vaincu" and tour["victoire"] is True
    assert client.get("/leaderboard").json()[0]["victoire"] is True
