"""Word-like ribbon package with clickable tabs (File / Home / Insert / Tools).

Package du ruban façon Word avec onglets cliquables (Fichier / Accueil /
Insertion / Outils) : un répertoire par onglet, un sous-répertoire par
groupe, un fichier par bouton ; fonctions partagées dans les fichiers
`_shared.py` (préfixe underscore = non-bouton).

Adding a button = adding one file in its group directory and one line in
that group's `__init__.py`. Adding a group = one new sub-directory plus a
`build_group` call in the tab's `__init__.py`. Adding a tab = one directory
plus one entry in TABS below.

Ajouter un bouton = un fichier de plus dans le répertoire de son groupe et
une ligne dans le `__init__.py` de ce groupe. Ajouter un groupe = un
nouveau sous-répertoire plus un appel `build_group` dans le `__init__.py`
de l'onglet. Ajouter un onglet = un répertoire plus une entrée dans TABS.
"""

from collections.abc import Callable
from types import ModuleType

import flet as ft

from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.app.ui.ribbon import file, home, insert, tools
from lestang_pdf_editor.app.ui.ribbon._shared import (
    FONT_FAMILIES,
    FONT_SIZES,
    HIGHLIGHT_COLORS,
    STAMPS,
    TEXT_COLORS,
    RibbonContext,
)

__all__ = [
    "FONT_FAMILIES",
    "FONT_SIZES",
    "HIGHLIGHT_COLORS",
    "STAMPS",
    "TEXT_COLORS",
    "RibbonContext",
    "build_ribbon",
]

TABS: list[tuple[str, str]] = [
    ("file", "ribbon.file"),
    ("home", "ribbon.home"),
    ("insert", "ribbon.insert"),
    ("tools", "ribbon.tools"),
]
"""Clickable ribbon tabs: (tab id, i18n label key).

Onglets cliquables du ruban : (id d'onglet, clé i18n du libellé).
"""

TAB_MODULES: dict[str, ModuleType] = {
    "file": file,
    "home": home,
    "insert": insert,
    "tools": tools,
}
"""Module implementing each tab's groups.

Module implémentant les groupes de chaque onglet.
"""

DEFAULT_TAB = "home"
"""Tab shown first (Home holds the text-editing tools).

Onglet affiché en premier (Accueil contient les outils d'édition de texte).
"""


def build_ribbon(
    state: AppState,
    refresh: Callable[[], None],
    toggle_tool: Callable[[str], None],
    actions: dict[str, Callable[..., None]],
) -> ft.Control:
    """Assemble the ribbon: a clickable tab row + the active tab's groups.

    Assemble le ruban : une ligne d'onglets cliquables + les groupes de
    l'onglet actif.
    """
    ctx = RibbonContext(
        state=state, refresh=refresh, toggle_tool=toggle_tool, actions=actions
    )
    current = {"tab": DEFAULT_TAB}
    content = ft.Container(expand=True)
    tab_buttons: dict[str, ft.TextButton] = {}

    def render_tab() -> None:
        module = TAB_MODULES[current["tab"]]
        content.content = ft.Row(
            controls=module.build_groups(ctx),
            spacing=16,
            scroll=ft.ScrollMode.ALWAYS,
        )
        for name, button in tab_buttons.items():
            button.style = (
                ft.ButtonStyle(bgcolor="#BBDEFB")
                if name == current["tab"]
                else ft.ButtonStyle()
            )
        page = state.page
        if page is not None:
            page.update()

    def make_tab(name: str, label_key: str) -> ft.TextButton:
        def on_click(_e: ft.ControlEvent, n: str = name) -> None:
            if current["tab"] != n:
                current["tab"] = n
                render_tab()

        button = ft.TextButton(text=state.t(label_key), on_click=on_click)
        tab_buttons[name] = button
        return button

    tabs_row = ft.Row(controls=[make_tab(n, k) for n, k in TABS], spacing=4)
    render_tab()
    return ft.Container(
        content=ft.Column(controls=[tabs_row, content], spacing=4, expand=True),
        padding=8,
        bgcolor="#FFFFFF",
        border=ft.border.only(bottom=ft.BorderSide(1, "#B0BEC5")),
    )
