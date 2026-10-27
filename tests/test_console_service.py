"""Contrato de consola con el mismo servicio de la interfaz gráfica."""

from typing import Any

import pytest

from mouse_for_fools.console_service import run_console_service
from mouse_for_fools.service import ServiceEvent


class FakeService:
    def __init__(self, notify: Any, *, interrupt: Any = False, failure: Any = False) -> None:
        self.notify = notify
        self.interrupt = interrupt
        self.failure = failure
        self.stopped = False
        self.joined = False

    def start(self) -> None:
        self.notify(ServiceEvent("ready"))
        self.notify(ServiceEvent("state", True))
        if self.failure:
            self.notify(ServiceEvent("error", message="Fallo del servicio"))

    def stop(self) -> None:
        self.stopped = True

    def join(self, timeout: Any) -> Any:
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt
        self.joined = True
        return True


@pytest.mark.parametrize("interrupt", [False, True])
def test_console_shares_service_and_always_stops_and_joins(interrupt: Any) -> None:
    instances = []

    def factory(notify: Any) -> Any:
        service = FakeService(notify, interrupt=interrupt)
        instances.append(service)
        return service

    modes = []
    assert run_console_service(modes.append, factory=factory) == 0
    assert modes == [True]
    assert instances[0].stopped
    assert instances[0].joined


def test_console_reports_failure_after_cleanup() -> None:
    instances = []

    def factory(notify: Any) -> Any:
        service = FakeService(notify, failure=True)
        instances.append(service)
        return service

    with pytest.raises(RuntimeError, match="Fallo del servicio"):
        run_console_service(lambda _: None, factory=factory)
    assert instances[0].stopped and instances[0].joined
