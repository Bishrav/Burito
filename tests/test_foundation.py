import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from burito.memory import Memory, data_directory
from burito.doctor import probe
from burito.__main__ import main


class FoundationTests(unittest.TestCase):
    def test_memory_survives_restart_and_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            identifier = memory.remember("Prefer concise answers", "owner")
            restarted = Memory(directory)
            record = restarted.list()[0]
            self.assertEqual(record["id"], identifier)
            self.assertEqual(record["status"], "confirmed")
            self.assertEqual(record["source"], "owner")
            self.assertTrue(restarted.forget(identifier))
            self.assertFalse(restarted.forget(identifier))
            self.assertEqual(Memory(directory).list(), [])

    def test_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(Path(directory) / "private")
            memory.initialize()
            self.assertEqual(memory.directory.stat().st_mode & 0o777, 0o700)
            self.assertEqual(memory.path.stat().st_mode & 0o777, 0o600)

    def test_reject_empty_or_oversized_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            for content, source in [(" ", "owner"), ("fact", ""), ("x" * 20001, "owner")]:
                with self.assertRaises(ValueError):
                    memory.remember(content, source)

    def test_sql_text_is_data(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory)
            content = "'); DROP TABLE memories; --"
            memory.remember(content)
            self.assertEqual(memory.list()[0]["content"], content)

    def test_reject_symlink_database(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.write_text("untouched")
            (Path(directory) / "memory.sqlite3").symlink_to(target)
            with self.assertRaises(OSError):
                Memory(directory).initialize()
            self.assertEqual(target.read_text(), "untouched")

    def test_override_requires_absolute_path(self):
        with patch.dict(os.environ, {"BURITO_DATA_DIR": "relative"}):
            with self.assertRaises(ValueError):
                data_directory()

    def test_missing_dependency_is_reported(self):
        with patch("burito.doctor.shutil.which", return_value=None):
            self.assertFalse(probe(["node", "--version"])["ok"])

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"BURITO_DATA_DIR": directory}):
                with patch("builtins.print"):
                    self.assertEqual(main(["init"]), 0)
                    self.assertEqual(main(["remember", "Synthetic test fact"]), 0)
                    identifier = Memory().list()[0]["id"]
                    self.assertEqual(main(["forget", identifier]), 0)
                    self.assertEqual(main(["forget", identifier]), 1)

    def test_memory_revision_and_conflict_cli_are_owner_reviewable(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"BURITO_DATA_DIR": directory}), \
             patch("builtins.print"):
            self.assertEqual(main(["init"]), 0)
            main(["remember", "Synthetic project uses backend A", "--category", "project",
                  "--claim-key", "project backend"])
            first_id = next(row["id"] for row in Memory().list()
                            if row["content"] == "Synthetic project uses backend A")
            main(["remember", "Synthetic project uses backend B", "--category", "project",
                  "--claim-key", "project backend"])
            self.assertEqual(main(["correct", first_id, "Synthetic corrected project backend",
                                   "--expected", "Synthetic project uses backend A"]), 0)
            self.assertEqual(main(["memory-history", first_id]), 0)
            self.assertEqual(Memory().history(first_id)[0]["content"],
                             "Synthetic project uses backend A")
            conflict_id = Memory().conflicts()[0]["id"]
            self.assertEqual(main(["memory-conflicts"]), 0)
            self.assertEqual(main(["memory-conflict-resolve", str(conflict_id), "superseded",
                                   "--supersede-memory", first_id]), 0)
            records = {row["id"]: row for row in Memory().list(include_superseded=True)}
            self.assertEqual(records[first_id]["active"], 0)
            self.assertEqual(sum(row["active"] for row in records.values()), 1)


if __name__ == "__main__":
    unittest.main()
