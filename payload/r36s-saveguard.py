#!/usr/bin/env python3
"""Versioned backups of small game saves. SPDX-License-Identifier: GPL-2.0-or-later."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import secrets
import time

MAX_FILE = 2 * 1024 * 1024
MAX_STORE = 48 * 1024 * 1024
RESERVE = 20 * 1024 * 1024


def blank(data):
    return not data or not data.strip(b'\xff') or not data.strip(b'\x00')


def confined(path, base):
    """Reject symlinks at every component, even if they resolve back into base."""
    try:
        rel = path.relative_to(base)
        current = base
        if current.is_symlink():
            return False
        for part in rel.parts:
            current = current / part
            if current.is_symlink():
                return False
        return path.resolve().is_relative_to(base.resolve())
    except (ValueError, OSError):
        return False


def durable(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.writing')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if tmp.exists():
            tmp.unlink()


def wanted(path):
    return (path.suffix.lower() in ('.srm', '.sav', '.mcd', '.eep', '.fla', '.rtc', '.ssg')
            or '.state' in path.name.lower() or 'SAVEDATA' in path.parts
            or path.parent.name == 'Scores' or path.name.lower() == 'gamedata.dat')


def open_parent(path, base, create=False, owner=None):
    """Walk through directory fds so a concurrent symlink swap cannot escape HOME."""
    parts = path.relative_to(base).parts
    if not parts or any(p in ('.', '..') for p in parts):
        raise OSError('invalid relative path')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(base, flags)
    try:
        for part in parts[:-1]:
            created = False
            if create:
                try:
                    os.mkdir(part, 0o755, dir_fd=fd)
                    created = True
                except FileExistsError:
                    pass
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            if created and owner is not None:
                os.fchown(fd, *owner)
        return fd, parts[-1]
    except Exception:
        os.close(fd)
        raise


def restore_home(path, base, data):
    owner = None
    if os.geteuid() == 0:
        import pwd
        player = pwd.getpwnam('player')
        owner = (player.pw_uid, player.pw_gid)
    fd, name = open_parent(path, base, create=True, owner=owner)
    temporary = '.r36s-restore-' + secrets.token_hex(12)
    try:
        file_fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=fd)
        with os.fdopen(file_fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            if owner is not None:
                os.fchown(stream.fileno(), *owner)
        os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=fd)
        except FileNotFoundError:
            pass
        os.close(fd)


class Guard:
    def __init__(self, home=Path('/home/player'), store=Path('/var/lib/r36s-save-backups')):
        self.home, self.store = home, store
        self.roots = [home / p for p in (
            '.config/retroarch/saves', '.config/retroarch/states', 'Juegos',
            'ports/god-of-war-psp/saves', 'ports/god-of-war-psp/states',
            '.srb2', '.neverball/Scores')]
        self.known = {}

    def read(self, path, base):
        if not confined(path, base):
            raise OSError('symlink or path outside permitted directory')
        parent, name = open_parent(path, base)
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        finally:
            os.close(parent)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
                raise OSError('not a small regular save')
            data = stream.read(MAX_FILE + 1)
            after = os.fstat(stream.fileno())
        if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            raise OSError('save changed while reading; retry next scan')
        return data

    def restore(self):
        files = self.store / 'files'
        if not files.is_dir():
            return
        for latest in files.rglob('latest'):
            target = self.home / latest.parent.relative_to(files)
            try:
                if not confined(target, self.home):
                    continue
                if target.exists() and not blank(self.read(target, self.home)):
                    continue
                data = self.read(latest, self.store)
                if blank(data):
                    continue
                restore_home(target, self.home, data)
                print('RESTORED', target.relative_to(self.home), flush=True)
            except (OSError, KeyError) as exc:
                print('RESTORE_ERROR', str(exc), flush=True)

    def scan(self):
        for root in self.roots:
            if not root.is_dir() or not confined(root, self.home):
                continue
            for directory, folders, names in os.walk(root, followlinks=False):
                folders[:] = [n for n in folders if not (Path(directory) / n).is_symlink()]
                for name in names:
                    source = Path(directory) / name
                    if not wanted(source) or not confined(source, self.home):
                        continue
                    try:
                        st = source.stat()
                        key = (st.st_mtime_ns, st.st_size)
                        if st.st_size > MAX_FILE or self.known.get(source) == key:
                            continue
                        data = self.read(source, self.home)
                        if blank(data):
                            continue
                        folder = self.store / 'files' / source.relative_to(self.home)
                        latest = folder / 'latest'
                        if latest.exists() and self.read(latest, self.store) == data:
                            self.known[source] = key
                            continue
                        used = sum(p.stat().st_size for p in self.store.rglob('*') if p.is_file())
                        if shutil.disk_usage(self.store).free < RESERVE or used + 2 * len(data) > MAX_STORE:
                            print('BACKUP_SPACE_LOW', flush=True)
                            continue
                        if not (folder / 'first-valid').exists():
                            durable(folder / 'first-valid', data)
                        for i in (3, 2, 1):
                            old = folder / (f'previous-{i-1}' if i > 1 else 'latest')
                            if old.exists():
                                old.replace(folder / f'previous-{i}')
                        durable(latest, data)
                        durable(folder / 'source.json', json.dumps({'time': time.time(), 'bytes': len(data)}).encode())
                        self.known[source] = key
                    except OSError as exc:
                        print('SAVE_ERROR', str(exc), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    guard = Guard()
    if guard.store.is_symlink():
        raise OSError('backup directory must not be a symbolic link')
    guard.store.mkdir(parents=True, exist_ok=True, mode=0o700)
    guard.store.chmod(0o700)
    alive = True

    def stop(*_):
        nonlocal alive
        alive = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    guard.restore()
    guard.scan()
    if not args.once:
        while alive:
            time.sleep(3)
            guard.scan()
        os.sync()


if __name__ == '__main__':
    main()
