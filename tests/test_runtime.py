"""Pruebas de orquestación sin instalar hooks globales."""

from dataclasses import dataclass, field

import pytest

from mouse_for_fools.acceleration import AccelerationProfile
from mouse_for_fools.input_router import ControlKey, InputRouter
from mouse_for_fools.runtime import MouseRuntime
from mouse_for_fools.state import Direction

_DIAGONAL_PIXEL_TOLERANCE = 1.5  # Dos ejes truncados acumulan menos de sqrt(2) px.


@dataclass
class RecordingPointer:
    """Adaptador de prueba que registra acciones solicitadas."""

    clicks: list[str] = field(default_factory=list)
    button_events: list[str] = field(default_factory=list)
    moves: list[tuple[int, int]] = field(default_factory=list)
    scrolls: list[int] = field(default_factory=list)

    def click_left(self) -> None:
        self.clicks.append("left")

    def double_click_left(self) -> None:
        self.clicks.append("double_left")

    def click_right(self) -> None:
        self.clicks.append("right")

    def press_left(self) -> None:
        self.button_events.append("down")

    def release_left(self) -> None:
        self.button_events.append("up")

    def move(self, delta_x: int, delta_y: int) -> None:
        self.moves.append((delta_x, delta_y))

    def scroll(self, vertical_units: int) -> None:
        self.scrolls.append(vertical_units)


class PartiallyFailingPointer(RecordingPointer):
    """Simula un backend que falla después de presionar físicamente."""

    def press_left(self) -> None:
        super().press_left()
        raise RuntimeError("fallo despues de presionar")


def activate(runtime: MouseRuntime) -> None:
    """Activa Mouse Mode mediante el acorde público."""
    runtime.press(ControlKey.CONTROL)
    runtime.press(ControlKey.ALT)
    runtime.press(ControlKey.M)
    runtime.release(ControlKey.CONTROL)
    runtime.release(ControlKey.ALT)
    runtime.release(ControlKey.M)


def moving_runtime(key: ControlKey) -> tuple[MouseRuntime, RecordingPointer]:
    """Crea un runtime activo con una dirección retenida."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    activate(runtime)
    runtime.press(key)
    return runtime, pointer


def test_runtime_dispatches_click_command_to_pointer() -> None:
    """Una acción discreta debe llegar una sola vez al adaptador del mouse."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    runtime.press(ControlKey.CONTROL)
    runtime.press(ControlKey.ALT)
    runtime.press(ControlKey.M)

    runtime.press(ControlKey.SPACE)

    assert pointer.clicks == ["left"]


def test_runtime_dispatches_one_double_click_for_repeated_q_keydown() -> None:
    """Q retenida debe ejecutar exactamente un doble clic en el adaptador."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    activate(runtime)

    runtime.press(ControlKey.Q)
    runtime.press(ControlKey.Q)

    assert pointer.clicks == ["double_left"]


def test_drag_holds_button_until_g_is_released() -> None:
    """G debe mantener el botón izquierdo sin repetir eventos físicos."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    activate(runtime)

    runtime.press(ControlKey.G)
    runtime.press(ControlKey.G)
    runtime.release(ControlKey.G)

    assert pointer.button_events == ["down", "up"]


def test_drag_allows_movement_while_button_remains_held() -> None:
    """WASD debe mover durante el drag sin liberar el botón prematuramente."""
    pointer = RecordingPointer()
    constant_profile = AccelerationProfile(12.0, 0.0, 12.0)
    runtime = MouseRuntime(pointer=pointer, acceleration_profile=constant_profile)
    activate(runtime)

    runtime.press(ControlKey.G)
    runtime.press(ControlKey.D)
    runtime.tick(1.0)

    assert pointer.moves == [(12, 0)]
    assert pointer.button_events == ["down"]

    runtime.release(ControlKey.G)
    assert pointer.button_events == ["down", "up"]


def test_escape_releases_active_drag_once() -> None:
    """Escape debe liberar el drag antes de desactivar Mouse Mode."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    activate(runtime)
    runtime.release(ControlKey.CONTROL)
    runtime.release(ControlKey.ALT)
    runtime.release(ControlKey.M)
    runtime.press(ControlKey.G)

    keep_running = runtime.press(ControlKey.ESCAPE)
    runtime.release(ControlKey.G)

    assert keep_running is True
    assert pointer.button_events == ["down", "up"]


def test_toggle_off_releases_drag_before_notifying_mode_change() -> None:
    """El callback OFF debe observar el botón izquierdo ya liberado."""
    events: list[str] = []
    pointer = RecordingPointer(button_events=events)
    runtime = MouseRuntime(
        pointer=pointer,
        on_mode_changed=lambda active: events.append("on" if active else "off"),
    )
    activate(runtime)
    runtime.release(ControlKey.CONTROL)
    runtime.release(ControlKey.ALT)
    runtime.release(ControlKey.M)
    events.clear()
    runtime.press(ControlKey.G)
    runtime.press(ControlKey.CONTROL)
    runtime.press(ControlKey.ALT)

    runtime.press(ControlKey.M)

    assert events == ["down", "up", "off"]


def test_emergency_chord_releases_drag_and_requests_stop() -> None:
    """Ctrl+Alt+Escape debe liberar el drag antes de cerrar el runtime."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    activate(runtime)
    runtime.release(ControlKey.CONTROL)
    runtime.release(ControlKey.ALT)
    runtime.release(ControlKey.M)
    runtime.press(ControlKey.G)
    runtime.press(ControlKey.CONTROL)
    runtime.press(ControlKey.ALT)

    keep_running = runtime.press(ControlKey.ESCAPE)

    assert keep_running is False
    assert pointer.button_events == ["down", "up"]


def test_cleanup_releases_drag_only_once() -> None:
    """La limpieza repetida debe ser segura ante rutas de cierre duplicadas."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    activate(runtime)
    runtime.press(ControlKey.G)

    runtime.cleanup()
    runtime.cleanup()

    assert pointer.button_events == ["down", "up"]


def test_cleanup_releases_button_after_partial_drag_start_failure() -> None:
    """La limpieza debe compensar un press físico que termina con error."""
    pointer = PartiallyFailingPointer()
    runtime = MouseRuntime(pointer=pointer)
    activate(runtime)

    with pytest.raises(RuntimeError, match="fallo despues de presionar"):
        runtime.press(ControlKey.G)

    runtime.cleanup()

    assert pointer.button_events == ["down", "up"]


def test_held_g_does_not_restart_drag_after_forced_release() -> None:
    """Reactivar con G retenida exige una liberación y nueva pulsación física."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    activate(runtime)
    runtime.release(ControlKey.CONTROL)
    runtime.release(ControlKey.ALT)
    runtime.release(ControlKey.M)
    runtime.press(ControlKey.G)
    runtime.press(ControlKey.ESCAPE)
    runtime.release(ControlKey.ESCAPE)
    activate(runtime)
    runtime.release(ControlKey.CONTROL)
    runtime.release(ControlKey.ALT)
    runtime.release(ControlKey.M)

    runtime.press(ControlKey.G)
    assert pointer.button_events == ["down", "up"]

    runtime.release(ControlKey.G)
    runtime.press(ControlKey.G)

    assert pointer.button_events == ["down", "up", "down"]


def test_runtime_moves_pointer_on_each_tick_while_direction_is_held() -> None:
    """El movimiento continuo debe ejecutarse fuera del callback del hook."""
    pointer = RecordingPointer()
    constant_profile = AccelerationProfile(12.0, 0.0, 12.0)
    runtime = MouseRuntime(pointer=pointer, acceleration_profile=constant_profile)
    activate(runtime)
    runtime.press(ControlKey.W)

    runtime.tick(1.0)

    assert pointer.moves == [(0, -12)]


@pytest.mark.parametrize(
    ("key", "expected_scroll"),
    [(ControlKey.R, 1), (ControlKey.F, -1)],
)
def test_runtime_scrolls_continuously_while_direction_is_held(
    key: ControlKey,
    expected_scroll: int,
) -> None:
    """R y F deben emitir scroll vertical acumulado en cada sentido."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer, scroll_units_per_second=6.0)
    activate(runtime)
    runtime.press(key)

    for _ in range(10):
        runtime.tick(1.0 / 60.0)

    assert pointer.scrolls == [expected_scroll]


def test_opposite_scroll_directions_cancel_each_other() -> None:
    """R y F simultáneas no deben producir desplazamiento vertical."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer, scroll_units_per_second=6.0)
    activate(runtime)
    runtime.press(ControlKey.R)
    runtime.press(ControlKey.F)

    runtime.tick(1.0)

    assert pointer.scrolls == []


def test_fractional_scroll_accumulates_and_release_stops_emission() -> None:
    """Ticks parciales deben acumularse y la liberación detener el scroll."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer, scroll_units_per_second=4.0)
    activate(runtime)
    runtime.press(ControlKey.R)

    runtime.tick(0.125)
    runtime.tick(0.125)
    runtime.release(ControlKey.R)
    runtime.tick(1.0)

    assert pointer.scrolls == [1]


def test_mode_deactivation_clears_scroll_state_and_remainder() -> None:
    """Un ciclo de modo debe descartar tanto dirección como residuo de scroll."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer, scroll_units_per_second=2.0)
    activate(runtime)
    runtime.press(ControlKey.R)
    runtime.tick(0.4)

    runtime.release(ControlKey.M)
    runtime.press(ControlKey.M)
    runtime.release(ControlKey.R)
    runtime.release(ControlKey.M)
    runtime.press(ControlKey.M)
    runtime.press(ControlKey.R)
    runtime.tick(0.1)

    assert pointer.scrolls == []


def test_scroll_reversal_does_not_inherit_opposite_remainder() -> None:
    """Invertir R por F entre ticks debe responder sin arrastrar residuo positivo."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer, scroll_units_per_second=6.0)
    activate(runtime)
    runtime.press(ControlKey.R)
    runtime.tick(0.15)

    runtime.press(ControlKey.F)
    runtime.release(ControlKey.R)
    runtime.tick(1.0 / 6.0)

    assert pointer.scrolls == [-1]


@pytest.mark.parametrize(
    "scroll_units_per_second",
    [-0.1, float("inf"), float("-inf"), float("nan")],
)
def test_runtime_rejects_invalid_scroll_rate(scroll_units_per_second: float) -> None:
    """La velocidad de scroll debe ser finita y no negativa."""
    with pytest.raises(ValueError, match="scroll_units_per_second"):
        MouseRuntime(
            pointer=RecordingPointer(),
            scroll_units_per_second=scroll_units_per_second,
        )


def test_runtime_stops_moving_after_direction_release() -> None:
    """La liberación de la tecla debe detener el siguiente ciclo."""
    pointer = RecordingPointer()
    constant_profile = AccelerationProfile(12.0, 0.0, 12.0)
    runtime = MouseRuntime(pointer=pointer, acceleration_profile=constant_profile)
    activate(runtime)
    runtime.press(ControlKey.D)
    runtime.tick(1.0)

    runtime.release(ControlKey.D)
    runtime.tick(1.0)

    assert pointer.moves == [(12, 0)]


def test_runtime_accelerates_held_direction() -> None:
    """Mantener una dirección debe incrementar la distancia de cada tick."""
    runtime, pointer = moving_runtime(ControlKey.D)

    runtime.tick(0.5)
    runtime.tick(0.5)

    assert pointer.moves == [(120, 0), (280, 0)]


def test_control_uses_fixed_precision_speed() -> None:
    """Control debe mover exactamente a la velocidad fija de precisión."""
    runtime, pointer = moving_runtime(ControlKey.D)
    runtime.press(ControlKey.CONTROL)

    runtime.tick(1.0)

    assert pointer.moves == [(90, 0)]


@pytest.mark.parametrize("shift_key", [ControlKey.SHIFT_LEFT, ControlKey.SHIFT_RIGHT])
def test_either_shift_uses_fixed_fast_speed(shift_key: ControlKey) -> None:
    """Cualquier Shift debe mover exactamente a la velocidad fija rápida."""
    runtime, pointer = moving_runtime(ControlKey.D)
    runtime.press(shift_key)

    runtime.tick(1.0)

    assert pointer.moves == [(1200, 0)]


def test_control_has_priority_over_shift_for_movement_speed() -> None:
    """Control debe conservar prioridad cuando Shift también está retenido."""
    runtime, pointer = moving_runtime(ControlKey.D)
    runtime.press(ControlKey.SHIFT_LEFT)
    runtime.press(ControlKey.CONTROL)

    runtime.tick(1.0)

    assert pointer.moves == [(90, 0)]


def test_normal_to_precision_discards_fractional_pixel_remainder() -> None:
    """Cambiar de modo no debe heredar residuos subpíxel del modo anterior."""
    pointer = RecordingPointer()
    fractional_profile = AccelerationProfile(1.0, 0.0, 1.0)
    runtime = MouseRuntime(pointer=pointer, acceleration_profile=fractional_profile)
    activate(runtime)
    runtime.press(ControlKey.D)
    runtime.tick(0.5)

    runtime.press(ControlKey.CONTROL)
    runtime.tick(1.0 / 180.0)

    assert pointer.moves == []


def test_modifier_cycle_between_ticks_resets_normal_acceleration() -> None:
    """Una transición completa entre ticks debe reiniciar el tiempo retenido."""
    runtime, pointer = moving_runtime(ControlKey.D)
    runtime.tick(0.5)
    runtime.tick(0.5)

    runtime.press(ControlKey.CONTROL)
    runtime.release(ControlKey.CONTROL)
    runtime.tick(0.5)

    assert pointer.moves == [(120, 0), (280, 0), (120, 0)]


@pytest.mark.parametrize("parameter", ["precision_speed", "fast_speed"])
@pytest.mark.parametrize("invalid_speed", [float("nan"), float("inf"), -1.0])
def test_runtime_rejects_invalid_fixed_speed(
    parameter: str,
    invalid_speed: float,
) -> None:
    """Cada velocidad fija debe ser finita y no negativa."""
    with pytest.raises(ValueError, match=parameter):
        MouseRuntime(pointer=RecordingPointer(), **{parameter: invalid_speed})


def test_acceleration_resets_after_direction_stops() -> None:
    """Soltar el movimiento debe iniciar desde la velocidad base al reanudar."""
    runtime, pointer = moving_runtime(ControlKey.D)
    runtime.tick(0.5)
    runtime.release(ControlKey.D)
    runtime.tick(0.5)
    runtime.press(ControlKey.D)
    runtime.tick(0.5)

    assert pointer.moves[-1] == (120, 0)


def test_release_and_repress_before_tick_resets_acceleration() -> None:
    """Un gap de tecla debe reiniciar aunque no haya un tick sin dirección."""
    runtime, pointer = moving_runtime(ControlKey.D)
    runtime.tick(0.5)
    runtime.release(ControlKey.D)
    runtime.press(ControlKey.D)

    runtime.tick(0.5)

    assert pointer.moves[-1] == (120, 0)


def test_mode_cycle_before_tick_resets_acceleration() -> None:
    """Desactivar y reactivar debe descartar la duración previa inmediatamente."""
    runtime, pointer = moving_runtime(ControlKey.D)
    runtime.tick(0.5)
    runtime.release(ControlKey.M)
    runtime.press(ControlKey.M)
    runtime.release(ControlKey.D)
    runtime.release(ControlKey.M)
    runtime.press(ControlKey.M)
    runtime.press(ControlKey.D)

    runtime.tick(0.5)

    assert pointer.moves[-1] == (120, 0)


def test_opposite_direction_resets_acceleration() -> None:
    """Invertir el eje debe reiniciar la aceleración sin un tick neutro."""
    runtime, pointer = moving_runtime(ControlKey.D)
    runtime.tick(0.5)
    runtime.press(ControlKey.A)
    runtime.release(ControlKey.D)

    runtime.tick(0.5)

    assert pointer.moves[-1] == (-120, 0)


def test_compatible_diagonal_preserves_acceleration() -> None:
    """Agregar un eje compatible debe conservar la velocidad acumulada."""
    runtime, pointer = moving_runtime(ControlKey.W)
    runtime.tick(0.5)
    runtime.press(ControlKey.D)
    runtime.tick(0.5)

    delta_x, delta_y = pointer.moves[-1]
    assert (delta_x**2 + delta_y**2) ** 0.5 == pytest.approx(
        280.0, abs=_DIAGONAL_PIXEL_TOLERANCE
    )


def test_removing_compatible_axis_preserves_acceleration() -> None:
    """Retirar un eje compatible debe conservar la velocidad acumulada."""
    runtime, pointer = moving_runtime(ControlKey.W)
    runtime.press(ControlKey.D)
    runtime.tick(0.5)
    runtime.release(ControlKey.D)

    runtime.tick(0.5)

    assert pointer.moves[-1] == (0, -280)


def test_diagonal_movement_matches_straight_magnitude() -> None:
    """Mover dos ejes no debe aumentar la distancia respecto de un eje."""
    straight_runtime, straight_pointer = moving_runtime(ControlKey.D)
    diagonal_runtime, diagonal_pointer = moving_runtime(ControlKey.W)
    diagonal_runtime.press(ControlKey.D)

    straight_runtime.tick(0.5)
    diagonal_runtime.tick(0.5)

    straight_x, straight_y = straight_pointer.moves[-1]
    diagonal_x, diagonal_y = diagonal_pointer.moves[-1]
    straight_distance = (straight_x**2 + straight_y**2) ** 0.5
    diagonal_distance = (diagonal_x**2 + diagonal_y**2) ** 0.5
    assert diagonal_distance == pytest.approx(straight_distance, abs=_DIAGONAL_PIXEL_TOLERANCE)


def test_tick_uses_one_direction_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Continuidad y desplazamiento deben usar el mismo snapshot de direcciones."""
    runtime, pointer = moving_runtime(ControlKey.D)
    snapshots = iter((frozenset({"right"}), frozenset({"left"})))
    read_count = 0

    def changing_directions(_router: InputRouter) -> frozenset[Direction]:
        nonlocal read_count
        read_count += 1
        return next(snapshots)

    monkeypatch.setattr(InputRouter, "directions", property(changing_directions))

    runtime.tick(0.5)

    assert read_count == 1
    assert pointer.moves == [(120, 0)]


def test_fractional_pixels_accumulate_across_small_ticks() -> None:
    """Los residuos subpíxel deben producir movimiento sin pérdida sistemática."""
    pointer = RecordingPointer()
    fractional_profile = AccelerationProfile(1.0, 0.0, 1.0)
    runtime = MouseRuntime(pointer=pointer, acceleration_profile=fractional_profile)
    activate(runtime)
    runtime.press(ControlKey.D)

    for _ in range(10):
        runtime.tick(0.1)

    assert pointer.moves == [(1, 0)]


def test_tick_without_elapsed_time_preserves_backend_compatibility() -> None:
    """El backend actual puede omitir tiempo hasta integrar su reloj monotónico."""
    pointer = RecordingPointer()
    constant_profile = AccelerationProfile(60.0, 0.0, 60.0)
    runtime = MouseRuntime(pointer=pointer, acceleration_profile=constant_profile)
    activate(runtime)
    runtime.press(ControlKey.D)

    runtime.tick()

    assert pointer.moves == [(1, 0)]


@pytest.mark.parametrize(
    "elapsed_seconds",
    [-0.1, float("inf"), float("-inf"), float("nan")],
)
def test_tick_rejects_invalid_elapsed_time_without_mutating_state(
    elapsed_seconds: float,
) -> None:
    """Tiempos inválidos deben fallar antes de alterar aceleración o residuos."""
    runtime, pointer = moving_runtime(ControlKey.D)

    with pytest.raises(ValueError, match="elapsed_seconds"):
        runtime.tick(elapsed_seconds)

    runtime.tick(0.5)
    assert pointer.moves == [(120, 0)]


def test_zero_elapsed_tick_preserves_held_direction_state() -> None:
    """Un tick nulo no debe mover ni modificar la continuidad retenida."""
    runtime, pointer = moving_runtime(ControlKey.D)
    runtime.tick(0.5)

    runtime.tick(0.0)
    runtime.tick(0.5)

    assert pointer.moves == [(120, 0), (280, 0)]


def test_runtime_notifies_each_mode_change() -> None:
    """La interfaz debe recibir feedback al activar y desactivar."""
    pointer = RecordingPointer()
    mode_changes: list[bool] = []
    runtime = MouseRuntime(pointer=pointer, on_mode_changed=mode_changes.append)

    runtime.press(ControlKey.CONTROL)
    runtime.press(ControlKey.ALT)
    runtime.press(ControlKey.M)
    runtime.release(ControlKey.M)
    runtime.press(ControlKey.M)

    assert mode_changes == [True, False]


def test_constructor_preserves_positional_mode_callback_compatibility() -> None:
    """El tercer argumento posicional debe seguir siendo el callback de modo."""
    pointer = RecordingPointer()
    profile = AccelerationProfile(12.0, 0.0, 12.0)
    mode_changes: list[bool] = []
    runtime = MouseRuntime(pointer, profile, mode_changes.append)

    activate(runtime)
    activate(runtime)

    assert mode_changes == [True, False]


def test_runtime_dispatches_right_click_to_pointer() -> None:
    """El clic contextual debe usar el botón derecho del adaptador."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    runtime.press(ControlKey.CONTROL)
    runtime.press(ControlKey.ALT)
    runtime.press(ControlKey.M)

    runtime.press(ControlKey.E)

    assert pointer.clicks == ["right"]


def test_runtime_requests_stop_for_emergency_chord() -> None:
    """El adaptador debe poder detener listener y worker de forma coordinada."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer=pointer)
    runtime.press(ControlKey.CONTROL)
    runtime.press(ControlKey.ALT)

    keep_running = runtime.press(ControlKey.ESCAPE)

    assert keep_running is False


def test_external_runtime_mode_has_one_notification_per_transition() -> None:
    """La UI y los atajos comparten el estado real, no una copia optimista."""
    modes: list[bool] = []
    runtime = MouseRuntime(RecordingPointer(), on_mode_changed=modes.append)
    assert runtime.active is False
    runtime.set_active(True)
    runtime.set_active(True)
    runtime.set_active(False)
    runtime.set_active(False)
    assert runtime.active is False
    assert modes == [True, False]


def test_external_disable_resets_motion_scroll_and_drag() -> None:
    """No quedan movimientos ni residuos después de desactivar y reactivar."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer)
    runtime.set_active(True)
    for key in (ControlKey.D, ControlKey.R, ControlKey.G):
        runtime.press(key)
    runtime.tick(0.001)
    runtime.set_active(False)
    runtime.tick(1.0)
    for key in (ControlKey.D, ControlKey.R, ControlKey.G):
        runtime.release(key)
    runtime.set_active(True)
    runtime.press(ControlKey.D)
    runtime.tick(0.004)
    assert pointer.moves == []
    assert pointer.scrolls == []
    assert pointer.button_events == ["down", "up"]


def test_keyboard_escape_updates_public_runtime_state() -> None:
    """El estado consultado por la UI sigue los comandos del teclado."""
    runtime = MouseRuntime(RecordingPointer())
    runtime.set_active(True)
    runtime.press(ControlKey.ESCAPE)
    assert runtime.active is False


def test_shutdown_prevents_late_input_and_is_idempotent() -> None:
    """Ningún evento tardío puede reactivar un motor cerrado."""
    pointer = RecordingPointer()
    runtime = MouseRuntime(pointer)
    runtime.set_active(True)
    runtime.press(ControlKey.G)
    runtime.press(ControlKey.D)
    runtime.press(ControlKey.R)
    runtime.shutdown()
    runtime.shutdown()
    runtime.tick(1.0)
    assert runtime.press(ControlKey.SPACE) is False
    runtime.release(ControlKey.G)
    assert runtime.active is False
    assert runtime.should_suppress(ControlKey.W) is False
    assert pointer.button_events == ["down", "up"]
    assert pointer.moves == []
    assert pointer.scrolls == []
    assert pointer.clicks == []
    with pytest.raises(RuntimeError, match="cerrado"):
        runtime.set_active(True)


class ReleaseFailsOncePointer(RecordingPointer):
    """Permite probar limpieza reintentable tras un fallo físico."""

    def __init__(self) -> None:
        super().__init__()
        self.release_attempts = 0

    def release_left(self) -> None:
        self.release_attempts += 1
        if self.release_attempts == 1:
            raise RuntimeError("release failed")
        super().release_left()


def test_shutdown_failure_is_visible_and_cleanup_can_retry() -> None:
    """El fallo no se silencia ni permite nuevos eventos del motor."""
    pointer = ReleaseFailsOncePointer()
    runtime = MouseRuntime(pointer)
    runtime.set_active(True)
    runtime.press(ControlKey.G)
    with pytest.raises(RuntimeError, match="release failed"):
        runtime.shutdown()
    assert runtime.press(ControlKey.SPACE) is False
    runtime.cleanup()
    runtime.shutdown()
    assert runtime.active is False
    assert pointer.button_events == ["down", "up"]
    assert pointer.release_attempts == 2


def test_runtime_exposes_suppression_decision() -> None:
    """El hook debe consultar la política sin acceder al router interno."""
    runtime = MouseRuntime(pointer=RecordingPointer())
    assert runtime.should_suppress(ControlKey.W) is False

    runtime.press(ControlKey.CONTROL)
    runtime.press(ControlKey.ALT)
    runtime.press(ControlKey.M)

    assert runtime.should_suppress(ControlKey.W) is True
