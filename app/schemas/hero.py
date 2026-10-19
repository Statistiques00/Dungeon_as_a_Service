from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

TOTAL_STATS = 10

Stat = Annotated[int, Field(strict=True, ge=1, le=8)]
Nom = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=20)]


class Classe(str, Enum):
    guerrier = "guerrier"
    mage = "mage"
    voleur = "voleur"


class HeroCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"nom": "Aragorn", "classe": "guerrier", "force": 6, "agilite": 2, "intelligence": 2}
            ]
        }
    )

    nom: Nom
    classe: Classe
    force: Stat
    agilite: Stat
    intelligence: Stat

    @model_validator(mode="after")
    def verifier_total(self) -> "HeroCreate":
        total = self.force + self.agilite + self.intelligence
        if total != TOTAL_STATS:
            raise ValueError(
                f"force + agilite + intelligence doit valoir exactement {TOTAL_STATS} (reçu : {total})"
            )
        return self


class HeroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    classe: Classe
    force: int
    agilite: int
    intelligence: int
    pv: int
    pv_max: int
    salle_actuelle: str
    or_: int = Field(serialization_alias="or")
    victoire: bool
    en_combat: bool
    est_vivant: bool
