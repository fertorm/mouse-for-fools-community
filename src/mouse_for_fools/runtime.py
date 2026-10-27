"""Orquestación entre entrada abstracta y el controlador del cursor."""

from collections.abc import Callable
from math import isfinite
from threading import RLock
from typing import Protocol

from mouse_for_fools.acceleration import AccelerationProfile
from mouse_for_fools.accumulator import FractionalAccumulator
from mouse_for_fools.input_router import Command, ControlKey, InputRouter, MovementMode
from mouse_for_fools.movement import movement_delta

DEFAULT_ACCELERATION_PROFILE = AccelerationProfile(240.0, 640.0, 1200.0)
DEFAULT_SCROLL_UNITS_PER_SECOND = 6.0
DEFAULT_PRECISION_SPEED = 90.0
DEFAULT_FAST_SPEED = 1200.0
_DEFAULT_TICK_SECONDS = 1.0 / 60.0


class Pointer(Protocol):
    """Contrato mínimo del adaptador de mouse."""

    def click_left(self) -> None:
        """Ejecuta un clic izquierdo."""

    def double_click_left(self) -> None:
        """Ejecuta un doble clic izquierdo."""

    def click_right(self) -> None:
        """Ejecuta un clic derecho."""

    def press_left(self) -> None:
        """Mantiene presionado el botón izquierdo."""

    def release_left(self) -> None:
        """Libera el botón izquierdo."""

    def move(self, delta_x: int, delta_y: int) -> None:
        """Mueve el cursor una distancia relativa."""

    def scroll(self, vertical_units: int) -> None:
        """Desplaza verticalmente una cantidad entera de unidades."""


def _ignore_mode_change(_active: bool) -> None:
    """Implementa el callback nulo por defecto."""


class MouseRuntime:
    """Ejecuta los comandos emitidos por el enrutador de entrada."""

    def __init__(
        self,
        pointer: Pointer,
        acceleration_profile: AccelerationProfile = DEFAULT_ACCELERATION_PROFILE,
        on_mode_changed: Callable[[bool], None] = _ignore_mode_change,
        *,
        scroll_units_per_second: float = DEFAULT_SCROLL_UNITS_PER_SECOND,
        precision_speed: float = DEFAULT_PRECISION_SPEED,
        fast_speed: float = DEFAULT_FAST_SPEED,
    ) -> None:
        self._validate_speed("scroll_units_per_second", scroll_units_per_second)
        self._validate_speed("precision_speed", precision_speed)
        self._validate_speed("fast_speed", fast_speed)
        self._pointer = pointer
        self._router = InputRouter()
        self._lock = RLock()
        self._acceleration_profile = acceleration_profile
        self._scroll_units_per_second = scroll_units_per_second
        self._precision_speed = precision_speed
        self._fast_speed = fast_speed
        self._on_mode_changed = on_mode_changed
        self._horizontal_pixels = FractionalAccumulator()
        self._vertical_pixels = FractionalAccumulator()
        self._scroll_units = FractionalAccumulator()
        self._held_seconds = 0.0
        self._previous_vector = (0.0, 0.0)
        self._previous_scroll_axis = 0
        self._left_button_held = False
        self._closed = False

    @staticmethod
    def _validate_speed(parameter: str, value: float) -> None:
        if not isfinite(value) or value < 0.0:
            raise ValueError(f"{parameter} debe ser finito y no negativo")

    @property
    def active(self) -> bool:
        """Devuelve el estado confirmado del motor."""
        with self._lock:
            return self._router.active

    def set_active(self, active: bool) -> None:
        """Cambia el modo; un motor cerrado no puede volver a activarse.

        Raises:
            RuntimeError: Si se intenta activar después del cierre definitivo.
        """
        with self._lock:
            if self._closed and active:
                raise RuntimeError("El motor esta cerrado")
            try:
                self._execute(self._router.set_active(active))
            finally:
                self._reset_if_stopped()

    def shutdown(self) -> None:
        """Bloquea eventos futuros y libera recursos; permite repetir limpieza."""
        with self._lock:
            self._closed = True
            self.set_active(False)
            self.cleanup()

    def press(self, key: ControlKey) -> bool:
        """Procesa una pulsación e indica si el runtime debe continuar."""
        with self._lock:
            if self._closed:
                return False
            previous_mode = self._router.movement_mode
            commands = self._router.press(key)
            self._reset_on_movement_mode_change(previous_mode)
            keep_running = self._execute(commands)
            self._reset_if_stopped()
            return keep_running

    def release(self, key: ControlKey) -> None:
        """Procesa la liberación de una tecla."""
        with self._lock:
            if self._closed:
                return
            previous_mode = self._router.movement_mode
            commands = self._router.release(key)
            self._reset_on_movement_mode_change(previous_mode)
            self._execute(commands)
            self._reset_if_stopped()

    def cleanup(self) -> None:
        """Libera recursos físicos retenidos de forma idempotente."""
        with self._lock:
            self._stop_drag()

    def _execute(self, commands: tuple[Command, ...]) -> bool:
        keep_running = True
        for command in commands:
            if command is Command.LEFT_CLICK:
                self._pointer.click_left()
            elif command is Command.DOUBLE_LEFT_CLICK:
                self._pointer.double_click_left()
            elif command is Command.RIGHT_CLICK:
                self._pointer.click_right()
            elif command is Command.DRAG_STARTED:
                self._start_drag()
            elif command is Command.DRAG_STOPPED:
                self._stop_drag()
            elif command is Command.MODE_ENABLED:
                self._on_mode_changed(True)
            elif command is Command.MODE_DISABLED:
                self._on_mode_changed(False)
            elif command is Command.SHUTDOWN:
                keep_running = False
        return keep_running

    def _start_drag(self) -> None:
        if not self._left_button_held:
            self._left_button_held = True
            self._pointer.press_left()

    def _stop_drag(self) -> None:
        if self._left_button_held:
            self._pointer.release_left()
            self._left_button_held = False

    def should_suppress(self, key: ControlKey) -> bool:
        """Expone supresión actual; el bridge conserva liberaciones pendientes."""
        with self._lock:
            return not self._closed and self._router.should_suppress(key)

    def tick(self, elapsed_seconds: float = _DEFAULT_TICK_SECONDS) -> None:
        """Aplica el movimiento continuo correspondiente al tiempo transcurrido.

        Raises:
            ValueError: Si el tiempo no es finito o es negativo.
        """
        with self._lock:
            if not isfinite(elapsed_seconds) or elapsed_seconds < 0.0:
                raise ValueError("elapsed_seconds debe ser finito y no negativo")
            if self._closed:
                return
            if elapsed_seconds == 0.0:
                return
            self._apply_movement(elapsed_seconds)
            self._apply_scroll(elapsed_seconds)

    def _apply_scroll(self, elapsed_seconds: float) -> None:
        directions = self._router.scroll_directions
        axis = int("up" in directions) - int("down" in directions)
        if axis == 0:
            self._reset_scroll()
            return
        if self._previous_scroll_axis == -axis:
            self._scroll_units.reset()
        amount = axis * self._scroll_units_per_second * elapsed_seconds
        emitted_units = self._scroll_units.consume(amount)
        if emitted_units != 0:
            self._pointer.scroll(emitted_units)
        self._previous_scroll_axis = axis

    def _apply_movement(self, elapsed_seconds: float) -> None:
        directions = self._router.directions
        current_vector = movement_delta(directions, 1.0)
        if current_vector == (0.0, 0.0):
            self._reset_movement()
            return
        if self._direction_changed(current_vector):
            self._held_seconds = 0.0
            self._reset_pixel_remainders()
        speed = self._speed_for_mode(self._router.movement_mode)
        distance = speed * elapsed_seconds
        delta_x = current_vector[0] * distance
        delta_y = current_vector[1] * distance
        emitted_x = self._horizontal_pixels.consume(delta_x)
        emitted_y = self._vertical_pixels.consume(delta_y)
        if (emitted_x, emitted_y) != (0, 0):
            self._pointer.move(emitted_x, emitted_y)
        self._held_seconds += elapsed_seconds
        self._previous_vector = current_vector

    def _speed_for_mode(self, mode: MovementMode) -> float:
        if mode is MovementMode.PRECISION:
            return self._precision_speed
        if mode is MovementMode.FAST:
            return self._fast_speed
        return self._acceleration_profile.speed(self._held_seconds)

    def _direction_changed(self, current_vector: tuple[float, float]) -> bool:
        if self._previous_vector == (0.0, 0.0):
            return False
        previous_x, previous_y = self._previous_vector
        current_x, current_y = current_vector
        dot_product = previous_x * current_x + previous_y * current_y
        return dot_product <= 0.0

    def _reset_movement(self) -> None:
        self._held_seconds = 0.0
        self._previous_vector = (0.0, 0.0)
        self._reset_pixel_remainders()

    def _reset_on_movement_mode_change(self, previous_mode: MovementMode) -> None:
        if self._router.movement_mode is previous_mode:
            return
        self._held_seconds = 0.0
        self._reset_pixel_remainders()

    def _reset_if_stopped(self) -> None:
        if not self._router.directions:
            self._reset_movement()
        scroll_directions = self._router.scroll_directions
        if int("up" in scroll_directions) - int("down" in scroll_directions) == 0:
            self._reset_scroll()

    def _reset_pixel_remainders(self) -> None:
        self._horizontal_pixels.reset()
        self._vertical_pixels.reset()

    def _reset_scroll(self) -> None:
        self._scroll_units.reset()
        self._previous_scroll_axis = 0
