"""Ribbon button: highlight color palette (Insert > Font > Highlight).

Bouton du ruban : palette de surlignage (Insertion > Police > Surlignage).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import (
    HIGHLIGHT_COLORS,
    RibbonContext,
    _color_palette,
)


def control(ctx: RibbonContext) -> ft.Control:
    """Build the highlight-color swatch palette button (with None entry).

    Construit le bouton de palette de surlignage (avec entrée « Aucun »).
    """
    return _color_palette(ctx, "highlight_color", HIGHLIGHT_COLORS, allow_none=True)
