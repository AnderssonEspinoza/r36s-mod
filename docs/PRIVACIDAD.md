# Contenido público y privacidad

Este repositorio se creó con archivos seleccionados expresamente. No es una copia de HOME ni de una imagen de microSD.

Se incluyen código propio, pruebas sintéticas, documentación y siete imágenes proporcionadas por el autor para mostrar el proyecto. En estas imágenes no se detectaron campos EXIF/metadatos en los PNG suministrados. Las fotos muestran la biblioteca y el identificador público @dvinci.sh de forma intencional; no contienen un volcado de sus juegos.

Se excluyen ROMs, BIOS, ISO/CSO, música, partidas, estados, imágenes de tarjetas, archivos PCAP personales, dumps, contraseñas, claves SSH, tokens, `/etc/shadow`, registros de sesiones, datos de cuentas y el informe privado con rutas de la laptop.

`.gitignore` reduce incorporaciones accidentales. `scripts/check-publication.py` revisa el índice Git: extensiones no permitidas, binarios inesperados, límites de tamaño, patrones de tokens/claves y rutas personales del equipo original. **No es una garantía de ausencia de todo secreto posible**; revisa siempre `git diff --cached` antes de publicar.

Los bundles del toolkit se generan en `build/`, que no se publica. No archives tu carpeta completa para adjuntarla a un issue. Los respaldos del instalador y las versiones de partidas permanecen en la consola y no se suben automáticamente.
