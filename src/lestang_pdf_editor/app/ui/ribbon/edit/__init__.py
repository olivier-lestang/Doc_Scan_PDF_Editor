"""Edit category of the ribbon (undo/search actions).

Catégorie Édition du ruban (actions annuler/rechercher).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext
from lestang_pdf_editor.app.ui.ribbon.edit import actions


def build_groups(ctx: RibbonContext) -> list[ft.Control]:
    """Return the ribbon groups of the Edit category.

    Retourne les groupes du ruban de la catégorie Édition.
    """
    return [actions.build_group(ctx)]
