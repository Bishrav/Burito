import unittest

from academy.foundations import (
    bayes, conditional_probability, derivative, dot, gradient_descent, matrix_multiply,
    mean, variance,
)


class MathematicalFoundationsTests(unittest.TestCase):
    def test_vector_and_matrix_operations(self):
        self.assertEqual(dot([1, 2, 3], [4, 5, 6]), 32)
        self.assertEqual(matrix_multiply([[1, 2], [3, 4]], [[5], [6]]), [[17], [39]])
        for left, right in (([1], [1, 2]), ([[1, 2]], [[1, 2]])):
            with self.subTest(left=left), self.assertRaises(ValueError):
                matrix_multiply(left, right) if isinstance(left[0], list) else dot(left, right)

    def test_mean_population_and_sample_variance(self):
        self.assertEqual(mean([1, 2, 3, 4]), 2.5)
        self.assertEqual(variance([1, 2, 3, 4]), 1.25)
        self.assertAlmostEqual(variance([1, 2, 3, 4], sample=True), 5 / 3)
        with self.assertRaisesRegex(ValueError, "at least two"):
            variance([4], sample=True)

    def test_conditional_probability_and_bayes(self):
        self.assertAlmostEqual(conditional_probability(0.2, 0.5), 0.4)
        self.assertAlmostEqual(bayes(0.01, 0.95, 0.05), 0.16101694915254236)
        with self.assertRaises(ValueError):
            conditional_probability(0.5, 0.2)
        with self.assertRaisesRegex(ValueError, "zero probability"):
            bayes(0, 0, 0)

    def test_central_derivative_matches_square_function(self):
        self.assertAlmostEqual(derivative(lambda x: x * x, 3), 6, places=7)

    def test_gradient_descent_reduces_convex_quadratic_loss(self):
        objective = lambda p: (p[0] - 2) ** 2 + 3 * (p[1] + 1) ** 2
        gradient = lambda p: [2 * (p[0] - 2), 6 * (p[1] + 1)]
        result = gradient_descent(objective, gradient, [8, 5],
                                  learning_rate=0.1, steps=100)
        self.assertLess(result["loss"], result["initial_loss"] * 1e-6)
        self.assertAlmostEqual(result["parameters"][0], 2, places=5)
        self.assertAlmostEqual(result["parameters"][1], -1, places=5)
        with self.assertRaises(ValueError):
            gradient_descent(objective, gradient, [1, 2], steps=0)


if __name__ == "__main__":
    unittest.main()
