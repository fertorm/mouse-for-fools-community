"""Pruebas de la interfaz de línea de comandos."""

import pytest

from mouse_for_fools import app
from mouse_for_fools.app import main


def test_self_check_confirms_windows_dependencies(capsys: pytest.CaptureFixture[str]) -> None:
    """El diagnóstico debe validar dependencias sin instalar el hook."""
    exit_code = main(["--check"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Autodiagnostico correcto" in captured.out


def test_console_startup_output_is_ascii_safe(capsys: pytest.CaptureFixture[str]) -> None:
    """La consola clásica de Windows no debe reemplazar caracteres del estado."""
    main(["--check"])

    captured = capsys.readouterr()
    assert captured.out.isascii()


def test_default_command_starts_windows_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ejecutar sin flags debe iniciar el experimento interactivo."""
    calls: list[str] = []

    def fake_runner() -> int:
        calls.append("run")
        return 0

    monkeypatch.setattr(app, "run_windows_app", fake_runner)

    assert main([]) == 0
    assert calls == ["run"]


def test_windows_app_prints_controls_and_delegates(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """El arranque debe explicar cómo recuperar el teclado antes del hook."""
    callbacks: list[object] = []

    def fake_runtime(*, on_mode_changed: object) -> int:
        callbacks.append(on_mode_changed)
        return 0

    monkeypatch.setattr(app, "run_windows_runtime", fake_runtime)

    assert app.run_windows_app() == 0
    output = capsys.readouterr().out
    assert "R/F: scroll" in output
    assert "Q: doble clic" in output
    assert "Ctrl+WASD: precision" in output
    assert "Shift+WASD: fast" in output
    assert output.isascii()
    assert "Mantener G: drag" in output
    assert "Ctrl + Alt + Esc: cerrar" in output
    assert callbacks == [app._notify_mode_changed]


def test_mode_change_emits_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cada transición debe intentar emitir una señal sonora."""
    beeps: list[int] = []
    monkeypatch.setattr(app.winsound, "MessageBeep", beeps.append)

    app._notify_mode_changed(True)
    app._notify_mode_changed(False)

    assert beeps == [app.winsound.MB_OK, app.winsound.MB_OK]
