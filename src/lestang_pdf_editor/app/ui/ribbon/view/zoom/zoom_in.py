"""Ribbon button: zoom in (View > Zoom).

Bouton du ruban : zoom avant (Affichage > Zoom).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.ADD,
        tooltip=ctx.state.t("ribbon.zoom_in"),
        on_click=lambda _e: ctx.actions["zoom_in"],
    )
