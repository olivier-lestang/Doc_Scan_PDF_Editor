"""Ribbon button: reset zoom to 100% (View > Zoom).

Bouton du ruban : réinitialiser le zoom à 100 % (Affichage > Zoom).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.TextButton(
        text="100%",
        tooltip=ctx.state.t("ribbon.zoom_reset"),
        on_click=lambda _e: ctx.actions["zoom_reset"](),
    )
