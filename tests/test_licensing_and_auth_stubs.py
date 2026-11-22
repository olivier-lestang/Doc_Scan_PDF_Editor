"""Tests for the offline licensing/auth stubs and the provider registry.

Tests des bouchons hors ligne de licence/auth et du registre de
fournisseurs de signature.
"""

from dataclasses import dataclass

import pytest

from docscanner.core.result import Ok, Result
from docscanner.data.auth.unauthenticated_auth_repository import (
    AuthUnavailableError,
    UnauthenticatedAuthRepository,
)
from docscanner.data.licensing.offline_license_manager import (
    OfflineLicenseManager,
)
from docscanner.domain.ports.licensing import Entitlement
from docscanner.domain.ports.signature_provider import (
    SignatureProviderRegistry,
)


@dataclass(frozen=True)
class FakeSignatureProvider:
    """Minimal provider used to test entitlement filtering.

    Fournisseur minimal utilisé pour tester le filtrage par droits.
    """

    provider_id: str
    required_entitlement: Entitlement | None

    def sign(self, document_id: str, destination_path: str) -> Result[str, str]:
        """Pretend to sign by echoing the destination path.

        Simule une signature en renvoyant le chemin de destination.
        """
        return Ok(destination_path)


def test_offline_license_manager_grants_nothing() -> None:
    """Offline, no paid entitlement is granted and refresh is a no-op.

    Hors ligne, aucun droit payant n'est accordé et refresh est sans effet.
    """
    manager = OfflineLicenseManager()
    assert manager.current_entitlements() == frozenset()
    manager.refresh()
    assert manager.current_entitlements() == frozenset()


def test_registry_hides_providers_without_entitlement() -> None:
    """A provider requiring eIDAS is hidden until the entitlement is granted.

    Un fournisseur exigeant l'eIDAS est caché tant que le droit n'est pas
    accordé.
    """
    registry = SignatureProviderRegistry()
    registry.register(FakeSignatureProvider("free", None))
    registry.register(
        FakeSignatureProvider("eidas", Entitlement.EIDAS_QUALIFIED_SIGNATURE)
    )
    free_only = registry.available(frozenset())
    assert [p.provider_id for p in free_only] == ["free"]
    with_eidas = registry.available(frozenset({Entitlement.EIDAS_QUALIFIED_SIGNATURE}))
    assert sorted(p.provider_id for p in with_eidas) == ["eidas", "free"]


def test_unauthenticated_auth_repository() -> None:
    """The auth stub is signed out and sign-in raises AuthUnavailableError.

    Le bouchon d'authentification est déconnecté et sign_in lève
    AuthUnavailableError.
    """
    repo = UnauthenticatedAuthRepository()
    assert repo.current_session() is None
    repo.sign_out()
    with pytest.raises(AuthUnavailableError):
        repo.sign_in("user", "password")
