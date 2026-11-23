"""Ribbon button: rectangle tool (Insert > Annotations).

Bouton du ruban : outil cadre (Insertion > Annotations).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.CROP_SQUARE,
        tooltip=ctx.state.t("doc.tool_rect"),
        selected=ctx.state.tool == "rect",
        on_click=lambda _e: ctx.toggle_tool("rect"),
    )
