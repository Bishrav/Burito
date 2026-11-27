import unittest

from academy.classical import (
    DecisionTree, classification_metrics, confusion_matrix, fit_logistic_regression,
    kmeans, knn_predict, predict_logistic, train_test_split,
    train_validation_test_split,
)


class ClassicalLearningTests(unittest.TestCase):
    def test_train_test_split_is_seeded_and_keeps_pairs(self):
        features = [[index] for index in range(20)]
        labels = [index % 2 for index in range(20)]
        first = train_test_split(features, labels, seed=17)
        self.assertEqual(first, train_test_split(features, labels, seed=17))
        train_x, train_y, test_x, test_y = first
        self.assertEqual(len(test_x), 5)
        self.assertEqual(len(train_x) + len(test_x), 20)
        self.assertTrue(all(int(row[0]) % 2 == label for row, label in zip(train_x, train_y)))
        self.assertTrue(all(int(row[0]) % 2 == label for row, label in zip(test_x, test_y)))

    def test_train_validation_test_split_is_seeded_and_disjoint(self):
        features = [[index] for index in range(20)]
        labels = [index % 2 for index in range(20)]
        first = train_validation_test_split(features, labels, seed=12)
        self.assertEqual(first, train_validation_test_split(features, labels, seed=12))
        train_x, train_y, validation_x, validation_y, test_x, test_y = first
        self.assertTrue(train_x and validation_x and test_x)
        pairs = list(zip(train_x, train_y)) + list(zip(validation_x, validation_y)) \
            + list(zip(test_x, test_y))
        self.assertEqual(sorted(pairs), list(zip(features, labels)))
        with self.assertRaises(ValueError):
            train_validation_test_split([[1], [2], [3]], [0, 1, 0],
                                        validation_fraction=0.5, test_fraction=0.5)

    def test_logistic_regression_learns_linearly_separable_binary_data(self):
        features = [[-3, -2], [-2, -1], [-1, -2], [1, 1], [2, 1], [3, 2]]
        labels = [0, 0, 0, 1, 1, 1]
        model = fit_logistic_regression(features, labels, learning_rate=0.2, steps=1500, l2=0.01)
        self.assertEqual(predict_logistic(model, features), labels)
        self.assertTrue(0 < model["loss"] < 0.1)
        self.assertEqual(len(predict_logistic(model, [[-5, -3], [5, 3]])), 2)
        with self.assertRaisesRegex(ValueError, "both labels"):
            fit_logistic_regression([[1], [2]], [1, 1])

    def test_knn_predicts_nearest_majority_with_stable_ties(self):
        self.assertEqual(knn_predict([[0], [1], [5], [6]], ["a", "a", "b", "b"], [0.5], neighbors=2), "a")
        self.assertEqual(knn_predict([[0], [2], [4]], [1, 0, 1], [1], neighbors=2), 0)
        with self.assertRaises(ValueError):
            knn_predict([[0]], [0], [1], neighbors=2)

    def test_decision_tree_fits_simple_threshold_and_checks_dimensions(self):
        features = [[0], [1], [2], [3], [4], [5]]
        labels = ["low", "low", "low", "high", "high", "high"]
        model = DecisionTree(max_depth=2).fit(features, labels)
        self.assertEqual(model.predict(features), labels)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            model.predict([[1, 2]])

    def test_kmeans_is_reproducible_and_reduces_within_cluster_error(self):
        features = [[0, 0], [0, 1], [1, 0], [10, 10], [10, 11], [11, 10]]
        first = kmeans(features, 2, seed=22)
        self.assertEqual(first, kmeans(features, 2, seed=22))
        self.assertEqual(len(set(first["labels"])), 2)
        self.assertLess(first["inertia"], 4)

    def test_confusion_precision_recall_f1_and_accuracy(self):
        self.assertEqual(confusion_matrix([0, 0, 1, 1], [0, 1, 1, 1]),
                         {"labels": [0, 1], "matrix": [[1, 1], [0, 2]]})
        metrics = classification_metrics([0, 0, 1, 1], [0, 1, 1, 1])
        self.assertEqual(metrics["accuracy"], 0.75)
        self.assertEqual(metrics["precision"], 2 / 3)
        self.assertEqual(metrics["recall"], 1)
        self.assertEqual(metrics["f1"], 0.8)


if __name__ == "__main__":
    unittest.main()
