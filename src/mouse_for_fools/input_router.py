"""Traducción de teclas abstractas a acciones de Mouse for Fools."""

from enum import StrEnum
from threading import RLock

from mouse_for_fools.state import Direction, MouseModeState, ScrollDirection


class MovementMode(StrEnum):
    """Velocidad de movimiento seleccionada por los modificadores."""

    NORMAL = "normal"
    PRECISION = "precision"
    FAST = "fast"


class ControlKey(StrEnum):
    """Teclas relevantes para el experimento."""

    CONTROL = "control"
    SHIFT_LEFT = "shift_left"
    SHIFT_RIGHT = "shift_right"
    ALT = "alt"
    M = "m"
    SPACE = "space"
    Q = "q"
    W = "w"
    A = "a"
    S = "s"
    D = "d"
    R = "r"
    F = "f"
    G = "g"
    E = "e"
    ESCAPE = "escape"


_DIRECTION_KEYS: dict[ControlKey, Direction] = {
    ControlKey.W: "up",
    ControlKey.A: "left",
    ControlKey.S: "down",
    ControlKey.D: "right",
}

_SCROLL_KEYS: dict[ControlKey, ScrollDirection] = {
    ControlKey.R: "up",
    ControlKey.F: "down",
}

_SHIFT_KEYS = frozenset({ControlKey.SHIFT_LEFT, ControlKey.SHIFT_RIGHT})


class Command(StrEnum):
    """Acciones discretas generadas por el teclado."""

    MODE_ENABLED = "mode_enabled"
    MODE_DISABLED = "mode_disabled"
    LEFT_CLICK = "left_click"
    DOUBLE_LEFT_CLICK = "double_left_click"
    RIGHT_CLICK = "right_click"
    DRAG_STARTED = "drag_started"
    DRAG_STOPPED = "drag_stopped"
    SHUTDOWN = "shutdown"


class InputRouter:
    """Mantiene las teclas presionadas y evita eventos repetidos."""

    def __init__(self) -> None:
        self._state = MouseModeState()
        self._pressed: set[ControlKey] = set()
        self._lock = RLock()

    @property
    def active(self) -> bool:
        """Indica si Mouse Mode está activo."""
        with self._lock:
            return self._state.active

    @property
    def directions(self) -> frozenset[Direction]:
        """Devuelve las direcciones activas de forma segura."""
        with self._lock:
            return self._state.directions

    @property
    def scroll_directions(self) -> frozenset[ScrollDirection]:
        """Devuelve las direcciones activas de scroll de forma segura."""
        with self._lock:
            return self._state.scroll_directions

    @property
    def movement_mode(self) -> MovementMode:
        """Devuelve el modo de movimiento seleccionado por los modificadores."""
        with self._lock:
            if ControlKey.CONTROL in self._pressed:
                return MovementMode.PRECISION
            if not self._pressed.isdisjoint(_SHIFT_KEYS):
                return MovementMode.FAST
            return MovementMode.NORMAL

    def set_active(self, active: bool) -> tuple[Command, ...]:
        """Solicita un estado sin simular teclas y devuelve efectos de transición."""
        with self._lock:
            if active == self._state.active:
                return ()
            if not active:
                return self._deactivate(Command.MODE_DISABLED)
            self._state.enable()
            return (Command.MODE_ENABLED,)

    def should_suppress(self, key: ControlKey) -> bool:
        """Indica si Windows debe ocultar la tecla a la aplicación enfocada."""
        with self._lock:
            if self._state.active:
                return True
            return key in {ControlKey.M, ControlKey.ESCAPE} and (
                self._activation_modifiers_pressed()
            )

    def press(self, key: ControlKey) -> tuple[Command, ...]:
        """Procesa una pulsación nueva y devuelve sus comandos."""
        with self._lock:
            if key in self._pressed:
                return ()
            self._pressed.add(key)
            if key is ControlKey.M and self._activation_modifiers_pressed():
                if self._state.active:
                    return self._deactivate(Command.MODE_DISABLED)
                self._state.enable()
                return (Command.MODE_ENABLED,)
            if key is ControlKey.ESCAPE and self._activation_modifiers_pressed():
                return self._deactivate(Command.SHUTDOWN)
            if key is ControlKey.ESCAPE and self._state.active:
                return self._deactivate(Command.MODE_DISABLED)
            if self._state.active and key is ControlKey.SPACE:
                return (Command.LEFT_CLICK,)
            if self._state.active and key is ControlKey.Q:
                return (Command.DOUBLE_LEFT_CLICK,)
            if self._state.active and key is ControlKey.E:
                return (Command.RIGHT_CLICK,)
            if self._state.active and key is ControlKey.G:
                self._state.start_drag()
                return (Command.DRAG_STARTED,)
            direction = _DIRECTION_KEYS.get(key)
            if direction is not None:
                self._state.hold_direction(direction)
            scroll_direction = _SCROLL_KEYS.get(key)
            if scroll_direction is not None:
                self._state.hold_scroll(scroll_direction)
            return ()

    def release(self, key: ControlKey) -> tuple[Command, ...]:
        """Procesa la liberación de una tecla y devuelve sus comandos."""
        with self._lock:
            self._pressed.discard(key)
            if key is ControlKey.G and self._state.drag_active:
                self._state.stop_drag()
                return (Command.DRAG_STOPPED,)
            direction = _DIRECTION_KEYS.get(key)
            if direction is not None:
                self._state.release_direction(direction)
            scroll_direction = _SCROLL_KEYS.get(key)
            if scroll_direction is not None:
                self._state.release_scroll(scroll_direction)
            return ()

    def _activation_modifiers_pressed(self) -> bool:
        return {ControlKey.CONTROL, ControlKey.ALT}.issubset(self._pressed)

    def _deactivate(self, final_command: Command) -> tuple[Command, ...]:
        commands: tuple[Command, ...] = ()
        if self._state.drag_active:
            self._state.stop_drag()
            commands = (Command.DRAG_STOPPED,)
        self._state.disable()
        return (*commands, final_command)
