from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from burito.doctor import gpu_context
from burito.education import teach
from burito.memory import Memory


class ReadinessTests(unittest.TestCase):
    def test_loaded_driver_without_devices_is_not_declared_broken(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            version = root / 'proc/driver/nvidia/version'
            version.parent.mkdir(parents=True)
            version.write_text('loaded')
            (root / 'dev').mkdir()
            (root / 'dev/nvidia-caps').mkdir()
            context = gpu_context({'ok': False}, root / 'proc', root / 'dev')
            self.assertTrue(context['kernel_driver_loaded'])
            self.assertIn('device files are not visible', context['assessment'])

    def test_memory_correction_preserves_identity_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            identifier = memory.remember('Prefer long answers')
            self.assertTrue(memory.correct(identifier, 'Prefer short answers'))
            self.assertFalse(memory.correct('missing', 'new fact'))
            record = Memory(directory).list()[0]
            self.assertEqual(record['content'], 'Prefer short answers')
            self.assertEqual(record['source'], 'owner correction')
            with self.assertRaises(ValueError):
                memory.correct(identifier, ' ')

    def test_backup_is_consistent_private_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = Memory(root / 'memory')
            memory.remember('Synthetic original')
            backup = memory.backup(root / 'snapshot.sqlite3')
            memory.remember('Later change')
            connection = sqlite3.connect(backup)
            try:
                self.assertEqual(connection.execute('SELECT content FROM memories').fetchall(),
                                 [('Synthetic original',)])
                self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            finally:
                connection.close()
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                memory.backup(backup)
            with self.assertRaises(ValueError):
                memory.backup('relative.sqlite3')

    def test_failed_backup_leaves_no_partial_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = Memory(root / 'memory')
            destination = root / 'failed.sqlite3'
            with patch.object(memory, '_connect', side_effect=OSError('test error')):
                with self.assertRaises(OSError):
                    memory.backup(destination)
            self.assertFalse(destination.exists())

    def test_education_skips_blank_answers_and_keeps_explicit_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            with patch('builtins.input', side_effect=['Example', '', 'Brief', '', 'Robotics']):
                with patch('builtins.print'):
                    self.assertEqual(teach(memory), 3)
            records = memory.list()
            self.assertEqual([record['content'] for record in records], ['Example', 'Brief', 'Robotics'])
            self.assertTrue(all(record['source'].startswith('owner onboarding:') for record in records))

    def test_education_interruption_preserves_prior_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            with patch('builtins.input', side_effect=['Example', KeyboardInterrupt]):
                with patch('builtins.print'):
                    self.assertEqual(teach(memory), 1)
            self.assertEqual(len(Memory(directory).list()), 1)
