"""Ribbon button: fit page (View > Zoom).

Bouton du ruban : ajuster à la page (Affichage > Zoom).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.TextButton(
        text=ctx.state.t("ribbon.fit_page"),
        on_click=lambda _e: ctx.actions["fit_page"](),
    )
