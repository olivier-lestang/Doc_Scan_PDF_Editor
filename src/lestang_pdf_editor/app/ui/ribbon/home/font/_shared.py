"""Shared builders for the Insert > Font group (not a button file).

Constructeurs partagés du groupe Insertion > Police (fichier non-bouton,
préfixe underscore).
"""

from collections.abc import Callable

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import (
    RibbonContext,
    _set_style,
    _toggle_style,
)


def style_dropdown(
    ctx: RibbonContext,
    attr: str,
    width: int,
    options: list[str],
    convert: Callable[[str], object],
) -> ft.Dropdown:
    """Build a style dropdown bound to a text-style attribute.

    Construit une liste déroulante liée à un attribut du style de texte.
    """
    return ft.Dropdown(
        width=width,
        value=str(getattr(ctx.state.text_style, attr)),
        options=[ft.dropdown.Option(name) for name in options],
        on_change=lambda e: _set_style(
            ctx.state, ctx.refresh, **{attr: convert(e.control.value or "")}
        ),
    )


def style_toggle(
    ctx: RibbonContext, icon: ft.Icon, tooltip_key: str, attr: str
) -> ft.IconButton:
    """Build a toggle button (bold/italic/underline) for a style attribute.

    Construit un bouton bascule (gras/italique/souligné) pour un attribut de
    style.
    """
    return ft.IconButton(
        icon=icon,
        tooltip=ctx.state.t(tooltip_key),
        selected=bool(getattr(ctx.state.text_style, attr)),
        on_click=lambda _e: _toggle_style(ctx.state, ctx.refresh, attr),
    )
