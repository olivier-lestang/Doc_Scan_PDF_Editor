"""Image category of the ribbon (enhance + OCR).

Catégorie Image du ruban (amélioration + OCR).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext
from lestang_pdf_editor.app.ui.ribbon.image import processing


def build_groups(ctx: RibbonContext) -> list[ft.Control]:
    """Return the ribbon groups of the Image category.

    Retourne les groupes du ruban de la catégorie Image.
    """
    return [processing.build_group(ctx)]
