"""Mouse cursors per editing tool (shared and reusable across views).

Curseurs de souris par outil d'édition (partagé, réutilisable dans toutes
les vues : il suffit de poser le curseur sur un GestureDetector).
"""

import flet as ft

TOOL_CURSORS: dict[str, ft.MouseCursor] = {
    "select": ft.MouseCursor.BASIC,
    # TEXT (not VERTICAL_TEXT): on the web renderer, verticalText maps to the
    # CSS "vertical-text" cursor (I-beam rotated 90°); TEXT maps to the
    # upright I-beam (CSS "text" / IDC_IBEAM on Windows desktop).
    # TEXT et non VERTICAL_TEXT : sur le rendu web, verticalText correspond au
    # curseur CSS « vertical-text » (I-beam pivoté à 90°) ; TEXT donne le
    # I-beam droit (CSS « text » / IDC_IBEAM sur Windows desktop).
    "text": ft.MouseCursor.TEXT,
    "rect": ft.MouseCursor.CLICK,
    "highlight": ft.MouseCursor.CLICK,
}
"""Cursor per tool name; add new tools here to reuse the mechanism.

Curseur par nom d'outil ; ajouter les nouveaux outils ici pour réutiliser
le mécanisme.
"""

DEFAULT_TOOL_CURSOR = ft.MouseCursor.BASIC
"""Cursor used when a tool has no entry in TOOL_CURSORS.

Curseur utilisé quand un outil n'a pas d'entrée dans TOOL_CURSORS.
"""


def cursor_for_tool(tool: str) -> ft.MouseCursor:
    """Return the mouse cursor for an editing tool (BASIC if unknown).

    Retourne le curseur de souris d'un outil d'édition (BASIC si inconnu).
    """
    return TOOL_CURSORS.get(tool, DEFAULT_TOOL_CURSOR)


def apply_tool_cursor(detector: ft.GestureDetector, tool: str) -> None:
    """Set a gesture detector's mouse cursor to the given tool's cursor.

    Pose le curseur de souris d'un détecteur de gestes sur celui de l'outil.
    """
    detector.mouse_cursor = cursor_for_tool(tool)
