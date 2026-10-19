import argparse
import getpass
import itertools
import os
import sys
import threading
import time
from pathlib import Path

import requests

API_URL = os.getenv("DUNGEON_API", "http://127.0.0.1:8000")
TOKEN_FILE = Path(".token")
HERO_FILE = Path(".hero")
TIMEOUT = 10

DIRECTIONS = {"nord": (0, -1), "sud": (0, 1), "est": (1, 0), "ouest": (-1, 0)}

if os.name == "nt":
    os.system("")  
COULEUR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def teinte(code: str):
    return lambda texte: f"\033[{code}m{texte}\033[0m" if COULEUR else str(texte)


gras, gris, rouge, vert, jaune, violet, cyan = map(teinte, ("1", "90", "31", "32", "33", "35", "36"))

BANNIERE = r"""
   ___
  |   \ _  _ _ _  __ _ ___ ___ _ _
  | |) | || | ' \/ _` / -_) _ \ ' \   as a
  |___/ \_,_|_||_\__, \___\___/_||_|  service
                 |___/          ~ pixel crypt ~
"""


class ErreurApi(Exception):
    pass


def appel(methode: str, chemin: str, auth: bool = True, **kwargs):
    entetes = {}
    if auth:
        if not TOKEN_FILE.exists():
            raise ErreurApi("pas de token : lancez d'abord « login ».")
        entetes["Authorization"] = f"Bearer {TOKEN_FILE.read_text().strip()}"
    try:
        r = requests.request(methode, API_URL + chemin, headers=entetes, timeout=TIMEOUT, **kwargs)
    except requests.ConnectionError:
        raise ErreurApi(f"serveur injoignable sur {API_URL} (fastapi dev app/main.py ?)") from None
    if r.ok:
        return r.json() if r.content else None
    raise ErreurApi(_message_erreur(r))


def _message_erreur(r: requests.Response) -> str:
    try:
        detail = r.json().get("detail")
    except ValueError:
        return f"{r.status_code} {r.reason}"
    if isinstance(detail, dict):
        return f"{r.status_code} {detail.get('error')} · {detail.get('message')}"
    if isinstance(detail, list):
        return "\n".join(f"422 · {'.'.join(map(str, e['loc'][1:]))} : {e['msg']}" for e in detail)
    return f"{r.status_code} · {detail}"


def hero_id(args) -> int:
    if args.hero:
        return args.hero
    if HERO_FILE.exists():
        return int(HERO_FILE.read_text())
    raise ErreurApi("aucun héros sélectionné : « create » ou --hero ID.")




def barre(valeur: int, maximum: int, largeur: int = 20) -> str:
    plein = round(largeur * valeur / maximum) if maximum else 0
    ratio = valeur / maximum if maximum else 0
    couleur = vert if ratio > 0.5 else jaune if ratio > 0.25 else rouge
    return f"{couleur('█' * plein)}{gris('░' * (largeur - plein))} {valeur}/{maximum}"


def afficher_hero(h: dict) -> None:
    etat = (
        rouge("☠ mort")
        if not h["est_vivant"]
        else rouge("⚔ en combat")
        if h["en_combat"]
        else vert("● libre")
    )
    couronne = jaune(" 👑") if h["victoire"] else ""
    print(f"{gras(h['nom'])} {gris('#' + str(h['id']))} · {h['classe']} · {etat}{couronne}")
    print(f"  PV  {barre(h['pv'], h['pv_max'])}")
    print(f"  FOR {h['force']}  AGI {h['agilite']}  INT {h['intelligence']}   {jaune(str(h['or']) + ' or')}")


def afficher_salle(s: dict) -> None:
    titre = f"{s['nom']}" + (violet("  ✦ salle finale") if s["salle_finale"] else "")
    print(f"\n{cyan('▌')} {gras(titre)}")
    print(f"{cyan('▌')} {gris(s['description'])}")
    print(f"{cyan('▌')} sorties : {', '.join(s['sorties']) or 'aucune'}")
    if m := s.get("monstre"):
        print(f"\n  {rouge('⚔ ' + m['nom'])}  {barre(m['pv'], m['pv_max'], 15)}  atk {m['attaque']}")


def dessiner_carte(carte: dict) -> str:
    salles = {s["id"]: s for s in carte["salles"]}
    pos = {carte["depart"]: (0, 0)}
    file = [carte["depart"]]
    inconnues = set()
    while file:
        courante = file.pop(0)
        x, y = pos[courante]
        for d, cible in salles[courante]["sorties"].items():
            dx, dy = DIRECTIONS.get(d, (0, 0))
            case = (x + dx, y + dy)
            if cible is None:
                inconnues.add(case)
            elif cible not in pos:
                pos[cible] = case
                file.append(cible)
    occupees = set(pos.values())
    inconnues -= occupees
    xs = [p[0] for p in occupees | inconnues]
    ys = [p[1] for p in occupees | inconnues]
    par_case = {v: k for k, v in pos.items()}

    lignes = []
    for y in range(min(ys), max(ys) + 1):
        haut, bas = [], []
        for x in range(min(xs), max(xs) + 1):
            rid = par_case.get((x, y))
            if rid:
                s = salles[rid]
                if rid == carte["position"]:
                    haut.append(jaune("[@]"))
                elif s["hantee"]:
                    haut.append(rouge("[!]"))
                else:
                    haut.append("[ ]")
                haut.append("─" if "est" in s["sorties"] else " ")
                bas.append(" │  " if "sud" in s["sorties"] else "    ")
            elif (x, y) in inconnues:
                haut.append(gris(" ? ") + " ")
                bas.append("    ")
            else:
                haut.append("    ")
                bas.append("    ")
        lignes.append("".join(haut).rstrip())
        lignes.append("".join(bas).rstrip())
    legende = f"{jaune('@')} vous  {rouge('!')} salle hantée  {gris('?')} inexploré"
    compteur = f"{carte['explorees']}/{carte['total']} salles explorées"
    return "\n".join(
        ["", *[f"  {l}" for l in lignes if l.strip()], "", f"  {legende}", f"  {gris(compteur)}"]
    )



def cmd_register(args):
    mdp = args.password or getpass.getpass("mot de passe : ")
    joueur = appel("POST", "/auth/register", auth=False, json={"username": args.username, "password": mdp})
    print(vert(f"compte créé : {joueur['username']} (#{joueur['id']})"))
    args.password = mdp
    cmd_login(args)


def cmd_login(args):
    mdp = args.password or getpass.getpass("mot de passe : ")
    token = appel("POST", "/auth/login", auth=False, data={"username": args.username, "password": mdp})
    TOKEN_FILE.write_text(token["access_token"])
    print(vert(f"connecté en tant que {args.username}, token enregistré dans {TOKEN_FILE}"))


def cmd_logout(_):
    for f in (TOKEN_FILE, HERO_FILE):
        f.unlink(missing_ok=True)
    print("à bientôt, aventurier.")


def cmd_create(args):
    corps = {
        "nom": args.nom,
        "classe": args.classe,
        "force": args.force,
        "agilite": args.agilite,
        "intelligence": args.intelligence,
    }
    h = appel("POST", "/heroes", json=corps)
    HERO_FILE.write_text(str(h["id"]))
    print(vert("un nouveau héros franchit la herse…\n"))
    afficher_hero(h)


def cmd_heroes(_):
    heros = appel("GET", "/heroes")
    actif = HERO_FILE.read_text().strip() if HERO_FILE.exists() else None
    if not heros:
        print(gris("aucun héros. créez-en un avec « create »."))
    for h in heros:
        print(jaune("▶ ") if str(h["id"]) == actif else "  ", end="")
        afficher_hero(h)


def cmd_use(args):
    h = appel("GET", f"/heroes/{args.id}")
    HERO_FILE.write_text(str(h["id"]))
    print(f"héros actif : {gras(h['nom'])}")


def cmd_look(args):
    hid = hero_id(args)
    afficher_hero(appel("GET", f"/heroes/{hid}"))
    afficher_salle(appel("GET", f"/heroes/{hid}/room"))


def cmd_move(args):
    afficher_salle(appel("POST", f"/heroes/{hero_id(args)}/move", json={"direction": args.direction}))


def cmd_attack(args):
    hid = hero_id(args)
    for _ in itertools.count():
        t = appel("POST", f"/heroes/{hid}/attack")
        print(jaune("✶ ") + t["recit"] if t["critique"] else t["recit"])
        print(gris(f"  héros {t['pv_heros']} PV · monstre {t['pv_monstre']} PV"))
        if t["issue"] == "monstre_vaincu":
            print(jaune(f"+{t['or_gagne']} or"))
            if t["victoire"]:
                print(violet(gras("\n  ✦ LA LICHE EST VAINCUE. LE DONJON EST LIBRE. ✦\n")))
            break
        if t["issue"] == "heros_mort":
            print(rouge(gras("\n  ☠  votre héros a péri. son nom rejoindra les murs de la crypte.\n")))
            break
        if not args.auto:
            break
        time.sleep(0.4)


def cmd_rest(args):
    hid = hero_id(args)
    fin = threading.Event()

    def ronfler():
        if not COULEUR:
            print("  le héros se repose…", flush=True)
            return
        for z in itertools.cycle(("z  ", "zZ ", "zZz")):
            if fin.wait(0.3):
                break
            print(f"\r  {cyan(z)} le héros se repose…", end="", flush=True)

    fil = threading.Thread(target=ronfler, daemon=True)
    fil.start()
    try:
        h = appel("POST", f"/heroes/{hid}/rest")
    finally:
        fin.set()
        fil.join()
        if COULEUR:
            print("\r" + " " * 40 + "\r", end="")
    print(vert("reposé !"))
    afficher_hero(h)


def cmd_map(args):
    print(dessiner_carte(appel("GET", f"/heroes/{hero_id(args)}/map")))


def cmd_health(_):
    etat = appel("GET", "/health", auth=False)
    print(vert(f"● {etat['status']}") + gris(f"  {etat.get('message', '')}  ({API_URL})"))


def cmd_leaderboard(_):
    print(gras("\n  ✦ panthéon de pixel crypt ✦\n"))
    for e in appel("GET", "/leaderboard", auth=False):
        marque = jaune("👑") if e["victoire"] else ("  " if e["est_vivant"] else gris("☠ "))
        print(
            f"  {e['rang']:>2}. {marque} {e['nom']:<20} {e['classe']:<9} {jaune(str(e['or']) + ' or'):>8}  {gris(e['joueur'])}"
        )




def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="play", description="Dungeon as a Service — client terminal")
    sub = p.add_subparsers(dest="commande", required=True, metavar="commande")

    avec_hero = argparse.ArgumentParser(add_help=False)
    avec_hero.add_argument("--hero", type=int, help="identifiant du héros (défaut : héros actif)")

    def ajouter(nom, fonction, aide, hero=False):
        sp = sub.add_parser(nom, help=aide, parents=[avec_hero] if hero else [])
        sp.set_defaults(fonction=fonction, hero=None)
        return sp

    for nom, fn, aide in (
        ("register", cmd_register, "créer un compte (et se connecter)"),
        ("login", cmd_login, "se connecter, token enregistré dans .token"),
    ):
        sp = ajouter(nom, fn, aide)
        sp.add_argument("--username", "-u", required=True)
        sp.add_argument("--password", "-p", help="demandé de façon masquée si absent")

    sp = ajouter("create", cmd_create, "créer un héros (il devient le héros actif)")
    sp.add_argument("--name", "-n", dest="nom", required=True)
    sp.add_argument("--classe", "-c", required=True, choices=["guerrier", "mage", "voleur"])
    for stat in ("force", "agilite", "intelligence"):
        sp.add_argument(f"--{stat}", type=int, required=True)

    ajouter("look", cmd_look, "regarder autour de soi", hero=True)
    ajouter("move", cmd_move, "se déplacer", hero=True).add_argument(
        "--direction", "-d", required=True, choices=list(DIRECTIONS)
    )
    ajouter("attack", cmd_attack, "jouer un tour de combat", hero=True).add_argument(
        "--auto", action="store_true", help="enchaîner les tours jusqu'à l'issue"
    )
    ajouter("rest", cmd_rest, "se reposer", hero=True)
    ajouter("map", cmd_map, "carte des salles découvertes", hero=True)
    ajouter("heroes", cmd_heroes, "lister ses héros")
    ajouter("use", cmd_use, "choisir le héros actif").add_argument("id", type=int)
    ajouter("leaderboard", cmd_leaderboard, "classement public")
    ajouter("health", cmd_health, "vérifier que l'api répond")
    ajouter("logout", cmd_logout, "oublier token et héros actif")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.commande in {"register", "create"}:
        print(violet(BANNIERE))
    try:
        args.fonction(args)
    except ErreurApi as e:
        print(rouge(f"✗ {e}"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())