from pydantic import BaseModel


class ErreurDetail(BaseModel):
    error: str
    message: str


class ErreurReponse(BaseModel):
    detail: ErreurDetail


def documenter(*statuts: int) -> dict[int, dict]:
    return {s: {"model": ErreurReponse} for s in statuts}
