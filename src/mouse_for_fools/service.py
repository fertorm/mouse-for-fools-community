"""Propietario del motor, del hook y de las solicitudes de consola/Qt."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic
from typing import Protocol

from mouse_for_fools.instance import SessionLease
from mouse_for_fools.runtime import MouseRuntime, Pointer

TICK_SECONDS = 1 / 60
STOP_TIMEOUT = 2.0
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceEvent:
    """Estado confirmado, sin datos de teclado ni excepciones internas."""

    kind: str
    active: bool = False
    message: str = ""


class Listener(Protocol):
    """Operaciones requeridas del adaptador de entrada."""

    @property
    def ready(self) -> bool:
        """Confirma instalación del hook."""

    @property
    def alive(self) -> bool:
        """Indica si el trabajador está vivo."""

    def start(self) -> None:
        """Inicia entrada."""

    def stop(self) -> None:
        """Solicita detener entrada."""

    def join(self, timeout: float) -> bool:
        """Confirma retirada."""

    def check(self) -> None:
        """Propaga fallo de entrada."""


class Lease(Protocol):
    """Reserva de instancia por sesión."""

    def acquire(self) -> bool:
        """Intenta reservar."""

    def release(self) -> None:
        """Libera la reserva."""


class WindowsService:
    """Ejecuta todos los ticks y solicitudes en un único trabajador."""

    def __init__(
        self,
        notify: Callable[[ServiceEvent], None],
        *,
        pointer: Pointer | None = None,
        listener_factory: Callable[[MouseRuntime, Callable[[], None]], Listener] | None = None,
        lease: Lease | None = None,
        timeout: float = STOP_TIMEOUT,
    ) -> None:
        from mouse_for_fools.windows_backend import _PynputPointer
        from mouse_for_fools.windows_listener import PynputListener

        self.runtime = MouseRuntime(pointer if pointer is not None else _PynputPointer())
        self._notify = notify
        self._factory = listener_factory or PynputListener
        self._lease = lease if lease is not None else SessionLease()
        self._timeout = timeout
        self._requests: Queue[bool] = Queue()
        self._stop = Event()
        self._thread: Thread | None = None
        self._listener: Listener | None = None
        self._last_active = False

    def start(self) -> None:
        """Inicia una sola vez; el evento ready confirma disponibilidad."""
        if self._thread is not None:
            raise RuntimeError("El servicio ya fue iniciado")
        self._thread = Thread(target=self._run, name="mouse-service", daemon=False)
        self._thread.start()

    def set_active(self, active: bool) -> None:
        """Encola el estado solicitado; no altera widgets ni simula teclas."""
        if not self._stop.is_set():
            self._requests.put(active)

    def stop(self) -> None:
        """Solicita cierre sin bloquear el hilo gráfico."""
        self._stop.set()

    def join(self, timeout: float) -> bool:
        """Espera al propietario y confirma si terminó."""
        if self._thread is None:
            return True
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def _run(self) -> None:
        failure = ""
        try:
            if not self._lease.acquire():
                failure = "La aplicación ya está abierta en esta sesión."
                return
            self._listener = self._factory(self.runtime, self.stop)
            self._listener.start()
            if self._await_ready():
                self._notify(ServiceEvent("ready"))
                _LOGGER.info("service_ready")
                self._loop()
        except Exception as error:
            _LOGGER.error("service_failure category=%s", type(error).__name__)
            failure = "El control no está disponible. Revisa el diagnóstico local."
        finally:
            cleanup_error = self._finish()
            failure = cleanup_error or failure
            self._notify(ServiceEvent("error" if failure else "stopped", message=failure))

    def _await_ready(self) -> bool:
        assert self._listener is not None
        deadline = monotonic() + self._timeout
        while not self._stop.is_set():
            self._listener.check()
            if self._listener.ready:
                return True
            if not self._listener.alive or monotonic() >= deadline:
                raise TimeoutError("Hook no disponible")
            self._stop.wait(TICK_SECONDS)
        return False

    def _loop(self) -> None:
        assert self._listener is not None
        previous = monotonic()
        while not self._stop.wait(TICK_SECONDS):
            self._listener.check()
            if not self._listener.alive:
                raise RuntimeError("Listener terminado inesperadamente")
            self._apply_request()
            if self._stop.is_set():
                break
            current = monotonic()
            self.runtime.tick(current - previous)
            previous = current
            if self.runtime.active != self._last_active:
                self._publish_state()
        self._listener.check()

    def _apply_request(self) -> None:
        try:
            requested = self._requests.get_nowait()
        except Empty:
            return
        self.runtime.set_active(requested)
        self._publish_state()

    def _publish_state(self) -> None:
        self._last_active = self.runtime.active
        self._notify(ServiceEvent("state", self._last_active))
        _LOGGER.info("mode_changed active=%s", self._last_active)

    def _finish(self) -> str:
        self._stop.set()
        failed = False
        try:
            self.runtime.shutdown()
        except Exception as error:
            failed = True
            _LOGGER.error("cleanup_failure category=%s", type(error).__name__)
        listener_stopped, listener_failed = self._stop_listener()
        failed = failed or listener_failed
        try:
            self.runtime.cleanup()
            if listener_stopped:
                self._lease.release()
        except Exception as error:
            failed = True
            _LOGGER.error("release_failure category=%s", type(error).__name__)
        if failed or not listener_stopped:
            return (
                "No se pudo confirmar el cierre seguro. "
                "Cierra la aplicación antes de reabrirla."
            )
        _LOGGER.info("service_stopped")
        return ""

    def _stop_listener(self) -> tuple[bool, bool]:
        if self._listener is None:
            return True, False
        stopped, failed = False, False
        try:
            self._listener.stop()
        except Exception as error:
            failed = True
            _LOGGER.error("listener_stop_failure category=%s", type(error).__name__)
        try:
            stopped = self._listener.join(self._timeout)
            self._listener.check()
        except Exception as error:
            failed = True
            _LOGGER.error("listener_exit_failure category=%s", type(error).__name__)
        return stopped, failed
