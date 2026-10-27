"""Pruebas del enrutamiento de teclas a comandos del mouse."""

import pytest

from mouse_for_fools.input_router import (
    Command,
    ControlKey,
    InputRouter,
    MovementMode,
)


def test_external_mode_change_is_idempotent() -> None:
    """Un estado deseado repetido no genera comandos duplicados."""
    router = InputRouter()
    assert router.set_active(False) == ()
    assert router.set_active(True) == (Command.MODE_ENABLED,)
    assert router.active is True
    assert router.set_active(True) == ()
    assert router.set_active(False) == (Command.MODE_DISABLED,)
    assert router.active is False
    assert router.set_active(False) == ()


def test_external_disable_cancels_drag_movement_and_scroll() -> None:
    """Desactivar desde la UI cancela las mismas acciones que Esc."""
    router = InputRouter()
    router.set_active(True)
    router.press(ControlKey.D)
    router.press(ControlKey.R)
    router.press(ControlKey.G)
    assert router.set_active(False) == (Command.DRAG_STOPPED, Command.MODE_DISABLED)
    assert router.directions == frozenset()
    assert router.scroll_directions == frozenset()
    assert router.release(ControlKey.G) == ()


def test_external_enable_does_not_invent_held_movement() -> None:
    """Una dirección pulsada desactivado no comienza a mover al activar."""
    router = InputRouter()
    router.press(ControlKey.D)
    router.set_active(True)
    assert router.directions == frozenset()
    assert router.press(ControlKey.D) == ()
    assert router.directions == frozenset()
    router.release(ControlKey.D)
    router.press(ControlKey.D)
    assert router.directions == frozenset({"right"})


def active_router() -> InputRouter:
    """Crea un router activo sin dejar retenido el acorde de activación."""
    router = InputRouter()
    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)
    router.press(ControlKey.M)
    router.release(ControlKey.CONTROL)
    router.release(ControlKey.ALT)
    router.release(ControlKey.M)
    return router


def test_control_enables_precision_movement() -> None:
    """Control debe seleccionar el movimiento preciso mientras está presionado."""
    router = InputRouter()

    router.press(ControlKey.CONTROL)

    assert router.movement_mode is MovementMode.PRECISION


@pytest.mark.parametrize("shift_key", [ControlKey.SHIFT_LEFT, ControlKey.SHIFT_RIGHT])
def test_shift_enables_fast_movement(shift_key: ControlKey) -> None:
    """Cualquier tecla Shift debe seleccionar el movimiento rápido."""
    router = InputRouter()

    router.press(shift_key)

    assert router.movement_mode is MovementMode.FAST


@pytest.mark.parametrize(
    "key",
    [ControlKey.CONTROL, ControlKey.SHIFT_LEFT, ControlKey.SHIFT_RIGHT],
)
def test_releasing_modifier_restores_normal_movement(key: ControlKey) -> None:
    """Soltar el único modificador debe restaurar el movimiento normal."""
    router = InputRouter()
    router.press(key)

    router.release(key)

    assert router.movement_mode is MovementMode.NORMAL


def test_control_has_priority_over_shift_for_movement() -> None:
    """Control debe priorizar precisión y devolver el control al Shift retenido."""
    router = InputRouter()
    router.press(ControlKey.SHIFT_LEFT)

    router.press(ControlKey.CONTROL)

    assert router.movement_mode is MovementMode.PRECISION
    router.release(ControlKey.CONTROL)
    assert router.movement_mode is MovementMode.FAST
    router.release(ControlKey.SHIFT_LEFT)
    assert router.movement_mode is MovementMode.NORMAL


def test_fast_movement_remains_until_both_shift_keys_are_released() -> None:
    """Soltar un Shift no debe cancelar el otro Shift todavía retenido."""
    router = InputRouter()
    router.press(ControlKey.SHIFT_LEFT)
    router.press(ControlKey.SHIFT_RIGHT)

    router.release(ControlKey.SHIFT_LEFT)

    assert router.movement_mode is MovementMode.FAST
    router.release(ControlKey.SHIFT_RIGHT)
    assert router.movement_mode is MovementMode.NORMAL


def test_activation_chord_toggles_mode_once_per_press() -> None:
    """El auto-repeat de M no debe alternar el modo repetidamente."""
    router = InputRouter()
    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)

    first_result = router.press(ControlKey.M)
    repeated_result = router.press(ControlKey.M)

    assert first_result == (Command.MODE_ENABLED,)
    assert repeated_result == ()
    assert router.active is True


def test_held_space_generates_only_one_left_click() -> None:
    """El auto-repeat de Space no debe producir clics accidentales."""
    router = InputRouter()
    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)
    router.press(ControlKey.M)

    first_result = router.press(ControlKey.SPACE)
    repeated_result = router.press(ControlKey.SPACE)
    router.release(ControlKey.SPACE)
    next_result = router.press(ControlKey.SPACE)

    assert first_result == (Command.LEFT_CLICK,)
    assert repeated_result == ()
    assert next_result == (Command.LEFT_CLICK,)


def test_q_generates_one_double_left_click_while_active() -> None:
    """Q debe generar un doble clic izquierdo al pulsarse en Mouse Mode."""
    key = getattr(ControlKey, "Q", None)
    command = getattr(Command, "DOUBLE_LEFT_CLICK", None)
    assert key is not None, "ControlKey.Q todavía no está implementada"
    assert command is not None, "DOUBLE_LEFT_CLICK todavía no está implementado"
    router = active_router()

    result = router.press(key)

    assert result == (command,)


def test_held_q_does_not_repeat_double_left_click() -> None:
    """El auto-repeat de Q no debe producir dobles clics adicionales."""
    key = getattr(ControlKey, "Q", None)
    assert key is not None, "ControlKey.Q todavía no está implementada"
    router = active_router()
    router.press(key)

    repeated_result = router.press(key)

    assert repeated_result == ()


def test_q_can_double_click_again_after_keyup() -> None:
    """Una nueva pulsación física de Q debe generar otro doble clic."""
    key = getattr(ControlKey, "Q", None)
    command = getattr(Command, "DOUBLE_LEFT_CLICK", None)
    assert key is not None, "ControlKey.Q todavía no está implementada"
    assert command is not None, "DOUBLE_LEFT_CLICK todavía no está implementado"
    router = active_router()
    router.press(key)

    router.release(key)
    next_result = router.press(key)

    assert next_result == (command,)


def test_q_outside_mouse_mode_does_nothing() -> None:
    """Q debe conservar su comportamiento normal fuera de Mouse Mode."""
    key = getattr(ControlKey, "Q", None)
    assert key is not None, "ControlKey.Q todavía no está implementada"
    router = InputRouter()

    result = router.press(key)

    assert result == ()


def test_direction_is_tracked_only_while_mode_is_active() -> None:
    """W no debe mover ni quedar retenida fuera de Mouse Mode."""
    router = InputRouter()

    router.press(ControlKey.W)
    router.release(ControlKey.W)
    assert router.directions == frozenset()

    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)
    router.press(ControlKey.M)
    router.release(ControlKey.W)
    router.press(ControlKey.W)
    assert router.directions == frozenset({"up"})

    router.release(ControlKey.W)
    assert router.directions == frozenset()


@pytest.mark.parametrize(
    ("key_name", "direction"),
    [
        ("W", "up"),
        ("A", "left"),
        ("S", "down"),
        ("D", "right"),
    ],
)
def test_wasd_maps_to_expected_direction(key_name: str, direction: str) -> None:
    """Cada tecla de movimiento debe representar un único eje."""
    key = getattr(ControlKey, key_name, None)
    assert key is not None, f"ControlKey.{key_name} todavía no está implementada"
    router = InputRouter()
    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)
    router.press(ControlKey.M)

    router.press(key)

    assert router.directions == frozenset({direction})


@pytest.mark.parametrize(
    ("key_name", "direction"),
    [
        ("R", "up"),
        ("F", "down"),
    ],
)
def test_scroll_keys_are_tracked_while_held(key_name: str, direction: str) -> None:
    """R y F deben mantener su dirección de scroll hasta ser liberadas."""
    key = getattr(ControlKey, key_name, None)
    assert key is not None, f"ControlKey.{key_name} todavía no está implementada"
    router = active_router()

    pressed = router.press(key)

    assert pressed == ()
    assert router.scroll_directions == frozenset({direction})
    assert router.release(key) == ()
    assert router.scroll_directions == frozenset()


def test_e_generates_one_right_click_while_active() -> None:
    """E debe generar un clic derecho sin repetición automática."""
    assert hasattr(ControlKey, "E"), "ControlKey.E todavía no está implementada"
    assert hasattr(Command, "RIGHT_CLICK"), "RIGHT_CLICK todavía no está implementado"
    router = InputRouter()
    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)
    router.press(ControlKey.M)

    first_result = router.press(ControlKey.E)
    repeated_result = router.press(ControlKey.E)

    assert first_result == (Command.RIGHT_CLICK,)
    assert repeated_result == ()


def test_g_emits_one_drag_start_and_one_drag_stop() -> None:
    """G inicia y detiene un único arrastre por pulsación física."""
    key = getattr(ControlKey, "G", None)
    drag_started = getattr(Command, "DRAG_STARTED", None)
    drag_stopped = getattr(Command, "DRAG_STOPPED", None)
    assert key is not None, "ControlKey.G todavía no está implementada"
    assert drag_started is not None, "DRAG_STARTED todavía no está implementado"
    assert drag_stopped is not None, "DRAG_STOPPED todavía no está implementado"
    router = active_router()

    first = router.press(key)
    repeated = router.press(key)
    released = router.release(key)

    assert first == (drag_started,)
    assert repeated == ()
    assert released == (drag_stopped,)


def test_escape_disables_mode_and_clears_movement() -> None:
    """Escape debe devolver inmediatamente el control al teclado normal."""
    assert hasattr(ControlKey, "ESCAPE"), "ControlKey.ESCAPE todavía no está implementada"
    router = InputRouter()
    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)
    router.press(ControlKey.M)
    router.release(ControlKey.CONTROL)
    router.release(ControlKey.ALT)
    router.release(ControlKey.M)
    router.press(ControlKey.W)

    result = router.press(ControlKey.ESCAPE)

    assert result == (Command.MODE_DISABLED,)
    assert router.active is False
    assert router.directions == frozenset()


def test_escape_forces_drag_stop_before_disabling() -> None:
    """Escape libera el botón antes de desactivar Mouse Mode."""
    router = active_router()
    router.press(ControlKey.G)

    result = router.press(ControlKey.ESCAPE)

    assert result == (Command.DRAG_STOPPED, Command.MODE_DISABLED)
    assert router.active is False


def test_forced_drag_does_not_resume_after_reactivation() -> None:
    """G retenida no reinicia drag hasta liberarse y pulsarse otra vez."""
    router = active_router()
    router.press(ControlKey.G)
    router.press(ControlKey.ESCAPE)
    router.release(ControlKey.ESCAPE)
    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)
    router.press(ControlKey.M)
    router.release(ControlKey.CONTROL)
    router.release(ControlKey.ALT)
    router.release(ControlKey.M)

    while_still_held = router.press(ControlKey.G)
    released = router.release(ControlKey.G)
    pressed_again = router.press(ControlKey.G)

    assert while_still_held == ()
    assert released == ()
    assert pressed_again == (Command.DRAG_STARTED,)


def test_toggle_off_forces_drag_stop_before_disabling() -> None:
    """El acorde de toggle libera el drag antes de apagar el modo."""
    router = active_router()
    router.press(ControlKey.G)
    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)

    result = router.press(ControlKey.M)

    assert result == (Command.DRAG_STOPPED, Command.MODE_DISABLED)
    assert router.active is False


@pytest.mark.parametrize("active", [False, True])
def test_emergency_chord_requests_shutdown_from_any_state(active: bool) -> None:
    """El cierre de emergencia no debe depender del estado del modo."""
    assert hasattr(Command, "SHUTDOWN"), "SHUTDOWN todavía no está implementado"
    router = InputRouter()
    if active:
        router.press(ControlKey.CONTROL)
        router.press(ControlKey.ALT)
        router.press(ControlKey.M)
        router.release(ControlKey.CONTROL)
        router.release(ControlKey.ALT)
        router.release(ControlKey.M)

    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)
    result = router.press(ControlKey.ESCAPE)

    assert result == (Command.SHUTDOWN,)
    assert router.active is False
    assert router.directions == frozenset()


def test_shutdown_forces_drag_stop_before_closing() -> None:
    """El cierre de emergencia libera el drag antes de finalizar."""
    router = active_router()
    router.press(ControlKey.G)
    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)

    result = router.press(ControlKey.ESCAPE)

    assert result == (Command.DRAG_STOPPED, Command.SHUTDOWN)
    assert router.active is False


def test_controlled_keys_are_suppressed_only_in_mouse_mode() -> None:
    """Fuera del modo, las teclas deben conservar su comportamiento normal."""
    router = InputRouter()
    assert router.should_suppress(ControlKey.W) is False

    router.press(ControlKey.CONTROL)
    router.press(ControlKey.ALT)
    router.press(ControlKey.M)

    for key in ControlKey:
        assert router.should_suppress(key) is True
