# Juegos, música, lectura e internet

## Juegos

Añade tus juegos según la estructura del [firmware](https://github.com/CodeZombie/goodluckOS#how-do-i-add-games) y tus archivos `.puppy`. Las ROMs, BIOS, traducciones empaquetadas con juegos y partidas personales no están en este repositorio. Para homebrew/ports, usa la [página enlazada por goodluckOS](https://ga36.genserek.net/) y los repositorios de cada autor.

En nuestra unidad se integraron GBA, GB/GBC, SNES, PS1 y algunos PSP, además de Celeste Classic, Skyland, Blind Jump, Freedoom, Sonic Robo Blast 2, Neverball y Neverputt. El port nativo de Mario 64 quedó pendiente. Consulta [HISTORIA.md](HISTORIA.md) para distinguir juegos instalados de recomendaciones.

Los núcleos y ports tienen sus propias licencias, dependencias y formatos de guardado. Un título de PSP que llega al menú puede ir lento durante la partida. Digimon Rumble Arena presentó una pantalla negra posterior a una imagen inicial; no se acreditó su funcionamiento completo.

## Referencia PSP

Nuestro núcleo PPSSPP se ajustó a JIT, memoria rápida, transformación por hardware, resolución 480 × 272/1×, sin escalado de texturas ni anisotropía, cachés habilitadas y spline bajo. God of War y Tekken utilizaron salto automático de hasta un fotograma; 3rd Strike se dejó sin salto.

No se instala un archivo `.opt` genérico en todos los núcleos: **las claves y rutas dependen de la versión del emulador**. Si experimentas, cambia un valor cada vez, conserva la configuración original y compara una escena real. El módulo `performance` solo configura CPU/GPU a través de los puntos de lanzamiento reconocidos.

La prueba de arranque de God of War pasó de 16,1 a 14,7 segundos. No mide combate. El modo de compatibilidad de 30 FPS no demostró una mejora fiable y fue revertido. El PPSSPP nativo se probó aparte y no reemplazó el núcleo principal. No hay promesa de 60 FPS ni equivalencia con otra placa.

## Música con kew

[kew](https://github.com/ravachol/kew) es el reproductor que dejamos finalmente. CMP se retiró. La compilación ARM32 y la adaptación completa de botones no están empaquetadas en esta primera publicación; sigue el código fuente y las instrucciones del autor, comprobando dependencias ARM.

Si ya tienes una versión funcional de kew compatible con estas opciones:

```ini
coverEnabled=1
coverAnsi=0
visualizerEnabled=1
```

Edita solo esas claves de tu configuración existente y guarda copia antes. `coverAnsi=0` permitió usar bloques de color en nuestra terminal; no todos los terminales admiten sixel. Una portada cuadrada embebida en el archivo o junto al álbum mejora el resultado. No se incluye nuestra canción de prueba.

En nuestra configuración el lanzador abría `kew all` cuando no recibía una búsqueda y no usaba `--nocover`. Cambia el comando solo si tu versión lo admite; usa el menú del propio kew para verificar reproducción, pausa y salida antes de añadirlo a Kennel.

## Lectura y vídeo

Kennel proporciona su lector de ebooks y terminal con teclado. Los PDF de nuestra intervención se abrían con fbpdf; los vídeos con FFplay. Esos binarios no se publican aquí y requieren su propia instalación/compilación compatible.

Probamos vídeo local básico y YouTube a 360p, no reproducción HD garantizada. El ajuste de volumen debe comprobarse en el mezclador del firmware además del reproductor. No fuerces auriculares si tu versión de firmware tiene advertencias de audio experimental.

## Internet

Nuestra intervención habilitó red USB NCM con módulos preparados para el kernel exacto de la consola y verificó DNS/HTTPS desde la laptop. Después añadimos YouTube ligero, radio, podcasts RSS y Spotify Connect. Spotify quedó sin vincular a la cuenta; los podcasts sin una prueba final elegida por el usuario.

**No se distribuyen aquí aquellos módulos ni un cambio genérico de USB.** Cargar módulos de otro kernel o modificar el gadget sin una ruta de recuperación puede cortar terminal y MTP. Las versiones nuevas de firmware/Kennel pueden añadir controles propios: consulta su documentación para tu versión.

Android quedó preparado, sin prueba directa completa registrada. Un adaptador Wi-Fi con antena fue investigado, pero no instalado ni validado físicamente. Esta publicación no convierte la consola en un dispositivo Wi-Fi, SDR o NFC por software.
