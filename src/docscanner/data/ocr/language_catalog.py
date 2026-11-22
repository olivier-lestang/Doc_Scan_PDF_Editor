"""OCR language catalog loaded from a bundled JSON asset.

Catalogue de langues OCR chargé depuis un asset JSON embarqué.

Language packs are data files (model weights) processed 100% on-device;
downloading a pack never sends user data anywhere.
"""

import json
from pathlib import Path

from docscanner.domain.entities.ocr import OcrLanguage


class OcrLanguageCatalog:
    """Selectable OCR languages offered to the user.

    Langues OCR sélectionnables proposées à l'utilisateur.
    """

    def __init__(self, languages: tuple[OcrLanguage, ...]) -> None:
        """Create the catalog from parsed language entries.

        Crée le catalogue à partir des entrées de langue analysées.
        """
        self._languages = languages

    @classmethod
    def from_json_file(cls, path: Path) -> "OcrLanguageCatalog":
        """Load the catalog from a JSON file on disk.

        Charge le catalogue depuis un fichier JSON sur disque.
        """
        raw = json.loads(path.read_text(encoding="utf-8"))
        languages = tuple(
            OcrLanguage(
                code=str(entry["code"]),
                names=dict(entry["names"]),
                engine_model=str(entry["engine_model"]),
                bundled=bool(entry["bundled"]),
                size_mb=float(entry["size_mb"]),
            )
            for entry in raw["languages"]
        )
        return cls(languages)

    def all(self) -> tuple[OcrLanguage, ...]:
        """Return every language in the catalog.

        Retourne toutes les langues du catalogue.
        """
        return self._languages

    def bundled(self) -> tuple[OcrLanguage, ...]:
        """Return the languages bundled with the app.

        Retourne les langues embarquées avec l'application.
        """
        return tuple(lang for lang in self._languages if lang.bundled)

    def get(self, code: str) -> OcrLanguage | None:
        """Look up a language by its code (e.g. "fra").

        Recherche une langue par son code (ex. « fra »).
        """
        for lang in self._languages:
            if lang.code == code:
                return lang
        return None

    def select(self, codes: tuple[str, ...]) -> tuple[OcrLanguage, ...]:
        """Return the languages chosen by the user (unknown codes skipped).

        Retourne les langues choisies par l'utilisateur (codes inconnus
        ignorés).
        """
        return tuple(lang for lang in self._languages if lang.code in set(codes))
