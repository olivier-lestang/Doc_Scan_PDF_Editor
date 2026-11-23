"""Ribbon button: highlight tool (Insert > Annotations).

Bouton du ruban : outil surlignage (Insertion > Annotations).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.HIGHLIGHT,
        tooltip=ctx.state.t("doc.tool_highlight"),
        selected=ctx.state.tool == "highlight",
        on_click=lambda _e: ctx.toggle_tool("highlight"),
    )
