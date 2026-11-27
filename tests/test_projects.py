import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from burito.context import build_context
from burito.memory import Memory
from burito.projects import Projects
from burito.school import School


ROOT = Path(__file__).resolve().parents[1]


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.memory = Memory(Path(self.temporary.name) / "memory")
        self.projects = Projects(self.memory)

    def tearDown(self):
        self.temporary.cleanup()

    def test_project_state_has_tasks_dependencies_decisions_blockers_and_next_steps(self):
        project = self.projects.create("Synthetic Atlas", "Build a private test project")
        project = self.projects.update(project["id"], current_milestone="Prototype",
                                       next_actions=["Run integration check"])
        project = self.projects.add_item(project["id"], "decision", "Use SQLite",
                                         details="Reuse the existing private database")
        project = self.projects.add_item(project["id"], "blocker", "Need fixture",
                                         details="The synthetic dataset is missing")
        first = self.projects.add_item(project["id"], "task", "Create fixture")
        second = self.projects.add_item(project["id"], "task", "Run evaluation",
                                        depends_on=[first["items"][-1]["id"]])
        project = self.projects.get(project["id"])
        self.assertEqual(project["current_milestone"], "Prototype")
        self.assertEqual(project["next_actions"], ["Run integration check"])
        self.assertIn("Use SQLite", [item["title"] for item in project["items"]])
        self.assertEqual(project["items"][-1]["depends_on"], [project["items"][-2]["id"]])
        with self.assertRaisesRegex(ValueError, "dependencies"):
            self.projects.update_item(project["id"], project["items"][-1]["id"],
                status="completed", evidence=[{"source": "test", "text": "Not yet",
                                                "verification": "direct_observation"}])

    def test_completion_requires_recorded_evidence_and_completed_dependencies(self):
        project = self.projects.create("Synthetic Workflow", "Test evidence gating")
        project = self.projects.add_item(project["id"], "task", "Prepare input")
        first_id = project["items"][-1]["id"]
        project = self.projects.add_item(project["id"], "task", "Evaluate result",
                                         depends_on=[first_id])
        second_id = project["items"][-1]["id"]
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.projects.update_item(project["id"], first_id, status="completed")
        evidence = [{"source": "synthetic test", "text": "Input fixture created"}]
        project = self.projects.update_item(project["id"], first_id,
            status="completed", evidence=[{**evidence[0], "verification": "independently_verified"}])
        project = self.projects.update_item(project["id"], second_id,
            status="completed", evidence=[{"source": "synthetic test", "text": "Evaluation passed",
                                            "verification": "direct_observation"}])
        with self.assertRaisesRegex(ValueError, "dependent tasks"):
            self.projects.update_item(project["id"], first_id, status="pending")
        context = self.projects.context()
        self.assertEqual(context[0]["completed_tasks"][0]["title"], "Prepare input")
        self.assertEqual(context[0]["completed_tasks"][0]["evidence"][0]["text"],
                         evidence[0]["text"])
        self.assertTrue(context[0]["completed_tasks"][0]["evidence"][0]["observed_at"])
        self.assertTrue(self.memory.history(project["id"]))

    def test_project_context_is_opt_in_and_bounded(self):
        School(self.memory).install("home")
        project = self.projects.create("Synthetic StudyCircle", "Finish database recovery")
        project = self.projects.add_item(project["id"], "task", "Verify restored database",
                                        details="Synthetic detail " * 180)
        hidden = build_context(memory=self.memory, include_system=False)
        self.assertNotIn("remembered_projects", hidden)
        included = build_context(memory=self.memory, include_project=True,
                                 include_system=False, max_chars=12000)
        self.assertEqual(included["remembered_projects"][0]["id"], project["id"])
        self.assertIn("Verify restored database", str(included["remembered_projects"]))
        small = build_context(memory=self.memory, include_project=True,
                              include_system=False, max_chars=2600)
        self.assertTrue(small["truncated"])
        self.assertNotIn("remembered_projects", small)

    def test_project_context_ranks_the_strongest_query_match_first(self):
        weaker = self.projects.create("Synthetic Atlas Notes", "Archive reference material")
        stronger = self.projects.create("Synthetic Atlas Backup", "Verify encrypted checkpoints")
        matches = self.projects.context("Atlas verify encrypted checkpoints")
        self.assertEqual(matches[0]["id"], stronger["id"])
        self.assertEqual(matches[1]["id"], weaker["id"])

    def test_project_continuity_survives_separate_cli_processes(self):
        env = {**os.environ, "BURITO_DATA_DIR": str(Path(self.temporary.name) / "process-memory")}
        def run(*args):
            return subprocess.run([sys.executable, "-m", "burito", *args], cwd=ROOT,
                                  env=env, check=True, capture_output=True, text=True)
        created = json.loads(run("project", "create", "Synthetic Restart", "Resume after process exit").stdout)
        run("project", "update", created["id"], "--milestone", "Restart validation",
            "--next-action", "Read the saved task")
        run("project", "update", created["id"], "--status", "closed")
        closed = json.loads(run("project", "show", created["id"]).stdout)
        self.assertEqual(closed["status"], "closed")
        run("project", "update", created["id"], "--status", "active")
        saved = run("project", "add-item", created["id"], "--kind", "task",
                    "--title", "Check continuity", "--details", "Read after restart")
        self.assertIn("Check continuity", saved.stdout)
        run("school", "install", "--stage", "home")
        restored = json.loads(run("context", "--include-project", "--no-system").stdout)
        project = restored["remembered_projects"][0]
        self.assertEqual(project["id"], created["id"])
        self.assertEqual(project["status"], "active")
        self.assertEqual(project["current_milestone"], "Restart validation")
        self.assertEqual(project["next_actions"], ["Read the saved task"])
        self.assertEqual(project["items"][0]["title"], "Check continuity")

    def test_duplicate_names_and_invalid_statuses_are_rejected(self):
        self.projects.create("Synthetic Duplicate", "First objective")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.projects.create("synthetic duplicate", "Second objective")
        project = self.projects.list()[0]
        with self.assertRaisesRegex(ValueError, "status"):
            self.projects.update(project["id"], status="done")

    def test_malformed_project_records_are_ignored_safely(self):
        self.memory.remember(json.dumps({"format": "burito-project", "schema": 1,
                                         "name": "Broken synthetic record"}),
                             source="test fixture", category="project")
        self.assertEqual(self.projects.list(), [])


if __name__ == "__main__":
    unittest.main()
