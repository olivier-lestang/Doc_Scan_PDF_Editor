"""Tests for the OpenCV one-tap enhancement pipeline.

Tests du pipeline d'amélioration en un clic OpenCV.
"""

import pytest

from docscanner.core.image_buffer import ImageBuffer
from docscanner.core.result import Ok
from docscanner.data.vision.opencv_enhancer import OpenCvEnhancer

cv2 = pytest.importorskip("cv2", exc_type=ImportError)
np = pytest.importorskip("numpy")


def make_noisy_image(width: int = 200, height: int = 120) -> ImageBuffer:
    """Build a low-contrast noisy RGB image.

    Construit une image RVB bruitée à faible contraste.
    """
    gradient = np.linspace(90, 110, width, dtype=np.float32)
    row = np.tile(gradient, (height, 1))
    noise = np.random.default_rng(0).normal(0, 4, (height, width))
    gray = np.clip(row + noise, 0, 255).astype(np.uint8)
    rgb = np.stack([gray] * 3, axis=-1)
    return ImageBuffer(width=width, height=height, channels=3, data=rgb.tobytes())


def test_enhance_keeps_geometry_and_increases_contrast() -> None:
    """Enhancement preserves size and increases local contrast (CLAHE).

    L'amélioration conserve la géométrie et augmente le contraste local
    (CLAHE).
    """
    image = make_noisy_image()
    result = OpenCvEnhancer().enhance(image)
    assert isinstance(result, Ok)
    out = result.value
    assert (out.width, out.height, out.channels) == (
        image.width,
        image.height,
        3,
    )
    before = np.frombuffer(image.data, dtype=np.uint8).astype(np.float32)
    after = np.frombuffer(out.data, dtype=np.uint8).astype(np.float32)
    assert after.std() > before.std()
