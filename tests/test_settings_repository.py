"""Tests for the local versioned settings repository.

Tests du dépôt de réglages local versionné.
"""

import json
from pathlib import Path

from lestang_pdf_editor.core.settings import SCHEMA_VERSION, ScanSettings, Settings
from lestang_pdf_editor.data.settings.local_settings_repository import (
    LocalSettingsRepository,
)


def make_repo(tmp_path: Path) -> LocalSettingsRepository:
    """Create a repository rooted in a temporary directory.

    Crée un dépôt racine dans un répertoire temporaire.
    """
    return LocalSettingsRepository(config_dir=tmp_path)


def test_load_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    """Without a settings file, defaults are returned.

    Sans fichier de réglages, les valeurs par défaut sont retournées.
    """
    repo = make_repo(tmp_path)
    settings = repo.load()
    assert settings.schema_version == SCHEMA_VERSION
    assert settings.scan.dpi == "auto"
    assert settings.language == "en"


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    """Saved settings (manual DPI, French) are loaded back identically.

    Les réglages sauvegardés (DPI manuel, français) sont relus à
    l'identique.
    """
    repo = make_repo(tmp_path)
    settings = Settings(scan=ScanSettings(dpi=600), language="fr")
    repo.save(settings)
    loaded = repo.load()
    assert loaded.scan.dpi == 600
    assert loaded.language == "fr"


def test_unknown_keys_are_ignored(tmp_path: Path) -> None:
    """Unknown keys from a newer version never break loading.

    Les clés inconnues d'une version plus récente ne cassent jamais le
    chargement.
    """
    repo = make_repo(tmp_path)
    repo.save(Settings())
    path = tmp_path / "settings.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["future_option"] = {"enabled": True}
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = repo.load()
    assert loaded.scan.dpi == "auto"


def test_old_schema_is_migrated(tmp_path: Path) -> None:
    """A file with an old schema version is migrated on load.

    Un fichier avec une ancienne version de schéma est migré au
    chargement.
    """
    repo = make_repo(tmp_path)
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"schema_version": 0, "language": "es"}), encoding="utf-8"
    )
    loaded = repo.load()
    assert loaded.schema_version == SCHEMA_VERSION
    assert loaded.language == "es"
