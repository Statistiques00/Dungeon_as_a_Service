import random
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import ClassVar, NamedTuple


class Coup(NamedTuple):
    degats: int
    critique: bool = False


class Heros(ABC):
    classe: ClassVar[str]
    _registre: ClassVar[dict[str, type["Heros"]]] = {}

    # chaque sous-classe s'inscrit d'elle-même : aucun if sur la classe ailleurs
    def __init_subclass__(cls, classe: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if classe:
            cls.classe = classe
            Heros._registre[classe] = cls

    def __init__(
        self,
        force: int,
        agilite: int,
        intelligence: int,
        pv: int | None = None,
        de: Callable[[], float] = random.random,
    ):
        self.force = force
        self.agilite = agilite
        self.intelligence = intelligence
        self.pv = self.pv_max if pv is None else pv
        self._de = de

    @classmethod
    def incarner(cls, classe: str, **attributs) -> "Heros":
        sous_classe = cls._registre.get(classe)
        if sous_classe is None:
            raise ValueError(f"classe inconnue : {classe}")
        return sous_classe(**attributs)

    @classmethod
    def classes(cls) -> tuple[str, ...]:
        return tuple(cls._registre)

    @property
    def pv_max(self) -> int:
        return 20 + self.force * 2

    @property
    def est_vivant(self) -> bool:
        return self.pv > 0

    @abstractmethod
    def calculer_degats(self) -> Coup: ...

    def subir_degats(self, attaque_monstre: int) -> int:
        return attaque_monstre

    def encaisser(self, degats: int) -> None:
        self.pv = max(0, self.pv - degats)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(pv={self.pv}/{self.pv_max})"


class Guerrier(Heros, classe="guerrier"):
    ARMURE = 1

    def calculer_degats(self) -> Coup:
        return Coup(2 + self.force * 2)

    def subir_degats(self, attaque_monstre: int) -> int:
        return max(1, attaque_monstre - self.ARMURE)


class Mage(Heros, classe="mage"):
    def calculer_degats(self) -> Coup:
        return Coup(1 + self.intelligence * 3)


class Voleur(Heros, classe="voleur"):
    CHANCE_CRITIQUE = 1 / 3

    def calculer_degats(self) -> Coup:
        base = 2 + self.agilite * 2
        if self._de() < self.CHANCE_CRITIQUE:
            return Coup(base * 2, critique=True)
        return Coup(base)
