"""Pruebas del estado puro de Mouse for Fools."""

import pytest

from mouse_for_fools.state import MouseModeState


def test_mouse_mode_starts_disabled() -> None:
    """El teclado debe conservar su comportamiento normal al iniciar."""
    state = MouseModeState()

    assert state.active is False


def test_disabling_mouse_mode_clears_held_directions() -> None:
    """Al salir no debe quedar movimiento residual."""
    state = MouseModeState()
    state.enable()
    state.hold_direction("up")
    state.hold_direction("right")

    state.disable()

    assert state.active is False
    assert state.directions == frozenset()


def test_releasing_direction_stops_only_that_axis() -> None:
    """Soltar una tecla no debe borrar las demás direcciones retenidas."""
    state = MouseModeState()
    state.enable()
    state.hold_direction("up")
    state.hold_direction("right")

    state.release_direction("up")

    assert state.directions == frozenset({"right"})


def test_scroll_directions_are_tracked_and_cleared() -> None:
    """Al salir no debe quedar scroll residual."""
    state = MouseModeState()
    state.enable()
    state.hold_scroll("up")
    state.hold_scroll("down")
    assert state.scroll_directions == frozenset({"up", "down"})
    state.disable()
    assert state.scroll_directions == frozenset()


def test_drag_state_is_cleared_when_mode_is_disabled() -> None:
    """Al salir no debe quedar un arrastre activo."""
    state = MouseModeState()
    state.enable()
    state.start_drag()
    state.disable()
    assert state.drag_active is False


def test_drag_state_cannot_be_initialized_externally() -> None:
    """El constructor no debe permitir saltarse las reglas de arrastre."""
    with pytest.raises(TypeError):
        MouseModeState(drag_active=True)


def test_drag_state_cannot_be_assigned_externally() -> None:
    """El estado de arrastre solo debe cambiar mediante su interfaz pública."""
    state = MouseModeState()

    with pytest.raises(AttributeError):
        state.drag_active = True


def test_scroll_and_drag_are_ignored_while_mode_is_inactive() -> None:
    """Las interacciones retenidas no deben activarse fuera de Mouse Mode."""
    state = MouseModeState()

    state.hold_scroll("up")
    state.start_drag()

    assert state.scroll_directions == frozenset()
    assert state.drag_active is False


def test_releasing_scroll_stops_only_that_direction() -> None:
    """Soltar scroll no debe borrar otras direcciones retenidas."""
    state = MouseModeState()
    state.enable()
    state.hold_scroll("up")
    state.hold_scroll("down")

    state.release_scroll("up")

    assert state.scroll_directions == frozenset({"down"})


def test_stopping_drag_deactivates_it() -> None:
    """Detener el arrastre debe desactivar su estado continuo."""
    state = MouseModeState()
    state.enable()
    state.start_drag()

    state.stop_drag()

    assert state.drag_active is False


def test_scroll_direction_snapshot_does_not_change_with_state() -> None:
    """Una instantánea previa debe permanecer inmutable ante cambios futuros."""
    state = MouseModeState()
    state.enable()
    state.hold_scroll("up")
    snapshot = state.scroll_directions

    state.hold_scroll("down")

    assert snapshot == frozenset({"up"})
    assert state.scroll_directions == frozenset({"up", "down"})
