"""Insert category of the ribbon (Annotations and Font groups).

Catégorie Insertion du ruban (groupes Annotations et Police).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext
from lestang_pdf_editor.app.ui.ribbon.insert import annotations, font


def build_groups(ctx: RibbonContext) -> list[ft.Control]:
    """Return the ribbon groups of the Insert category.

    Retourne les groupes du ruban de la catégorie Insertion.
    """
    return [annotations.build_group(ctx), font.build_group(ctx)]
