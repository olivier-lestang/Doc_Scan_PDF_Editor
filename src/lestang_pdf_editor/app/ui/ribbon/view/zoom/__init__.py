"""View > Zoom ribbon group (zoom in/out/reset, fit width/page).

Groupe Affichage > Zoom du ruban (zoom avant/arrière/réinit, ajuster
largeur/page).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext, _ribbon_group
from lestang_pdf_editor.app.ui.ribbon.view.zoom import (
    fit_page,
    fit_width,
    zoom_in,
    zoom_out,
    zoom_reset,
)


def build_group(ctx: RibbonContext) -> ft.Control:
    """Build the Zoom group: one control per button module.

    Construit le groupe Zoom : un contrôle par module de bouton.
    """
    return _ribbon_group(
        ctx.state.t("ribbon.view"),
        [
            zoom_in.control(ctx),
            zoom_out.control(ctx),
            zoom_reset.control(ctx),
            fit_width.control(ctx),
            fit_page.control(ctx),
        ],
    )
