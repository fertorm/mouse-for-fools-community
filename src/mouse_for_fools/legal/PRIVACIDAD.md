# Privacidad

Mouse for Fools — Nexum by Fertorm. Versión experimental local.
Fecha: 4 de septiembre de 2026.

## Funcionamiento local

Mientras está abierta, la aplicación recibe eventos globales del teclado para
reconocer atajos y controlar el cursor. Esto incluye eventos recibidos mientras
otra aplicación tiene el foco. Procesa códigos y estados de teclas en memoria;
no construye ni guarda un historial del texto escrito, contraseñas o documentos.
Desactivar el control mantiene la escucha necesaria para reconocer el atajo de
activación. Salir de la aplicación detiene el servicio y libera el hook.

El código actual no implementa cuentas, cookies, publicidad, analítica,
actualizaciones automáticas ni transmisión de datos a servidores.
No solicita nombre, correo ni datos de pago. Esta descripción corresponde a
la aplicación; no describe los servicios propios de Windows u otros programas.

## Registro de diagnóstico

Guarda fechas y horas, inicio y cierre del servicio, cambios de activación y
categorías de errores para diagnosticar fallos. No registra teclas, texto escrito
ni el contenido de otras ventanas.

Ubicación: `%LOCALAPPDATA%\MouseForFools\logs`.
El archivo `application.log` rota al alcanzar aproximadamente 512.000 bytes y
conserva hasta dos copias anteriores. La retención depende del tamaño, no de
un plazo: los archivos permanecen hasta rotar o ser eliminados manualmente.
Los usuarios o programas con acceso a esa carpeta pueden leerlos.

Para eliminarlos, cierre la aplicación y borre la carpeta `logs`. Se volverá a
crear al iniciar. Borrar el portable no elimina estos registros. No hay envío
automático de logs; si decide compartirlos para soporte, revíselos antes.

## Alcance y cambios

Este aviso documenta la prueba local actual. Esta copia de código abierto es mantenida por Luis Fernando Torrico Moscoso. Para consultas, solicita un canal privado mediante un issue sin adjuntar datos personales. Antes de ofrecer nuevos binarios o incorporar recopilación de datos, deben revisarse el aviso y los requisitos aplicables.

Cualquier futura función que recopile o transmita datos requiere actualizar
este aviso y evaluar su finalidad, retención, destinatarios y consentimiento
o fundamento aplicable antes de habilitarla.
