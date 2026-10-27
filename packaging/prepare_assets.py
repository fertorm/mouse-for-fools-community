"""Prepara icono y avisos desde el entorno de build, sin tocar el código."""

import shutil
import sys
from importlib.metadata import distribution
from pathlib import Path

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("PySide6", "PySide6_Essentials", "shiboken6", "pynput", "six", "PyInstaller")


def prepare_icon() -> None:
    """Genera el icono original para el recurso del ejecutable Windows."""
    sys.path.insert(0, str(ROOT / "src"))
    from mouse_for_fools.ui.icon import application_icon

    app = QApplication.instance() or QApplication([])
    target = ROOT / "build" / "application.ico"
    target.parent.mkdir(exist_ok=True)
    if not application_icon().pixmap(64, 64).save(str(target), "ICO"):
        raise RuntimeError("No se pudo crear el icono")
    app.quit()


def collect_licenses() -> None:
    """Copia avisos completos de las distribuciones y la licencia de Python."""
    target = ROOT / "build" / "licenses"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "packaging" / "licenses", target, dirs_exist_ok=True)
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", target / "Python-LICENSE.txt")
    inventory = []
    for name in PACKAGES:
        package = distribution(name)
        inventory.append(f"{name}=={package.version}")
        for item in package.files or ():
            if any(word in str(item).lower() for word in ("license", "copying", "copyright")):
                destination = target / name / Path(str(item)).name
                destination.parent.mkdir(exist_ok=True)
                shutil.copy2(package.locate_file(item), destination)
    (target / "COMPONENTS.txt").write_text("\n".join(inventory) + "\n", encoding="utf-8")


def main() -> None:
    """Prepara recursos de distribución con el intérprete de compilación."""
    prepare_icon()
    collect_licenses()


if __name__ == "__main__":
    main()
