"""Ribbon button: italic toggle (Insert > Font).

Bouton du ruban : bouton italique (Insertion > Police).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    from lestang_pdf_editor.app.ui.ribbon.home.font import _shared

    return _shared.style_toggle(ctx, ft.Icons.FORMAT_ITALIC, "ribbon.italic", "italic")
