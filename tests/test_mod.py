import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

BASE = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = load('mod', BASE / 'scripts/r36s_mod.py')
guard = load('guard', BASE / 'payload/r36s-saveguard.py')
builder = load('builder', BASE / 'scripts/build-toolkit.py')
FIXTURE = b'''#!/bin/sh
start_launcher() {
    STATE=launcher
}
do_launch() {
    STATE=app
}
do_stop_app() {
    [ "$APP_GEN" != 0 ] && cg_signal "$CG_ROOT/app" TERM
}
shutdown_all() {
    trap '' TERM INT HUP
}
'''


class InstallerTests(unittest.TestCase):
    def test_preserve_save_paths_and_remove_duplicate_option(self):
        source = 'savefile_directory = "/custom"\nautosave_interval = "0"\nautosave_interval = "5"\n'
        result = mod.set_config(source, {'autosave_interval': '3'})
        self.assertIn('savefile_directory = "/custom"', result)
        self.assertEqual(result.count('autosave_interval'), 1)

    def test_fstab_preserves_actual_device_and_other_mounts(self):
        source = 'UUID=some-card /home/player vfat rw,async,uid=1000 0 0\n/dev/mmcblk1p1 /media/external vfat ro 0 0\n'
        result = mod.sync_home(source)
        self.assertIn('UUID=some-card', result)
        self.assertIn('uid=1000,sync,errors=remount-ro', result)
        self.assertIn('/dev/mmcblk1p1 /media/external vfat ro 0 0', result)
        self.assertEqual(mod.sync_home(result), result)

    def test_fstab_refuses_ambiguous_or_unknown_home(self):
        for source in ('', '/x /home/player ext4 rw 0 0\n', '/x /home/player vfat rw 0 0\n/y /home/player vfat rw 0 0\n'):
            with self.assertRaises(ValueError):
                mod.sync_home(source)

    def test_supervisor_patch_rejects_unknown_file(self):
        with self.assertRaises(ValueError):
            mod.patch_appctl(FIXTURE, ['saves'])

    def test_patch_orders_termination_before_sync_and_supports_performance(self):
        with mock.patch.object(mod, 'APPCTL_SHA256', mod.digest(FIXTURE)):
            result = mod.patch_appctl(FIXTURE, ['saves', 'performance']).decode()
        self.assertIn('kill -TERM "$_ra_pid"', result)
        self.assertLess(result.index('    do_stop_app\n'), result.index('    sync\n'))
        self.assertIn('r36s-game-performance start', result)
        self.assertEqual(result.count('r36s-game-performance restore'), 3)

    def test_transaction_restores_original_and_removes_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new = root / 'old', root / 'new'
            old.write_bytes(b'original')
            folder = mod.apply_plan([(old, b'changed', 0o644), (new, b'new', 0o644)], root / 'backups')
            self.assertEqual(old.read_bytes(), b'changed')
            mod.restore(folder)
            self.assertEqual(old.read_bytes(), b'original')
            self.assertFalse(new.exists())

    def test_restore_preserves_later_user_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'config'
            target.write_text('before')
            folder = mod.apply_plan([(target, b'installed', 0o644)], root / 'backups')
            target.write_text('user edit')
            with self.assertRaises(ValueError):
                mod.restore(folder)
            self.assertEqual(target.read_text(), 'user edit')

    def test_transaction_rolls_back_first_write_if_second_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = root / 'one', root / 'two'
            first.write_bytes(b'original')
            original_atomic = mod.atomic

            def fail_second(path, *args):
                if path == second:
                    raise OSError('simulated failure')
                return original_atomic(path, *args)

            with mock.patch.object(mod, 'atomic', side_effect=fail_second):
                with self.assertRaises(OSError):
                    mod.apply_plan([(first, b'new', 0o644), (second, b'new', 0o644)], root / 'backups')
            self.assertEqual(first.read_bytes(), b'original')

    def test_refuses_symlink_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'link').symlink_to(root / 'outside')
            with self.assertRaises(ValueError):
                mod.safe_target(root / 'link/file')

    def test_doctor_rejects_pc_and_readonly_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, text in {
                'proc/mounts': '/dev/root / ext4 rw 0 0\n/dev/card /home/player vfat ro 0 0\n',
                'proc/device-tree/compatible': 'allwinner,sun8i-a33\0',
                'proc/device-tree/model': 'GA36-MB R36S',
                'etc/os-release': 'ID=goodluckos\n',
            }.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            self.assertTrue(mod.inspect(root, machine='x86_64')['issues'])
            self.assertTrue(mod.inspect(root, machine='armv7l')['issues'])
            (root / 'proc/mounts').write_text('/dev/root / ext4 rw 0 0\n/dev/card /home/player vfat rw 0 0\n')
            self.assertFalse(mod.inspect(root, machine='armv7l')['issues'])


class SaveGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home, self.store = self.root / 'home', self.root / 'store'
        self.home.mkdir()
        self.store.mkdir()
        self.guard = guard.Guard(self.home, self.store)
        self.save = self.home / '.config/retroarch/saves/test.srm'
        self.save.parent.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_flash128_survives_blank_replacement_and_restore(self):
        data = bytearray(b'\xff' * 131072)
        data[0], data[65536] = 2, 0x58
        self.save.write_bytes(data)
        self.guard.scan()
        self.save.write_bytes(b'\xff' * 131072)
        self.guard.scan()
        self.guard.restore()
        self.assertEqual(self.save.read_bytes(), data)

    def test_versions_keep_first_and_previous(self):
        for number in range(1, 7):
            self.save.write_bytes(bytes([number]) * 100)
            self.guard.scan()
        folder = self.store / 'files/.config/retroarch/saves/test.srm'
        self.assertEqual((folder / 'first-valid').read_bytes(), b'\x01' * 100)
        self.assertEqual((folder / 'latest').read_bytes(), b'\x06' * 100)
        self.assertEqual((folder / 'previous-3').read_bytes(), b'\x03' * 100)

    def test_symlink_cannot_copy_files_outside_home(self):
        secret = self.root / 'private'
        secret.write_bytes(b'do not publish or copy')
        self.save.symlink_to(secret)
        self.guard.scan()
        self.assertFalse((self.store / 'files').exists())

    def test_parent_directory_symlink_cannot_escape_home(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'test.srm').write_bytes(b'private')
        link = self.home / 'Juegos'
        link.symlink_to(outside, target_is_directory=True)
        self.guard.scan()
        self.assertFalse((self.store / 'files').exists())
        with self.assertRaises(OSError):
            guard.open_parent(link / 'test.srm', self.home)

    def test_restore_does_not_follow_symlink_or_overwrite_nonblank(self):
        self.save.write_bytes(b'good')
        self.guard.scan()
        self.save.write_bytes(b'new valid')
        self.guard.restore()
        self.assertEqual(self.save.read_bytes(), b'new valid')
        self.save.unlink()
        outside = self.root / 'other'
        outside.write_bytes(b'\xff')
        self.save.symlink_to(outside)
        self.guard.restore()
        self.assertEqual(outside.read_bytes(), b'\xff')

    def test_space_limit_preserves_latest(self):
        self.save.write_bytes(b'valid')
        self.guard.scan()
        self.save.write_bytes(b'new')
        with mock.patch.object(guard.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 0})()):
            self.guard.scan()
        self.assertEqual((self.store / 'files/.config/retroarch/saves/test.srm/latest').read_bytes(), b'valid')

    def test_large_file_is_not_backed_up(self):
        self.save.write_bytes(b'x' * (guard.MAX_FILE + 1))
        self.guard.scan()
        self.assertFalse((self.store / 'files').exists())


if __name__ == '__main__':
    unittest.main()
