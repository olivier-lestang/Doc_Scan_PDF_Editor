"""Insert > Font ribbon group (family, size, bold, italic, underline, colors).

Groupe Insertion > Police du ruban (police, taille, gras, italique,
souligné, couleurs).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext, _ribbon_group
from lestang_pdf_editor.app.ui.ribbon.home.font import (
    bold,
    family,
    highlight_color,
    italic,
    size,
    text_color,
    underline,
)


def build_group(ctx: RibbonContext) -> ft.Control:
    """Build the Font group: one control per button module.

    Construit le groupe Police : un contrôle par module de bouton.
    """
    return _ribbon_group(
        ctx.state.t("ribbon.font"),
        [
            family.control(ctx),
            size.control(ctx),
            bold.control(ctx),
            italic.control(ctx),
            underline.control(ctx),
            text_color.control(ctx),
            highlight_color.control(ctx),
        ],
    )
