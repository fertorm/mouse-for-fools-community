"""Instancia real de Windows y diagnóstico local sin hooks."""

import logging
from typing import Any
from uuid import uuid4

from mouse_for_fools.diagnostics import configure_logging
from mouse_for_fools.instance import SessionLease


def test_session_lease_rejects_duplicate_and_allows_reopen() -> None:
    name = "Local\\MouseForFools.Test." + uuid4().hex
    first, second = SessionLease(name), SessionLease(name)
    try:
        assert first.acquire()
        assert not second.acquire()
        first.release()
        first.release()
        assert second.acquire()
    finally:
        first.release()
        second.release()


def test_logging_uses_localappdata_and_does_not_duplicate_handlers(
    tmp_path: Any, monkeypatch: Any
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = configure_logging()
    assert path.parent == tmp_path / "MouseForFools" / "logs"
    assert configure_logging() == path
    logger = logging.getLogger("mouse_for_fools")
    logger.info("service_ready")
    handlers = [handler for handler in logger.handlers if hasattr(handler, "baseFilename")]
    assert len(handlers) == 1
    for handler in handlers:
        handler.flush()
    assert path.read_text(encoding="utf-8").count("service_ready") == 1
    for handler in handlers:
        logger.removeHandler(handler)
        handler.close()
