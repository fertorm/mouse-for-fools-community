"""Visor local de documentos informativos; no abre enlaces de red."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from mouse_for_fools.ui import tokens

DOCUMENTS = (
    ("Privacidad", "PRIVACIDAD.md"),
    ("Condiciones de uso", "TERMINOS.md"),
    ("Licencias", "LICENCIAS.md"),
)
DOCUMENT_DIRECTORY = Path(__file__).resolve().parent.parent / "legal"


class LegalDialog(QDialog):
    """Muestra documentos incluidos sin acceder a servicios externos."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Privacidad y licencias — Nexum by Fertorm")
        self.resize(tokens.WINDOW_WIDTH, tokens.WINDOW_HEIGHT)
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        for title, filename in DOCUMENTS:
            browser = QTextBrowser(tabs)
            browser.setOpenLinks(False)
            browser.setOpenExternalLinks(False)
            try:
                document = (DOCUMENT_DIRECTORY / filename).read_text(encoding="utf-8")
            except OSError:
                document = "Documento no disponible. Recupera el paquete completo."
            browser.setMarkdown(document)
            tabs.addTab(browser, title)
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
