"""Ciclo de vida del hook de pynput 1.8.2, aislado de Qt y del motor."""

from collections.abc import Callable
from importlib import import_module
from threading import Thread
from typing import Any

from mouse_for_fools.runtime import MouseRuntime
from mouse_for_fools.windows_backend import (
    _KEY_DOWN_MESSAGES,
    _KEY_UP_MESSAGES,
    KeyboardEventBridge,
)


class PynputListener:
    """Confirma el hook real y conserva errores sin registrar entradas."""

    def __init__(self, runtime: MouseRuntime, request_stop: Callable[[], None]) -> None:
        from pynput import keyboard

        self._bridge = KeyboardEventBridge(runtime)
        self._request_stop = request_stop
        self._error: Exception | None = None
        self._listener: Any = keyboard.Listener(win32_event_filter=self._filter)

    @property
    def ready(self) -> bool:
        """Comprueba el handle instalado, no el aviso prematuro de pynput."""
        # pynput 1.8.2 marca ready antes de SetWindowsHookEx. Este acceso privado
        # queda acotado al adaptador y debe revisarse al actualizar pynput.
        hooks = import_module("pynput._util.win32").SystemHook
        hook = hooks._HOOKS.get(self._listener.ident)
        return bool(hook is not None and hook._hook and self.alive)

    @property
    def alive(self) -> bool:
        """Indica si el hilo del hook sigue vivo."""
        return bool(self._listener.is_alive())

    def start(self) -> None:
        """Inicia el hilo; el servicio espera ready con límite temporal."""
        self._listener.start()

    def stop(self) -> None:
        """Solicita la retirada del hook sin esperar desde el callback."""
        self._listener.stop()

    def join(self, timeout: float) -> bool:
        """Espera el hilo y verifica su terminación, incluso tras error."""
        if self._listener.ident is not None:
            Thread.join(self._listener, timeout)
        return not self.alive

    def check(self) -> None:
        """Propaga errores del filtro al propietario del servicio."""
        if self._error is not None:
            raise self._error

    def _filter(self, message: int, data: Any) -> bool | None:
        if message not in _KEY_DOWN_MESSAGES | _KEY_UP_MESSAGES:
            return None
        try:
            decision = self._bridge.handle_event(
                data.vkCode,
                key_down=message in _KEY_DOWN_MESSAGES,
                scan_code=data.scanCode,
            )
        except Exception as error:
            self._error = error
            self._request_stop()
            return False
        if not decision.keep_running:
            self._request_stop()
        # suppress_event lanza una excepción de control de pynput; no es fallo.
        if decision.suppress:
            self._listener.suppress_event()
        return False
