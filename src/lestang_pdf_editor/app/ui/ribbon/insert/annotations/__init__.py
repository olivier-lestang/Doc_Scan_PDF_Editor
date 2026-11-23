"""Insert > Annotations ribbon group (text box, rectangle, highlight, stamp).

Groupe Insertion > Annotations du ruban (zone de texte, cadre, surlignage,
tampon).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext, _ribbon_group
from lestang_pdf_editor.app.ui.ribbon.insert.annotations import (
    add_text,
    highlight_tool,
    rectangle,
    stamp,
)


def build_group(ctx: RibbonContext) -> ft.Control:
    """Build the Annotations group: one control per button module.

    Construit le groupe Annotations : un contrôle par module de bouton.
    """
    return _ribbon_group(
        ctx.state.t("ribbon.insert"),
        [
            add_text.control(ctx),
            rectangle.control(ctx),
            highlight_tool.control(ctx),
            stamp.control(ctx),
        ],
    )
