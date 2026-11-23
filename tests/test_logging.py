"""Tests for the rotating log file and the search progress callback.

Tests du fichier de log rotatif et du callback de progression de la
recherche.
"""

import logging
from pathlib import Path

from pypdf import PdfWriter

from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.core.logging_setup import get_logger, setup_logging
from lestang_pdf_editor.core.result import Ok


def test_setup_logging_writes_rotating_file(tmp_path: Path) -> None:
    """setup_logging creates app.log in the given dir and records messages.

    setup_logging crée app.log dans le dossier donné et enregistre les
    messages.
    """
    log_path = setup_logging(tmp_path)
    assert log_path == tmp_path / "app.log"
    logger = get_logger("test")
    logger.info("hello-log")
    for handler in logging.getLogger("lestang_pdf_editor").handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")
    assert "hello-log" in content
    assert "lestang_pdf_editor.test" in content


def test_search_reports_progress_per_page(tmp_path: Path) -> None:
    """search() calls progress(done, total) once per page, in order.

    search() appelle progress(done, total) une fois par page, dans l'ordre.
    """
    assets = Path(__file__).resolve().parents[1] / "assets"
    state = AppState(
        config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache",
        assets_dir=assets,
    )
    pdf = tmp_path / "doc.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=595, height=842)
    with pdf.open("wb") as handle:
        writer.write(handle)
    assert isinstance(state.open_path(str(pdf)), Ok)
    for index in range(3):
        state.page_ocr[index] = f"page {index}"
    calls: list[tuple[int, int]] = []
    matches = state.search("page", progress=lambda d, t: calls.append((d, t)))
    assert matches == [0, 1, 2]
    assert calls == [(1, 3), (2, 3), (3, 3)]
