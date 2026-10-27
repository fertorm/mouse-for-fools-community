"""Icono original dibujado con primitivas Qt, sin assets de terceros."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from mouse_for_fools.ui import tokens

ICON_SIZE = 64


def application_icon() -> QIcon:
    """Dibuja un mouse blanco sobre fondo del color de acento."""
    pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(tokens.ACCENT))
    painter.drawRoundedRect(QRectF(0, 0, 64, 64), 12, 12)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(tokens.WHITE), 3))
    painter.drawRoundedRect(QRectF(18, 9, 28, 46), 13, 13)
    painter.drawLine(32, 10, 32, 28)
    painter.drawLine(19, 29, 45, 29)
    painter.end()
    return QIcon(pixmap)
