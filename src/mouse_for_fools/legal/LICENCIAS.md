# Licencias y estado de distribución

Mouse for Fools — Nexum by Fertorm. 4 de septiembre de 2026.

## Código propio

El código propio se publica bajo MIT por decisión del titular, Luis Fernando Torrico Moscoso, el 27 de octubre de 2026. Consulta LICENSE en la raíz del repositorio y en los futuros paquetes que se construyan desde esta copia. Los componentes externos conservan sus licencias y avisos.

## Componentes externos

- CPython 3.14.2: licencia PSF y avisos adicionales.
- PySide6, Shiboken y Qt 6.11.2: opción LGPLv3 para los componentes seleccionados,
  junto con las licencias de sus dependencias.
- pynput 1.8.2: LGPL según su texto original incluido.
- six 1.17.0: MIT.
- PyInstaller 6.22.2: GPL con excepción para el bootloader.

El portable incluye `THIRD-PARTY-NOTICES.md` y la carpeta `licenses` con los
textos y atribuciones originales. Manténgalos junto con el paquete. Las DLL de
Qt/PySide6 están separadas bajo `_internal`; no se prohíbe sustituirlas ni
depurar modificaciones en los términos de sus licencias.

## Revisión pendiente antes de entregar a terceros

Incluir textos de licencia no basta por sí solo para afirmar cumplimiento.
Debe comprobarse el inventario exacto del binario, el código fuente
correspondiente y su mecanismo de entrega, la posibilidad efectiva de sustituir
las bibliotecas y los requisitos de redistribución de componentes Microsoft.
Los enlaces de origen por sí solos no se presentan como una oferta de fuentes
suficiente. Los avisos de terceros no conceden derechos sobre el código propio.

Fuentes oficiales consultadas:

- https://doc.qt.io/qt-6/licensing.html
- https://doc.qt.io/qtforpython-6/licenses.html
- https://www.gnu.org/licenses/lgpl-3.0.html
- https://pyinstaller.org/en/stable/license.html

Este documento es un inventario técnico con pendientes; no certifica aprobación
jurídica ni autoriza publicación comercial.
