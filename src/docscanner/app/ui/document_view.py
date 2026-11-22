"""Document editor view: ribbon, centered zoomable canvas, OCR, export.

Vue éditeur de document : ruban, canevas centré et zoomable, OCR, export.
"""

import json
from collections.abc import Callable

import flet as ft

from docscanner.app.state import AppState
from docscanner.app.ui.common import page_scaffold, show_message
from docscanner.core.result import Err, Ok
from docscanner.domain.entities.annotation import (
    HighlightAnnotation,
    RectangleAnnotation,
    TextAnnotation,
)

TOOL_ICONS = {
    "select": ft.Icons.TOUCH_APP,
    "text": ft.Icons.TEXT_FIELDS,
    "rect": ft.Icons.CROP_SQUARE,
    "highlight": ft.Icons.HIGHLIGHT,
}
"""Icon per annotation tool.

Icône par outil d'annotation.
"""

TOOL_CURSORS = {
    "select": ft.MouseCursor.BASIC,
    "text": ft.MouseCursor.VERTICAL_TEXT,
    "rect": ft.MouseCursor.CLICK,
    "highlight": ft.MouseCursor.CLICK,
}
"""Mouse cursor per tool (the text tool shows a text-insertion cursor).

Curseur de souris par outil (l'outil texte affiche un curseur d'insertion
de texte).
"""

FONT_FAMILIES = ["Helvetica", "Arial", "Times New Roman", "Courier New"]
"""Font families offered in the ribbon.

Polices proposées dans le ruban.
"""

FONT_SIZES = [8, 10, 12, 14, 18, 24, 32, 48, 72]
"""Font sizes (pt) offered in the ribbon.

Tailles de police (pt) proposées dans le ruban.
"""

TEXT_COLORS = {
    "#000000": "Black",
    "#D32F2F": "Red",
    "#1976D2": "Blue",
    "#388E3C": "Green",
}
"""Text colors offered in the ribbon (hex -> label key suffix).

Couleurs de texte proposées dans le ruban (hex -> libellé).
"""

HIGHLIGHT_COLORS: dict[str, str] = {
    "#FFFF00": "Yellow",
    "#C6FF00": "Green",
    "#40C4FF": "Blue",
    "#FF80AB": "Pink",
}
"""Highlight (marker) colors offered in the ribbon.

Couleurs de surlignage (marqueur) proposées dans le ruban.
"""


def build_document_view(state: AppState) -> None:
    """Build the document editor view for the open document.

    Construit la vue éditeur pour le document ouvert.
    """
    page = state.page
    page.title = state.t("app_name")

    save_picker = ft.FilePicker(on_result=lambda e: _on_save(state, e))
    page.overlay.append(save_picker)

    thumbnails = ft.ListView(expand=False, width=140, spacing=8)
    canvas_stack = ft.Stack()
    gesture: ft.GestureDetector | None = None
    ocr_text = ft.TextField(multiline=True, read_only=True, expand=True, label="OCR")
    ocr_panel = ft.Container(
        content=ft.Column(
            controls=[ft.Text(state.t("doc.ocr_result")), ocr_text],
            expand=True,
        ),
        width=320,
        padding=8,
        visible=False,
    )
    status = ft.Text("")
    zoom_label = ft.Text("100%")

    def refresh() -> None:
        nonlocal gesture
        gesture = _refresh_all(
            state,
            thumbnails,
            canvas_stack,
            gesture,
            ocr_text,
            ocr_panel,
            status,
            zoom_label,
        )
        page.update()

    def toggle_tool(tool: str) -> None:
        state.toggle_tool(tool)
        refresh()

    def on_scroll(event: ft.ScrollEvent) -> None:
        _on_scroll(state, event, refresh)

    gesture = ft.GestureDetector(
        content=canvas_stack,
        on_tap=lambda e: _on_tap(state, e, canvas_stack, refresh),
        on_pan_start=lambda e: _on_pan_start(state, e),
        on_pan_update=lambda e: _on_pan_update(state, e),
        on_pan_end=lambda e: _on_pan_end(state, e),
        on_scroll=on_scroll,
    )

    page.on_keyboard_event = lambda e: _on_keyboard(state, e, refresh)

    state.add_listener(refresh)

    ribbon = _build_ribbon(
        state, refresh, toggle_tool, save_picker, status, ocr_text, ocr_panel
    )

    canvas_area = ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column(
            controls=[
                ft.Row(controls=[gesture], scroll=ft.ScrollMode.ALWAYS),
            ],
            scroll=ft.ScrollMode.ALWAYS,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
    body = ft.Row(
        controls=[
            ft.Container(content=thumbnails, padding=4),
            ft.VerticalDivider(width=1),
            canvas_area,
            ocr_panel,
        ],
        expand=True,
    )
    zoom_controls = ft.Row(
        controls=[
            ft.IconButton(
                icon=ft.Icons.REMOVE,
                tooltip=state.t("ribbon.zoom_out"),
                on_click=lambda _e: _zoom(state, refresh, "out"),
            ),
            zoom_label,
            ft.IconButton(
                icon=ft.Icons.ADD,
                tooltip=state.t("ribbon.zoom_in"),
                on_click=lambda _e: _zoom(state, refresh, "in"),
            ),
            ft.TextButton(
                text="100%",
                tooltip=state.t("ribbon.zoom_reset"),
                on_click=lambda _e: _zoom(state, refresh, "reset"),
            ),
        ],
        spacing=4,
    )
    bottom_bar = ft.Container(
        content=ft.Row(
            controls=[status, zoom_controls],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=8,
        bgcolor="#FFFFFF",
        border=ft.border.only(top=ft.BorderSide(1, "#B0BEC5")),
    )
    content = ft.Column(controls=[ribbon, body, bottom_bar], expand=True)

    def go_home() -> None:
        from docscanner.app.ui.home import build_home_view

        build_home_view(state)

    page.controls.clear()
    page.controls.append(
        page_scaffold(state, state.t("app_name"), content, on_back=go_home)
    )
    refresh()


def _ribbon_group(caption: str, controls: list[ft.Control]) -> ft.Control:
    """Build one ribbon group: a small caption above a row of controls.

    Construit un groupe du ruban : une légende au-dessus d'une ligne
    d'outils.
    """
    return ft.Column(
        controls=[
            ft.Text(caption, size=10, color="#607D8B"),
            ft.Row(controls=controls, spacing=4),
        ],
        spacing=2,
    )


def _set_style(state: AppState, refresh: Callable[[], None], **kwargs: object) -> None:
    """Update fields of the current text style and refresh the ribbon.

    Met à jour des champs du style de texte courant et rafraîchit le ruban.
    """
    for key, value in kwargs.items():
        setattr(state.text_style, key, value)
    refresh()


def _toggle_style(state: AppState, refresh: Callable[[], None], attr: str) -> None:
    """Toggle a boolean field of the current text style.

    Inverse un champ booléen du style de texte courant.
    """
    setattr(state.text_style, attr, not getattr(state.text_style, attr))
    refresh()


def _build_ribbon(
    state: AppState,
    refresh: Callable[[], None],
    toggle_tool: Callable[[str], None],
    save_picker: ft.FilePicker,
    status: ft.Text,
    ocr_text: ft.TextField,
    ocr_panel: ft.Container,
) -> ft.Control:
    """Build the Word-like ribbon with font, insert, image and file groups.

    Construit le ruban façon Word : groupes police, insertion, image et
    fichier.
    """
    style = state.text_style
    family = ft.Dropdown(
        width=150,
        value=style.font_family,
        options=[ft.dropdown.Option(name) for name in FONT_FAMILIES],
        on_change=lambda e: _set_style(state, refresh, font_family=e.control.value),
    )
    size = ft.Dropdown(
        width=70,
        value=str(int(style.font_size_pt)),
        options=[ft.dropdown.Option(str(s)) for s in FONT_SIZES],
        on_change=lambda e: _set_style(
            state, refresh, font_size_pt=float(e.control.value or 14)
        ),
    )
    bold_btn = ft.IconButton(
        icon=ft.Icons.FORMAT_BOLD,
        tooltip=state.t("ribbon.bold"),
        selected=style.bold,
        on_click=lambda _e: _toggle_style(state, refresh, "bold"),
    )
    italic_btn = ft.IconButton(
        icon=ft.Icons.FORMAT_ITALIC,
        tooltip=state.t("ribbon.italic"),
        selected=style.italic,
        on_click=lambda _e: _toggle_style(state, refresh, "italic"),
    )
    underline_btn = ft.IconButton(
        icon=ft.Icons.FORMAT_UNDERLINED,
        tooltip=state.t("ribbon.underline"),
        selected=style.underline,
        on_click=lambda _e: _toggle_style(state, refresh, "underline"),
    )
    text_color = ft.Dropdown(
        width=110,
        value=style.text_color,
        options=[ft.dropdown.Option(value, key) for key, value in TEXT_COLORS.items()],
        on_change=lambda e: _set_style(state, refresh, text_color=e.control.value),
    )
    highlight = ft.Dropdown(
        width=110,
        value=style.highlight_color or "",
        options=[ft.dropdown.Option("", state.t("ribbon.none"))]
        + [ft.dropdown.Option(value, key) for key, value in HIGHLIGHT_COLORS.items()],
        on_change=lambda e: _set_style(
            state, refresh, highlight_color=e.control.value or None
        ),
    )
    font_group = _ribbon_group(
        state.t("ribbon.font"), [family, size, bold_btn, italic_btn, underline_btn]
    )
    color_group = _ribbon_group(state.t("ribbon.colors"), [text_color, highlight])
    add_text_style = (
        ft.ButtonStyle(bgcolor="#BBDEFB") if state.tool == "text" else ft.ButtonStyle()
    )
    insert_group = _ribbon_group(
        state.t("ribbon.insert"),
        [
            ft.ElevatedButton(
                text=state.t("doc.add_text"),
                icon=ft.Icons.TEXT_FIELDS,
                style=add_text_style,
                on_click=lambda _e: toggle_tool("text"),
            ),
            ft.IconButton(
                icon=ft.Icons.CROP_SQUARE,
                tooltip=state.t("doc.tool_rect"),
                selected=state.tool == "rect",
                on_click=lambda _e: toggle_tool("rect"),
            ),
            ft.IconButton(
                icon=ft.Icons.HIGHLIGHT,
                tooltip=state.t("doc.tool_highlight"),
                selected=state.tool == "highlight",
                on_click=lambda _e: toggle_tool("highlight"),
            ),
        ],
    )
    image_group = _ribbon_group(
        state.t("ribbon.image"),
        [
            ft.ElevatedButton(
                text=state.t("doc.enhance"),
                icon=ft.Icons.AUTO_FIX_HIGH,
                on_click=lambda _e: _enhance(state, refresh),
            ),
            ft.ElevatedButton(
                text=state.t("doc.ocr"),
                icon=ft.Icons.SCANNER,
                on_click=lambda _e: _run_ocr(
                    state, ocr_text, ocr_panel, status, refresh
                ),
            ),
        ],
    )
    file_group = _ribbon_group(
        state.t("ribbon.file"),
        [
            ft.ElevatedButton(
                text=state.t("doc.export"),
                icon=ft.Icons.SAVE,
                on_click=lambda _e: save_picker.save_file(
                    file_name="document.pdf", allowed_extensions=["pdf"]
                ),
            ),
        ],
    )
    return ft.Container(
        content=ft.Row(
            controls=[font_group, color_group, insert_group, image_group, file_group],
            spacing=20,
        ),
        padding=8,
        bgcolor="#FFFFFF",
        border=ft.border.only(bottom=ft.BorderSide(1, "#B0BEC5")),
    )


def _refresh_all(
    state: AppState,
    thumbnails: ft.ListView,
    canvas_stack: ft.Stack,
    gesture: ft.GestureDetector | None,
    ocr_text: ft.TextField,
    ocr_panel: ft.Container,
    status: ft.Text,
    zoom_label: ft.Text,
) -> ft.GestureDetector:
    """Rebuild thumbnails, canvas, OCR panel and zoom label from state.

    Reconstruit vignettes, canevas, panneau OCR et zoom depuis l'état.
    """
    thumbnails.controls.clear()
    for index in range(state.page_count()):
        png = state.page_png_path(index, 72)
        if isinstance(png, Ok):
            thumbnails.controls.append(
                ft.GestureDetector(
                    content=ft.Image(src=str(png.value), width=120),
                    on_tap=lambda _e, i=index: _select_page(state, i),
                )
            )
    canvas_stack.controls.clear()
    if state.document is not None and gesture is not None:
        index = state.selected_page
        png = state.page_png_path(index, state.display_dpi())
        if isinstance(png, Ok):
            from PIL import Image

            with Image.open(png.value) as img:
                base_width, base_height = img.size
            scale = state.zoom
            canvas_width = int(base_width * scale)
            canvas_height = int(base_height * scale)
            canvas_stack.width = canvas_width
            canvas_stack.height = canvas_height
            canvas_stack.controls.append(
                ft.Image(
                    src=str(png.value),
                    width=canvas_width,
                    height=canvas_height,
                    fit=ft.ImageFit.FILL,
                )
            )
            canvas_stack.controls.extend(
                _annotation_overlays(state, canvas_width, canvas_height)
            )
        ocr_panel.visible = index in state.page_ocr
        ocr_text.value = state.page_ocr.get(index, "")
        lang = state.page_language.get(index, "")
        status.value = f"Page {index + 1}/{state.page_count()}" + (
            f" — lang: {lang}" if lang else ""
        )
        zoom_label.value = f"{int(state.zoom * 100)}%"
        gesture.mouse_cursor = TOOL_CURSORS[state.tool]
    return gesture


def _select_page(state: AppState, index: int) -> None:
    """Select a page by index and notify listeners.

    Sélectionne une page par son index et notifie les auditeurs.
    """
    state.selected_page = index
    state._notify()


def _annotation_overlays(
    state: AppState, width: int, height: int
) -> list[ft.Container]:
    """Build overlay containers for the current page's annotations.

    Construit les conteneurs de superposition des annotations de la page
    courante (infobulle auteur + horodatage au survol d'un texte).
    """
    overlays: list[ft.Container] = []
    for annotation in state.annotations():
        if annotation.page_index != state.selected_page:
            continue
        x, y, w, h = annotation.rect
        if isinstance(annotation, TextAnnotation):
            tooltip = ""
            if annotation.author or annotation.created_at:
                tooltip = f"{annotation.author}\n{annotation.created_at}"
            overlays.append(
                ft.Container(
                    content=ft.Text(
                        annotation.content,
                        size=annotation.font_size_pt,
                        color=annotation.color,
                        weight=(ft.FontWeight.BOLD if annotation.bold else None),
                        italic=annotation.italic,
                        style=(
                            ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE)
                            if annotation.underline
                            else None
                        ),
                        bgcolor=(
                            ft.Colors.with_opacity(0.45, annotation.highlight_color)
                            if annotation.highlight_color
                            else None
                        ),
                    ),
                    left=x * width,
                    top=y * height,
                    tooltip=tooltip or None,
                )
            )
        elif isinstance(annotation, RectangleAnnotation):
            overlays.append(
                ft.Container(
                    left=x * width,
                    top=y * height,
                    width=w * width,
                    height=h * height,
                    border=ft.border.all(
                        annotation.stroke_width_pt, annotation.stroke_color
                    ),
                )
            )
        elif isinstance(annotation, HighlightAnnotation):
            overlays.append(
                ft.Container(
                    left=x * width,
                    top=y * height,
                    width=w * width,
                    height=h * height,
                    bgcolor=ft.Colors.with_opacity(0.35, annotation.color),
                )
            )
    return overlays


def _local_point(event: object) -> tuple[float, float]:
    """Extract local (x, y) from a pointer event, tolerating raw JSON data.

    Extrait (x, y) en coordonnées locales d'un événement pointeur, même
    si l'événement brut arrive sous forme de données JSON.
    """
    x = getattr(event, "local_x", None)
    y = getattr(event, "local_y", None)
    data = getattr(event, "data", None)
    if (x is None or y is None) and data:
        try:
            parsed = json.loads(str(data))
            x = parsed.get("lx", x)
            y = parsed.get("ly", y)
        except (TypeError, ValueError):
            pass
    return float(x or 0.0), float(y or 0.0)


def _on_tap(
    state: AppState,
    event: ft.TapEvent,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
) -> None:
    """With the text tool, open an inline editor at the exact click point.

    Avec l'outil texte, ouvre un éditeur en ligne au point exact du clic.
    """
    if state.tool != "text" or state.document is None:
        return
    page = state.page
    point_x, point_y = _local_point(event)
    image = state.page_image(state.selected_page, state.display_dpi())
    if isinstance(image, Err):
        return
    canvas_width = image.value.width * state.zoom
    canvas_height = image.value.height * state.zoom
    norm_x = point_x / canvas_width
    norm_y = point_y / canvas_height
    style = state.text_style

    field = ft.TextField(
        label=state.t("doc.text_content"),
        autofocus=True,
        width=260,
        on_submit=lambda _e: commit(),
    )

    def commit() -> None:
        text = (field.value or "").strip()
        if text:
            state.add_annotation(
                TextAnnotation(
                    page_index=state.selected_page,
                    rect=(
                        norm_x,
                        norm_y,
                        260 / canvas_width,
                        40 / canvas_height,
                    ),
                    content=text,
                    font_family=style.font_family,
                    font_size_pt=style.font_size_pt,
                    color=style.text_color,
                    bold=style.bold,
                    italic=style.italic,
                    underline=style.underline,
                    highlight_color=style.highlight_color,
                    author=state.author_name(),
                    created_at=state.new_timestamp(),
                )
            )
        if editor in canvas_stack.controls:
            canvas_stack.controls.remove(editor)
        refresh()

    editor = ft.Container(
        content=ft.Row(
            controls=[
                field,
                ft.IconButton(
                    icon=ft.Icons.CHECK,
                    tooltip=state.t("doc.validate"),
                    on_click=lambda _e: commit(),
                ),
            ],
            spacing=4,
        ),
        left=point_x,
        top=point_y,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#1976D2"),
        padding=4,
    )
    canvas_stack.controls.append(editor)
    page.update()


def _on_pan_start(state: AppState, event: ft.DragStartEvent) -> None:
    """Remember the drag start point for rect/highlight tools.

    Mémorise le point de début de glisser pour les outils cadre/surlignage.
    """
    state._drag_start = _local_point(event)
    state._drag_last = state._drag_start


def _on_pan_update(state: AppState, event: ft.DragUpdateEvent) -> None:
    """Track the current drag position (DragEndEvent has no coordinates).

    Suit la position courante du glisser (DragEndEvent n'a pas de
    coordonnées).
    """
    state._drag_last = _local_point(event)


def _on_pan_end(state: AppState, event: ft.DragEndEvent) -> None:
    """Create a rect/highlight annotation from the drag gesture.

    Crée une annotation cadre/surlignage à partir du geste de glisser.
    """
    if state.tool not in ("rect", "highlight") or state.document is None:
        return
    start = getattr(state, "_drag_start", None)
    if start is None:
        return
    end = getattr(state, "_drag_last", None) or start
    image = state.page_image(state.selected_page, state.display_dpi())
    if isinstance(image, Err):
        return
    width = image.value.width * state.zoom
    height = image.value.height * state.zoom
    x1, y1 = start[0] / width, start[1] / height
    x2, y2 = end[0] / width, end[1] / height
    rect = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    if rect[2] < 0.005 or rect[3] < 0.005:
        return
    if state.tool == "rect":
        state.add_annotation(
            RectangleAnnotation(page_index=state.selected_page, rect=rect)
        )
    else:
        state.add_annotation(
            HighlightAnnotation(page_index=state.selected_page, rect=rect)
        )


def _on_keyboard(
    state: AppState, event: ft.KeyboardEvent, refresh: Callable[[], None]
) -> None:
    """Track Ctrl/Cmd and handle zoom shortcuts Ctrl +/-/0.

    Suit Ctrl/Cmd et gère les raccourcis de zoom Ctrl +/-/0.
    """
    state.ctrl_pressed = bool(event.ctrl or event.meta)
    if state.ctrl_pressed:
        key = (event.key or "").lower()
        if key in ("+", "=", "add", "num_add"):
            state.zoom_in()
            refresh()
        elif key in ("-", "_", "subtract", "num_subtract"):
            state.zoom_out()
            refresh()
        elif key == "0":
            state.zoom_reset()
            refresh()


def _on_scroll(
    state: AppState, event: ft.ScrollEvent, refresh: Callable[[], None]
) -> None:
    """Ctrl/Cmd + mouse wheel zooms the page (works on Win/macOS/Linux).

    Ctrl/Cmd + molette zoome la page (Windows/macOS/Linux).
    """
    if state.ctrl_pressed:
        delta = getattr(event, "scroll_delta_y", 0.0) or 0.0
        if delta:
            state.set_zoom(state.zoom * (1.1 ** (-delta / 50.0)))
            refresh()


def _zoom(state: AppState, refresh: Callable[[], None], direction: str) -> None:
    """Apply a zoom button action: "in", "out" or "reset".

    Applique un bouton de zoom : « in », « out » ou « reset ».
    """
    if direction == "in":
        state.zoom_in()
    elif direction == "out":
        state.zoom_out()
    else:
        state.zoom_reset()
    refresh()


def _enhance(state: AppState, refresh: Callable[[], None]) -> None:
    """Run the one-tap enhancement on the current page.

    Lance l'amélioration en un clic sur la page courante.
    """
    result = state.enhance_page(state.selected_page)
    if isinstance(result, Ok):
        refresh()


def _run_ocr(
    state: AppState,
    ocr_text: ft.TextField,
    ocr_panel: ft.Container,
    status: ft.Text,
    refresh: Callable[[], None],
) -> None:
    """Run OCR on the current page and show the recognized text.

    Lance l'OCR sur la page courante et affiche le texte reconnu.
    """
    result = state.ocr_page(state.selected_page)
    if isinstance(result, Ok):
        ocr_panel.visible = True
        ocr_text.value = state.page_ocr.get(state.selected_page, "")
        status.value = (
            f"OCR: {len(result.value)} blocks, "
            f"lang: {state.page_language.get(state.selected_page, '?')}"
        )
    refresh()


def _on_save(state: AppState, event: ft.FilePickerResultEvent) -> None:
    """Handle the save-file result: export the document as PDF.

    Gère le résultat du sélecteur de sauvegarde : exporte le document en
    PDF.
    """
    if not event.path:
        return
    result = state.export_pdf(event.path)
    if isinstance(result, Ok):
        show_message(state.page, "OK", f"Saved: {event.path}")
    else:
        show_message(state.page, "Error", result.error)
