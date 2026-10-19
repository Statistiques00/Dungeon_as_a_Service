from dataclasses import dataclass


@dataclass
class Monstre:
    nom: str
    pv_max: int
    attaque: int
    recompense: int
    pv: int | None = None

    def __post_init__(self) -> None:
        if self.pv is None:
            self.pv = self.pv_max

    @property
    def est_vivant(self) -> bool:
        return self.pv > 0

    def encaisser(self, degats: int) -> None:
        self.pv = max(0, self.pv - degats)
