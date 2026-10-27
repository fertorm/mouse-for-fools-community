# Alcance de validación del portable

La interfaz y el servicio tienen 204 pruebas automatizadas aprobadas,
95,77 % de cobertura y aprobación del usuario de la ventana/bandeja.

El paquete incluye el runtime de Python y las dependencias. La comprobación
local de este artefacto, el 2026-09-04, confirmó:

- Arranque desactivado desde una carpeta externa con espacios.
- PATH limitado a Windows y PYTHONPATH/PYTHONHOME ausentes.
- Python, Qt y Shiboken cargados desde _internal del propio paquete.
- Una sola instalación de hook al abrir dos procesos.
- Cierre normal y evento service_stopped sin proceso residual.

Detalles: docs/PORTABLE-VALIDATION.md del proyecto.

Pendiente de aceptación externa: ejecución en otra máquina/VM sin Python,
verificación manual completa de controles y revisión de avisos para distribución.
No se ha comprobado compatibilidad con todas las versiones de Windows 10/11,
escritorio seguro, UAC ni aplicaciones elevadas.
