"""Adaptador de pynput con hilo real y hook nativo sustituido."""

from threading import Event, Thread
from types import SimpleNamespace
from typing import Any

import pytest
from test_windows_backend import NullPointer

from mouse_for_fools.input_router import ControlKey
from mouse_for_fools.runtime import MouseRuntime
from mouse_for_fools.windows_listener import PynputListener


class Suppressed(Exception):
    """Excepción de control equivalente a suppress_event."""


class NativeThread(Thread):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.callback = kwargs["win32_event_filter"]
        self.done = Event()
        self.begun = Event()

    def run(self) -> None:
        self.begun.set()
        self.done.wait(2)

    def stop(self) -> None:
        self.done.set()

    def suppress_event(self) -> None:
        raise Suppressed


@pytest.fixture
def adapter(monkeypatch: Any) -> Any:
    from pynput import keyboard

    import mouse_for_fools.windows_listener as module

    hooks = {}
    monkeypatch.setattr(keyboard, "Listener", NativeThread)
    monkeypatch.setattr(
        module,
        "import_module",
        lambda _: SimpleNamespace(SystemHook=SimpleNamespace(_HOOKS=hooks)),
    )
    runtime = MouseRuntime(NullPointer())
    stops = []
    listener = PynputListener(runtime, lambda: stops.append(True))
    yield listener, runtime, stops, hooks
    listener.stop()
    assert listener.join(2)


def test_readiness_requires_live_thread_and_nonzero_hook(adapter: Any) -> None:
    listener, _, _, hooks = adapter
    assert not listener.ready
    listener.start()
    assert listener._listener.begun.wait(2)
    assert not listener.ready
    hooks[listener._listener.ident] = SimpleNamespace(_hook=0)
    assert not listener.ready
    hooks[listener._listener.ident]._hook = 1
    assert listener.ready
    listener.stop()
    assert listener.join(2)
    assert not listener.ready


def test_filter_processes_before_suppression_and_pairs_release(adapter: Any) -> None:
    listener, runtime, _, _ = adapter
    runtime.set_active(True)
    data = SimpleNamespace(vkCode=0x47, scanCode=0)
    with pytest.raises(Suppressed):
        listener._filter(0x0100, data)
    runtime.set_active(False)
    with pytest.raises(Suppressed):
        listener._filter(0x0101, data)
    listener.check()  # Suppression was not reported as an operational failure.
    assert listener._filter(0x0101, data) is False
    assert listener._filter(0xFFFF, data) is None


def test_filter_failure_is_propagated_without_escaping_to_pynput(
    adapter: Any, monkeypatch: Any
) -> None:
    listener, runtime, stops, _ = adapter

    def fail(_key: Any) -> None:
        raise RuntimeError("private error")

    monkeypatch.setattr(runtime, "press", fail)
    assert listener._filter(0x0100, SimpleNamespace(vkCode=0x47, scanCode=0)) is False
    assert stops == [True]
    with pytest.raises(RuntimeError):
        listener.check()


def test_emergency_close_requests_owner_stop(adapter: Any) -> None:
    listener, runtime, stops, _ = adapter
    runtime.press(ControlKey.CONTROL)
    runtime.press(ControlKey.ALT)
    with pytest.raises(Suppressed):
        listener._filter(0x0100, SimpleNamespace(vkCode=0x1B, scanCode=0))
    assert stops == [True]
