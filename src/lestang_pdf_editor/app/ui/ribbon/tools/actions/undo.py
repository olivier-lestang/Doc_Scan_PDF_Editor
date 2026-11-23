"""Ribbon button: undo (Edit > Actions).

Bouton du ruban : annuler (Édition > Actions).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.UNDO,
        tooltip=f"{ctx.state.t('ribbon.undo')} (Ctrl+Z)",
        on_click=lambda _e: ctx.actions["undo"](),
    )
