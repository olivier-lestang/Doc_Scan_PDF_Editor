"""Ribbon button: one-tap enhance (Image > Processing).

Bouton du ruban : amélioration en un clic (Image > Traitement).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.ElevatedButton(
        text=ctx.state.t("doc.enhance"),
        icon=ft.Icons.AUTO_FIX_HIGH,
        on_click=lambda _e: ctx.actions["enhance"](),
    )
