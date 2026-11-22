"""Local JSON settings repository in the OS user config directory.

Dépôt de réglages JSON local dans le répertoire de configuration
utilisateur de l'OS.

Settings live outside the app install directory, so they survive app
updates and reinstalls.
"""

import json
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

from docscanner.core.settings import SCHEMA_VERSION, ScanSettings, Settings

SETTINGS_FILE_NAME = "settings.json"
"""Name of the JSON settings file in the user config directory.

Nom du fichier JSON de réglages dans le répertoire de configuration
utilisateur.
"""


class LocalSettingsRepository:
    """Persist settings as versioned JSON; survives updates/reinstalls.

    Persiste les réglages en JSON versionné ; survit aux mises à jour et
    réinstallations.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """Create the repository, optionally overriding the config dir.

        Crée le dépôt, avec éventuellement un répertoire de configuration
        imposé (utile pour les tests).
        """
        base = config_dir or Path(
            user_config_dir("DocScanPdfEditor", "Olivier Lestang")
        )
        self._path = base / SETTINGS_FILE_NAME

    def load(self) -> Settings:
        """Load settings; missing file or keys fall back to defaults.

        Charge les réglages ; fichier ou clés manquants -> valeurs par
        défaut. Unknown keys are ignored (forward compatibility).
        """
        if not self._path.exists():
            return Settings()
        raw = self._migrate(json.loads(self._path.read_text(encoding="utf-8")))
        scan_raw: dict[str, Any] = raw.get("scan", {})
        return Settings(
            schema_version=raw.get("schema_version", SCHEMA_VERSION),
            scan=ScanSettings(dpi=scan_raw.get("dpi", "auto")),
            language=str(raw.get("language", "en")),
            first_name=str(raw.get("first_name", "")),
            last_name=str(raw.get("last_name", "")),
            theme_mode=str(raw.get("theme_mode", "system")),
            recent_files=tuple(raw.get("recent_files", [])),
        )

    def save(self, settings: Settings) -> None:
        """Write settings atomically to the user config directory.

        Écrit les réglages de façon atomique dans le répertoire de
        configuration utilisateur.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": settings.schema_version,
            "scan": {"dpi": settings.scan.dpi},
            "language": settings.language,
            "first_name": settings.first_name,
            "last_name": settings.last_name,
            "theme_mode": settings.theme_mode,
            "recent_files": list(settings.recent_files),
        }
        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self._path)

    def _migrate(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Migrate older settings schemas forward to SCHEMA_VERSION.

        Migre les anciens schémas de réglages vers SCHEMA_VERSION.
        """
        version = int(raw.get("schema_version", 0))
        if version < SCHEMA_VERSION:
            raw["schema_version"] = SCHEMA_VERSION
        return raw
