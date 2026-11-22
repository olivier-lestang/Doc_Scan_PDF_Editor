"""Test for the on-device RapidOCR engine on a rendered text image.

Test du moteur OCR embarqué RapidOCR sur une image de texte rendue.
"""

import pytest

from lestang_pdf_editor.core.image_buffer import ImageBuffer
from lestang_pdf_editor.core.result import Ok
from lestang_pdf_editor.data.ocr.rapid_ocr_engine import RapidOcrEngine

pytest.importorskip("rapidocr_onnxruntime", exc_type=ImportError)
Image = pytest.importorskip("PIL.Image")
ImageDraw = pytest.importorskip("PIL.ImageDraw")
ImageFont = pytest.importorskip("PIL.ImageFont")


def make_text_image(text: str = "HELLO OCR 123") -> ImageBuffer:
    """Render large text on a white image and return it as a buffer.

    Rend un texte en grand sur une image blanche et le retourne en tampon.
    """
    image = Image.new("RGB", (900, 200), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 64)
    except OSError:
        font = ImageFont.load_default()
    draw.text((30, 60), text, fill="black", font=font)
    return ImageBuffer(
        width=image.width,
        height=image.height,
        channels=3,
        data=image.convert("RGB").tobytes(),
    )


def test_recognize_text_finds_the_words() -> None:
    """OCR on a rendered 'HELLO OCR 123' image finds those words.

    L'OCR sur une image « HELLO OCR 123 » retrouve ces mots.
    """
    engine = RapidOcrEngine()
    result = engine.recognize_text(make_text_image(), ("eng",))
    assert isinstance(result, Ok)
    joined = " ".join(block.text for block in result.value).upper()
    assert "HELLO" in joined
    assert result.value[0].language == "eng"
    box = result.value[0].bounding_box
    assert all(0.0 <= v <= 1.0 for v in box)
