"""Ribbon button: search (Edit > Actions).

Bouton du ruban : rechercher (Édition > Actions).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.SEARCH,
        tooltip=f"{ctx.state.t('ribbon.search')} (Ctrl+F)",
        on_click=lambda _e: ctx.actions["search"](),
    )
