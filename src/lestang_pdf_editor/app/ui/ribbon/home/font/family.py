"""Ribbon button: font family dropdown (Insert > Font).

Bouton du ruban : liste des polices (Insertion > Police).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    from lestang_pdf_editor.app.ui.ribbon._shared import FONT_FAMILIES
    from lestang_pdf_editor.app.ui.ribbon.home.font import _shared

    return _shared.style_dropdown(ctx, "font_family", 140, FONT_FAMILIES, str)
