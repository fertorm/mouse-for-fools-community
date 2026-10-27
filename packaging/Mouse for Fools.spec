# Configuración PyInstaller: dependencias dinámicas de pynput explícitas.
from pathlib import Path

root = Path(SPECPATH).parent
analysis = Analysis(
    [str(root / "bin" / "gui.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "src" / "mouse_for_fools" / "legal"), "mouse_for_fools/legal")],
    hiddenimports=[
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "pynput._util.win32",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6", "PySide2"],
    noarchive=False,
)
# Los hooks genéricos de Qt incluyen plugins ajenos a esta app de Widgets.
# Mantener solo la plataforma Windows, estilo nativo e iconos; sin PDF/QML.
qt_libraries = {"Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Network.dll"}
qt_plugins = {"qwindows.dll", "qmodernwindowsstyle.dll", "qico.dll"}
analysis.binaries = [
    item for item in analysis.binaries
    if not (
        (Path(item[0]).name.startswith("Qt6") and Path(item[0]).name not in qt_libraries)
        or ("plugins" in Path(item[0]).parts and Path(item[0]).name not in qt_plugins)
    )
]
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Mouse for Fools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(root / "build" / "application.ico"),
)
bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Mouse for Fools",
)
