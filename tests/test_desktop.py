"""Pruebas de widgets reales sin hook global."""

import os
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from mouse_for_fools.service import ServiceEvent
from mouse_for_fools.ui.coordinator import DesktopCoordinator
from mouse_for_fools.ui.window import MainWindow


@pytest.fixture(scope="session")
def qapp() -> Any:
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


class FakeService:
    """Servicio externo controlable; la UI debe esperar confirmación."""

    def __init__(self) -> None:
        self.requests = []
        self.stopping = False
        self.finished = False

    def start(self) -> None:
        pass

    def set_active(self, active: Any) -> Any:
        self.requests.append(active)

    def stop(self) -> None:
        self.stopping = True

    def join(self, timeout: Any) -> Any:
        return self.finished


@pytest.fixture
def desktop(qapp: Any) -> Any:
    window = MainWindow()
    service = FakeService()
    coordinator = DesktopCoordinator(window, service=service, tray_available=False)
    window.show()
    qapp.processEvents()
    yield window, service, coordinator
    coordinator.timer.stop()
    coordinator.tray.hide()
    window.allow_close = True
    window.close()


def test_initial_state_and_activation_wait_for_confirmation(desktop: Any) -> None:
    window, service, coordinator = desktop
    assert window.status.text() == "Iniciando…"
    assert not window.toggle_button.isEnabled()
    coordinator.receive(ServiceEvent("ready"))
    assert window.status.text() == "Desactivado"
    window.toggle_button.click()
    assert service.requests == [True]
    assert not window.toggle_button.isEnabled()
    assert window.status.text() == "Desactivado"
    coordinator.receive(ServiceEvent("state", True))
    assert window.toggle_button.isEnabled()
    assert window.status.text() == "Activado"
    assert coordinator.tray.toggle_action.text() == "Desactivar control"


def test_hotkey_state_and_tray_action_share_confirmation(desktop: Any) -> None:
    window, service, coordinator = desktop
    coordinator.receive(ServiceEvent("ready"))
    coordinator.receive(ServiceEvent("state", True))
    coordinator.tray.toggle_action.trigger()
    assert service.requests == [False]
    assert not coordinator.tray.toggle_action.isEnabled()
    coordinator.receive(ServiceEvent("state", False))
    assert window.status.text() == "Desactivado"


def test_error_restores_hidden_window_and_ignores_stale_state(desktop: Any) -> None:
    window, _, coordinator = desktop
    coordinator.receive(ServiceEvent("ready"))
    window.hide()
    coordinator.receive(ServiceEvent("error", message="No disponible"))
    coordinator.receive(ServiceEvent("state", True))
    assert window.isVisible()
    assert window.status.text() == "No disponible"
    assert not window.toggle_button.isEnabled()


def test_close_waits_for_worker_then_emits_finished(desktop: Any) -> None:
    window, service, coordinator = desktop
    done = []
    coordinator.finished.connect(lambda: done.append(True))
    window.close()
    assert service.stopping
    assert window.isVisible()
    coordinator.receive(ServiceEvent("stopped"))
    coordinator.poll_shutdown()
    assert done == []
    service.finished = True
    coordinator.poll_shutdown()
    assert done == [True]
    assert not window.isVisible()


def test_missing_tray_keeps_window_reachable(desktop: Any) -> None:
    window, _, coordinator = desktop
    coordinator.minimize()
    assert window.isVisible()
    assert window.isMinimized()
    assert "bandeja" in window.notice.text().lower()


def test_tray_minimize_and_restore_preserve_active_state(desktop: Any) -> None:
    window, _, coordinator = desktop
    coordinator.tray.available = True
    coordinator.receive(ServiceEvent("ready"))
    coordinator.receive(ServiceEvent("state", True))
    coordinator.minimize()
    assert not window.isVisible()
    coordinator.restore()
    assert window.isVisible()
    assert window.status.text() == "Activado"


def test_enter_activates_focused_button_and_guides_are_not_focusable(desktop: Any) -> None:
    window, service, coordinator = desktop
    coordinator.receive(ServiceEvent("ready"))
    window.toggle_button.setFocus()
    QTest.keyClick(window.toggle_button, Qt.Key.Key_Return)
    assert service.requests == [True]
    assert window.toggle_button.accessibleName() == "Activar control"
    assert window.minimumWidth() <= 360


def test_responsive_columns_stack_without_hiding_primary_action(
    desktop: Any, qapp: Any
) -> None:
    window, _, _ = desktop
    window.resize(360, 620)
    qapp.processEvents()
    assert window.guide_layout.direction() == window.guide_layout.Direction.TopToBottom
    assert window.toggle_button.isVisible()


def test_join_without_terminal_notification_does_not_close_early(desktop: Any) -> None:
    window, service, coordinator = desktop
    window.close()
    service.finished = True
    coordinator.poll_shutdown()
    assert window.isVisible()
    coordinator.receive(ServiceEvent("error", message="Error al liberar el teclado"))
    assert window.isVisible()
    assert window.status.text() == "No disponible"


def test_start_failure_is_visible_and_can_close(desktop: Any, monkeypatch: Any) -> None:
    window, service, coordinator = desktop

    def fail() -> None:
        raise RuntimeError("private exception")

    monkeypatch.setattr(service, "start", fail)
    coordinator.start()
    assert window.status.text() == "No disponible"
    assert "private" not in window.description.text()


def test_graphical_entry_opens_disabled_and_exits_without_console(
    qapp: Any, monkeypatch: Any
) -> None:
    from PySide6.QtCore import QTimer

    import mouse_for_fools.gui as gui

    service = FakeService()
    service.finished = True

    def factory(window: Any) -> Any:
        coordinator = DesktopCoordinator(window, service=service, tray_available=False)
        QTimer.singleShot(0, lambda: coordinator.receive(ServiceEvent("stopped")))
        return coordinator

    monkeypatch.setattr(gui, "DesktopCoordinator", factory)
    monkeypatch.setattr(gui, "configure_logging", lambda: None)
    assert gui.main() == 0
