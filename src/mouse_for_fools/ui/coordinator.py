"""Coordinación Qt mediante señales encoladas y cierre no bloqueante."""

import logging
from time import monotonic
from typing import Protocol

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot

from mouse_for_fools.service import ServiceEvent, WindowsService
from mouse_for_fools.ui.tray import Tray
from mouse_for_fools.ui.window import MainWindow

POLL_MILLISECONDS = 30
UI_STOP_TIMEOUT = 5.0


class Service(Protocol):
    """Interfaz compartida por el servicio Windows y sus pruebas."""

    def start(self) -> None:
        """Inicia el servicio."""

    def set_active(self, active: bool) -> None:
        """Solicita un modo."""

    def stop(self) -> None:
        """Solicita cierre."""

    def join(self, timeout: float) -> bool:
        """Comprueba fin del trabajador."""


class DesktopCoordinator(QObject):
    """Mantiene sincronizadas ventana y bandeja con el servicio confirmado."""

    event_received = Signal(object)
    finished = Signal()

    def __init__(
        self,
        window: MainWindow,
        *,
        service: Service | None = None,
        tray_available: bool | None = None,
    ) -> None:
        super().__init__(window)
        self.window = window
        self.active = False
        self.ready = False
        self.pending = False
        self.closing = False
        self.terminal = False
        self._deadline = 0.0
        self.event_received.connect(self.receive, Qt.ConnectionType.QueuedConnection)
        self.service = (
            service if service is not None else WindowsService(self.event_received.emit)
        )
        self.tray = Tray(
            window, self.restore, self.toggle, self.request_close, available=tray_available
        )
        self.timer = QTimer(self)
        self.timer.setInterval(POLL_MILLISECONDS)
        self.timer.timeout.connect(self.poll_shutdown)
        window.toggle_button.clicked.connect(self.toggle)
        window.minimize_requested.connect(self.minimize)
        window.close_requested.connect(self.request_close)

    def start(self) -> None:
        """Arranca el servicio después de mostrar la ventana."""
        try:
            self.service.start()
        except Exception as error:
            logging.getLogger(__name__).error(
                "startup_failure category=%s", type(error).__name__
            )
            self.service.stop()
            self._show_error(
                "No se pudo iniciar el control. Cierra y vuelve a abrir la aplicación."
            )

    @Slot(object)
    def receive(self, event: ServiceEvent) -> None:
        """Procesa confirmaciones en el hilo principal; un error es terminal."""
        if self.terminal:
            return
        if event.kind == "error":
            self._show_error(event.message)
        elif event.kind == "stopped":
            self.terminal = True
            self.request_close()
        elif not self.closing:
            changed = self.active != event.active
            self.active, self.ready, self.pending = event.active, True, False
            self.window.set_state(self.active)
            self.tray.set_state(self.active, enabled=True)
            if changed:
                self._beep()

    def _show_error(self, message: str) -> None:
        self.terminal, self.ready, self.pending = True, False, False
        self.closing = False
        self.timer.stop()
        self.window.status.setText("No disponible")
        self.window.description.setText(message)
        self.window.toggle_button.setEnabled(False)
        self.tray.set_state(False, enabled=False)
        self.tray.icon.setToolTip("Mouse for Fools · No disponible")
        self.restore()

    @staticmethod
    def _beep() -> None:
        import logging
        import winsound

        try:
            winsound.MessageBeep(winsound.MB_OK)
        except RuntimeError:
            logging.getLogger(__name__).warning("notification_unavailable")

    @Slot()
    def toggle(self) -> None:
        """Deshabilita acciones hasta recibir una confirmación."""
        if not self.ready or self.pending or self.closing or self.terminal:
            return
        self.pending = True
        self.window.toggle_button.setEnabled(False)
        self.tray.toggle_action.setEnabled(False)
        self.service.set_active(not self.active)

    @Slot()
    def minimize(self) -> None:
        """Oculta solo si existe bandeja; de lo contrario conserva barra de tareas."""
        if self.closing:
            return
        if self.tray.available:
            self.window.hide()
        else:
            self.window.show_notice(
                "Bandeja no disponible; usa la barra de tareas para volver."
            )
            if not self.window.isMinimized():
                self.window.showMinimized()

    @Slot()
    def restore(self) -> None:
        """Muestra y enfoca la ventana solo por una acción explícita o fallo."""
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    @Slot()
    def request_close(self) -> None:
        """Inicia el cierre; no espera al listener en el hilo gráfico."""
        if self.closing:
            return
        self.closing = True
        self.window.toggle_button.setEnabled(False)
        self.tray.toggle_action.setEnabled(False)
        self.window.description.setText("Cerrando y liberando el teclado…")
        self._deadline = monotonic() + UI_STOP_TIMEOUT
        self.service.stop()
        self.timer.start()

    @Slot()
    def poll_shutdown(self) -> None:
        """Cierra Qt únicamente tras comprobar fin del trabajador propietario."""
        if self.service.join(0) and self.terminal:
            self.timer.stop()
            self.tray.hide()
            self.window.allow_close = True
            self.window.close()
            self.finished.emit()
        elif monotonic() >= self._deadline:
            self._show_error("El cierre tarda demasiado. Vuelve a pulsar X para reintentar.")
