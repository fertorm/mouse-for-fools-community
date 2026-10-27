"""Ventana accesible de controles; no instala hooks ni ejecuta movimiento."""

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import (
    QBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from mouse_for_fools.ui import tokens
from mouse_for_fools.ui.icon import application_icon
from mouse_for_fools.ui.legal import LegalDialog

SHORTCUTS = (
    ("Espacio", "Clic izquierdo"),
    ("Q", "Doble clic"),
    ("E", "Clic derecho"),
    ("R / F", "Desplazar"),
    ("Mantener G", "Arrastrar"),
)


def label(text: str, style: str = "", *, centered: bool = False) -> QLabel:
    """Crea texto informativo con ajuste de línea y estilo nombrado."""
    result = QLabel(text)
    result.setWordWrap(True)
    result.setObjectName(style)
    if centered:
        result.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return result


class MainWindow(QWidget):
    """Presenta instrucciones y emite intenciones hacia el coordinador."""

    close_requested = Signal()
    minimize_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.allow_close = False
        self.setWindowTitle("Mouse for Fools — Nexum by Fertorm")
        self.setWindowIcon(application_icon())
        self.setStyleSheet(tokens.stylesheet())
        self.setMinimumSize(tokens.MIN_WIDTH, tokens.MIN_HEIGHT)
        self.resize(tokens.WINDOW_WIDTH, tokens.WINDOW_HEIGHT)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(tokens.MARGIN,) * 4)
        layout.setSpacing(tokens.SPACE * 2)
        self.status = label("Iniciando…", "status")
        self.description = label("Preparando el control del teclado", "secondary")
        layout.addWidget(self.status)
        layout.addWidget(self.description)
        layout.addWidget(self._guides(), 1)
        self.toggle_button = QPushButton("Iniciando…")
        self.toggle_button.setObjectName("primary")
        self.toggle_button.setEnabled(False)
        self.toggle_button.setAutoDefault(True)
        layout.addWidget(self.toggle_button)
        layout.addWidget(label("Ctrl + Alt + M: activar / desactivar", centered=True))
        layout.addWidget(label("Esc: desactivar · Ctrl + Alt + Esc: salir", centered=True))
        self.minimize_button = QPushButton("Minimizar a bandeja")
        self.minimize_button.setAutoDefault(True)
        self.minimize_button.clicked.connect(self.minimize_requested.emit)
        layout.addWidget(self.minimize_button)
        self.notice = label("", "secondary", centered=True)
        self.notice.hide()
        layout.addWidget(self.notice)
        layout.addWidget(label("Nexum by Fertorm", "secondary", centered=True))
        self.legal_button = QPushButton("Privacidad, uso y licencias")
        self.legal_button.clicked.connect(self._show_legal)
        layout.addWidget(self.legal_button)
        QWidget.setTabOrder(self.toggle_button, self.minimize_button)

    def _show_legal(self) -> None:
        self.legal_dialog = LegalDialog(self)
        self.legal_dialog.show()

    def _guides(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        self.guide_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, content)
        self.guide_layout.setSpacing(tokens.MARGIN)
        self.guide_layout.addWidget(self._movement_guide(), 1)
        self.guide_layout.addWidget(self._shortcut_guide(), 1)
        scroll.setWidget(content)
        return scroll

    def _movement_guide(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(label("Mover el cursor", "heading", centered=True))
        grid = QGridLayout()
        for key, row, column in (("W", 0, 1), ("A", 1, 0), ("S", 1, 1), ("D", 1, 2)):
            guide = label(key, "key", centered=True)
            guide.setMinimumSize(tokens.KEY_SIZE, tokens.KEY_SIZE)
            grid.addWidget(guide, row, column)
        layout.addLayout(grid)
        layout.addWidget(label("Ctrl: precisión", centered=True))
        layout.addWidget(label("Shift: rápido", centered=True))
        layout.addStretch()
        return panel

    def _shortcut_guide(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)
        layout.setVerticalSpacing(tokens.MARGIN)
        for row, (key, action) in enumerate(SHORTCUTS):
            layout.addWidget(label(key, "shortcut"), row, 0)
            layout.addWidget(label(action), row, 1)
        layout.setRowStretch(len(SHORTCUTS), 1)
        return panel

    def set_state(self, active: bool, *, enabled: bool = True) -> None:
        """Muestra un estado confirmado; nunca se llama optimistamente."""
        self.status.setText("Activado" if active else "Desactivado")
        self.description.setText(
            "El teclado controla el cursor" if active else "Tu teclado funciona normalmente"
        )
        text = "Desactivar control" if active else "Activar control"
        self.toggle_button.setText(text)
        self.toggle_button.setAccessibleName(text)
        self.toggle_button.setEnabled(enabled)

    def show_notice(self, message: str) -> None:
        """Muestra información accionable, ajustada al ancho disponible."""
        self.notice.setText(message)
        self.notice.setVisible(bool(message))

    def closeEvent(self, event: QCloseEvent) -> None:
        """Espera confirmación de cierre del servicio antes de desaparecer."""
        if self.allow_close:
            event.accept()
        else:
            event.ignore()
            self.close_requested.emit()

    def changeEvent(self, event: QEvent) -> None:
        """Integra el botón de minimizar del sistema con la bandeja."""
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            self.minimize_requested.emit()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Apila las guías en ventanas estrechas."""
        super().resizeEvent(event)
        if hasattr(self, "guide_layout"):
            direction = (
                QBoxLayout.Direction.TopToBottom
                if self.width() < tokens.STACK_WIDTH
                else QBoxLayout.Direction.LeftToRight
            )
            self.guide_layout.setDirection(direction)
