"""Port: signature providers; eIDAS QES arrives later behind a license.

Port : fournisseurs de signature ; l'eIDAS QES arrivera plus tard derrière
une licence.
"""

from typing import Protocol

from lestang_pdf_editor.core.result import Result
from lestang_pdf_editor.domain.ports.licensing import Entitlement


class SignatureProvider(Protocol):
    """One way to sign a document (handwritten, certificate, eIDAS...).

    Une façon de signer un document (manuscrite, certificat, eIDAS...).
    """

    @property
    def provider_id(self) -> str:
        """Stable identifier of the provider.

        Identifiant stable du fournisseur.
        """
        ...

    @property
    def required_entitlement(self) -> Entitlement | None:
        """Entitlement needed to use this provider (None = free).

        Droit requis pour utiliser ce fournisseur (None = gratuit).
        """
        ...

    def sign(self, document_id: str, destination_path: str) -> Result[str, str]:
        """Sign the document and write the signed file.

        Signe le document et écrit le fichier signé.
        """
        ...


class SignatureProviderRegistry:
    """Registry exposing only providers allowed by current entitlements.

    Registre n'exposant que les fournisseurs autorisés par les droits
    actuels.
    """

    def __init__(self) -> None:
        """Create an empty registry.

        Crée un registre vide.
        """
        self._providers: list[SignatureProvider] = []

    def register(self, provider: SignatureProvider) -> None:
        """Register a signature provider.

        Enregistre un fournisseur de signature.
        """
        self._providers.append(provider)

    def available(
        self, entitlements: frozenset[Entitlement]
    ) -> tuple[SignatureProvider, ...]:
        """Return providers whose entitlement is granted (or free).

        Retourne les fournisseurs dont le droit est accordé (ou gratuits).
        """
        return tuple(
            provider
            for provider in self._providers
            if provider.required_entitlement is None
            or provider.required_entitlement in entitlements
        )
