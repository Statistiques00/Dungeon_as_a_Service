from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nom: str = Field(max_length=20)
    classe: str
    force: int
    agilite: int
    intelligence: int
    pv: int
    pv_max: int
    salle_actuelle: str
    or_: int = 0
    monstre_pv: int | None = None  # none : aucun combat en cours
    victoire: bool = False
    salles_decouvertes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    owner_id: int | None = Field(default=None, foreign_key="player.id", index=True)

    @property
    def en_combat(self) -> bool:
        return self.monstre_pv is not None

    @property
    def est_vivant(self) -> bool:
        return self.pv > 0
