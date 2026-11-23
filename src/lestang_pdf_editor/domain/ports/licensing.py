"""Port: entitlements and license resolution (offline base for now).

Port : droits (entitlements) et résolution de licence (base hors ligne
pour l'instant).
"""

from enum import StrEnum
from typing import Protocol


class Entitlement(StrEnum):
    """Paid capabilities; extensible without breaking existing code.

    Capacités payantes ; extensible sans casser le code existant.
    """

    EIDAS_QUALIFIED_SIGNATURE = "eidas.qes"


class LicenseManager(Protocol):
    """Resolves the effective entitlements of the user.

    Résout les droits effectifs de l'utilisateur.
    """

    def current_entitlements(self) -> frozenset[Entitlement]:
        """Return the entitlements available right now (offline = base).

        Retourne les droits disponibles maintenant (hors ligne = base).
        """
        ...

    def refresh(self) -> None:
        """Refresh entitlements from the license source (no-op offline).

        Rafraîchit les droits depuis la source de licence (sans effet hors
        ligne).
        """
        ...
