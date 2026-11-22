"""Port: subscriptions from the future website or from app stores.

Port : abonnements du futur site web ou des stores d'applications.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

SubscriptionSource = Literal["website", "store"]
"""Where the subscription was purchased: own website or app store.

Lieu d'achat de l'abonnement : site propre ou store d'applications.
"""


@dataclass(frozen=True)
class Subscription:
    """One subscription (active or expired).

    Un abonnement (actif ou expiré).
    """

    product_id: str
    source: SubscriptionSource
    status: str
    expires_at: datetime | None


class SubscriptionProvider(Protocol):
    """Subscription source: website API or StoreKit / Play Billing.

    Source d'abonnements : API du site ou StoreKit / Play Billing.
    """

    source: SubscriptionSource

    def subscriptions(self) -> tuple[Subscription, ...]:
        """List the subscriptions of the current account.

        Liste les abonnements du compte courant.
        """
        ...
