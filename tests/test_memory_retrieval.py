import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from burito.context import build_context
from burito import memory as memory_module
from burito.memory import Memory
from burito.school import School


class MemoryRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.memory = Memory(Path(self.temporary.name) / "memory")
        School(self.memory).install("home")
        self.gpu_id = self.memory.remember("The local GPU is an RTX 5070.", "owner statement")
        self.project_id = self.memory.remember("StudyCircle is an active project.", "owner statement")

    def tearDown(self):
        self.temporary.cleanup()

    def test_search_ranks_matching_facts_and_preserves_provenance(self):
        result = self.memory.search("RTX GPU")
        self.assertEqual(result[0]["id"], self.gpu_id)
        self.assertEqual(result[0]["source"], "owner statement")
        self.assertEqual(result[0]["status"], "confirmed")

    def test_search_can_scope_retrieval_to_one_memory_category(self):
        project = self.memory.remember("Synthetic RTX migration project", "test fixture",
                                       category="project")
        self.assertEqual([row["id"] for row in
                          self.memory.search("RTX migration", limit=5, category="project")],
                         [project])
        with self.assertRaises(ValueError):
            self.memory.search("RTX", category=[])

    def test_search_can_scope_to_multiple_categories_without_personal_crossing(self):
        project = self.memory.remember("Synthetic StudyCircle plan for RTX", "test fixture",
                                       category="project")
        selected = self.memory.search("StudyCircle RTX", categories=("semantic", "personal"))
        self.assertNotIn(project, {row["id"] for row in selected})
        self.assertTrue(self.memory.search("RTX", categories=("semantic",)))
        with self.assertRaises(ValueError):
            self.memory.search("RTX", category="semantic", categories=("personal",))

    def test_index_is_volatile_and_correction_and_deletion_are_reflected(self):
        self.assertTrue(self.memory.correct(self.gpu_id, "The local GPU is an RTX 5080."))
        self.assertEqual(self.memory.search("RTX 5080")[0]["id"], self.gpu_id)
        self.assertEqual(self.memory.search("5070"), [])
        with closing(sqlite3.connect(self.memory.path)) as db:
            self.assertNotIn("memory_search", {row[0] for row in db.execute(
                "SELECT name FROM sqlite_schema WHERE type='table'")})
        self.assertTrue(self.memory.forget(self.gpu_id))
        self.assertEqual(self.memory.search("RTX 5080"), [])

    def test_personal_context_uses_query_relevance_and_keeps_source(self):
        context = build_context(memory=self.memory, include_personal=True,
                                include_system=False, knowledge_query="StudyCircle project")
        self.assertEqual([item["id"] for item in context["personal_facts"]], [self.project_id])
        self.assertEqual(context["personal_facts"][0]["source"], "owner statement")

    def test_memory_retrieval_is_not_called_without_personal_opt_in(self):
        with patch.object(self.memory, "search") as search:
            context = build_context(memory=self.memory, include_system=False,
                                    knowledge_query="StudyCircle project")
        self.assertEqual(context["personal_facts"], [])
        search.assert_not_called()

    def test_search_rejects_empty_or_excessive_queries(self):
        for query in (" ", "what were we doing", "word " * 17, None):
            with self.subTest(query=query), self.assertRaises(ValueError):
                self.memory.search(query)

    def test_list_can_filter_categories_without_changing_default_results(self):
        baseline = self.memory.list()
        project = self.memory.remember("Synthetic project-only row", "test fixture",
                                       category="project")
        self.assertEqual([row["id"] for row in self.memory.list(category="project")], [project])
        self.assertEqual({row["id"] for row in self.memory.list(category="semantic")},
                         {row["id"] for row in baseline if row["category"] == "semantic"})
        with self.assertRaises(ValueError):
            self.memory.list(category="not-a-memory-category")
        with self.assertRaises(ValueError):
            self.memory.list(category=[])
        self.assertEqual(len(self.memory.list()), len(baseline) + 1)

    def test_memory_metadata_validation_rejects_unbounded_confidence(self):
        for confidence in (float("nan"), float("inf"), -0.1, 1.1, "unknown"):
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                self.memory.remember("Synthetic confidence fixture", confidence=confidence)
        with self.assertRaises(ValueError):
            self.memory.remember("Synthetic metadata fixture", category="unknown")

    def test_v1_migration_preserves_records_and_adds_unknown_provenance(self):
        directory = Path(self.temporary.name) / "legacy"
        directory.mkdir()
        database = directory / "memory.sqlite3"
        with closing(sqlite3.connect(database)) as db:
            db.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status='confirmed'))")
            db.execute("INSERT INTO memories VALUES ('synthetic-id','Synthetic preserved fact','owner statement','2026-01-02T00:00:00+00:00','confirmed')")
            db.execute("PRAGMA user_version=1")
            db.commit()
        migrated = Memory(directory).list()[0]
        self.assertEqual(migrated["content"], "Synthetic preserved fact")
        self.assertEqual(migrated["source"], "owner statement")
        self.assertEqual(migrated["category"], "semantic")
        self.assertEqual(migrated["verification"], "owner_statement")
        self.assertIsNone(migrated["confidence"])
        self.assertEqual(migrated["updated_at"], migrated["created_at"])
        with closing(sqlite3.connect(database)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 2)

    def test_correction_history_is_attributed_and_deleted_with_memory(self):
        identifier = self.memory.remember("Original pear preference", "owner", category="preference")
        self.assertFalse(self.memory.correct(identifier, "wrong replacement", expected_content="stale"))
        self.assertTrue(self.memory.correct(identifier, "Updated apple preference",
                                             expected_content="Original pear preference"))
        current = next(row for row in self.memory.list() if row["id"] == identifier)
        self.assertEqual(current["id"], identifier)
        self.assertEqual(current["verification"], "owner_statement")
        self.assertEqual(self.memory.history(identifier)[0]["content"], "Original pear preference")
        self.assertFalse(any(row["id"] == identifier for row in self.memory.search("pear")))
        self.assertEqual(self.memory.search("apple preference")[0]["id"], identifier)
        self.assertTrue(self.memory.forget(identifier))
        self.assertEqual(self.memory.history(identifier), [])

    def test_claim_key_conflicts_are_visible_until_owner_supersedes_old_record(self):
        old = self.memory.remember("The synthetic project uses model A", "test fixture",
                                   category="semantic", claim_key="Project model")
        new = self.memory.remember("The synthetic project uses model B", "test fixture",
                                   category="semantic", claim_key="project MODEL")
        conflicts = self.memory.conflicts()
        self.assertEqual(len(conflicts), 1)
        self.assertIn("model A", conflicts[0]["left_content"])
        context = build_context(memory=self.memory, include_personal=True,
                                include_system=False, knowledge_query="model")
        old_context = next(row for row in context["personal_facts"] if row["id"] == old)
        self.assertTrue(old_context["unresolved_conflict"])
        self.assertEqual(old_context["category"], "semantic")
        self.assertEqual(old_context["verification"], "owner_statement")
        self.assertTrue(self.memory.resolve_conflict(
            conflicts[0]["id"], resolution="superseded", superseded_id=old))
        results = self.memory.search("model A")
        self.assertNotIn(old, {row["id"] for row in results})
        self.assertIn(new, {row["id"] for row in results})
        self.assertEqual(self.memory.conflicts("all")[0]["status"], "superseded")

    def test_duplicate_detection_is_exact_and_does_not_merge_records(self):
        first = self.memory.remember("A duplicate-safe synthetic note", "test fixture")
        second = self.memory.remember("  a   DUPLICATE-safe synthetic note ", "test fixture")
        duplicates = self.memory.find_duplicates("A duplicate-safe synthetic note")
        self.assertEqual({item["id"] for item in duplicates}, {first, second})

    def test_unsupported_schema_version_is_refused_without_mutation(self):
        directory = Path(self.temporary.name) / "future"
        directory.mkdir()
        database = directory / "memory.sqlite3"
        with closing(sqlite3.connect(database)) as db:
            db.execute("CREATE TABLE sentinel (value TEXT)")
            db.execute("INSERT INTO sentinel VALUES ('synthetic')")
            db.execute("PRAGMA user_version=99")
            db.commit()
        with self.assertRaisesRegex(ValueError, "Unsupported memory database schema"):
            Memory(directory).initialize()
        with closing(sqlite3.connect(database)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 99)
            self.assertEqual(db.execute("SELECT value FROM sentinel").fetchone()[0], "synthetic")

    def test_brain_database_uses_pinned_directory_and_closes_its_descriptor(self):
        brain = Path(self.temporary.name) / "brain"
        data = brain / "data"
        data.mkdir(parents=True)
        with patch.object(memory_module, "BRAIN_MOUNT", brain), \
             patch.object(memory_module, "brain_available", return_value=True):
            memory = Memory(data)
            connection = memory._connect()
            directory_fd = connection.directory_fd
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            connection.close()
            with self.assertRaises(OSError):
                os.fstat(directory_fd)

    def test_brain_mount_change_during_open_does_not_create_database(self):
        brain = Path(self.temporary.name) / "brain"
        data = brain / "data"
        data.mkdir(parents=True)
        with patch.object(memory_module, "BRAIN_MOUNT", brain), \
             patch.object(memory_module, "brain_available", side_effect=[True, False]):
            with self.assertRaisesRegex(ValueError, "changed during connection"):
                Memory(data)._connect()
        self.assertFalse((data / "memory.sqlite3").exists())

    def test_brain_data_path_cannot_escape_mount_with_parent_segment(self):
        brain = Path(self.temporary.name) / "brain"
        (brain / "data").mkdir(parents=True)
        outside = brain.parent / "escape"
        with patch.object(memory_module, "BRAIN_MOUNT", brain), \
             patch.object(memory_module, "brain_available", return_value=True):
            with self.assertRaisesRegex(ValueError, "cannot escape"):
                Memory(brain / "data" / ".." / ".." / "escape").initialize()
        self.assertFalse(outside.exists())

    def test_backup_cannot_write_to_brain_mount_placeholder(self):
        brain = Path(self.temporary.name) / "brain"
        data = brain / "data"
        data.mkdir(parents=True)
        destination = data / "backup.sqlite3"
        with patch.object(memory_module, "BRAIN_MOUNT", brain):
            with self.assertRaisesRegex(ValueError, "outside the brain filesystem"):
                self.memory.backup(destination)
        self.assertFalse(destination.exists())

    def test_backup_cannot_use_symlink_alias_to_brain_mount(self):
        brain = Path(self.temporary.name) / "brain"
        brain.mkdir()
        alias = Path(self.temporary.name) / "alias"
        alias.symlink_to(brain, target_is_directory=True)
        destination = alias / "backup.sqlite3"
        with patch.object(memory_module, "BRAIN_MOUNT", brain):
            with self.assertRaisesRegex(ValueError, "outside the brain filesystem"):
                self.memory.backup(destination)
        self.assertFalse((brain / "backup.sqlite3").exists())

    def test_brain_manifest_is_created_once_and_schema_versioned(self):
        brain = Path(self.temporary.name) / "brain"
        data = brain / "memory"
        (brain / "manifest").mkdir(parents=True)
        data.mkdir()
        with patch.object(memory_module, "BRAIN_MOUNT", brain), \
             patch.object(memory_module, "BRAIN_DATA", data), \
             patch.object(memory_module, "BRAIN_UUID", "synthetic-volume"), \
             patch.object(memory_module, "brain_available", return_value=True):
            connection = Memory()._connect()
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            connection.close()
            manifest_path = brain / "manifest" / "brain.json"
            first = json.loads(manifest_path.read_text())
            second = Memory()._connect()
            second.close()
            self.assertEqual(json.loads(manifest_path.read_text())["brain_id"], first["brain_id"])
        self.assertEqual(first["filesystem"]["uuid"], "synthetic-volume")
        self.assertEqual(first["database_schema_versions"]["memory.sqlite3"], 2)
        self.assertEqual(manifest_path.stat().st_mode & 0o777, 0o600)

    def test_manifest_records_database_schema_migration(self):
        brain = Path(self.temporary.name) / "brain"
        data = brain / "memory"
        manifest_dir = brain / "manifest"
        manifest_dir.mkdir(parents=True)
        data.mkdir()
        manifest_path = manifest_dir / "brain.json"
        seed = {
            "format": "burito-brain", "manifest_version": 1,
            "brain_id": "14dbcd63-e4e1-4685-92b6-03bfbb1c4525",
            "filesystem": {"uuid": "synthetic-volume", "type": "ext4"},
            "storage_schema_version": 1,
            "database_schema_versions": {"memory.sqlite3": 1},
            "runtime_compatibility": {"minimum": "0.1.0"},
            "models": [], "datasets": [], "migration_history": [],
            "integrity": {"algorithm": "sha256", "checked_at": None},
            "backup": {"independent_verified_at": None},
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        manifest_path.write_text(json.dumps(seed))
        manifest_path.chmod(0o600)
        with patch.object(memory_module, "BRAIN_MOUNT", brain), \
             patch.object(memory_module, "BRAIN_DATA", data), \
             patch.object(memory_module, "BRAIN_UUID", "synthetic-volume"), \
             patch.object(memory_module, "brain_available", return_value=True):
            connection = Memory()._connect()
            connection.close()
        updated = json.loads(manifest_path.read_text())
        self.assertEqual(updated["database_schema_versions"]["memory.sqlite3"], 2)
        self.assertEqual(updated["migration_history"][0]["from"], 1)
        self.assertEqual(updated["migration_history"][0]["to"], 2)

    def test_existing_database_without_manifest_is_not_adopted(self):
        brain = Path(self.temporary.name) / "brain"
        data = brain / "memory"
        (brain / "manifest").mkdir(parents=True)
        data.mkdir()
        database = data / "memory.sqlite3"
        database.write_bytes(b"synthetic existing database")
        with patch.object(memory_module, "BRAIN_MOUNT", brain), \
             patch.object(memory_module, "BRAIN_DATA", data), \
             patch.object(memory_module, "BRAIN_UUID", "synthetic-volume"), \
             patch.object(memory_module, "brain_available", return_value=True):
            with self.assertRaisesRegex(ValueError, "without a brain manifest"):
                Memory()._connect()
        self.assertEqual(database.read_bytes(), b"synthetic existing database")
        self.assertFalse((brain / "manifest" / "brain.json").exists())


if __name__ == "__main__":
    unittest.main()
