"""Ribbon button: zoom out (View > Zoom).

Bouton du ruban : zoom arrière (Affichage > Zoom).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.REMOVE,
        tooltip=ctx.state.t("ribbon.zoom_out"),
        on_click=lambda _e: ctx.actions["zoom_out"],
    )
