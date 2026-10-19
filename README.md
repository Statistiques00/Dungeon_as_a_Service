# Dungeon as a Service

Moteur de jeu du RPG rétro **Dungeon as a Service** (studio *Pixel Crypt*) : tout le jeu est une API FastAPI, le terminal n'est qu'un client.

```
   ___
  |   \ _  _ _ _  __ _ ___ ___ _ _
  | |) | || | ' \/ _` / -_) _ \ ' \   as a
  |___/ \_,_|_||_\__, \___\___/_||_|  service
                 |___/          ~ pixel crypt ~
```

## Installation (à faire une seule fois)

Prérequis : Python 3.10 ou plus récent (`python --version`).

```bash
# 1. Créer et activer un environnement virtuel
python -m venv .venv
# Windows (PowerShell) :
.venv\Scripts\Activate.ps1
# macOS / Linux :
source .venv/bin/activate

# 2. Installer les dépendances
pip install -r requirements.txt
```

## Lancer l'API

Depuis la racine du projet (le dossier qui contient `app/`) :

```bash
fastapi dev app/main.py
```

Ouvrez ensuite <http://127.0.0.1:8000/docs> : la route `GET /health` doit répondre `{"status": "ok", ...}`.

Pour utiliser les routes `/heroes` dans Swagger : `POST /auth/register`, puis bouton **Authorize** (nom d'utilisateur + mot de passe).

### Variables d'environnement (toutes facultatives, voir `.env.example`)

| Variable | Défaut | Rôle |
|---|---|---|
| `JWT_SECRET_KEY` | valeur de développement | clé de signature des tokens |
| `JWT_EXPIRE_MINUTES` | `120` | durée de vie d'un token |
| `DATABASE_URL` | `sqlite:///./dungeon.db` | base de données (lue par `app/database.py`) |
| `LOG_LEVEL` | `INFO` | niveau du journal de jeu |
| `DUNGEON_API` | `http://127.0.0.1:8000` | URL utilisée par le client terminal |

## Réinitialiser la partie

Arrêtez le serveur et supprimez le fichier `dungeon.db` : il sera recréé au prochain lancement.
À faire aussi après l'ajout d'une colonne à une table (SQLite ne met pas à jour une table existante).

---

## Architecture

```
app/
├── main.py              point d'entrée, lifespan, branchement des routers
├── database.py          connexion SQLite, get_session()          (FOURNI, non modifié)
├── core/
│   ├── config.py        variables d'environnement
│   ├── erreurs.py       une classe par erreur métier → {"detail": {"error", "message"}}
│   └── journal.py       logging du jeu (bonus B-5)
├── domain/              règles du jeu pures : ni FastAPI, ni base de données
│   ├── heros.py         Heros (ABC) · Guerrier · Mage · Voleur · Coup
│   ├── monstre.py       Monstre
│   └── combat.py        tour_de_combat() → Tour (+ récit du tour)
├── models/              tables SQLModel : Hero, Player
├── schemas/             entrées / sorties Pydantic
├── services/
│   ├── dungeon_map.py   lecture de la carte                      (FOURNI, non modifié)
│   ├── carte.py         vue typée de la carte (Salle, FicheMonstre)
│   ├── hero_service.py  création, consultation, déplacement, carte, repos
│   ├── combat_service.py
│   ├── auth_service.py  hachage, JWT, inscription, connexion
│   └── classement_service.py
└── routes/              couche HTTP uniquement
    ├── deps.py          SessionDep, JoueurCourant, HeroDuJoueur
    └── auth.py · heroes.py · public.py
client/play.py           client terminal (bonus B-1)
tests/                   pytest (bonus B-3)
data/dungeon_map.json    carte du donjon                          (FOURNIE, non modifiée)
```

**Chemin d'une requête** : `route` (HTTP) → `deps` (token → joueur → héros possédé) → `service` (orchestration + persistance) → `domain` (calcul) → `schema` de sortie.

### Choix techniques à savoir expliquer

**Validation (FT-2)** — `HeroCreate` utilise des types annotés : `Stat = Annotated[int, Field(strict=True, ge=1, le=8)]` (le mode strict refuse `"6"` ou `6.5`) et un `@model_validator(mode="after")` pour la somme égale à 10. Aucune condition dans la route : FastAPI renvoie lui-même le 422.

**Programmation orientée objet** — `Heros` hérite d'`ABC`, `calculer_degats()` est abstraite et renvoie un `Coup(degats, critique)`. Le guerrier redéfinit `subir_degats()` (armure, minimum 1). Chaque sous-classe **s'inscrit elle-même** via `__init_subclass__` :

```python
class Mage(Heros, classe="mage"): ...
heros = Heros.incarner("mage", force=2, agilite=2, intelligence=6)
```

Le service n'écrit donc **jamais** `if classe == "guerrier"` : ajouter une classe (un paladin…) revient à écrire une sous-classe, rien d'autre. Le dé du voleur est injectable (`de=`), ce qui rend les critiques testables.

**Carte** — `services/carte.py` transforme les dictionnaires de `dungeon_map` (`name`, `exits`, `hp`, `attack`, `gold`) en objets typés `Salle` et `FicheMonstre`. Le reste du code ne manipule jamais le JSON brut.

**Combat** — `tour_de_combat(heros, monstre)` vit dans le domaine et renvoie un `Tour` immuable. Le service construit les objets métier depuis la ligne en base, délègue le calcul, puis persiste le résultat (`pv`, `monstre_pv`, `or_`, `victoire`).

**États du héros** — `monstre_pv` à `None` signifie « pas de combat » ; on expose à la place `en_combat` et `est_vivant` (propriétés du modèle). Ordre des contrôles : 401 → 404 → 403 → 409 `HERO_DEAD` → 409 `IN_COMBAT` / `NO_MONSTER` → 400 `NO_EXIT`.

**Repos asynchrone (FT-9)** — la route est `async def` et attend `hero_service.reposer()`, qui fait `await asyncio.sleep(3)` : la boucle d'événements reste libre pendant la sieste. Les autres routes sont des `def` synchrones (accès base bloquant), exécutées par FastAPI dans un pool de threads. Après la sieste, l'état est relu en base : si le héros a été tué ou est entré en combat entre-temps, le repos est annulé.

**Sécurité** — `OAuth2PasswordBearer(auto_error=False)` permet de lever nos propres 401 au format imposé. Le hachage utilise `PasswordHash.recommended()` (Argon2). À la connexion d'un utilisateur inconnu, on vérifie quand même un hash factice pour ne pas révéler par le temps de réponse si un compte existe. La propriété d'un héros est vérifiée dans une dépendance (`HeroDuJoueur`) réutilisée par toutes les routes `/heroes/{id}/…`.

**Format d'erreur** — `core/erreurs.py` définit une classe par erreur (`PasDeSortie`, `EnCombat`, `PasTonHeros`…), toutes dérivées de `HTTPException`. Chaque route documente ses erreurs possibles dans Swagger (`responses=documenter(403, 404, 409)`).

---

## Le donjon

```
                     [Salle du trône]  ← La Liche (50 PV, atk 7, 100 or)
                            │
                      [Antichambre] ──── [Source sacrée]
                         Ogre                (calme)
                            │
                        [Couloir]
                        Rat géant
                            │
     [Bibliothèque] ──── [Hall] ──── [Crypte]
        Gobelin             │        Squelette
                        [Entrée]
```

Le donjon est maudit : un monstre renaît chaque fois qu'on entre dans sa salle. Fuir est impossible (409 `IN_COMBAT`). Une fois l'ogre vaincu, on peut se reposer dans l'antichambre puis monter au trône (attention : revenir de la source sacrée vers l'antichambre réveille l'ogre). Avec ce repos, chaque classe peut vaincre la Liche — c'est vérifié par un test sur la vraie carte (`test_chaque_classe_peut_vaincre_la_liche`, dans le pire cas pour le voleur : aucun critique).

| Classe | Dégâts | Particularité | Exemple (6 en stat principale) |
|---|---|---|---|
| Guerrier | 2 + force × 2 | armure : attaque − 1, minimum 1 | 14 dégâts, 32 PV |
| Mage | 1 + intelligence × 3 | — | 19 dégâts, 24 PV |
| Voleur | 2 + agilité × 2 | critique ×2, une chance sur trois | 14 (28) dégâts, 24 PV |

---

## Endpoints

| Méthode | Route | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | état du serveur |
| POST | `/auth/register` | — | créer un compte (201) |
| POST | `/auth/login` | — | formulaire OAuth2 → token JWT |
| GET | `/auth/me` | ✔ | joueur connecté |
| POST | `/heroes` | ✔ | créer un héros (201) |
| GET | `/heroes` | ✔ | mes héros |
| GET | `/heroes/{id}` | ✔ | détail d'un héros |
| GET | `/heroes/{id}/room` | ✔ | salle courante (+ monstre si combat) |
| POST | `/heroes/{id}/move` | ✔ | `{"direction": "nord"}` |
| GET | `/heroes/{id}/map` | ✔ | **extra** : carte des salles découvertes (brouillard de guerre) |
| POST | `/heroes/{id}/attack` | ✔ | un tour de combat (+ champ `recit`) |
| POST | `/heroes/{id}/rest` | ✔ | 3 s de repos, PV restaurés |
| GET | `/leaderboard` | — | top 10 : vainqueurs, puis or |

Exemple de réponse d'attaque (guerrier contre le squelette de la crypte) :

```json
{ "degats_infliges": 14, "critique": false, "degats_subis": 3, "pv_heros": 29,
  "pv_monstre": 1, "issue": "en_cours", "or_gagne": 0, "victoire": false,
  "recit": "Aragorn frappe Squelette : 14 dégâts. Squelette riposte : 3 dégâts." }
```

---

## Validation des paliers dans Swagger

1. **Palier 1** — créer `{"nom": "Aragorn", "classe": "guerrier", "force": 6, "agilite": 2, "intelligence": 2}` → 201 ; même requête avec `6/5/4` → 422 ; `GET /heroes/9999` → 404 `HERO_NOT_FOUND`.
2. **Palier 2** — `move` nord → `hall` ; depuis l'entrée, `move` est → 400 `NO_EXIT` ; redémarrer le serveur, `GET /heroes/{id}` → toujours dans le hall.
3. **Palier 3** — depuis le hall, `move` ouest (gobelin), `attack` → `monstre_vaincu`, or +10 ; `rest` ; `move` est puis ouest : le gobelin revient, `move` → 409 `IN_COMBAT`.
4. **Palier 4** — deux comptes ; le premier crée un héros ; le second tente `move` dessus → 403 `NOT_YOUR_HERO` ; `GET /heroes` sans token → 401.

---

## Bonus

### B-1 — Client terminal

```bash
python client/play.py health
python client/play.py register --username alice --password secret1   # crée le compte et se connecte (.token)
python client/play.py login --username alice --password secret1
python client/play.py create --name Aragorn --classe guerrier --force 6 --agilite 2 --intelligence 2
python client/play.py look
python client/play.py move --direction nord
python client/play.py attack            # --auto : enchaîne les tours jusqu'à l'issue
python client/play.py rest
python client/play.py map               # carte ascii des salles découvertes
python client/play.py look --hero 1     # --hero sur toute commande d'action
python client/play.py heroes | use 3 | leaderboard | logout
```

Le héros créé devient le héros actif (fichier `.hero`), `--hero` est donc facultatif. Barres de PV colorées, carte ASCII avec brouillard de guerre (`@` vous, `!` salle hantée, `?` inexploré), animation pendant le repos. Les couleurs se désactivent avec `NO_COLOR=1` ou hors terminal.

### B-2 — Classement

`GET /leaderboard`, public : 10 héros, vainqueurs de la Liche d'abord puis par or, avec le nom du joueur.

### B-3 — Tests

```bash
pytest
```

31 tests : règles métier (exemples chiffrés du sujet, armure, critique, classe abstraite, carte fournie, équilibrage contre la Liche) et API (201, 422 ×6, 404, 400, 409 `IN_COMBAT` · `NO_MONSTER` · `HERO_DEAD` · `USERNAME_TAKEN`, 401, 403, partie complète jusqu'à la victoire, repos non bloquant). Les tests utilisent une base SQLite en mémoire et ne touchent pas `dungeon.db`.

### B-4 — PostgreSQL

```bash
docker compose up -d
# macOS / Linux
export DATABASE_URL=postgresql+psycopg://dungeon:dungeon@localhost:5432/dungeon
# Windows PowerShell
$env:DATABASE_URL="postgresql+psycopg://dungeon:dungeon@localhost:5432/dungeon"
fastapi dev app/main.py
```

Aucune modification de code : `app/database.py` lit `DATABASE_URL`. Le pilote `psycopg[binary]` a été ajouté à `requirements.txt`. La liste des salles découvertes est stockée en colonne `JSON`, compatible SQLite et PostgreSQL.

### B-5 — Journalisation

Chaque création, déplacement, tour de combat, repos et inscription est tracé dans la console :

```
21:42:10 │ dungeon.exploration │ Sylvanas : hall --nord--> couloir ⚔ Rat géant surgit
21:42:11 │ dungeon.combat  │ Sylvanas frappe Rat géant : coup critique ! 28 dégâts. Rat géant s'effondre. [monstre_vaincu] pv héros 24 · pv Rat géant 0
21:42:12 │ dungeon.exploration │ Sylvanas s'assoupit (3s)…
```

---


## Notre rendu

- **Membres du groupe :** D'Amore Théo, Briki Ilian
- **Lien du dépôt Git :** _https://github.com/…/dungeon-api_
- **Palier atteint :** 4 (les quatre validations Swagger passent)
- **Bonus réalisés :** B-1 client terminal, B-2 classement, B-3 tests (31 tests pytest), B-4 PostgreSQL, B-5 journalisation
- **Ce qui ne fonctionne pas / difficultés :**
  - aucun bug connu, toute la suite de tests passe (`pytest`) ;
  - le critique du voleur est aléatoire (une chance sur trois à chaque coup) : sur peu de coups, la fréquence observée peut s'écarter de « une fois sur trois » ;
  - un héros mort ne peut pas être ressuscité : il reste consultable, mais toute action renvoie 409 `HERO_DEAD` ;
  - pas de route de suppression de héros (optionnelle dans le sujet).
