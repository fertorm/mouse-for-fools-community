"""Pruebas del mapeo Win32 sin instalar hooks globales."""

from typing import Any

import pytest

from mouse_for_fools.input_router import ControlKey
from mouse_for_fools.runtime import MouseRuntime
from mouse_for_fools.windows_backend import (
    KeyboardEventBridge,
    SuppressionTracker,
    _PynputPointer,
    control_key_from_vk,
    virtual_key_from_pynput,
)


def test_external_disable_preserves_pending_suppressed_release() -> None:
    """La UI no filtra un keyup cuyo keydown fue suprimido."""
    runtime = MouseRuntime(NullPointer())
    bridge = KeyboardEventBridge(runtime)
    runtime.set_active(True)
    assert bridge.handle_event(0x57, key_down=True).suppress is True
    runtime.set_active(False)
    assert bridge.handle_event(0x57, key_down=False).suppress is True
    assert bridge.handle_event(0x57, key_down=False).suppress is False


def test_external_enable_does_not_suppress_unpaired_control_release() -> None:
    """El Ctrl recibido por Windows conserva su liberación al activar desde UI."""
    runtime = MouseRuntime(NullPointer())
    bridge = KeyboardEventBridge(runtime)
    assert bridge.handle_event(0x11, key_down=True).suppress is False
    runtime.set_active(True)
    assert bridge.handle_event(0x11, key_down=False).suppress is False


class NullPointer:
    """Adaptador sin efectos para probar eventos de teclado."""

    def __init__(self) -> None:
        self.button_events: list[str] = []
        self.double_clicks = 0
        self.moves: list[tuple[int, int]] = []

    def click_left(self) -> None:
        pass

    def double_click_left(self) -> None:
        self.double_clicks += 1

    def click_right(self) -> None:
        pass

    def press_left(self) -> None:
        self.button_events.append("down")

    def release_left(self) -> None:
        self.button_events.append("up")

    def move(self, delta_x: int, delta_y: int) -> None:
        self.moves.append((delta_x, delta_y))

    def scroll(self, vertical_units: int) -> None:
        pass


@pytest.mark.parametrize(
    ("virtual_key", "expected_name"),
    [
        (0x11, "CONTROL"),
        (0xA2, "CONTROL"),
        (0xA3, "CONTROL"),
        (0x12, "ALT"),
        (0x4D, "M"),
        (0x57, "W"),
        (0x41, "A"),
        (0x53, "S"),
        (0x44, "D"),
        (0x45, "E"),
        (0x52, "R"),
        (0x46, "F"),
        (0x47, "G"),
        (0x20, "SPACE"),
        (0x1B, "ESCAPE"),
    ],
)
def test_virtual_keys_map_to_control_keys(virtual_key: int, expected_name: str) -> None:
    """Las teclas físicas relevantes deben usar un mapeo independiente del layout."""
    control_key = control_key_from_vk(virtual_key)

    assert control_key is not None
    assert control_key.name == expected_name


def test_key_release_remains_suppressed_after_mode_is_disabled() -> None:
    """Un keyup suelto no debe filtrarse a la aplicación enfocada."""
    tracker = SuppressionTracker()

    assert tracker.observe(ControlKey.W, key_down=True, suppress_now=True) is True
    assert tracker.observe(ControlKey.W, key_down=False, suppress_now=False) is True
    assert tracker.observe(ControlKey.W, key_down=False, suppress_now=False) is False


def test_key_release_is_not_suppressed_when_keydown_reached_windows() -> None:
    """Activar el modo no debe dejar Ctrl o Alt retenidos en la ventana activa."""
    tracker = SuppressionTracker()

    assert tracker.observe(ControlKey.CONTROL, key_down=True, suppress_now=False) is False
    assert tracker.observe(ControlKey.CONTROL, key_down=False, suppress_now=True) is False


def test_event_bridge_activates_and_suppresses_movement_key() -> None:
    """El puente debe conectar códigos Win32 con el runtime sin lógica duplicada."""
    runtime = MouseRuntime(pointer=NullPointer())
    bridge = KeyboardEventBridge(runtime)
    bridge.press_vk(0x11)
    bridge.press_vk(0x12)
    bridge.press_vk(0x4D)

    assert bridge.should_suppress_event(0x57, key_down=True) is True
    assert bridge.press_vk(0x57) is True


def test_event_bridge_processes_a_suppressed_key_inside_filter() -> None:
    """La supresión no debe impedir que el comando llegue al runtime."""
    runtime = MouseRuntime(pointer=NullPointer())
    bridge = KeyboardEventBridge(runtime)
    bridge.handle_event(0x11, key_down=True)
    bridge.handle_event(0x12, key_down=True)

    activation = bridge.handle_event(0x4D, key_down=True)

    assert activation.suppress is True
    assert activation.keep_running is True
    assert runtime.should_suppress(ControlKey.W) is True


def test_event_bridge_dispatches_drag_press_and_release() -> None:
    """El puente debe completar el ciclo físico de drag sin errores de adaptador."""
    pointer = NullPointer()
    runtime = MouseRuntime(pointer=pointer)
    bridge = KeyboardEventBridge(runtime)
    bridge.press_vk(0x11)
    bridge.press_vk(0x12)
    bridge.press_vk(0x4D)
    bridge.handle_event(0x47, key_down=True)
    bridge.handle_event(0x47, key_down=False)

    assert pointer.button_events == ["down", "up"]


def test_pynput_key_exposes_virtual_key_through_direct_attribute() -> None:
    """Las letras de pynput deben convertirse al código virtual de Windows."""
    key = type("FakeKey", (), {"vk": 0x57})()

    assert virtual_key_from_pynput(key) == 0x57


def test_pynput_special_key_exposes_nested_virtual_key() -> None:
    """Ctrl, Alt, Space y Escape usan el valor anidado de pynput."""
    value = type("FakeValue", (), {"vk": 0x1B})()
    key = type("FakeSpecialKey", (), {"value": value})()

    assert virtual_key_from_pynput(key) == 0x1B


def test_pynput_pointer_delegates_vertical_scroll_without_real_controller() -> None:
    """El adaptador debe traducir scroll vertical sin inicializar pynput."""
    scroll_calls: list[tuple[int, int]] = []

    def record_scroll(_controller: object, horizontal: int, vertical: int) -> None:
        scroll_calls.append((horizontal, vertical))

    controller = type(
        "FakeController",
        (),
        {"scroll": record_scroll},
    )()
    pointer = _PynputPointer.__new__(_PynputPointer)
    pointer._controller = controller

    pointer.scroll(-2)

    assert scroll_calls == [(0, -2)]


def test_pynput_pointer_delegates_left_button_hold_in_order() -> None:
    """El adaptador debe delegar press y release sin eventos reales."""
    button_calls: list[tuple[str, object]] = []

    def record_press(_controller: object, button: object) -> None:
        button_calls.append(("press", button))

    def record_release(_controller: object, button: object) -> None:
        button_calls.append(("release", button))

    controller = type(
        "FakeController",
        (),
        {"press": record_press, "release": record_release},
    )()
    left_button: Any = object()
    pointer = _PynputPointer.__new__(_PynputPointer)
    pointer._controller = controller
    pointer._left_button = left_button

    pointer.press_left()
    pointer.release_left()

    assert button_calls == [("press", left_button), ("release", left_button)]


@pytest.mark.parametrize(
    ("virtual_key", "scan_code", "expected_name"),
    [
        (0x11, None, "CONTROL"),
        (0xA2, None, "CONTROL"),
        (0xA3, None, "CONTROL"),
        (0x12, None, "ALT"),
        (0x4D, None, "M"),
        (0x57, None, "W"),
        (0x41, None, "A"),
        (0x53, None, "S"),
        (0x44, None, "D"),
        (0x45, None, "E"),
        (0x52, None, "R"),
        (0x46, None, "F"),
        (0x47, None, "G"),
        (0x20, None, "SPACE"),
        (0x1B, None, "ESCAPE"),
        (0x51, None, "Q"),
        (0x10, 0x2A, "SHIFT_LEFT"),
        (0x10, 0x36, "SHIFT_RIGHT"),
        (0x10, None, "SHIFT_LEFT"),
        (0xA0, 0x36, "SHIFT_LEFT"),
        (0xA1, 0x2A, "SHIFT_RIGHT"),
    ],
)
def test_scan_codes_map_to_control_keys(
    virtual_key: int,
    scan_code: int | None,
    expected_name: str,
) -> None:
    """Las teclas físicas deben conservar identidad aunque cambie el VK de salida."""
    control_key = control_key_from_vk(virtual_key, scan_code)

    assert control_key is not None
    assert control_key.name == expected_name


def test_generic_shift_with_unknown_scan_code_is_not_guessed() -> None:
    assert control_key_from_vk(0x10, 0x00) is None


def activate_bridge(bridge: KeyboardEventBridge) -> None:
    for virtual_key in (0x11, 0x12, 0x4D):
        bridge.handle_event(virtual_key, key_down=True)
    for virtual_key in (0x11, 0x12, 0x4D):
        bridge.handle_event(virtual_key, key_down=False)


def test_generic_right_shift_keydown_pairs_with_direct_keyup_suppression() -> None:
    runtime = MouseRuntime(pointer=NullPointer())
    bridge = KeyboardEventBridge(runtime)
    activate_bridge(bridge)

    pressed = bridge.handle_event(0x10, key_down=True, scan_code=0x36)
    released = bridge.handle_event(0xA1, key_down=False, scan_code=0x36)
    orphan = bridge.handle_event(0xA1, key_down=False, scan_code=0x36)

    assert pressed.suppress is True
    assert released.suppress is True
    assert orphan.suppress is False


def test_both_generic_shift_keys_keep_fast_mode_until_last_release() -> None:
    pointer = NullPointer()
    runtime = MouseRuntime(pointer=pointer)
    bridge = KeyboardEventBridge(runtime)
    activate_bridge(bridge)
    bridge.handle_event(0x10, key_down=True, scan_code=0x2A)
    bridge.handle_event(0x10, key_down=True, scan_code=0x36)
    bridge.handle_event(0x44, key_down=True)

    bridge.handle_event(0xA0, key_down=False, scan_code=0x2A)
    runtime.tick(0.1)
    bridge.handle_event(0xA1, key_down=False, scan_code=0x36)
    runtime.tick(0.5)

    assert pointer.moves == [(120, 0), (120, 0)]


def test_handle_event_suppresses_q_cycle_and_ignores_repeat() -> None:
    pointer = NullPointer()
    runtime = MouseRuntime(pointer=pointer)
    bridge = KeyboardEventBridge(runtime)
    activate_bridge(bridge)

    first = bridge.handle_event(0x51, key_down=True)
    repeated = bridge.handle_event(0x51, key_down=True)
    released = bridge.handle_event(0x51, key_down=False)

    assert first.suppress is True
    assert repeated.suppress is True
    assert released.suppress is True
    assert pointer.double_clicks == 1


def test_q_keyup_after_activation_does_not_suppress_orphan_release() -> None:
    pointer = NullPointer()
    runtime = MouseRuntime(pointer=pointer)
    bridge = KeyboardEventBridge(runtime)

    outside_press = bridge.handle_event(0x51, key_down=True)
    activate_bridge(bridge)
    orphan_release = bridge.handle_event(0x51, key_down=False)

    assert outside_press.suppress is False
    assert orphan_release.suppress is False
    assert pointer.double_clicks == 0


def test_pynput_pointer_delegates_double_left_click() -> None:
    calls: list[tuple[object, int]] = []
    controller = type(
        "FakeController",
        (),
        {"click": lambda _self, button, count=1: calls.append((button, count))},
    )()
    pointer = _PynputPointer.__new__(_PynputPointer)
    pointer._controller = controller
    pointer._left_button = "left"

    pointer.double_click_left()

    assert calls == [("left", 2)]
