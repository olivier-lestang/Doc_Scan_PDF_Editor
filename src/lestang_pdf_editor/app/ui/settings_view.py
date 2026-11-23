"""Settings view: UI language, scan DPI, OCR languages, legal pages.

Vue des réglages : langue de l'UI, DPI de numérisation, langues OCR,
pages légales.
"""

import flet as ft

from lestang_pdf_editor.app.state import LEGAL_NOTICE, PRIVACY_TEXT, AppState
from lestang_pdf_editor.app.ui.common import page_scaffold, show_scrollable_text
from lestang_pdf_editor.app.ui.home import build_home_view

UI_LANGUAGES = {"en": "English", "fr": "Français", "es": "Español", "zh": "中文"}
"""Available UI languages.

Langues disponibles pour l'UI.
"""

DPI_CHOICES = ["auto", "150", "200", "300", "400", "600"]
"""Selectable DPI values ("auto" plus manual values).

Valeurs de DPI sélectionnables (« auto » plus valeurs manuelles).
"""

THEME_CHOICES = {"system": "theme_system", "light": "theme_light", "dark": "theme_dark"}
"""Theme modes mapped to their i18n label keys.

Modes de thème associés à leurs clés i18n de libellé.
"""


def build_settings_view(state: AppState) -> None:
    """Build the settings view on the page bound to the state.

    Construit la vue des réglages sur la page associée à l'état.
    """
    page = state.page
    page.title = state.t("settings.title")

    language_dropdown = ft.Dropdown(
        label=state.t("settings.language"),
        value=state.settings.language,
        options=[
            ft.dropdown.Option(code, label) for code, label in UI_LANGUAGES.items()
        ],
        on_change=lambda e: state.set_ui_language(e.control.value),
    )
    current_dpi = str(state.settings.scan.dpi)
    dpi_dropdown = ft.Dropdown(
        label=state.t("settings.dpi"),
        value=current_dpi if current_dpi in DPI_CHOICES else "auto",
        options=[
            ft.dropdown.Option(
                code, state.t("settings.dpi_auto") if code == "auto" else code
            )
            for code in DPI_CHOICES
        ],
        on_change=lambda e: state.set_dpi(
            "auto" if e.control.value == "auto" else int(e.control.value)
        ),
    )

    def save_name(_e: ft.ControlEvent) -> None:
        from dataclasses import replace

        state.settings = replace(
            state.settings,
            first_name=first_name_field.value or "",
            last_name=last_name_field.value or "",
        )
        state.settings_repo.save(state.settings)

    first_name_field = ft.TextField(
        label=state.t("settings.first_name"),
        value=state.settings.first_name,
        width=200,
        on_submit=save_name,
        on_blur=save_name,
    )
    last_name_field = ft.TextField(
        label=state.t("settings.last_name"),
        value=state.settings.last_name,
        width=200,
        on_submit=save_name,
        on_blur=save_name,
    )

    theme_dropdown = ft.Dropdown(
        label=state.t("settings.theme"),
        value=state.settings.theme_mode
        if state.settings.theme_mode in THEME_CHOICES
        else "system",
        options=[
            ft.dropdown.Option(code, state.t(f"settings.{label}"))
            for code, label in THEME_CHOICES.items()
        ],
        on_change=lambda e: state.set_theme_mode(e.control.value),
    )

    ocr_checkboxes = [
        ft.Checkbox(
            label=lang.names.get(state.settings.language, lang.names["en"]),
            value=lang.code in state.ocr_languages,
            on_change=lambda e, code=lang.code: _toggle_ocr_language(state, code, e),
        )
        for lang in state.catalog.all()
    ]

    def show_legal(_e: ft.ControlEvent) -> None:
        show_scrollable_text(page, state.t("legal.legal_notice"), LEGAL_NOTICE)

    def show_oss(_e: ft.ControlEvent) -> None:
        show_scrollable_text(
            page, state.t("legal.open_source_licenses"), state.load_oss_licenses()
        )

    def show_notes(_e: ft.ControlEvent) -> None:
        show_scrollable_text(
            page, state.t("legal.release_notes"), state.load_release_notes()
        )

    def show_privacy(_e: ft.ControlEvent) -> None:
        show_scrollable_text(page, state.t("legal.privacy"), PRIVACY_TEXT)

    legal_buttons = ft.Row(
        controls=[
            ft.TextButton(text=state.t("legal.legal_notice"), on_click=show_legal),
            ft.TextButton(
                text=state.t("legal.open_source_licenses"), on_click=show_oss
            ),
            ft.TextButton(text=state.t("legal.release_notes"), on_click=show_notes),
            ft.TextButton(text=state.t("legal.privacy"), on_click=show_privacy),
        ],
        wrap=True,
    )

    body = ft.Column(
        controls=[
            ft.Text(state.t("settings.title"), size=20, weight=ft.FontWeight.BOLD),
            ft.Row(controls=[first_name_field, last_name_field], spacing=8),
            language_dropdown,
            dpi_dropdown,
            theme_dropdown,
            ft.Text(state.t("settings.ocr_languages"), weight=ft.FontWeight.BOLD),
            ft.Column(controls=ocr_checkboxes),
            ft.Divider(),
            ft.Text(state.t("legal.title"), weight=ft.FontWeight.BOLD),
            legal_buttons,
            ft.ElevatedButton(text="←", on_click=lambda _e: build_home_view(state)),
        ],
        scroll=ft.ScrollMode.ALWAYS,
        expand=True,
    )
    page.controls.clear()
    page.controls.append(
        page_scaffold(
            state,
            state.t("settings.title"),
            ft.Container(content=body, padding=16, expand=True),
        )
    )
    page.update()


def _toggle_ocr_language(state: AppState, code: str, event: ft.ControlEvent) -> None:
    """Toggle an OCR language in the user's selection.

    Active/désactive une langue OCR dans la sélection de l'utilisateur.
    """
    selected = set(state.ocr_languages)
    if event.control.value:
        selected.add(code)
    else:
        selected.discard(code)
    state.ocr_languages = tuple(sorted(selected))
    state._notify()
