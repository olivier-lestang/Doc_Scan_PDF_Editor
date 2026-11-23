"""Ribbon button: text color palette (Insert > Font > Text color).

Bouton du ruban : palette de couleur du texte (Insertion > Police >
Couleur du texte).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import (
    TEXT_COLORS,
    RibbonContext,
    _color_palette,
)


def control(ctx: RibbonContext) -> ft.Control:
    """Build the text-color swatch palette button.

    Construit le bouton de palette de pastilles pour la couleur du texte.
    """
    return _color_palette(ctx, "text_color", TEXT_COLORS)
