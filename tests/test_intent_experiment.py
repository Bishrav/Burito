import unittest

from academy.experiments.intent_classifier import evaluate


class IntentExperimentTests(unittest.TestCase):
    def test_candidate_is_reproducible_and_not_better_than_rule_baseline(self):
        result = evaluate()
        metrics = result["metrics"]
        self.assertEqual(result["dataset"]["train_examples"], 40)
        self.assertEqual(result["dataset"]["held_out_examples"], 20)
        self.assertEqual(metrics["deterministic_rule_baseline"]["accuracy"], 0.9)
        candidate = metrics["one_vs_rest_logistic_regression"]
        self.assertEqual(candidate["accuracy"], 0.9)
        self.assertLessEqual(candidate["macro_f1"],
                             metrics["deterministic_rule_baseline"]["macro_f1"])
        self.assertTrue(metrics["cpu_only"])
        self.assertTrue(result["failure_cases"])


if __name__ == "__main__":
    unittest.main()
