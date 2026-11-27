import unittest

from academy.evaluations.memory_retrieval import evaluate


class RetrievalEvaluationTests(unittest.TestCase):
    def test_diverse_synthetic_suite_checks_lifecycle_conflict_and_privacy(self):
        result = evaluate(records=100, repeats=1)
        self.assertEqual(result["suite"], "burito-memory-retrieval-v2")
        self.assertEqual(len(result["cases"]), 13)
        self.assertEqual(result["metrics"]["recall_at_5"], 1.0)
        self.assertGreaterEqual(result["metrics"]["precision_at_5"], 0)
        self.assertTrue(all(result["safety_checks"].values()))
        cases = {case["kind"]: case for case in result["cases"]}
        self.assertEqual(cases["multiple_relevant"]["hits"], 2)
        self.assertEqual(cases["deleted_record"]["returned"], 0)
        self.assertEqual(cases["ambiguous"]["query_terms"], [])


if __name__ == "__main__":
    unittest.main()
