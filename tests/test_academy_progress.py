import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from academy.progress import AcademyProgress
from burito.memory import Memory


ROOT = Path(__file__).resolve().parents[1]
LINEAR_SOURCE = {
    "url": "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/",
    "title": "MIT 18.06 Linear Algebra",
    "license": "Link only; no content imported; verify per asset before ingestion.",
    "verified": True,
}


class AcademyProgressTests(unittest.TestCase):
    def test_progress_stages_are_persistent_and_evidence_based(self):
        with tempfile.TemporaryDirectory() as directory:
            progress = AcademyProgress(Memory(directory))
            planned = progress.record("math.vectors", "Vectors", prerequisites=["Algebra"])
            self.assertEqual(planned["current_stage"], "planned")
            sources = progress.record("math.vectors", "Vectors", sources=[LINEAR_SOURCE],
                                      stage="sources_verified")
            self.assertEqual(sources["prerequisites"], ["Algebra"])
            registered = AcademyProgress(Memory(directory)).record(
                "math.vectors", "Vectors", stage="material_registered")
            self.assertEqual(registered["current_stage"], "material_registered")
            with self.assertRaisesRegex(ValueError, "evaluation evidence"):
                progress.record("math.vectors", "Vectors", stage="exercise_passed")
            passed = progress.record("math.vectors", "Vectors", stage="exercise_passed",
                                     evidence=["Matrix-vector products matched the hand calculation"])
            self.assertEqual(passed["current_stage"], "exercise_passed")
            self.assertEqual(len(AcademyProgress(Memory(directory)).get("math.vectors")["events"]), 4)

    def test_verified_sources_and_https_are_required_before_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            progress = AcademyProgress(Memory(directory))
            bad = {**LINEAR_SOURCE, "verified": False}
            with self.assertRaisesRegex(ValueError, "verified sources"):
                progress.record("math.vectors", "Vectors", stage="sources_verified", sources=[bad])
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                progress.record("math.vectors", "Vectors", stage="sources_verified",
                    sources=[{**LINEAR_SOURCE, "url": "http://example.invalid"}])
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                progress.record("math.vectors", "Vectors", stage="sources_verified",
                    sources=[{**LINEAR_SOURCE, "url": "https://"}])

    def test_cli_progress_survives_a_separate_process(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, "BURITO_DATA_DIR": str(Path(directory) / "memory")}
            run = lambda *args: subprocess.run([sys.executable, "-m", "burito", *args],
                cwd=ROOT, env=env, check=True, capture_output=True, text=True)
            run("academy", "record", "math.vectors", "Vectors",
                "--stage", "sources_verified", "--source", LINEAR_SOURCE["url"],
                "--source-title", LINEAR_SOURCE["title"], "--source-license",
                LINEAR_SOURCE["license"], "--verify-sources")
            state = json.loads(run("academy", "list").stdout)
            self.assertEqual(state[0]["topic_id"], "math.vectors")
            self.assertEqual(state[0]["current_stage"], "sources_verified")


if __name__ == "__main__":
    unittest.main()
