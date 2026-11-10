# Autores, referencias y licencias

El firmware, los emuladores, el launcher y los juegos pertenecen a sus respectivos proyectos. No se presentan como desarrollos propios de r36s-mod. No se redistribuyen binarios ni recursos de juegos.

| Proyecto | Uso/referencia | Licencia indicada por el proyecto |
|---|---|---|
| [goodluckOS](https://github.com/CodeZombie/goodluckOS) | Firmware, integración y supervisor de aplicaciones | GPL-2.0 |
| [Kennel](https://github.com/rincewindcz/kennel) | Launcher, lector y terminal con teclado | MIT; fuentes/iconos tienen avisos adicionales |
| [kew](https://github.com/ravachol/kew) | Reproductor musical final de nuestra consola | GPL-2.0-or-later |
| [Debian](https://www.debian.org/) | Paquetes ARMHF para la receta de toolkit | Licencias individuales incluidas en los paquetes |
| [RetroArch](https://github.com/libretro/RetroArch) / [PPSSPP](https://github.com/hrydgard/ppsspp) | Contexto de emulación y perfiles de nuestra instalación | Ver licencias de cada proyecto y núcleo |
| [Sonic Robo Blast 2](https://github.com/STJr/SRB2) / [Neverball](https://github.com/Neverball/neverball) | Ports utilizados en la intervención histórica | Ver código y datos de cada proyecto |

Referencias revisadas el 10 de noviembre de 2026:

- goodluckOS: versión de intervención `0.1.0`; hash SHA256 de la referencia oficial `rootfs/board/my-device/rootfs-overlay/usr/local/bin/appctl`: `8b32ebc9ef6d90a196bd92d31dda17ed72e5d0444974141e9a35f76e22d04a51`.
- [README de goodluckOS](https://github.com/CodeZombie/goodluckOS/blob/4b51c1f4b20a3247448750d0a45189fa33b6d319/README.md): identificación y builder oficial.
- [Kennel](https://github.com/rincewindcz/kennel/tree/57e23d4e3954ce18b26019f425f769265520b8c4): instalación del ZIP en HOME, fuentes `.puppy` y lector/terminal.
- [kew](https://github.com/ravachol/kew/tree/795be2d2541ed6c6f9f83d4e35a87e07ad5feb93): proyecto del reproductor; no implica que esa revisión exacta sea la compilada en nuestra intervención anterior.

Los enlaces a releases pueden cambiar. El instalador no descarga ni ejecuta código de la rama principal de esos proyectos. Sus módulos se limitan a archivos propios y a un parche generado contra un supervisor cuyo contenido se verifica.

Los parches al supervisor goodluckOS se publican bajo GPL-2.0-or-later, junto al resto del código propio de este repositorio. La licencia no cambia las condiciones de los componentes externos.
