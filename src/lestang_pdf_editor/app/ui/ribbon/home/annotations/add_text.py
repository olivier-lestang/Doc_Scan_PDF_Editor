"""Ribbon button: Add text tool (Insert > Annotations > Add text).

Bouton du ruban : outil Ajouter du texte (Insertion > Annotations > Ajouter du texte).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    style = (
        ft.ButtonStyle(bgcolor="#BBDEFB")
        if ctx.state.tool == "text"
        else ft.ButtonStyle()
    )
    return ft.ElevatedButton(
        text=ctx.state.t("doc.add_text"),
        icon=ft.Icons.TEXT_FIELDS,
        style=style,
        on_click=lambda _e: ctx.toggle_tool("text"),
    )
