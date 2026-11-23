"""Offline license stub: base (free) entitlements only, refresh is a no-op.

Bouchon de licence hors ligne : droits de base (gratuits) uniquement,
refresh sans effet.
"""

from lestang_pdf_editor.domain.ports.licensing import Entitlement


class OfflineLicenseManager:
    """License manager used until accounts and subscriptions exist.

    Gestionnaire de licence utilisé tant que comptes et abonnements
    n'existent pas.
    """

    def current_entitlements(self) -> frozenset[Entitlement]:
        """Return the free base entitlements (empty set).

        Retourne les droits de base gratuits (ensemble vide).
        """
        return frozenset()

    def refresh(self) -> None:
        """No-op: there is no remote license source yet.

        Sans effet : aucune source de licence distante pour l'instant.
        """
