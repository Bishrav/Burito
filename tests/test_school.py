from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from burito.memory import Memory
from burito.school import School, catalog


class SchoolTests(unittest.TestCase):
    def test_home_installs_once_and_stays_separate_from_owner_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            memory.remember("Synthetic owner preference")
            school = School(memory)
            self.assertEqual(school.install(), 3)
            self.assertEqual(school.install(), 0)
            self.assertEqual(len(School(Memory(directory)).installed()), 3)
            self.assertEqual(len(memory.list()), 1)

    def test_school_includes_prerequisites_and_all_have_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            school = School(Memory(directory))
            self.assertEqual(school.install("school"), len(catalog()))
            self.assertTrue(all(item["sources"] for item in school.installed()))
            self.assertEqual(school.install("all"), 0)

    def test_conflicting_same_revision_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            school = School(Memory(directory))
            school.install()
            changed = deepcopy(catalog())
            changed[0]["notes"] = ["Unexpected replacement"]
            with patch("burito.school.catalog", return_value=changed):
                with self.assertRaises(ValueError):
                    school.install()
            self.assertNotEqual(school.installed()[0]["notes"], ["Unexpected replacement"])

    def test_catalog_rejects_missing_prerequisite(self):
        with tempfile.TemporaryDirectory() as directory:
            lessons = deepcopy(catalog())
            lessons[0]["prerequisites"] = ["does.not.exist"]
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps({"lessons": lessons}))
            with self.assertRaises(ValueError):
                catalog(path)
