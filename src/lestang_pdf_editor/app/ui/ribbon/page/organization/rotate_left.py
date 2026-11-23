"""Ribbon button: rotate left (Page > Organization).

Bouton du ruban : pivoter à gauche (Page > Organisation).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.ROTATE_LEFT,
        tooltip=f"{ctx.state.t('ribbon.rotate_left')}",
        on_click=lambda _e: ctx.actions["rotate_left"],
    )
