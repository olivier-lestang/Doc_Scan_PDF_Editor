"""Image > Processing ribbon group (enhance, OCR).

Groupe Image > Traitement du ruban (amélioration, OCR).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext, _ribbon_group
from lestang_pdf_editor.app.ui.ribbon.tools.processing import enhance, ocr


def build_group(ctx: RibbonContext) -> ft.Control:
    """Build the Processing group: one control per button module.

    Construit le groupe Traitement : un contrôle par module de bouton.
    """
    return _ribbon_group(
        ctx.state.t("ribbon.image"),
        [enhance.control(ctx), ocr.control(ctx)],
    )
