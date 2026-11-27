import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from burito.__main__ import main
from burito.learning import Experiences, SkillProposals
from burito.memory import Memory


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.memory = Memory(self.temporary.name)
        self.experiences = Experiences(self.memory)

    def tearDown(self):
        self.temporary.cleanup()

    def _verified_experience(self):
        return self.experiences.record(
            "Diagnose a synthetic test failure", "Isolated temporary repository",
            "Run the focused test then inspect the failing assertion",
            attempted_actions=["Ran tests/test_sample.py"],
            observed_results=["One assertion failed; corrected fixture passes"],
            errors=["Fixture expected an old label"],
            recovery_steps=["Updated the synthetic fixture and reran the test"],
            verified_lessons=["Check the fixture contract before changing production code"],
            outcome="succeeded", verification="independently_verified",
            evidence=[{"source": "test runner", "text": "Focused rerun passed"}],
        )

    def test_attempt_is_not_success_and_cannot_seed_skill(self):
        attempt = self.experiences.record(
            "Synthetic attempt", "Isolated", "Try a diagnostic",
            attempted_actions=["Ran a command"], outcome="attempted")
        self.assertEqual(attempt["outcome"], "attempted")
        skills = SkillProposals(self.memory)
        with self.assertRaisesRegex(ValueError, "verified successful"):
            skills.propose("Synthetic skill", [attempt["id"]], inputs=[],
                preconditions=["Synthetic precondition"], required_tools=[], permissions=[],
                procedure=["Synthetic procedure"], expected_outcome="Check completes",
                verification_method="Read test result", failure_conditions=[],
                recovery_strategy=[])

    def test_success_requires_observed_result_evidence_and_verification(self):
        with self.assertRaisesRegex(ValueError, "requires observed results"):
            self.experiences.record("Synthetic objective", "Test context", "Test approach",
                attempted_actions=["Attempted"], outcome="succeeded")
        record = self._verified_experience()
        self.assertEqual(record["outcome"], "succeeded")
        self.assertEqual(record["verification"], "independently_verified")
        self.assertEqual(record["evidence"][0]["source"], "test runner")
        self.assertEqual(self.experiences.get(record["id"])["observed_results"],
                         record["observed_results"])

    def test_skill_proposal_is_complete_reviewable_and_never_executable(self):
        experience = self._verified_experience()
        skills = SkillProposals(self.memory)
        proposal = skills.propose(
            "Run a focused Python regression check", [experience["id"]],
            inputs=["Test module path"], preconditions=["Correct repository is open"],
            required_tools=["Python unittest"], permissions=["Read repository tests"],
            procedure=["Run the named test module", "Inspect its exit status"],
            expected_outcome="A test result is reported with its exit code",
            verification_method="Confirm the process exit status and test summary",
            failure_conditions=["Test module is unavailable"],
            recovery_strategy=["Verify the repository and module path"], version=2,
        )
        self.assertEqual(proposal["review_status"], "proposed")
        self.assertFalse(proposal["executable"])
        self.assertEqual(proposal["source_experiences"], [experience["id"]])
        self.assertTrue(skills.review(proposal["id"], "accepted", "Synthetic review"))
        reviewed = skills.list()[0]
        self.assertEqual(reviewed["review_status"], "accepted")
        self.assertFalse(reviewed["executable"])
        self.assertTrue(self.memory.history(proposal["id"]))

    def test_cli_records_experience_and_lists_skill_proposal(self):
        with patch.dict(os.environ, {"BURITO_DATA_DIR": self.temporary.name}):
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([
                    "experience", "record", "--objective", "Synthetic CLI check",
                    "--context", "Temporary test", "--approach", "Run one test",
                    "--action", "Ran the focused suite", "--result", "All assertions passed",
                    "--outcome", "succeeded", "--verification", "direct_observation",
                    "--evidence", "Exit code 0", "--evidence-source", "test runner",
                ]), 0)
            experience = json.loads(output.getvalue())
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([
                    "skill", "propose", "--purpose", "Run a focused test",
                    "--experience", experience["id"], "--precondition", "Test fixture exists",
                    "--tool", "Python unittest", "--permission", "Read synthetic tests",
                    "--step", "Run the test", "--expected", "Exit code is reported",
                    "--verification-method", "Read process status",
                    "--failure", "Test module is absent", "--recovery", "Check the module path",
                ]), 0)
            proposal = json.loads(output.getvalue())
            self.assertFalse(proposal["executable"])
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["skill", "list"]), 0)
            self.assertIn(proposal["id"], output.getvalue())


if __name__ == "__main__":
    unittest.main()
