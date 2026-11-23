"""Home category of the ribbon (currently the File group).

Catégorie Accueil du ruban (actuellement le groupe Fichier).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext
from lestang_pdf_editor.app.ui.ribbon.home import file


def build_groups(ctx: RibbonContext) -> list[ft.Control]:
    """Return the ribbon groups of the Home category.

    Retourne les groupes du ruban de la catégorie Accueil.
    """
    return [file.build_group(ctx)]
