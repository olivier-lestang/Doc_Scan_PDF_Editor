"""Word-like ribbon package (one directory per category, one file per button).

Package du ruban façon Word : un répertoire par catégorie (onglet), un
sous-répertoire par groupe, un fichier par bouton ; fonctions partagées
dans les fichiers `_shared.py` (préfixe underscore = non-bouton).

Adding a button = adding one file in its group directory and one line in
that group's `__init__.py`. Adding a group = one new sub-directory plus a
`build_group` call in the category's `__init__.py`.

Ajouter un bouton = un fichier de plus dans le répertoire de son groupe et
une ligne dans le `__init__.py` de ce groupe. Ajouter un groupe = un
nouveau sous-répertoire plus un appel `build_group` dans le `__init__.py`
de la catégorie.
"""

from collections.abc import Callable

import flet as ft

from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.app.ui.ribbon import edit, home, image, insert, page, view
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


def build_ribbon(
    state: AppState,
    refresh: Callable[[], None],
    toggle_tool: Callable[[str], None],
    actions: dict[str, Callable[..., None]],
) -> ft.Control:
    """Assemble the ribbon row from the per-category group builders.

    Assemble la ligne du ruban à partir des constructeurs de groupes par
    catégorie (Accueil, Page, Insertion, Image, Affichage, Édition).
    """
    ctx = RibbonContext(
        state=state, refresh=refresh, toggle_tool=toggle_tool, actions=actions
    )
    groups = [
        *home.build_groups(ctx),
        *page.build_groups(ctx),
        *insert.build_groups(ctx),
        *image.build_groups(ctx),
        *view.build_groups(ctx),
        *edit.build_groups(ctx),
    ]
    return ft.Container(
        content=ft.Row(controls=groups, spacing=16, scroll=ft.ScrollMode.ALWAYS),
        padding=8,
        bgcolor="#FFFFFF",
        border=ft.border.only(bottom=ft.BorderSide(1, "#B0BEC5")),
    )
