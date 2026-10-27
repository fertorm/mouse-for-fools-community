"""Entrada gráfica independiente de stdout y del runner de consola."""

import logging
import sys
from typing import cast

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from mouse_for_fools.diagnostics import configure_logging
from mouse_for_fools.ui.coordinator import DesktopCoordinator
from mouse_for_fools.ui.window import MainWindow


def main() -> int:
    """Abre la ventana y mantiene Qt hasta confirmar el cierre del servicio."""
    app = cast(QApplication, QApplication.instance()) or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    try:
        configure_logging()
        coordinator = DesktopCoordinator(window)
    except Exception as error:
        logging.getLogger(__name__).error(
            "desktop_startup_failure category=%s", type(error).__name__
        )
        window.status.setText("No disponible")
        window.description.setText(
            "No se pudo preparar la aplicación. Cierra y vuelve a intentarlo."
        )
        window.allow_close = True
        app.setQuitOnLastWindowClosed(True)
    else:
        coordinator.finished.connect(app.quit)
        QTimer.singleShot(0, coordinator.start)
    screen = app.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        window.resize(
            min(window.width(), available.width()), min(window.height(), available.height())
        )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
