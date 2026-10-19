from pydantic import BaseModel

from app.domain.combat import Issue


class AttackResult(BaseModel):
    degats_infliges: int
    critique: bool
    degats_subis: int
    pv_heros: int
    pv_monstre: int
    issue: Issue
    or_gagne: int
    victoire: bool
    recit: str
