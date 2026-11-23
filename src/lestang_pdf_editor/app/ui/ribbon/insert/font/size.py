"""Ribbon button: font size dropdown (Insert > Font).

Bouton du ruban : taille de police (Insertion > Police).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    from lestang_pdf_editor.app.ui.ribbon._shared import FONT_SIZES
    from lestang_pdf_editor.app.ui.ribbon.insert.font import _shared

    return _shared.style_dropdown(
        ctx,
        "font_size_pt",
        64,
        [str(s) for s in FONT_SIZES],
        lambda v: float(v or 14),
    )
