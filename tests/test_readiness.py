from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from burito.doctor import gpu_context
from burito.education import teach
from burito.memory import Memory
from burito.projects import Projects
from academy.progress import AcademyProgress


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
            Projects(memory).create('Synthetic restore project', 'Check project recovery')
            AcademyProgress(memory).record(
                'synthetic.restore', 'Synthetic restore', stage='algorithm_implemented',
                sources=[{'url': 'https://example.test/source', 'title': 'Synthetic source',
                          'license': 'Synthetic', 'verified': True}],
                evidence=['Synthetic restore unit test'],
            )
            backup = memory.backup(root / 'snapshot.sqlite3')
            manifest = memory.verify_backup(backup)
            self.assertEqual(manifest['database_schema_version'], 2)
            self.assertIsNone(manifest['source_brain'])
            self.assertEqual(len(manifest['database_sha256']), 64)
            memory.remember('Later change')
            connection = sqlite3.connect(backup)
            try:
                saved = {row[0] for row in connection.execute('SELECT content FROM memories')}
                self.assertTrue(any('Synthetic original' in item for item in saved))
                self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            finally:
                connection.close()
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(f'{backup}.manifest.json').stat().st_mode & 0o777, 0o600)
            connection = sqlite3.connect(backup)
            restored_dir = root / 'restored-memory'
            restored_dir.mkdir(mode=0o700)
            restored = sqlite3.connect(restored_dir / 'memory.sqlite3')
            try:
                connection.backup(restored)
                self.assertEqual(restored.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            finally:
                connection.close()
                restored.close()
            recovered = Memory(restored_dir)
            self.assertEqual(recovered.search('Synthetic original', limit=1)[0]['content'],
                             'Synthetic original')
            self.assertEqual(Projects(recovered).list()[0]['objective'],
                             'Check project recovery')
            self.assertEqual(AcademyProgress(recovered).list()[0]['topic_id'],
                             'synthetic.restore')
            with self.assertRaises(FileExistsError):
                memory.backup(backup)
            with self.assertRaises(ValueError):
                memory.backup('relative.sqlite3')

    def test_backup_manifest_detects_changed_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = Memory(root / 'memory')
            backup = memory.backup(root / 'snapshot.sqlite3')
            with backup.open('r+b') as snapshot:
                snapshot.seek(0)
                snapshot.write(b'X')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                memory.verify_backup(backup)

    def test_backup_verification_rejects_symlinked_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = Memory(root / 'memory')
            backup = memory.backup(root / 'snapshot.sqlite3')
            alias = root / 'alias.sqlite3'
            alias.symlink_to(backup)
            Path(f'{alias}.manifest.json').symlink_to(Path(f'{backup}.manifest.json'))
            with self.assertRaises(OSError):
                memory.verify_backup(alias)

    def test_backup_requires_an_owner_only_destination_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared = root / 'shared'
            shared.mkdir(mode=0o755)
            with self.assertRaisesRegex(ValueError, 'owner-only'):
                Memory(root / 'memory').backup(shared / 'snapshot.sqlite3')

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
