import unittest

from academy.linear_regression import evaluate_line, fit_gradient_descent, fit_line


class LinearRegressionTests(unittest.TestCase):
    def test_recovers_line_and_evaluates_held_out_synthetic_points(self):
        slope, intercept = fit_line([(0, 1), (1, 3), (2, 5)])
        self.assertAlmostEqual(slope, 2)
        self.assertAlmostEqual(intercept, 1)
        self.assertEqual(evaluate_line([(3, 7), (4, 9)], slope, intercept),
                         {"mse": 0.0, "mae": 0.0, "r2": 1.0})

    def test_metrics_report_error_and_undefined_constant_target_r2(self):
        self.assertEqual(evaluate_line([(0, 1), (1, 3)], 1, 1),
                         {"mse": 0.5, "mae": 0.5, "r2": 0.5})
        self.assertIsNone(evaluate_line([(0, 4), (1, 4)], 0, 3)["r2"])

    def test_gradient_descent_regression_matches_closed_form_on_held_out_points(self):
        points = [(0, 1), (1, 3), (2, 5), (3, 7)]
        result = fit_gradient_descent(points, learning_rate=0.05, steps=5000)
        self.assertLess(result["loss"], result["initial_loss"] * 1e-8)
        self.assertAlmostEqual(result["slope"], 2, places=4)
        self.assertAlmostEqual(result["intercept"], 1, places=4)
        self.assertEqual(evaluate_line([(4, 9), (5, 11)], result["slope"],
                                       result["intercept"])["r2"], 1.0)

    def test_rejects_insufficient_degenerate_and_nonfinite_data(self):
        for points in ([], [(1, 2)], [(1, 2), (1, 3)], [(0, 1), (1, float("nan"))]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                fit_line(points)
        with self.assertRaises(ValueError):
            evaluate_line([(0, 1), (1, 2)], float("inf"), 0)


if __name__ == "__main__":
    unittest.main()
