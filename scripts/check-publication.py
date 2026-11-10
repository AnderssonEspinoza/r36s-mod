#!/usr/bin/env python3
"""Check the exact Git index for private content and unwanted binaries. GPL-2.0-or-later."""
from pathlib import Path
import re
import subprocess
import sys

FORBIDDEN = {'.img', '.iso', '.cso', '.gba', '.gb', '.gbc', '.nds', '.chd', '.bin', '.cue',
             '.pbp', '.srm', '.sav', '.mcd', '.rtc', '.zip', '.7z', '.deb', '.pcap', '.pcapng',
             '.mp3', '.flac', '.wad', '.tar', '.gz', '.pyc'}
PATTERNS = [
    rb'gh[pousr]_[A-Za-z0-9]{30,}',
    rb'github_pat_[A-Za-z0-9_]{30,}',
    rb'-----BEGIN ' + rb'(?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
    rb'\$6\$[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{40,}',
    rb'/home/' + rb'andersson',
]


def main():
    failures = []
    files = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
    for name in filter(None, files):
        path = Path(name)
        if path.suffix.lower() in FORBIDDEN or '.state' in path.name.lower():
            failures.append((name, 'archivo privado, juego o binario empaquetado'))
        data = subprocess.check_output(['git', 'show', ':' + name])
        if len(data) > 3 * 1024 * 1024:
            failures.append((name, 'archivo demasiado grande'))
        if path.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            if any(re.search(pattern, data) for pattern in PATTERNS):
                failures.append((name, 'posible secreto o ruta personal; revisar localmente'))
            if data.startswith(b'\x7fELF') or b'\0' in data:
                failures.append((name, 'binario inesperado'))
    for name, reason in failures:
        print(name + ': ' + reason)
    print('Archivos revisados:', len([name for name in files if name]))
    print('Publicación:', 'DETENIDA' if failures else 'sin coincidencias en las reglas configuradas')
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
