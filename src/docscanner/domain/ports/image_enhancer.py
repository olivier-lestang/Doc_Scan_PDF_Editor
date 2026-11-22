"""Port: one-tap image enhancement (contrast, brightness, denoise).

Port : amélioration d'image en un clic (contraste, luminosité, débruitage).
"""

from typing import Protocol

from docscanner.core.image_buffer import ImageBuffer
from docscanner.core.result import Result


class ImageEnhancer(Protocol):
    """Abstraction over the OpenCV enhancement pipeline (CLAHE, denoise).

    Abstraction au-dessus du pipeline d'amélioration OpenCV (CLAHE,
    débruitage).
    """

    def enhance(self, image: ImageBuffer) -> Result[ImageBuffer, str]:
        """Apply the full enhancement pipeline to a scanned image.

        Applique le pipeline complet d'amélioration à une image numérisée.
        """
        ...
