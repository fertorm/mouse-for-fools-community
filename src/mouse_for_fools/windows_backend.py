"""Adaptadores de entrada y cursor para Windows."""

from collections.abc import Callable
from dataclasses import dataclass

from mouse_for_fools.input_router import ControlKey
from mouse_for_fools.runtime import MouseRuntime

_KEY_DOWN_MESSAGES = {0x0100, 0x0104}
_KEY_UP_MESSAGES = {0x0101, 0x0105}

_VK_TO_CONTROL: dict[int, ControlKey] = {
    0xA0: ControlKey.SHIFT_LEFT,
    0xA1: ControlKey.SHIFT_RIGHT,
    0x51: ControlKey.Q,
    0x11: ControlKey.CONTROL,
    0xA2: ControlKey.CONTROL,
    0xA3: ControlKey.CONTROL,
    0x12: ControlKey.ALT,
    0xA4: ControlKey.ALT,
    0xA5: ControlKey.ALT,
    0x4D: ControlKey.M,
    0x57: ControlKey.W,
    0x41: ControlKey.A,
    0x53: ControlKey.S,
    0x44: ControlKey.D,
    0x45: ControlKey.E,
    0x52: ControlKey.R,
    0x46: ControlKey.F,
    0x47: ControlKey.G,
    0x20: ControlKey.SPACE,
    0x1B: ControlKey.ESCAPE,
}


_GENERIC_SHIFT_VK = 0x10
_SHIFT_SCAN_CODE_TO_CONTROL = {
    0x2A: ControlKey.SHIFT_LEFT,
    0x36: ControlKey.SHIFT_RIGHT,
}


def control_key_from_vk(
    virtual_key: int,
    scan_code: int | None = None,
) -> ControlKey | None:
    """Convierte VK y scan code de Windows a una tecla lógica estable."""
    if virtual_key == _GENERIC_SHIFT_VK:
        if scan_code is None:
            # Fallback para callers sin KBDLLHOOKSTRUCT: conserva compatibilidad.
            return ControlKey.SHIFT_LEFT
        return _SHIFT_SCAN_CODE_TO_CONTROL.get(scan_code)
    return _VK_TO_CONTROL.get(virtual_key)


def virtual_key_from_pynput(key: object) -> int | None:
    """Extrae el código virtual de un objeto de tecla de pynput."""
    virtual_key = getattr(key, "vk", None)
    if isinstance(virtual_key, int):
        return virtual_key
    nested_value = getattr(key, "value", None)
    nested_virtual_key = getattr(nested_value, "vk", None)
    return nested_virtual_key if isinstance(nested_virtual_key, int) else None


class SuppressionTracker:
    """Conserva la supresión hasta recibir la liberación correspondiente."""

    def __init__(self) -> None:
        self._pending_releases: set[ControlKey] = set()

    def observe(self, key: ControlKey, *, key_down: bool, suppress_now: bool) -> bool:
        """Decide la supresión y actualiza las liberaciones pendientes."""
        if key_down:
            if suppress_now:
                self._pending_releases.add(key)
            return suppress_now
        if key in self._pending_releases:
            self._pending_releases.remove(key)
            return True
        return False


@dataclass(frozen=True)
class EventDecision:
    """Resultado de procesar un evento dentro del filtro Win32."""

    suppress: bool
    keep_running: bool


class KeyboardEventBridge:
    """Conecta eventos Win32 con el runtime probado del experimento."""

    def __init__(self, runtime: MouseRuntime) -> None:
        self._runtime = runtime
        self._suppression = SuppressionTracker()

    def press_vk(
        self,
        virtual_key: int,
        *,
        scan_code: int | None = None,
    ) -> bool:
        """Procesa un keydown y devuelve si el listener debe continuar."""
        control_key = control_key_from_vk(virtual_key, scan_code)
        if control_key is None:
            return True
        return self._runtime.press(control_key)

    def release_vk(
        self,
        virtual_key: int,
        *,
        scan_code: int | None = None,
    ) -> None:
        """Procesa un keyup reconocido."""
        control_key = control_key_from_vk(virtual_key, scan_code)
        if control_key is not None:
            self._runtime.release(control_key)

    def should_suppress_event(
        self,
        virtual_key: int,
        *,
        key_down: bool,
        scan_code: int | None = None,
    ) -> bool:
        """Determina si un evento Win32 debe ocultarse al resto del sistema."""
        control_key = control_key_from_vk(virtual_key, scan_code)
        if control_key is None:
            return False
        return self._suppression.observe(
            control_key,
            key_down=key_down,
            suppress_now=self._runtime.should_suppress(control_key),
        )

    def handle_event(
        self,
        virtual_key: int,
        *,
        key_down: bool,
        scan_code: int | None = None,
    ) -> EventDecision:
        """Procesa el evento antes de que pynput pueda suprimir su callback."""
        suppress = self.should_suppress_event(
            virtual_key,
            key_down=key_down,
            scan_code=scan_code,
        )
        if key_down:
            keep_running = self.press_vk(virtual_key, scan_code=scan_code)
        else:
            self.release_vk(virtual_key, scan_code=scan_code)
            keep_running = True
        return EventDecision(suppress=suppress, keep_running=keep_running)


class _PynputPointer:
    """Controla el cursor real mediante el backend Win32 de pynput."""

    def __init__(self) -> None:
        from pynput.mouse import Button, Controller

        self._controller = Controller()
        self._left_button = Button.left
        self._right_button = Button.right

    def click_left(self) -> None:
        self._controller.click(self._left_button)

    def double_click_left(self) -> None:
        self._controller.click(self._left_button, 2)

    def click_right(self) -> None:
        self._controller.click(self._right_button)

    def press_left(self) -> None:
        self._controller.press(self._left_button)

    def release_left(self) -> None:
        self._controller.release(self._left_button)

    def move(self, delta_x: int, delta_y: int) -> None:
        self._controller.move(delta_x, delta_y)

    def scroll(self, vertical_units: int) -> None:
        self._controller.scroll(0, vertical_units)


def run_windows_runtime(on_mode_changed: Callable[[bool], None]) -> int:
    """Ejecuta en consola el mismo servicio utilizado por la interfaz Qt."""
    from mouse_for_fools.console_service import run_console_service

    return run_console_service(on_mode_changed)
