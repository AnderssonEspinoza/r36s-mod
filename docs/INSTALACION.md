# Instalación paso a paso

## 0. Qué vas a instalar

Este proyecto añade módulos a **goodluckOS en una GA36-MB A33 ARM32**. No instala el firmware, no incluye el catálogo de nuestras fotos y no convierte un RK3326 en A33. El instalador público es nuevo; pruébalo primero en una tarjeta de repuesto y conserva una copia externa.

Necesitas una laptop Linux, lector microSD para preparar el sistema, cable USB de datos, tarjeta de repuesto, tu respaldo original y acceso al terminal root de la consola. Para el constructor del toolkit: Python 3, APT y `dpkg-deb` en Debian/Ubuntu/Mint. No uses estos pasos como instrucciones de flasheo para otros equipos.

## 1. Identifica y respalda

1. Usa el [Firmware Builder oficial](https://codezombie.github.io/goodluckOS/download.html) para identificar tu variante a partir de la tarjeta original.
2. Conserva una imagen completa de esa tarjeta y copia aparte las partidas, incluidos los archivos `.srm`, `.sav`, tarjetas virtuales y estados que uses.
3. Verifica qué tarjeta es la original y cuál es la de prueba por capacidad real e identificadores; una etiqueta «64 GB» no garantiza esa capacidad.
4. Guarda la original. Evita seleccionar unidades por una ruta fija como `/dev/sda`, que puede cambiar al reconectar.

El builder oficial necesita datos del arranque original y permite generar el firmware adecuado. Sigue sus instrucciones de grabación y selección de panel. **No publicamos una imagen genérica que debas grabar a ciegas.** Nuestra instalación histórica utilizó goodluckOS 0.1.0 / A33 Gecko / Panel 1; eso no identifica el panel de otra consola.

## 2. Arranca goodluckOS e instala Kennel

Cuando goodluckOS arranque y Puppy funcione:

1. Descarga `kennel-glos.zip` desde las [releases oficiales de Kennel](https://github.com/rincewindcz/kennel/releases).
2. Descomprímelo en la raíz de HOME. Por MTP, es `GA36MB → HOME`.
3. Abre Kennel desde la categoría System de Puppy.
4. En Kennel elige `Settings → Launcher at boot → kennel`.

Ese es el procedimiento del autor de Kennel. El lector y el terminal con teclado vienen en su paquete. No cambies ni borres los archivos `.puppy` que ya tengan tus juegos.

Si no hay una release disponible, consulta su [README de compilación](https://github.com/rincewindcz/kennel#build). La compilación cruzada necesita más espacio y dependencias que esta instalación modular; no se ejecuta automáticamente.

## 3. Prepara Python o el toolkit SOC

Sigue [TOOLKIT.md](TOOLKIT.md). El instalador requiere **Python 3.9 o posterior**; el constructor usa Debian bookworm ARMHF y obtiene Python 3.11 con sus dependencias.

La ubicación esperada en la consola es `/opt/r36s-toolkit/bin/python3`. Si ya existe un toolkit en esa ruta, **no lo reemplaces**. Comprueba primero:

```sh
/opt/r36s-toolkit/bin/python3 -c 'import argparse, pathlib, json, shutil, subprocess; print("Python preparado")'
```

No añadas una contraseña compartida ni copies `/etc/shadow` desde otra consola. Configura tu propia contraseña mediante `passwd` en la sesión root.

## 4. Copia y revisa este proyecto

En la laptop:

```bash
git clone https://github.com/AnderssonEspinoza/r36s-mod.git
cd r36s-mod
python3 -m unittest discover -s tests -v
```

Copia el código del repositorio a `HOME/ports/r36s-mod`. No necesitas transferir `.git`, `build` ni `__pycache__`. Puedes exportar una carpeta limpia usando los archivos del commit:

```bash
mkdir -p ../r36s-mod-transfer
git archive HEAD | tar -x -C ../r36s-mod-transfer
```

En la consola, abre un terminal o conecta la terminal serial del firmware con tus propias credenciales. La laptop suele detectar el terminal como `/dev/ttyACM0`, pero verifica el nombre real. Ejecuta **dentro de la consola**:

```sh
cd /home/player/ports/r36s-mod
sh install.sh doctor
sh install.sh plan
```

`doctor` identifica firmware, arquitectura, placa y montajes. `plan` verifica los requisitos y muestra los archivos que cambiaría. Ninguno instala ni modifica archivos.

## 5. Aplica solo después de revisar el plan

Desde una sesión **root en la consola**, con los juegos cerrados:

```sh
cd /home/player/ports/r36s-mod
sh install.sh apply
```

Para seleccionar componentes, usa el mismo conjunto en `plan` y `apply`:

```sh
sh install.sh plan --modules saves performance
sh install.sh apply --modules saves performance
```

Qué modifica cada módulo:

| Módulo | Archivos |
|---|---|
| `saves` | Supervisor `appctl`, configuración principal de RetroArch, opciones de HOME en `/etc/fstab`, programa saveguard y servicio de inicio |
| `performance` | Helper de frecuencia y hooks en `appctl` |
| `soc` | Programa SOC y un archivo propio `.puppy` en `~/.local/share/applications` |

Los cambios al supervisor solo se generan si su contenido coincide con la referencia oficial de goodluckOS 0.1.0. Se conservan **todos** los originales antes de la primera escritura, en un directorio root con permisos privados. Si falla una escritura, se intenta revertir lo ya escrito.

Anota la ruta de respaldo que muestra el instalador. **No cambia el arranque inmediatamente ni reinicia servicios**: usa el apagado del menú y vuelve a encender. Desconecta el cable si tu firmware presenta problemas de reinicio USB.

## 6. Comprueba el resultado

1. Confirma que Kennel vuelve a arrancar y tus entradas siguen presentes.
2. Abre `SOC y forense → Laboratorio SOC (r36s-mod)` si elegiste ese módulo.
3. Si instalaste `saves`, revisa `ps` y `/tmp/r36s-saveguard.log`; debería existir el proceso del servicio, sin errores de importación Python.
4. Comprueba `/proc/mounts`: HOME debe incluir `rw,sync` después del encendido.
5. Haz la [prueba manual de guardado](GUARDADOS.md#prueba-manual-con-un-juego-propio) antes de confiarle una partida larga.
6. Para rendimiento, revisa el gobernador durante un juego de RetroArch y al volver al menú; debe restaurar el valor anterior.

## Si el instalador se detiene

- **Placa distinta:** no lo fuerces. Usa documentación de tu plataforma.
- **Supervisor distinto o ya modificado:** esto incluye nuestra propia consola personalizada. El instalador no intenta adivinar ni reemplazarlo. Compara los cambios en `scripts/r36s_mod.py` y pide revisión para tu versión. Puedes instalar solo `soc` si cumple sus requisitos, pero no conviertas ese diagnóstico en un permiso para sobrescribir el supervisor.
- **HOME en solo lectura:** puede haber corrupción o un problema de almacenamiento. No la remonte a escritura para ocultarlo. Respalda y revisa desmontada desde un lector.
- **Falta Python/Kennel:** completa los pasos previos.
- **Sin espacio en la raíz:** la instalación exige al menos 25 MiB libres. No borres archivos del sistema al azar.
- **La nueva versión de firmware cambia las rutas:** el perfil de esta versión no está validado para ella; no se garantiza que baste con cambiar el hash.

## Desinstalar

Con los juegos cerrados, desde root:

```sh
sh install.sh restore --backup /var/lib/r36s-mod/backups/FECHA-PID
```

Sustituye el ejemplo por el directorio real. El programa comprueba todos los archivos antes de restaurar; si alguno tiene cambios posteriores, se detiene sin sobrescribirlos. Conserva las partidas y los respaldos de saveguard. Apaga desde el menú y vuelve a encender después.

La restauración cubre el overlay aplicado por este instalador. No desinstala goodluckOS, Kennel ni el toolkit, que se instalaron por separado.
