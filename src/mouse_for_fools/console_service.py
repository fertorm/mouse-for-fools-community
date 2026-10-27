"""Adaptación bloqueante del servicio compartido para la consola."""

from collections.abc import Callable

from mouse_for_fools.service import STOP_TIMEOUT, ServiceEvent, WindowsService


def run_console_service(
    on_mode_changed: Callable[[bool], None],
    *,
    factory: Callable[[Callable[[ServiceEvent], None]], WindowsService] = WindowsService,
) -> int:
    """Espera el servicio, limpia en Ctrl+C y propaga fallos tras el cierre."""
    errors: list[str] = []

    def notify(event: ServiceEvent) -> None:
        if event.kind == "state":
            on_mode_changed(event.active)
        elif event.kind == "error":
            errors.append(event.message)

    service = factory(notify)
    try:
        service.start()
        while not service.join(STOP_TIMEOUT):
            pass
    except KeyboardInterrupt:
        service.stop()
    finally:
        service.stop()
        if not service.join(STOP_TIMEOUT):
            raise RuntimeError("No se pudo confirmar el cierre del servicio")
    if errors:
        raise RuntimeError(errors[-1])
    return 0
