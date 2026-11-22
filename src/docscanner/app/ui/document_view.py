"""Document editor view: pages, canvas with annotations, OCR, export.

Vue éditeur de document : pages, canevas avec annotations, OCR, export.
"""

import json
from collections.abc import Callable

import flet as ft

from docscanner.app.state import AppState
from docscanner.app.ui.common import app_bar, show_message
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
    gesture = ft.GestureDetector(
        content=canvas_stack,
        on_tap=lambda e: _on_tap(state, e),
        on_pan_start=lambda e: _on_pan_start(state, e),
        on_pan_update=lambda e: _on_pan_update(state, e),
        on_pan_end=lambda e: _on_pan_end(state, e),
    )
    canvas_scroll = ft.Column(
        scroll=ft.ScrollMode.ALWAYS,
        controls=[ft.Row(scroll=ft.ScrollMode.ALWAYS, controls=[gesture], expand=True)],
        expand=True,
    )
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

    def refresh() -> None:
        _refresh_all(
            state, thumbnails, canvas_stack, gesture, ocr_text, ocr_panel, status
        )
        page.update()

    state.add_listener(refresh)

    def set_tool(tool: str) -> Callable[[ft.ControlEvent], None]:
        def handler(_e: ft.ControlEvent) -> None:
            state.tool = tool
            refresh()

        return handler

    toolbar = ft.Row(
        controls=[
            ft.IconButton(
                icon=TOOL_ICONS["select"],
                tooltip="Select",
                on_click=set_tool("select"),
            ),
            ft.IconButton(
                icon=TOOL_ICONS["text"],
                tooltip=state.t("doc.tool_text"),
                on_click=set_tool("text"),
            ),
            ft.IconButton(
                icon=TOOL_ICONS["rect"],
                tooltip=state.t("doc.tool_rect"),
                on_click=set_tool("rect"),
            ),
            ft.IconButton(
                icon=TOOL_ICONS["highlight"],
                tooltip=state.t("doc.tool_highlight"),
                on_click=set_tool("highlight"),
            ),
            ft.VerticalDivider(width=1),
            ft.ElevatedButton(
                text=state.t("doc.enhance"),
                on_click=lambda _e: _enhance(state, status, refresh),
            ),
            ft.ElevatedButton(
                text=state.t("doc.ocr"),
                on_click=lambda _e: _run_ocr(
                    state, ocr_text, ocr_panel, status, refresh
                ),
            ),
            ft.ElevatedButton(
                text=state.t("doc.export"),
                on_click=lambda _e: save_picker.save_file(
                    file_name="document.pdf",
                    allowed_extensions=["pdf"],
                ),
            ),
        ],
        wrap=True,
    )

    body = ft.Row(
        controls=[
            ft.Container(content=thumbnails, padding=4),
            ft.VerticalDivider(width=1),
            ft.Container(content=canvas_scroll, expand=True, padding=4),
            ocr_panel,
        ],
        expand=True,
    )

    def go_home() -> None:
        from docscanner.app.ui.home import build_home_view

        build_home_view(state)

    page.controls.clear()
    page.controls.append(app_bar(state, state.t("app_name"), on_back=go_home))
    page.controls.append(toolbar)
    page.controls.append(body)
    page.controls.append(status)
    refresh()


def _refresh_all(
    state: AppState,
    thumbnails: ft.ListView,
    canvas_stack: ft.Stack,
    gesture: ft.GestureDetector,
    ocr_text: ft.TextField,
    ocr_panel: ft.Container,
    status: ft.Text,
) -> None:
    """Rebuild thumbnails, canvas and OCR panel from the state.

    Reconstruit les vignettes, le canevas et le panneau OCR depuis l'état.
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
    if state.document is not None:
        index = state.selected_page
        png = state.page_png_path(index, state.display_dpi())
        if isinstance(png, Ok):
            from PIL import Image

            with Image.open(png.value) as img:
                width, height = img.size
            canvas_stack.width = width
            canvas_stack.height = height
            canvas_stack.controls.append(
                ft.Image(
                    src=str(png.value),
                    width=width,
                    height=height,
                    fit=ft.ImageFit.FILL,
                )
            )
            canvas_stack.controls.extend(_annotation_overlays(state, width, height))
            gesture.content = canvas_stack
        ocr_panel.visible = index in state.page_ocr
        ocr_text.value = state.page_ocr.get(index, "")
        lang = state.page_language.get(index, "")
        status.value = f"Page {index + 1}/{state.page_count()}" + (
            f" — lang: {lang}" if lang else ""
        )


def _select_page(state: AppState, index: int) -> None:
    """Select a page by index and notify listeners.

    Sélectionne une page par son index et notifie les auditeurs.
    """
    state.selected_page = index
    state._notify()


def _annotation_overlays(
    state: AppState, width: int, height: int
) -> list[ft.Container]:
    """Build the overlay containers for the current page's annotations.

    Construit les conteneurs de superposition pour les annotations de la
    page courante.
    """
    overlays: list[ft.Container] = []
    for annotation in state.annotations():
        if annotation.page_index != state.selected_page:
            continue
        x, y, w, h = annotation.rect
        if isinstance(annotation, TextAnnotation):
            overlays.append(
                ft.Container(
                    content=ft.Text(
                        annotation.content,
                        size=annotation.font_size_pt,
                        color=annotation.color,
                    ),
                    left=x * width,
                    top=y * height,
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


def _on_tap(state: AppState, event: ft.TapEvent) -> None:
    """Handle a tap: with the text tool, open the text annotation dialog.

    Gère un appui : avec l'outil texte, ouvre la boîte de dialogue de
    l'annotation texte.
    """
    if state.tool != "text" or state.document is None:
        return
    page = state.page
    content_field = ft.TextField(label=state.t("doc.text_content"), expand=True)
    size_dropdown = ft.Dropdown(
        label=state.t("doc.font_size"),
        value="14",
        options=[
            ft.dropdown.Option(str(size))
            for size in (8, 10, 12, 14, 18, 24, 32, 48, 72)
        ],
    )

    def confirm(_e: ft.ControlEvent) -> None:
        image = state.page_image(state.selected_page, state.display_dpi())
        if isinstance(image, Err):
            return
        point_x, point_y = _local_point(event)
        x = point_x / image.value.width
        y = point_y / image.value.height
        state.add_annotation(
            TextAnnotation(
                page_index=state.selected_page,
                rect=(x, y, 0.4, 0.06),
                content=content_field.value or "",
                font_size_pt=float(size_dropdown.value or 14),
            )
        )
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        title=ft.Text(state.t("doc.add_text")),
        content=ft.Column(controls=[content_field, size_dropdown], tight=True),
        actions=[
            ft.TextButton(text="OK", on_click=confirm),
        ],
    )
    page.overlay.append(dialog)
    dialog.open = True
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
    width, height = image.value.width, image.value.height
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


def _enhance(state: AppState, status: ft.Text, refresh: Callable[[], None]) -> None:
    """Run the one-tap enhancement on the current page.

    Lance l'amélioration en un clic sur la page courante.
    """
    result = state.enhance_page(state.selected_page)
    status.value = (
        state.t("doc.enhanced") if isinstance(result, Ok) else f"Error: {result.error}"
    )
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
    else:
        status.value = f"OCR error: {result.error}"
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
