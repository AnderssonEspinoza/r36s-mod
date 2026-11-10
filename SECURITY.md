# Seguridad

No publiques credenciales, partidas ni imágenes de tarjetas en issues. Para una vulnerabilidad del instalador, usa la opción privada **Report a vulnerability** de GitHub si está disponible. Si no lo está, abre un issue sin detalles explotables para solicitar un canal privado al mantenedor.

Este proyecto modifica archivos del sistema cuando se ejecuta `apply` como root. Revisa el código, prueba en una tarjeta de repuesto y conserva una copia externa. `doctor` y `plan` solo leen. No hay instalador `curl | sh`, flasheo automático, cambios de contraseña, telemetría ni envío de partidas.

Los análisis SOC son locales y no invocan una shell con el nombre del archivo. La receta de toolkit utiliza APT autenticado; no desactives verificaciones para resolver un fallo de descarga. No analices muestras hostiles en un equipo que quieras conservar como entorno confiable.
