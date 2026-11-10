#!/usr/bin/env python3
"""Build an isolated Debian armhf toolkit using signed apt indexes. GPL-2.0-or-later.

Runs on a Debian/Ubuntu/Mint PC as a regular user. No host packages are installed.
The generated bundle is for local transfer, not committed or redistributed here.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

GROUPS = {
    'minimal': ['python3'],
    'soc': ['python3', 'file', 'binutils', 'xxd', 'tcpdump', 'yara', 'binwalk'],
    'full': ['python3', 'file', 'binutils', 'xxd', 'tcpdump', 'yara', 'binwalk',
             'nmap', 'tshark', 'git', 'tmux', 'nnn', 'nano', 'micro', 'htop', 'sqlite3',
             'jq', 'ripgrep', 'curl', 'wget', 'bind9-dnsutils', 'openssh-client', 'python3-serial'],
}
COMMANDS = {'python3', 'file', 'strings', 'xxd', 'tcpdump', 'yara', 'binwalk', 'nmap',
            'tshark', 'git', 'tmux', 'nnn', 'nano', 'micro', 'htop', 'sqlite3', 'jq',
            'rg', 'curl', 'wget', 'dig', 'ssh'}


def wrappers(bundle):
    root = bundle / 'opt/r36s-toolkit/root'
    out = bundle / 'opt/r36s-toolkit/bin'
    out.mkdir(parents=True)
    for name in sorted(COMMANDS):
        binary = root / 'usr/bin' / name
        if not binary.exists():
            # Python's /usr/bin/python3 is usually a relative symlink into the same tree.
            continue
        header = '''#!/bin/sh
set -eu
R=/opt/r36s-toolkit/root
export LD_LIBRARY_PATH="$R/usr/lib/arm-linux-gnueabihf:$R/lib/arm-linux-gnueabihf:$R/usr/lib:$R/lib"
export SSL_CERT_FILE="$R/etc/ssl/certs/ca-certificates.crt"
export CURL_CA_BUNDLE="$SSL_CERT_FILE"
export GIT_EXEC_PATH="$R/usr/lib/git-core"
export MAGIC="$R/usr/share/misc/magic.mgc"
export TERMINFO="$R/usr/share/terminfo"
export PYTHONHOME="$R/usr"
L="$R/usr/lib/arm-linux-gnueabihf/ld-linux-armhf.so.3"
[ -x "$L" ] || L="$R/lib/arm-linux-gnueabihf/ld-linux-armhf.so.3"
[ -x "$L" ] || { echo 'No se encuentra el cargador ARM del toolkit.' >&2; exit 1; }
'''
        # Debian binwalk 2 is a Python script; other selected commands are ELF.
        with binary.open('rb') as stream:
            is_elf = stream.read(4) == b'\x7fELF'
        command = f'"$R/usr/bin/{name}"' if is_elf else f'"$R/usr/bin/python3" "$R/usr/bin/{name}"'
        script = header + f'exec "$L" --library-path "$LD_LIBRARY_PATH" {command} "$@"\n'
        (out / name).write_text(script)
        (out / name).chmod(0o755)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=GROUPS, default='minimal')
    parser.add_argument('--build', action='store_true', help='Download/extract; otherwise show the plan')
    args = parser.parse_args()
    print('Debian bookworm / armhf:', ', '.join(GROUPS[args.profile]))
    print('Destino: build/toolkit-' + args.profile)
    if not args.build:
        print('Vista previa. Añade --build para descargar desde el archivo oficial firmado.')
        return 0
    if os.geteuid() == 0:
        raise ValueError('Ejecuta este constructor SIN sudo en la laptop.')
    for name in ('apt-get', 'dpkg-deb'):
        if not shutil.which(name):
            raise ValueError('Falta ' + name + ' en la laptop.')
    work = Path(__file__).resolve().parent.parent / 'build' / ('toolkit-' + args.profile)
    if work.exists():
        raise ValueError('Ya existe ' + str(work) + '; no se borra ni sobrescribe automáticamente.')
    for path in ('state/lists/partial', 'cache/archives/partial', 'bundle/opt/r36s-toolkit/root'):
        (work / path).mkdir(parents=True)
    key = Path('/usr/share/keyrings/debian-archive-keyring.gpg')
    if not key.is_file():
        # Bootstrap from the PC's authenticated apt repositories, without installing.
        keys = work / 'keyring'
        keys.mkdir()
        subprocess.run(['apt-get', 'download', 'debian-archive-keyring'], cwd=keys, check=True)
        packages = list(keys.glob('debian-archive-keyring_*.deb'))
        if len(packages) != 1:
            raise ValueError('No se pudo obtener el keyring desde los repositorios de la laptop.')
        subprocess.run(['dpkg-deb', '-x', str(packages[0]), str(keys)], check=True)
        key = keys / 'usr/share/keyrings/debian-archive-keyring.gpg'
        if not key.is_file():
            raise ValueError('Falta el keyring de Debian; no se desactiva la verificación.')
    (work / 'state/status').touch()
    sources = work / 'sources.list'
    sources.write_text(f'deb [arch=armhf signed-by={key}] https://deb.debian.org/debian bookworm main\n'
                       f'deb [arch=armhf signed-by={key}] https://deb.debian.org/debian-security bookworm-security main\n')
    options = ['-o', f'Dir::Etc::sourcelist={sources}', '-o', 'Dir::Etc::sourceparts=-',
               '-o', f'Dir::State={work / "state"}', '-o', f'Dir::State::status={work / "state/status"}',
               '-o', f'Dir::Cache={work / "cache"}', '-o', 'APT::Architecture=armhf',
               '-o', 'APT::Architectures::=armhf', '-o', 'Acquire::Languages=none',
               '-o', 'APT::Install-Recommends=false', '-o', 'APT::Install-Suggests=false']
    # apt verifies InRelease signatures and package hashes; no insecure override flags.
    subprocess.run(['apt-get', *options, 'update'], check=True)
    subprocess.run(['apt-get', *options, '--yes', '--download-only', 'install', *GROUPS[args.profile]], check=True)
    packages = sorted((work / 'cache/archives').glob('*.deb'))
    if not packages:
        raise ValueError('No se descargaron paquetes.')
    root = work / 'bundle/opt/r36s-toolkit/root'
    versions = []
    for package in packages:
        versions.append(subprocess.check_output(['dpkg-deb', '-f', str(package), 'Package', 'Version', 'Architecture'], text=True))
        # Extract data only. Never run package maintainer scripts.
        subprocess.run(['dpkg-deb', '-x', str(package), str(root)], check=True)
    (work / 'packages.txt').write_text('\n'.join(versions))
    certs = Path('/etc/ssl/certs/ca-certificates.crt')
    if certs.is_file():
        target = root / 'etc/ssl/certs/ca-certificates.crt'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(certs, target)
    wrappers(work / 'bundle')
    loaders = [root / p for p in ('usr/lib/arm-linux-gnueabihf/ld-linux-armhf.so.3',
                                  'lib/arm-linux-gnueabihf/ld-linux-armhf.so.3')]
    if not any(p.is_file() for p in loaders):
        raise ValueError('El paquete no contiene el cargador ARM esperado; no se crea el archivo.')
    archive = work / 'r36s-toolkit.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(work / 'bundle/opt/r36s-toolkit', arcname='r36s-toolkit')
    with archive.open('rb') as stream:
        checksum = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    (work / 'SHA256SUMS').write_text(checksum.hexdigest() + '  r36s-toolkit.tar.gz\n')
    print('Preparado en:', work / 'bundle/opt/r36s-toolkit')
    print('Lee docs/TOOLKIT.md antes de transferir. No se ejecutaron binarios ARM aquí.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print('DETENIDO:', str(exc), file=sys.stderr)
        sys.exit(1)
