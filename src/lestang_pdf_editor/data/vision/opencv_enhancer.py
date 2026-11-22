"""One-tap enhancement pipeline with OpenCV (CLAHE, denoise, sharpen).

Pipeline d'amélioration en un clic avec OpenCV (CLAHE, débruitage,
netteté).

Heavy imports (cv2, numpy) are lazy so the app starts fast and unit tests
that do not enhance images stay light.
"""

from lestang_pdf_editor.core.image_buffer import ImageBuffer
from lestang_pdf_editor.core.result import Err, Ok, Result


class OpenCvEnhancer:
    """ImageEnhancer using CLAHE on the L channel + denoise + sharpen.

    ImageEnhancer utilisant CLAHE sur le canal L + débruitage + netteté.
    """

    def enhance(self, image: ImageBuffer) -> Result[ImageBuffer, str]:
        """Apply contrast (CLAHE), brightness balance, denoise, sharpen.

        Applique contraste (CLAHE), équilibrage de luminosité, débruitage
        et netteté.
        """
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            return Err(f"OpenCV unavailable: {exc}")
        try:
            array = np.frombuffer(image.data, dtype=np.uint8).reshape(
                image.height, image.width, image.channels
            )
            if image.channels == 1:
                gray = array
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                enhanced = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
                out = enhanced
                channels = 1
            else:
                rgb = array
                lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
                lightness, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                lightness = clahe.apply(lightness)
                # Rebalance brightness toward the mid range.
                lightness = cv2.normalize(lightness, None, 16, 240, cv2.NORM_MINMAX)
                merged = cv2.merge((lightness, a, b))
                bgr = cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
                denoised = cv2.fastNlMeansDenoisingColored(bgr, None, 10, 10, 7, 21)
                kernel = np.array(
                    [[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32
                )
                out = cv2.filter2D(denoised, -1, kernel)
                channels = 3
            return Ok(
                ImageBuffer(
                    width=image.width,
                    height=image.height,
                    channels=channels,
                    data=out.tobytes(),
                )
            )
        except Exception as exc:
            return Err(f"enhance failed: {exc}")
