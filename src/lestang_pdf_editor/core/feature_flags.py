"""Local feature flags; remote flags arrive with the future website.

Drapeaux de fonctionnalités locaux ; les drapeaux distants arriveront avec
le futur site web.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureFlags:
    """Toggle optional features without changing navigation code.

    Active des fonctionnalités optionnelles sans modifier la navigation.
    """

    account_enabled: bool = False
    """Account/subscription UI; off until the website exists.

    UI compte/abonnement ; désactivée tant que le site n'existe pas.
    """

    cloud_ocr_enabled: bool = False
    """Cloud OCR opt-in; always off by default (on-device only).

    OCR cloud en option ; toujours désactivé par défaut (local uniquement).
    """


DEFAULT_FLAGS = FeatureFlags()
"""Default flags shipped with the app.

Drapeaux par défaut livrés avec l'application.
"""
