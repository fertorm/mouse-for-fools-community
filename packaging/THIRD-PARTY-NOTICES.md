# Componentes de terceros

Mouse for Fools — Nexum by Fertorm. Paquete local experimental para evaluación.
No existe afiliación con los proveedores mencionados.

| Componente | Licencia / referencia | Procedencia |
| --- | --- | --- |
| CPython 3.14.2 | PSF y avisos incluidos en Python-LICENSE.txt | https://www.python.org/downloads/release/python-3142/ |
| PySide6 y Shiboken 6.11.2 | Opción LGPLv3; véanse textos y avisos Qt | https://download.qt.io/official_releases/QtForPython/ |
| Qt 6.11.2 | QtCore, QtGui, QtWidgets y dependencias/plugin Windows | https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/ |
| pynput 1.8.2 | LGPL, texto COPYING.LGPL incluido | https://github.com/moses-palmer/pynput |
| six 1.17.0 | MIT, texto incluido | https://github.com/benjaminp/six |
| PyInstaller 6.22.2 | GPL con excepción del bootloader, texto incluido | https://pyinstaller.org/en/stable/license.html |

Los avisos originales recuperados del entorno están en licenses, sin alterarlos.
licenses/Qt/third-party contiene 93 archivos de licencia y atribución del código
fuente oficial qtbase 6.11.2. Incluye también avisos de componentes que podrían
no estar habilitados en esta compilación; los avisos no prueban su presencia.
Los metadatos de los wheels de PySide6 declaran LGPL-3.0-only OR GPL-2.0-only OR
GPL-3.0-only; también contienen un aviso comercial para licenciatarios comerciales.
Ese aviso no convierte esta descarga comunitaria en una licencia comercial.
Se incluyen además LGPLv3 y GPLv3 originales del tag v6.11.2 de qtbase.

El código de Qt/PySide6 no se modifica y sus bibliotecas dinámicas se conservan
separadas bajo _internal. Se respetan los derechos de modificación, sustitución y
depuración otorgados por sus licencias; este documento no impone restricciones
adicionales sobre esos componentes.

Referencias de atribución y fuentes:

- https://doc.qt.io/qt-6/licenses-used-in-qt.html
- https://doc.qt.io/qtforpython-6/licenses.html
- https://code.qt.io/cgit/qt/qtbase.git/tree/?h=v6.11.2
- https://code.qt.io/cgit/pyside/pyside-setup.git/tree/?h=v6.11.2

El icono de mouse es propio y se genera desde ui/icon.py. La interfaz utiliza
la fuente instalada en Windows; no distribuye archivos de Segoe UI.

Antes de distribución externa o publicación comercial, verificar el inventario
final de bibliotecas, la disponibilidad del código fuente correspondiente y los requisitos
de distribución de Microsoft. Este paquete no declara aprobación legal.
