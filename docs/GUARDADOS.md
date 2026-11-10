# Partidas, respaldos y recuperación

## Qué pasó en nuestra consola

El primer ajuste guardaba RAM cada tres segundos y permitía terminar la escritura al salir de RetroArch. Pasó una prueba de cerrar y reabrir, pero no habíamos comprobado todavía el apagado completo. Más tarde se perdieron avances.

Al revisar la Kingtom se encontró corrupción de FAT. Cristal tenía archivos que apuntaban a clusters libres; varios guardados de GBA estaban llenos de `FF`. Antes de reparar se creó una imagen completa y se copiaron los archivos legibles. Una búsqueda de sectores sobre esa copia no permitió recuperar una partida avanzada completa con confianza.

**Los avances anteriores de Pokémon no se recuperaron.** Reparar el sistema de archivos no equivale a reconstruir una partida.

Después se reparó la FAT y se instalaron escritura síncrona, copias a ext4 y cierre ordenado. Una ROM propia de prueba FLASH128K verificó ambos bancos tras un apagado completo y un nuevo encendido. No fue una prueba de permanecer apagada varios días.

## Qué publica este repositorio

El módulo `saves` incorpora las protecciones de software mediante un instalador revisable. Preserva rutas y clasificación de partidas: no mueve una partida para «hacerla aparecer» ni sustituye tu archivo por una plantilla vacía.

Los respaldos se guardan en `/var/lib/r36s-save-backups/files`, con permisos privados. Cada archivo tiene `first-valid`, `latest` y hasta tres `previous-N`. El servicio revisa las carpetas conocidas cada tres segundos, omite enlaces simbólicos, archivos mayores de 2 MiB y contenido completamente vacío/`FF`/`00`. Limita el almacén a 48 MiB y reserva 20 MiB libres.

Rutas cubiertas: guardados y estados de RetroArch en su ubicación habitual, `HOME/Juegos`, saves/states del port de God of War, datos conocidos de SRB2 y puntuaciones de Neverball. **Una ruta personalizada fuera de esas carpetas no queda cubierta automáticamente.** Revisa `Guard.roots` antes de depender de ella.

La restauración automática se realiza al arrancar el servicio, cuando el original falta o está vacío. No reemplaza archivos no vacíos basándose en suposiciones sobre su validez. No hay interpretación completa de todos los formatos; un archivo no vacío puede estar corrupto y una lectura concurrente puede no representar una partida coherente.

La versión pública no ejecuta reparación FAT ni inserta un `fsck` de arranque. Esa parte de nuestra intervención era específica de la tarjeta y del orden de arranque. Una tarjeta con errores necesita diagnóstico independiente.

## Prueba manual con un juego propio

1. Respalda fuera de la consola cualquier partida existente.
2. Abre un juego propio sin progreso importante y guarda desde el menú del juego.
3. Espera unos segundos y sal con **START + SELECT**, sin FN. Comprueba que recupera el guardado al volver a abrir.
4. Sal, apaga mediante el menú, espera a que termine el apagado y vuelve a encender.
5. Abre el juego y verifica el progreso concreto. Ver solo el nombre del archivo no basta.
6. Revisa también que el servicio haya creado una copia y que `/tmp/r36s-saveguard.log` no muestre errores.

Si aparece «Nueva partida», no guardes encima de la partida que esperabas recuperar. Cierra, conserva archivos y respaldos y revisa la ruta usada por ese núcleo/juego.

## Si la tarjeta falla

- Deja de escribir en ella. No formatees ni lances reparaciones repetidas sin una copia.
- Trabaja con un lector y crea una imagen completa antes de reparar si necesitas recuperar datos.
- Una comprobación/reparación FAT debe hacerse **con la partición desmontada**. Este proyecto no selecciona automáticamente un `/dev/sdX` por ti.
- Si tienes una copia válida, restáurala al archivo que efectivamente utiliza el emulador, con el juego cerrado y conservando antes el archivo actual.

Los respaldos internos y HOME residen en la **misma microSD**. Copia periódicamente los datos a la laptop o a otra unidad: si falla físicamente la tarjeta, el respaldo interno puede perderse con ella.

## Deshacer el módulo

Usa `install.sh restore --backup DIRECTORIO` con la ruta devuelta por la instalación, desde root y sin juego abierto. Detiene el servicio y restaura solo archivos sin modificaciones posteriores. No borra las partidas ni el almacén de copias. El toolkit y el firmware se mantienen.
