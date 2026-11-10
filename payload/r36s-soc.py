#!/usr/bin/env python3
"""Local, read-only SOC exercises. SPDX-License-Identifier: GPL-2.0-or-later."""
import hashlib
import ipaddress
from pathlib import Path
import re
import shutil
import subprocess

LIMIT = 32 * 1024 * 1024
TOOLS = Path('/opt/r36s-toolkit/bin')


def tool(name, args):
    path = TOOLS / name
    binary = str(path) if path.is_file() else shutil.which(name)
    if not binary:
        print('No instalado:', name, '— consulta docs/TOOLKIT.md')
        return
    try:
        subprocess.run([binary, *args], timeout=30, check=False)
    except subprocess.TimeoutExpired:
        print('Se agotaron los 30 segundos de esta operación.')


def analyze(action, path):
    path = path.expanduser().resolve(strict=True)
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError('Elige un archivo regular de hasta 32 MiB, no una carpeta.')
    # Absolute resolved paths cannot become command-line switches; never use a shell.
    if action == 'hash':
        with path.open('rb') as stream:
            value = hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else None
        if value is None:
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(65536), b''):
                    h.update(chunk)
            value = h.hexdigest()
        print(value, path.name)
    elif action == 'file':
        tool('file', [str(path)])
        tool('strings', ['-n', '8', str(path)])
    elif action == 'ioc':
        text = path.read_text(errors='replace')
        candidates = sorted(set(re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)))
        for value in candidates:
            try:
                print('IPv4:', ipaddress.ip_address(value))
            except ValueError:
                pass
        for value in sorted(set(re.findall(r'https?://[^\s<>"\x27]+', text))):
            print('URL:', value)
        print('Indicadores sintácticos; no es una clasificación de amenaza.')
    elif action == 'pcap':
        tool('tcpdump', ['-n', '-c', '100', '-r', str(path)])
    elif action == 'firmware':
        tool('binwalk', ['--signature', str(path)])  # Never extract or execute the sample.


def main():
    actions = {'1': 'file', '2': 'ioc', '3': 'pcap', '4': 'hash', '5': 'firmware'}
    while True:
        print('\nSOC local · 1 Archivo · 2 IOC · 3 PCAP · 4 SHA256 · 5 Firmware · 0 Salir')
        try:
            choice = input('Opción: ').strip()
            if choice == '0':
                return
            if choice not in actions:
                continue
            analyze(actions[choice], Path(input('Ruta del archivo: ').strip()))
        except (OSError, ValueError) as exc:
            print('No se analizó:', str(exc))
        except (EOFError, KeyboardInterrupt):
            return


if __name__ == '__main__':
    main()
