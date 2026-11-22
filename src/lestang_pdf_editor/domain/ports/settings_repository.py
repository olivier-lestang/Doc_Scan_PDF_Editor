"""Port: persistent, versioned user settings that survive app updates.

Port : réglages utilisateur persistants et versionnés qui survivent aux
mises à jour de l'application.
"""

from typing import Protocol

from lestang_pdf_editor.core.settings import Settings


class SettingsRepository(Protocol):
    """Load/save settings outside the app install directory.

    Charge/sauvegarde les réglages hors du répertoire d'installation.
    """

    def load(self) -> Settings:
        """Load settings, merging defaults for missing keys.

        Charge les réglages en fusionnant les valeurs par défaut pour les
        clés manquantes.
        """
        ...

    def save(self, settings: Settings) -> None:
        """Persist settings to the OS user data directory.

        Persiste les réglages dans le répertoire de données utilisateur de
        l'OS.
        """
        ...
