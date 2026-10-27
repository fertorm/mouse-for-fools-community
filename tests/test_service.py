"""Contrato del servicio con motor real y adaptadores sin efectos externos."""

from queue import Queue
from threading import Event
from typing import Any

import pytest
from test_windows_backend import NullPointer

from mouse_for_fools.input_router import ControlKey
from mouse_for_fools.runtime import MouseRuntime
from mouse_for_fools.service import ServiceEvent, WindowsService


class FakeListener:
    """Sustituye únicamente el hook del sistema."""

    def __init__(self) -> None:
        self.ready = True
        self.alive = False
        self.error: Exception | None = None
        self.stuck = False
        self.started = Event()

    def start(self) -> None:
        self.alive = True
        self.started.set()

    def stop(self) -> None:
        if not self.stuck:
            self.alive = False

    def join(self, timeout: float) -> bool:
        return not self.alive

    def check(self) -> None:
        if self.error:
            raise self.error


class FakeLease:
    """Reserva local controlable sin alterar la sesión Windows."""

    def __init__(self) -> None:
        self.available = True
        self.released = False

    def acquire(self) -> bool:
        return self.available

    def release(self) -> None:
        self.released = True


def make_service() -> Any:
    events: Queue[ServiceEvent] = Queue()
    pointer = NullPointer()
    listener = FakeListener()
    lease = FakeLease()
    service = WindowsService(
        events.put,
        pointer=pointer,
        listener_factory=lambda *_args: listener,
        lease=lease,
        timeout=0.1,
    )
    return service, events, pointer, listener, lease


def test_start_disabled_and_confirm_changes_before_terminal_close() -> None:
    service, events, _, listener, lease = make_service()
    service.start()
    try:
        assert events.get(timeout=2) == ServiceEvent("ready", False)
        service.set_active(True)
        assert events.get(timeout=2) == ServiceEvent("state", True)
        service.set_active(True)
        assert events.get(timeout=2) == ServiceEvent("state", True)
        service.set_active(False)
        assert events.get(timeout=2) == ServiceEvent("state", False)
    finally:
        service.stop()
        assert service.join(2)
    assert not listener.alive
    assert lease.released
    assert events.get(timeout=2).kind == "stopped"
    with pytest.raises(RuntimeError):
        service.start()


def test_close_releases_drag_and_rejects_late_actions() -> None:
    service, events, pointer, _, _ = make_service()
    service.start()
    assert events.get(timeout=2).kind == "ready"
    service.set_active(True)
    events.get(timeout=2)
    service.runtime.press(ControlKey.G)
    service.runtime.press(ControlKey.D)
    service.stop()
    assert service.join(2)
    assert pointer.button_events == ["down", "up"]
    previous = list(pointer.moves)
    service.runtime.tick(1)
    assert not service.runtime.press(ControlKey.SPACE)
    assert pointer.moves == previous
    service.set_active(True)
    assert not service.runtime.active


@pytest.mark.parametrize("failure", ["listener", "tick", "startup", "duplicate"])
def test_failures_are_terminal_and_release_resources(failure: Any, monkeypatch: Any) -> None:
    service, events, _, listener, lease = make_service()
    if failure == "startup":
        listener.ready = False
    elif failure == "duplicate":
        lease.available = False
    service.start()
    if failure in ("listener", "tick"):
        assert events.get(timeout=2).kind == "ready"
        if failure == "listener":
            listener.error = RuntimeError("secret exception text")
        else:

            def fail_tick(_self: Any, _elapsed: Any) -> None:
                raise RuntimeError("secret exception text")

            monkeypatch.setattr(MouseRuntime, "tick", fail_tick)
    assert service.join(2)
    result = events.get(timeout=2)
    assert result.kind == "error"
    assert "secret" not in result.message
    assert not listener.alive
    assert lease.released


def test_stop_during_startup_does_not_emit_ready() -> None:
    service, events, _, listener, _ = make_service()
    listener.ready = False
    service.start()
    assert listener.started.wait(2)
    service.stop()
    assert service.join(2)
    assert events.get(timeout=2).kind == "stopped"


def test_live_listener_timeout_is_not_reported_as_success() -> None:
    service, events, _, listener, lease = make_service()
    service.start()
    events.get(timeout=2)
    listener.stuck = True
    service.stop()
    assert service.join(2)
    assert events.get(timeout=2).kind == "error"
    assert not lease.released  # Do not allow a second hook while one survives.


def test_listener_error_during_startup_is_not_lost(monkeypatch: Any) -> None:
    service, events, _, listener, _ = make_service()

    def start_with_error() -> None:
        listener.error = RuntimeError("callback failure")
        service.stop()

    monkeypatch.setattr(listener, "start", start_with_error)
    service.start()
    assert service.join(2)
    assert events.get(timeout=2).kind == "error"


def test_listener_is_joined_even_if_stop_raises(monkeypatch: Any) -> None:
    service, events, _, listener, _ = make_service()
    joined = []
    service.start()
    events.get(timeout=2)

    def fail_stop() -> None:
        listener.alive = False
        raise RuntimeError("stop failure")

    monkeypatch.setattr(listener, "stop", fail_stop)
    monkeypatch.setattr(listener, "join", lambda _: joined.append(True) or True)
    service.stop()
    assert service.join(2)
    assert joined == [True]
    assert events.get(timeout=2).kind == "error"


def test_hook_mode_change_is_forwarded_to_the_same_state_stream() -> None:
    service, events, _, _, _ = make_service()
    service.start()
    assert events.get(timeout=2).kind == "ready"
    try:
        for key in (ControlKey.CONTROL, ControlKey.ALT, ControlKey.M):
            service.runtime.press(key)
        assert events.get(timeout=2) == ServiceEvent("state", True)
        service.runtime.press(ControlKey.ESCAPE)
        assert events.get(timeout=2) == ServiceEvent("state", False)
    finally:
        service.stop()
        assert service.join(2)


def test_service_ticks_use_actual_elapsed_time(monkeypatch: Any) -> None:
    import mouse_for_fools.service as module

    service, _, _, listener, _ = make_service()
    listener.alive = True
    service._listener = listener
    waits = iter((False, False, True))

    class ScriptedStop:
        def wait(self, _timeout: Any) -> Any:
            return next(waits)

        def is_set(self) -> Any:
            return False

    service._stop = ScriptedStop()
    times = iter((10.0, 10.25, 11.0))
    ticks = []
    monkeypatch.setattr(module, "monotonic", lambda: next(times))
    monkeypatch.setattr(service.runtime, "tick", ticks.append)
    service._loop()
    assert ticks == [0.25, 0.75]
