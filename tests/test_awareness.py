import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from burito.awareness import Awareness, files, enable, quote_unit
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
                    run.return_value.stderr = 'test bus unavailable'
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
