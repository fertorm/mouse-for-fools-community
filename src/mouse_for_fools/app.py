"""Interfaz de consola de Mouse for Fools."""

import argparse
import logging
import platform
import winsound
from collections.abc import Sequence

from mouse_for_fools.windows_backend import run_windows_runtime

APP_TITLE = "Mouse for Fools - Nexum by Fertorm"


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _notify_mode_changed(active: bool) -> None:
    state_label = "ACTIVADO" if active else "DESACTIVADO"
    logging.getLogger(__name__).info("Mouse Mode %s", state_label)
    try:
        winsound.MessageBeep(winsound.MB_OK)
    except RuntimeError:
        logging.getLogger(__name__).warning("No se pudo emitir la senal sonora")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument(
        "--check",
        action="store_true",
        help="valida el entorno sin instalar el hook global",
    )
    return parser


def _self_check() -> int:
    if platform.system() != "Windows":
        print("Error: Experiment 001 solo admite Windows 10/11.")
        return 1
    from pynput import keyboard, mouse

    if keyboard.Listener is None or mouse.Controller is None:
        print("Error: pynput no expone los adaptadores esperados.")
        return 1
    print("Autodiagnostico correcto: Windows y pynput disponibles.")
    return 0


def run_windows_app() -> int:
    """Inicia el experimento interactivo y presenta sus controles."""
    _configure_logging()
    print("Ctrl + Alt + M: activar/desactivar")
    print("WASD: mover | Ctrl+WASD: precision | Shift+WASD: fast")
    print("Space: clic izquierdo | Q: doble clic | E: clic derecho")
    print("R/F: scroll | Mantener G: drag")
    print("Esc: desactivar | Ctrl + Alt + Esc: cerrar")
    return run_windows_runtime(on_mode_changed=_notify_mode_changed)


def main(arguments: Sequence[str] | None = None) -> int:
    """Ejecuta la interfaz de consola y devuelve un código de salida."""
    options = _build_parser().parse_args(arguments)
    print(APP_TITLE)
    if options.check:
        return _self_check()
    return run_windows_app()
