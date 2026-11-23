"""Ribbon button: delete page (Page > Organization).

Bouton du ruban : supprimer la page (Page > Organisation).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.DELETE,
        tooltip=f"{ctx.state.t('ribbon.delete_page')}",
        on_click=lambda _e: ctx.actions["delete_page"],
    )
