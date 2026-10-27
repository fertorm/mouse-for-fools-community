"""Diagnóstico rotativo local sin registrar entradas ni datos personales."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

MAX_LOG_BYTES = 512_000
LOG_COPIES = 2


def configure_logging() -> Path:
    """Configura una sola salida rotativa en LOCALAPPDATA; devuelve su ruta."""
    directory = Path(os.environ["LOCALAPPDATA"]) / "MouseForFools" / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "application.log"
    logger = logging.getLogger("mouse_for_fools")
    if not any(isinstance(handler, RotatingFileHandler) for handler in logger.handlers):
        handler = RotatingFileHandler(
            path, maxBytes=MAX_LOG_BYTES, backupCount=LOG_COPIES, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return path
