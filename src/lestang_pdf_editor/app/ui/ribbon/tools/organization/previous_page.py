"""Ribbon button: previous page (Page > Organization).

Bouton du ruban : page précédente (Page > Organisation).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.ARROW_BACK,
        tooltip=f"{ctx.state.t('ribbon.prev')} (PgUp)",
        on_click=lambda _e: ctx.actions["prev"],
    )
