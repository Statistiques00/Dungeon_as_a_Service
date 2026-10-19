from pydantic import BaseModel, Field

from app.schemas.hero import Classe


class EntreeClassement(BaseModel):
    rang: int
    nom: str
    classe: Classe
    joueur: str
    or_: int = Field(serialization_alias="or")
    victoire: bool
    est_vivant: bool


class HealthRead(BaseModel):
    status: str = "ok"
    message: str = "Le donjon vous attend..."
