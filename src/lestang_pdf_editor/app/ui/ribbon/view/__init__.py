"""View category of the ribbon (zoom controls).

Catégorie Affichage du ruban (contrôles de zoom).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext
from lestang_pdf_editor.app.ui.ribbon.view import zoom


def build_groups(ctx: RibbonContext) -> list[ft.Control]:
    """Return the ribbon groups of the View category.

    Retourne les groupes du ruban de la catégorie Affichage.
    """
    return [zoom.build_group(ctx)]
