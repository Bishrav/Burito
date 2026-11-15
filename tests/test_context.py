from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from burito.context import build_context
from burito.memory import Memory
from burito.school import School
from burito.chat import chat


class ContextTests(unittest.TestCase):
    def test_only_selected_lesson_and_no_personal_data_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            memory.remember('Synthetic private fact')
            School(memory).install()
            context = build_context(memory=memory)
            self.assertEqual(context['lesson']['id'], 'home.honesty')
            self.assertEqual(context['personal_facts'], [])
            self.assertFalse(context['understanding_assessed'])
            self.assertNotIn('Synthetic private fact', str(context))

    def test_corrected_and_deleted_facts_refresh_in_next_context(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            School(memory).install()
            identifier = memory.remember('Synthetic original')
            memory.correct(identifier, 'Synthetic correction')
            context = build_context(include_personal=True, memory=memory)
            self.assertEqual(context['personal_facts'][0]['content'], 'Synthetic correction')
            memory.forget(identifier)
            self.assertEqual(build_context(include_personal=True, memory=memory)['personal_facts'], [])

    def test_context_is_bounded_and_unknown_lessons_do_not_sneak_in(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            School(memory).install()
            memory.remember('x' * 15000)
            context = build_context(include_personal=True, memory=memory)
            self.assertTrue(context['truncated'])
            self.assertEqual(context['personal_facts'], [])
            with self.assertRaises(ValueError):
                build_context('health.sources', memory=memory)

    def test_missing_runtime_reports_actionable_setup_step(self):
        with patch('burito.chat.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'setup-runtime.sh'):
                chat('synthetic-model', 8192)

    def test_launcher_enforces_local_mode_and_explicit_memory_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cli = root / 'runtime/node_modules/.bin/eve'
            cli.parent.mkdir(parents=True)
            cli.touch()
            with patch('burito.chat.ROOT', root), \
                 patch('burito.chat.shutil.which', return_value='/fake/node'), \
                 patch('burito.context.build_context', return_value={}), \
                 patch('burito.chat.subprocess.run', return_value=SimpleNamespace(returncode=0)) as run, \
                 patch('builtins.print'):
                self.assertEqual(chat('synthetic-model', 8192), 0)
            args, kwargs = run.call_args
            self.assertEqual(args[0], ['/fake/node', str(cli), 'dev', '--no-default-extensions'])
            self.assertEqual(kwargs['env']['BURITO_MODE'], 'local')
            self.assertEqual(kwargs['env']['BURITO_INCLUDE_PERSONAL_MEMORY'], '0')
            self.assertEqual(kwargs['env']['EVE_TELEMETRY_DISABLED'], '1')
            self.assertEqual(kwargs['env']['EVE_TRACES_CONTENT'], 'off')
