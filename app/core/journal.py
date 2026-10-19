import logging
import sys

from app.core.config import LOG_LEVEL

FORMAT = "%(asctime)s │ %(name)-15s │ %(message)s"


def configurer_journal() -> None:
    racine = logging.getLogger("dungeon")
    if racine.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(FORMAT, datefmt="%H:%M:%S"))
    racine.addHandler(handler)
    racine.setLevel(LOG_LEVEL)
    racine.propagate = False


def journal(nom: str) -> logging.Logger:
    return logging.getLogger(f"dungeon.{nom}")
