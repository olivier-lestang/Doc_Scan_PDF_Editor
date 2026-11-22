"""Platform-neutral raw image buffer (no heavy native type at the boundary).

Tampon d'image brut neutre (aucun type natif lourd à la frontière).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageBuffer:
    """Raw 8-bit image, grayscale (1 channel) or RGB (3 channels).

    Image brute 8 bits, niveaux de gris (1 canal) ou RVB (3 canaux).
    """

    width: int
    height: int
    channels: int
    data: bytes

    def __post_init__(self) -> None:
        """Validate that the byte count matches the geometry.

        Valide que le nombre d'octets correspond à la géométrie.
        """
        expected = self.width * self.height * self.channels
        if len(self.data) != expected:
            msg = f"expected {expected} bytes, got {len(self.data)}"
            raise ValueError(msg)
