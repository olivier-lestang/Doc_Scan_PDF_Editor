"""Application logging setup: rotating log file in the OS user log dir.

Configuration du logging applicatif : fichier log rotatif dans le
répertoire de logs utilisateur de l'OS.

Logs contain file paths, sizes, page counts and timings — never document
content (OCR text, annotations). The file lives in the per-user log dir
(`user_log_dir` from platformdirs, e.g. under LOCALAPPDATA on Windows),
rotated at 2 MB with 3 backups.

Les logs contiennent chemins, tailles, nombres de pages et durées —
jamais le contenu des documents (texte OCR, annotations).
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_dir

LOGGER_NAME = "lestang_pdf_editor"
"""Root logger name for the whole application.

Nom du logger racine pour toute l'application.
"""

MAX_BYTES = 2_000_000
"""Rotate the log file after 2 MB.

Fait tourner le fichier de log après 2 Mo.
"""

BACKUP_COUNT = 3
"""Number of rotated log backups kept.

Nombre de sauvegardes de logs conservées.
"""


def default_log_dir() -> Path:
    """Return the OS per-user log directory for the app.

    Retourne le répertoire de logs utilisateur de l'OS pour l'appli.
    """
    return Path(user_log_dir("LestangPdfEditor", "Olivier Lestang"))


def setup_logging(log_dir: Path | None = None) -> Path:
    """Configure the app logger: rotating file + console, return the file path.

    Configure le logger de l'appli : fichier rotatif + console, et retourne
    le chemin du fichier de log.
    """
    log_dir = log_dir or default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        file_handler = RotatingFileHandler(
            log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        logger.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        logger.addHandler(console)
    logger.info("logging started -> %s", log_path)
    return log_path


def get_logger(name: str) -> logging.Logger:
    """Return a child logger of the app logger (name is appended to the root).

    Retourne un logger enfant du logger de l'appli (le nom est ajouté à la
    racine), ex. get_logger("engine") -> "lestang_pdf_editor.engine".
    """
    return logging.getLogger(f"{LOGGER_NAME}.{name}")
