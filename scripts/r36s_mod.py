#!/usr/bin/env python3
"""Read-only by default, reversible goodluckOS overlay. GPL-2.0-or-later."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

BASE = Path(__file__).resolve().parent.parent
APPCTL_SHA256 = '8b32ebc9ef6d90a196bd92d31dda17ed72e5d0444974141e9a35f76e22d04a51'
BACKUPS = Path('/var/lib/r36s-mod/backups')
MODULES = ('saves', 'performance', 'soc')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def mount_info(root=Path('/')):
    rows = (root / 'proc/mounts').read_text().splitlines()
    result = {}
    for row in rows:
        fields = row.split()
        if len(fields) >= 4:
            result[fields[1]] = (fields[0], fields[2], fields[3].split(','))
    return result


def inspect(root=Path('/'), machine=None):
    def read(name):
        p = root / name
        return p.read_text(errors='replace').replace('\0', ' ') if p.exists() else ''
    compatible = read('proc/device-tree/compatible')
    model = read('proc/device-tree/model')
    release = read('etc/os-release')
    machine = machine or platform.machine()
    mounts = mount_info(root)
    home = mounts.get('/home/player', ('', '', []))
    rootfs = mounts.get('/', ('', '', []))
    issues = []
    if 'sun8i-a33' not in compatible or not any(w in model.lower() for w in ('ga36', 'r36', 'gecko')):
        issues.append('Placa no identificada como GA36/R36 A33: no aplicar este perfil.')
    if machine not in ('armv7l', 'armv7'):
        issues.append('Este perfil requiere ARM de 32 bits, no RK3326/aarch64/x86.')
    if not re.search(r'^ID=["\']?goodluckos["\']?$', release, re.M):
        issues.append('No se ha identificado goodluckOS.')
    if home[1] != 'vfat' or 'rw' not in home[2]:
        issues.append('HOME debe estar montada vfat y en escritura; no se intenta repararla aquí.')
    if rootfs[1] != 'ext4' or 'rw' not in rootfs[2]:
        issues.append('La raíz debe ser ext4 en escritura para conservar los respaldos.')
    return {'model': model.strip(), 'compatible': compatible.strip(), 'machine': machine,
            'home_mount': home, 'root_mount': rootfs, 'issues': issues}


def set_config(text, values):
    lines = [line for line in text.splitlines() if line.split('=', 1)[0].strip() not in values]
    return '\n'.join(lines) + '\n' + ''.join(f'{key} = "{value}"\n' for key, value in values.items())


def sync_home(text):
    rows = text.splitlines()
    matches = 0
    for index, row in enumerate(rows):
        fields = row.split()
        if not fields or fields[0].startswith('#') or len(fields) < 4:
            continue
        if fields[1] != '/home/player':
            continue
        if fields[2] != 'vfat':
            raise ValueError('fstab HOME no es vfat; se requiere revisión manual.')
        options = [item for item in fields[3].split(',')
                   if item not in ('async', 'sync') and not item.startswith('errors=')]
        options.extend(('sync', 'errors=remount-ro'))
        fields[3] = ','.join(options)
        rows[index] = '\t'.join(fields)
        matches += 1
    if matches != 1:
        raise ValueError('Se esperaba una única entrada HOME en fstab.')
    return '\n'.join(rows) + '\n'


def patch_appctl(data, modules):
    if digest(data) != APPCTL_SHA256:
        raise ValueError('appctl no coincide con la referencia de goodluckOS 0.1.0. '
                         'No se parchea un supervisor desconocido o ya modificado. '
                         'Consulta docs/INSTALACION.md.')
    text = data.decode()
    if 'saves' in modules:
        old = '''do_stop_app() {
    [ "$APP_GEN" != 0 ] && cg_signal "$CG_ROOT/app" TERM
}'''
        new = '''do_stop_app() {
    [ "$APP_GEN" != 0 ] || return 0
    # R36S-MOD: let RetroArch save before its parent exits.
    _ra_found=0
    for _ra_pid in $(cat "$CG_ROOT/app/cgroup.procs" 2>/dev/null); do
        read -r _ra_name <"/proc/$_ra_pid/comm" 2>/dev/null || continue
        if [ "$_ra_name" = retroarch ]; then
            kill -TERM "$_ra_pid" 2>/dev/null && _ra_found=1
        fi
    done
    [ "$_ra_found" = 1 ] || cg_signal "$CG_ROOT/app" TERM
}'''
        if text.count(old) != 1:
            raise ValueError('No se encontró el bloque de cierre esperado.')
        text = text.replace(old, new, 1)
        text = text.replace('shutdown_all() {\n', '''shutdown_all() {
    # R36S-MOD: allow up to three seconds for graceful save completion.
    do_stop_app
    _save_wait=0
    while cg_populated "$CG_ROOT/app" && [ "$_save_wait" -lt 30 ]; do
        sleep 0.1
        _save_wait=$((_save_wait+1))
    done
    sync
''', 1)
    if 'performance' in modules:
        text = text.replace('start_launcher() {\n', 'start_launcher() {\n    /usr/local/bin/r36s-game-performance restore\n', 1)
        text = text.replace('shutdown_all() {\n', 'shutdown_all() {\n    /usr/local/bin/r36s-game-performance restore\n', 1)
        anchor = '    STATE=app\n'
        if text.count(anchor) != 1:
            raise ValueError('No se encontró el bloque de lanzamiento esperado.')
        text = text.replace(anchor, '''    # R36S-MOD: native frequencies; restore on return to launcher.
    /usr/local/bin/r36s-game-performance restore
    case "$_cmd" in
        *retroarch*|*god-of-war-psp*|*ports/srb2/*|*ports/neverball/*|*ports/neverputt/*)
            /usr/local/bin/r36s-game-performance start ;;
    esac
''' + anchor, 1)
    with tempfile.NamedTemporaryFile() as check:
        check.write(text.encode())
        check.flush()
        subprocess.run(['/bin/sh', '-n', check.name], check=True, capture_output=True)
    return text.encode()


def safe_target(path):
    current = Path('/')
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError(f'No se modifica una ruta con enlaces simbólicos: {path}')
    if path.exists() and not path.is_file():
        raise ValueError(f'No es un archivo regular: {path}')


def make_plan(modules, root=Path('/')):
    changes = []
    def add(name, data, mode=0o755):
        path = root / name
        safe_target(path)
        changes.append((path, data if isinstance(data, bytes) else data.encode(), mode))
    if {'saves', 'performance'} & set(modules):
        path = root / 'usr/local/bin/appctl'
        safe_target(path)
        add('usr/local/bin/appctl', patch_appctl(path.read_bytes(), modules))
    if 'saves' in modules:
        if not (root / 'opt/r36s-toolkit/bin/python3').is_file():
            raise ValueError('Falta /opt/r36s-toolkit/bin/python3: lee docs/TOOLKIT.md.')
        cfg = root / 'home/player/.config/retroarch/retroarch.cfg'
        safe_target(cfg)
        # Preserve the save paths and sorting already used by this particular console.
        values = {'autosave_interval': '3', 'savestate_auto_load': 'false', 'savestate_auto_save': 'false'}
        add('home/player/.config/retroarch/retroarch.cfg', set_config(cfg.read_text(), values), 0o644)
        fstab = root / 'etc/fstab'
        safe_target(fstab)
        add('etc/fstab', sync_home(fstab.read_text()), 0o644)
        for source, target in [('r36s-saveguard.py', 'usr/local/libexec/r36s-saveguard.py'),
                               ('S56r36s-saveguard', 'etc/init.d/S56r36s-saveguard')]:
            add(target, (BASE / 'payload' / source).read_bytes())
    if 'performance' in modules:
        add('usr/local/bin/r36s-game-performance', (BASE / 'payload/r36s-game-performance').read_bytes())
    if 'soc' in modules:
        if not (root / 'home/player/ports/kennel/kennel-term').is_file():
            raise ValueError('Instala primero Kennel desde su proyecto oficial.')
        if not (root / 'opt/r36s-toolkit/bin/python3').is_file():
            raise ValueError('Falta el toolkit Python: lee docs/TOOLKIT.md.')
        add('usr/local/libexec/r36s-soc.py', (BASE / 'payload/r36s-soc.py').read_bytes())
        add('home/player/.local/share/applications/r36s-mod.puppy', '''[ENTRY]
CATEGORY=SOC y forense
NAME=Laboratorio SOC (r36s-mod)
DESCRIPTION=Análisis local: archivos, hashes, IOC, PCAP y firmware.
COMMAND=/home/player/ports/kennel/kennel-term -e "/opt/r36s-toolkit/bin/python3 /usr/local/libexec/r36s-soc.py"
COLOR=#9475df
''', 0o644)
    return changes


def atomic(path, data, mode, uid, gid):
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_target(path)
    fd, temp = tempfile.mkstemp(prefix='.r36s-mod-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        if os.geteuid() == 0:
            os.chown(temp, uid, gid)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def apply_plan(changes, backup_root=BACKUPS):
    safe_target(backup_root / 'manifest-probe')
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup_root.chmod(0o700)
    folder = backup_root / (time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()))
    folder.mkdir(mode=0o700)
    manifest = {'version': 1, 'files': [], 'state': 'prepared'}
    # Validate and preserve EVERY original before the first target write.
    for i, (target, data, mode) in enumerate(changes):
        safe_target(target)
        info = target.stat() if target.exists() else None
        entry = {'target': str(target), 'existed': info is not None, 'installed_sha256': digest(data),
                 'mode': stat.S_IMODE(info.st_mode) if info else mode,
                 'uid': info.st_uid if info else 0, 'gid': info.st_gid if info else 0,
                 'backup': f'{i}.original'}
        if info:
            original = target.read_bytes()
            entry['original_sha256'] = digest(original)
            atomic(folder / entry['backup'], original, 0o600, os.geteuid(), os.getegid())
        manifest['files'].append(entry)
    manifest_path = folder / 'manifest.json'
    atomic(manifest_path, json.dumps(manifest, indent=2).encode(), 0o600, os.geteuid(), os.getegid())
    os.sync()
    written = []
    try:
        for entry, (target, data, mode) in zip(manifest['files'], changes):
            atomic(target, data, mode, entry['uid'], entry['gid'])
            written.append(entry)
        manifest['state'] = 'installed'
        atomic(manifest_path, json.dumps(manifest, indent=2).encode(), 0o600, os.geteuid(), os.getegid())
        os.sync()
    except Exception:
        for entry in reversed(written):
            target = Path(entry['target'])
            if entry['existed']:
                atomic(target, (folder / entry['backup']).read_bytes(), entry['mode'], entry['uid'], entry['gid'])
            else:
                target.unlink()
        os.sync()
        raise
    return folder


def restore(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest.get('version') != 1 or manifest.get('state') != 'installed':
        raise ValueError('El respaldo no corresponde a una instalación completada.')
    # Check the whole transaction before reverting anything; preserve later user edits.
    for entry in manifest['files']:
        target = Path(entry['target'])
        safe_target(target)
        if not target.is_file() or digest(target.read_bytes()) != entry['installed_sha256']:
            raise ValueError(f'Hay cambios posteriores en {target}; no se sobrescriben.')
        original = folder / entry['backup']
        if entry['existed'] and digest(original.read_bytes()) != entry['original_sha256']:
            raise ValueError('El respaldo original fue alterado.')
    for entry in reversed(manifest['files']):
        target = Path(entry['target'])
        if entry['existed']:
            atomic(target, (folder / entry['backup']).read_bytes(), entry['mode'], entry['uid'], entry['gid'])
        else:
            target.unlink()
    manifest['state'] = 'restored'
    atomic(folder / 'manifest.json', json.dumps(manifest, indent=2).encode(), 0o600, os.geteuid(), os.getegid())
    os.sync()


def no_game_running():
    for comm in Path('/proc').glob('[0-9]*/comm'):
        try:
            name = comm.read_text().strip().lower()
        except OSError:
            continue
        if name in ('retroarch', 'ppssppsdl', 'srb2', 'neverball', 'neverputt'):
            raise ValueError('Cierra los juegos y vuelve al menú antes de aplicar/restaurar.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('doctor', 'plan', 'apply', 'restore'))
    parser.add_argument('--modules', nargs='+', choices=MODULES, default=list(MODULES))
    parser.add_argument('--backup', type=Path, help='Directorio devuelto por apply, solo para restore')
    args = parser.parse_args()
    try:
        report = inspect()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if args.action == 'doctor':
            return 0 if not report['issues'] else 1
        if report['issues']:
            raise ValueError('La comprobación de compatibilidad no pasó; no se escribirá nada.')
        if args.action == 'restore':
            if os.geteuid() != 0 or args.backup is None:
                raise ValueError('restore requiere root y --backup DIRECTORIO.')
            folder = args.backup.resolve()
            if not folder.is_relative_to(BACKUPS.resolve()) or folder.parent != BACKUPS.resolve():
                raise ValueError('El respaldo debe estar directamente dentro de ' + str(BACKUPS))
            no_game_running()
            service = Path('/etc/init.d/S56r36s-saveguard')
            if service.exists():
                subprocess.run([str(service), 'stop'], check=True)
            restore(folder)
            print('Restaurado. Apaga desde el menú y vuelve a encender. No se borraron partidas ni respaldos.')
            return 0
        changes = make_plan(args.modules)
        for path, data, mode in changes:
            print(f'{path}: {len(data)} bytes; permisos {mode:o}')
        if args.action == 'plan':
            print('Solo vista previa: no se escribió ningún archivo.')
            return 0
        if os.geteuid() != 0:
            raise ValueError('apply requiere root dentro de la consola, no sudo en tu laptop.')
        no_game_running()
        if shutil.disk_usage('/').free < 25 * 1024 * 1024:
            raise ValueError('Faltan 25 MiB libres en la raíz para instalar con respaldo.')
        folder = apply_plan(changes)
        print('Instalado. Respaldo:', folder)
        print('Apaga desde el menú y vuelve a encender para cargar los cambios.')
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print('DETENIDO:', str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
