"""Versioned application settings model, persisted across updates.

Modèle de réglages de l'application, versionné et persisté entre les mises
à jour.
"""

from dataclasses import dataclass, field
from typing import Literal

SCHEMA_VERSION = 1
"""Current settings schema version (bump and migrate on change).

Version actuelle du schéma de réglages (à incrémenter avec migration).
"""

DpiSetting = Literal["auto"] | int
"""DPI target: "auto" or a manual value in 150-600.

DPI cible : « auto » ou une valeur manuelle entre 150 et 600.
"""


@dataclass(frozen=True)
class ScanSettings:
    """Scan-related settings.

    Réglages de numérisation.
    """

    dpi: DpiSetting = "auto"
    """Target DPI; "auto" = 300 for OCR, 150-200 for preview.

    DPI cible ; « auto » = 300 pour l'OCR, 150-200 pour l'aperçu.
    """


@dataclass(frozen=True)
class Settings:
    """Root settings persisted in the OS user data directory.

    Réglages racine persistés dans le répertoire de données utilisateur.
    """

    schema_version: int = SCHEMA_VERSION
    scan: ScanSettings = field(default_factory=ScanSettings)
    language: str = "en"
