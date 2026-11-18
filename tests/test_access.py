import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from burito.access import resolve, list_files, read_text, find_files, applications, launch_application, dispatch
from burito.memory import Memory


class AccessTests(unittest.TestCase):
    def test_text_read_has_exact_path_hash_and_bounded_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'note.txt'
            path.write_text('first\nsecond\nthird\n')
            result = read_text(path, start_line=2, max_lines=1, allowed_roots=[directory])
            self.assertEqual(result['text'], 'second')
            self.assertEqual(result['path'], str(path))
            self.assertEqual(len(result['sha256']), 64)
            self.assertTrue(result['truncated'])

    def test_symlink_escape_credential_paths_and_parent_traversal_are_denied(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            secret = root / '.ssh/key.txt'
            secret.parent.mkdir()
            secret.write_text('synthetic credential')
            (root / 'alias.txt').symlink_to(secret)
            (root / 'escape').symlink_to(outside, target_is_directory=True)
            for path in (secret, root / 'alias.txt', root / 'escape', root / '../anything'):
                with self.assertRaises(ValueError):
                    resolve(path, [root])
            for path in ('/proc/self/environ', '/dev/random', '/etc/shadow'):
                with self.assertRaises(ValueError):
                    resolve(path)

    def test_special_binary_and_oversized_files_cannot_be_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'binary').write_bytes(b'a\0b')
            (root / 'large').write_bytes(b'x' * 262145)
            os.mkfifo(root / 'pipe')
            for name in ('binary', 'large', 'pipe'):
                with self.assertRaises(ValueError):
                    read_text(root / name, allowed_roots=[root])

    def test_browsing_pages_and_live_filename_search(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('a.txt', 'b.txt', 'c.txt'):
                (root / name).write_text('synthetic')
            (root / '.ssh').mkdir()
            (root / '.ssh/private.txt').write_text('not returned')
            page = list_files(root, limit=2, allowed_roots=[root])
            self.assertEqual(len(page['entries']), 2)
            self.assertEqual(page['next_offset'], 2)
            result = find_files('.txt', root, [root])
            self.assertEqual({Path(item['path']).name for item in result['matches']}, {'a.txt', 'b.txt', 'c.txt'})

    def test_failed_read_is_audited_without_content(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(Path(directory) / 'private')
            with self.assertRaises(ValueError):
                dispatch({'action': 'read', 'path': '/etc/shadow'}, memory)
            connection = memory._connect()
            try:
                row = connection.execute('SELECT action, outcome FROM pc_access_audit').fetchone()
                self.assertEqual(tuple(row), ('read', 'failed'))
            finally:
                connection.close()

    def test_app_discovery_does_not_execute_and_changed_launchers_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / 'demo.desktop'
            app.write_text('[Desktop Entry]\nType=Application\nName=Demo App\nExec=/usr/bin/true\n')
            registry = {'test': root}
            with patch('burito.access.subprocess.run') as run:
                found = applications('demo', registry)
                self.assertEqual(found[0]['app_id'], 'test:demo.desktop')
                run.assert_not_called()
                app.write_text(app.read_text() + 'Comment=changed\n')
                with self.assertRaisesRegex(ValueError, 'changed'):
                    launch_application(found[0]['app_id'], found[0]['sha256'], registry)
                run.assert_not_called()

    def test_launch_uses_approved_snapshot_and_reports_only_request_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / 'demo.desktop'
            app.write_text('[Desktop Entry]\nType=Application\nName=Demo App\nExec=/usr/bin/true\n')
            registry = {'test': root}
            found = applications(directories=registry)[0]
            with patch.dict(os.environ, {'BURITO_DATA_DIR': str(root / 'private')}), \
                 patch('burito.access.subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
                result = launch_application(found['app_id'], found['sha256'], registry)
                launched_path = Path(run.call_args.args[0][2])
                self.assertNotEqual(launched_path, app)
                self.assertEqual(launched_path.read_bytes(), app.read_bytes())
                self.assertEqual(result['status'], 'launch_request_accepted')

    def test_bridge_does_not_accept_an_ungated_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'BURITO_APPROVED_APP_LAUNCH': '0'}):
                with self.assertRaisesRegex(ValueError, 'approved eve'):
                    dispatch({'action': 'launch', 'app_id': 'anything', 'sha256': 'x'}, Memory(directory))

    def test_window_captions_are_not_written_to_access_audit(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {'BURITO_DESKTOP_CONTROL': '1'}), \
             patch('burito.windows.list_windows', return_value={
                 'windows': [{'internalId': 'a' * 36, 'caption': 'synthetic private title'}]}):
            memory = Memory(Path(directory) / 'private')
            result = dispatch({'action': 'windows'}, memory)
            self.assertEqual(result['windows'][0]['caption'], 'synthetic private title')
            connection = memory._connect()
            try:
                target = connection.execute('SELECT target FROM pc_access_audit').fetchone()[0]
                self.assertEqual(target, 'KWin window request')
                self.assertNotIn('synthetic private title', target)
            finally:
                connection.close()

    def test_window_focus_bridge_still_requires_the_approved_tool_path(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {
                 'BURITO_DESKTOP_CONTROL': '1',
                 'BURITO_APPROVED_WINDOW_FOCUS': '0',
             }):
            with self.assertRaisesRegex(ValueError, 'approved eve tool path'):
                dispatch({'action': 'focus_window', 'internalId': 'a' * 36}, Memory(directory))
