# Toolkit ARM32 sin instalar paquetes ARM en tu laptop

`scripts/build-toolkit.py` construye un árbol aislado para la consola usando paquetes **Debian bookworm armhf**. Obtiene índices APT firmados, valida los paquetes mediante APT y extrae sus datos con `dpkg-deb -x`. No ejecuta scripts de instalación de los paquetes, no modifica la configuración APT de tu sistema y no instala nada en la laptop.

Es una receta nueva para reconstruir herramientas, no una copia exacta de nuestro antiguo toolkit privado. **La descarga/extracción se verifica en la laptop; la ejecución del paquete resultante requiere validación en tu consola.** Si una herramienta necesita configuración de un servicio o un script de mantenimiento de Debian, extraer el paquete puede no bastar.

## Construir

En una laptop Debian/Ubuntu/Mint con Python 3, `apt-get` y `dpkg-deb`, **sin sudo**:

```bash
python3 scripts/build-toolkit.py
python3 scripts/build-toolkit.py --build
```

El primer comando muestra el plan. El segundo descarga el perfil mínimo con Python completo. Se usan directorios propios dentro de `build/toolkit-minimal`. Si falta el keyring de Debian, se obtiene `debian-archive-keyring` desde los repositorios APT autenticados de tu laptop y se extrae localmente. Si falla la autenticación, el proceso se detiene: no utiliza `--allow-unauthenticated`.

Otros perfiles:

```bash
python3 scripts/build-toolkit.py --profile soc --build
python3 scripts/build-toolkit.py --profile full --build
```

| Perfil | Contenido principal |
|---|---|
| `minimal` | Python 3 y dependencias |
| `soc` | Python, file, strings/binutils, xxd, tcpdump, YARA y Binwalk |
| `full` | Lo anterior más Nmap, TShark, Git, tmux, nnn, editores, htop, SQLite, jq, ripgrep, curl/wget, dig, SSH cliente y pyserial |

El tamaño depende de las versiones y dependencias resueltas. `full` puede ocupar bastante más que el perfil mínimo; mira el resumen de APT antes de copiar y comprueba espacio libre en la consola. No se crean servicios de red de escucha.

El constructor no sobrescribe una construcción anterior. Si quieres volver a construir, renombra su directorio para conservarlo. Los paquetes se actualizan en los repositorios de Debian; `packages.txt` registra las versiones exactas de cada construcción, pero no se afirma que dos fechas produzcan archivos idénticos.

## Transferir

La salida es:

```text
build/toolkit-minimal/
├── bundle/opt/r36s-toolkit/
├── packages.txt
├── r36s-toolkit.tar.gz
└── SHA256SUMS
```

Si elegiste `soc` o `full`, usa su directorio correspondiente. Conserva el archivo TAR para mantener enlaces simbólicos: copiar individualmente por MTP puede perderlos.

1. Comprueba localmente el archivo generado:

   ```bash
   cd build/toolkit-minimal
   sha256sum -c SHA256SUMS
   ```

2. Copia **ese TAR generado por ti** y `SHA256SUMS` a la raíz HOME de la consola. No uses un bundle recibido de terceros sin verificar su procedencia. El checksum detecta cambios en la transferencia, no acredita por sí solo a su autor.
3. Desde el terminal root de la consola, comprueba el espacio y la ausencia de una instalación anterior:

   ```sh
   df -h / /home/player
   test ! -e /opt/r36s-toolkit
   ```

   Si la segunda instrucción no termina correctamente, **detente**: ya existe una instalación que debes conservar. No mezcles perfiles o versiones encima de ella.

4. Verifica y extrae únicamente si la ruta estaba libre y tienes espacio suficiente:

   ```sh
   cd /home/player
   sha256sum -c SHA256SUMS
   mkdir -p /opt
   test ! -e /opt/r36s-toolkit && tar -xzf r36s-toolkit.tar.gz -C /opt
   /opt/r36s-toolkit/bin/python3 -c 'import argparse, pathlib, json, shutil, subprocess; print("Python preparado")'
   ```

   No continúes si falla la verificación del checksum o la prueba de Python. Este paso necesita espacio en la **partición raíz**, no solo en HOME. Nuestra raíz original era pequeña; si no cabe el perfil elegido, usa `minimal` y revisa una ubicación alternativa con alguien que conozca el firmware, sin mover bibliotecas del sistema.

## Uso

Los ejecutables se llaman por su ruta, por ejemplo:

```sh
/opt/r36s-toolkit/bin/python3 --version
/opt/r36s-toolkit/bin/file /home/player/ejemplo.txt
/opt/r36s-toolkit/bin/tcpdump -n -c 20 -r /home/player/captura-de-prueba.pcap
```

No se sustituyen `/lib`, `/usr/bin/python3` ni libc del firmware. Los wrappers usan el cargador dinámico y las bibliotecas del árbol aislado. Si una dependencia no funciona con el kernel o hardware, conserva el error y no copies bibliotecas sobre el sistema para resolverlo.

El menú SOC limita sus entradas a archivos de hasta 32 MiB y 30 segundos por comando externo. En esta primera versión las rutas se escriben con el teclado en pantalla: no es una reproducción exacta de los seis selectores de nuestro menú personal. `IOC` encuentra patrones de direcciones y enlaces; no determina por sí solo si un archivo es malicioso. Binwalk se usa para firmas, **sin extracción automática**.

Para compartir un bundle de terceros fuera de tu equipo, revisa sus licencias y las obligaciones de distribución de código fuente. Este repositorio publica la receta, no distribuye los paquetes compilados.
