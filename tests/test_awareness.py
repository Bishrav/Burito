import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import shutil
import subprocess

from burito.awareness import Awareness, files, enable, quote_unit, render_units, working_directory_value, monitor_status
from burito.memory import Memory
from burito.context import build_context
from burito.school import School


class AwarenessTests(unittest.TestCase):
    def test_baseline_then_add_modify_remove(self):
        with tempfile.TemporaryDirectory() as directory:
            awareness = Awareness(Memory(directory))
            self.assertEqual(awareness.scan({'packages': {'old': '1', 'keep': '1'}})['changes_detected'], 0)
            self.assertEqual(awareness.scan({'packages': {'new': '1', 'keep': '2'}})['changes_detected'], 3)
            changes = {(event['kind'], event['name']) for event in awareness.changes()}
            self.assertEqual(changes, {('added', 'new'), ('modified', 'keep'), ('removed', 'old')})

    def test_failed_and_partial_scans_do_not_invent_removals(self):
        with tempfile.TemporaryDirectory() as directory:
            awareness = Awareness(Memory(directory))
            awareness.scan({'home_files': {'a': 1, 'b': 1}, 'packages': {'app': '1'}})
            awareness.scan({'home_files': {'a': 2}}, {'home_files': ['capped'], 'packages': ['unavailable']})
            self.assertEqual([(event['kind'], event['name']) for event in awareness.changes()], [('modified', 'a')])
            self.assertEqual(awareness.summary()['inventory_counts']['home_files'], 2)
            self.assertEqual(awareness.summary()['inventory_counts']['packages'], 1)
            self.assertIn('packages', awareness.summary()['partial_or_unavailable'])
            awareness.scan({'home_files': {'a': 2}})
            self.assertEqual(awareness.changes()[0]['kind'], 'removed')

    def test_metadata_only_excludes_hidden_and_dependency_folders(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / 'document.txt').write_text('SECRET CONTENT NEVER INDEXED')
            (root / '.ssh').mkdir()
            (root / '.ssh/key').write_text('PRIVATE KEY')
            (root / 'node_modules').mkdir()
            (root / 'node_modules/code.js').write_text('not indexed')
            (Path(outside) / 'outside.txt').write_text('not indexed')
            (root / 'external').symlink_to(outside, target_is_directory=True)
            metadata, errors = files(root)
            self.assertEqual(errors, [])
            self.assertEqual(set(metadata), {'document.txt', 'external'})
            self.assertEqual(metadata['external']['kind'], 'symlink')
            self.assertNotIn('SECRET CONTENT', json.dumps(metadata))

    def test_scan_limit_is_explicit_and_does_not_open_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            for index in range(5):
                (Path(directory) / str(index)).touch()
            metadata, errors = files(directory, limit=2)
            self.assertEqual(len(metadata), 2)
            self.assertIn('limit reached', errors[0])

    def test_inventory_context_opt_out_and_personal_fact_separation(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            School(memory).install()
            Awareness(memory).scan({'hardware': {'cpu': 'Synthetic CPU'}, 'packages': {'demo': '1'}})
            included = build_context(memory=memory)
            self.assertEqual(included['pc_inventory']['hardware']['cpu'], 'Synthetic CPU')
            self.assertEqual(included['personal_facts'], [])
            self.assertEqual(memory.list(), [])
            self.assertNotIn('pc_inventory', build_context(memory=memory, include_system=False))

    def test_unit_files_are_prepared_even_when_session_bus_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}):
                with patch('burito.awareness.subprocess.run') as run:
                    run.return_value.returncode = 1
                    run.return_value.stderr = 'Failed to connect to user scope bus: Operation not permitted'
                    with self.assertRaisesRegex(ValueError, 'Konsole'):
                        enable()
                unit = Path(directory) / 'systemd/user/burito-awareness.service'
                timer = Path(directory) / 'systemd/user/burito-awareness.timer'
                self.assertIn('-m burito pc scan', unit.read_text())
                self.assertIn('OnUnitInactiveSec=60', timer.read_text())
                self.assertIn('WantedBy=timers.target', timer.read_text())

    def test_systemd_path_escaping(self):
        self.assertEqual(quote_unit('/tmp/a b%f'), '"/tmp/a b%%f"')
        with self.assertRaises(ValueError):
            quote_unit('/tmp/a\nExecStart=bad')

    def test_working_directory_is_absolute_not_a_quoted_command_argument(self):
        service, timer = render_units('/tmp/project folder', '/usr/bin/python3', '/tmp/private')
        value = next(line.split('=', 1)[1] for line in service.splitlines() if line.startswith('WorkingDirectory='))
        self.assertTrue(Path(value).is_absolute())
        self.assertEqual(value, '/tmp/project folder')
        self.assertEqual(working_directory_value('/tmp/100%'), '/tmp/100%%')
        for invalid in ('relative', '/tmp/a\nExecStart=bad', '/tmp/a/../b'):
            with self.assertRaises(ValueError):
                working_directory_value(invalid)

    @unittest.skipUnless(shutil.which('systemd-analyze'), 'systemd analyzer unavailable')
    def test_generated_units_pass_native_systemd_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service, timer = render_units(root, '/usr/bin/python3', root / 'private')
            paths = [root / 'burito-awareness.service', root / 'burito-awareness.timer']
            paths[0].write_text(service)
            paths[1].write_text(timer)
            result = subprocess.run(['systemd-analyze', 'verify', '--man=no', *map(str, paths)],
                                    capture_output=True, text=True, timeout=15, check=False)
            errors = [line for line in result.stderr.splitlines() if line.strip()]
            if result.returncode and errors and all('Operation not permitted' in line for line in errors):
                self.skipTest('Native systemd verification needs sockets blocked by this sandbox')
            self.assertEqual(result.returncode, 0, result.stderr)
            # The same native parser must reject the exact original regression.
            bad = root / 'burito-invalid.service'
            bad.write_text(service.replace(f'WorkingDirectory={root}', f'WorkingDirectory="{root}"'))
            invalid = subprocess.run(['systemd-analyze', 'verify', '--man=no', str(bad)],
                                     capture_output=True, text=True, timeout=15, check=False)
            self.assertNotEqual(invalid.returncode, 0, 'Native verifier accepted the original invalid WorkingDirectory')

    def test_start_failure_points_to_journal_instead_of_blind_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}), \
                 patch('burito.awareness.subprocess.run', side_effect=[
                     SimpleNamespace(returncode=0, stdout='', stderr=''),
                     SimpleNamespace(returncode=1, stdout='', stderr='Job failed')]):
                with self.assertRaisesRegex(ValueError, 'journalctl --user'):
                    enable()

    def test_status_distinguishes_enabled_timer_from_an_active_one(self):
        data = ('Id=burito-awareness.timer\nLoadState=loaded\nActiveState=inactive\n'
                'UnitFileState=enabled\n\nId=burito-awareness.service\nResult=exit-code\nExecMainStatus=1\n')
        with patch('burito.awareness.subprocess.run', return_value=SimpleNamespace(
                returncode=0, stdout=data, stderr='')):
            result = monitor_status()
        self.assertFalse(result['verified_active'])
        self.assertEqual(result['units']['burito-awareness.service']['ExecMainStatus'], '1')
