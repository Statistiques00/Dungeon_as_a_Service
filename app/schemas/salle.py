from enum import Enum

from pydantic import BaseModel, ConfigDict


class Direction(str, Enum):
    nord = "nord"
    sud = "sud"
    est = "est"
    ouest = "ouest"


class MoveRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"direction": "nord"}]})

    direction: Direction


class MonstreRead(BaseModel):
    nom: str
    pv: int
    pv_max: int
    attaque: int


class SalleRead(BaseModel):
    id: str
    nom: str
    description: str
    sorties: list[str]
    monstre: MonstreRead | None = None
    salle_finale: bool = False


class SalleCarte(BaseModel):
    id: str
    nom: str
    hantee: bool
    sorties: dict[str, str | None]  # none : destination encore inconnue


class CarteRead(BaseModel):
    depart: str
    position: str
    salles: list[SalleCarte]
    explorees: int
    total: int
