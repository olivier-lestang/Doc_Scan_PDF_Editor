"""Page category of the ribbon (file/page organization).

Catégorie Page du ruban (organisation des fichiers/pages).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext
from lestang_pdf_editor.app.ui.ribbon.page import organization


def build_groups(ctx: RibbonContext) -> list[ft.Control]:
    """Return the ribbon groups of the Page category.

    Retourne les groupes du ruban de la catégorie Page.
    """
    return [organization.build_group(ctx)]
