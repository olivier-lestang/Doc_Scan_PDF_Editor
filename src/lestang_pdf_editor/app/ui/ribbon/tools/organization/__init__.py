"""Page > Organization ribbon group (page navigation and edits).

Groupe Page > Organisation du ruban (navigation et modifications de pages).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext, _ribbon_group
from lestang_pdf_editor.app.ui.ribbon.tools.organization import (
    delete_page,
    duplicate_page,
    next_page,
    previous_page,
    rotate_left,
    rotate_right,
)


def build_group(ctx: RibbonContext) -> ft.Control:
    """Build the Page/Organization group: one control per button module.

    Construit le groupe Page/Organisation : un contrôle par module de
    bouton.
    """
    return _ribbon_group(
        ctx.state.t("ribbon.page"),
        [
            previous_page.control(ctx),
            next_page.control(ctx),
            rotate_left.control(ctx),
            rotate_right.control(ctx),
            delete_page.control(ctx),
            duplicate_page.control(ctx),
        ],
    )
