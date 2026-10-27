"""Icono y menú de bandeja; las acciones delegan al coordinador."""

from collections.abc import Callable

from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from mouse_for_fools.ui.icon import application_icon


class Tray:
    """Comparte el estado confirmado de la ventana."""

    def __init__(
        self,
        parent: QWidget,
        show: Callable[[], None],
        toggle: Callable[[], None],
        stop: Callable[[], None],
        *,
        available: bool | None = None,
    ) -> None:
        self.available = (
            QSystemTrayIcon.isSystemTrayAvailable() if available is None else available
        )
        self.icon = QSystemTrayIcon(application_icon(), parent)
        self.menu = QMenu(parent)
        self.show_action = self.menu.addAction("Mostrar ventana")
        self.toggle_action = self.menu.addAction("Activar control")
        self.exit_action = self.menu.addAction("Salir")
        self.show_action.triggered.connect(show)
        self.toggle_action.triggered.connect(toggle)
        self.exit_action.triggered.connect(stop)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(
            lambda reason: (
                show() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
            )
        )
        self.set_state(False, enabled=False)
        if self.available:
            self.icon.show()

    def set_state(self, active: bool, *, enabled: bool) -> None:
        """Actualiza tooltip y acción usando el mismo estado que la ventana."""
        state = "Activado" if active else "Desactivado"
        self.icon.setToolTip(f"Mouse for Fools · {state}")
        self.toggle_action.setText("Desactivar control" if active else "Activar control")
        self.toggle_action.setEnabled(enabled)

    def hide(self) -> None:
        """Retira el icono cuando el servicio ha terminado."""
        self.icon.hide()
