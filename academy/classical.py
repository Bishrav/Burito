"""Small, deterministic classical ML algorithms for Academy exercises."""

from collections import Counter
import math
import random


def _dataset(features, labels=None):
    rows = [[float(value) for value in row] for row in features]
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("Features must be a non-empty rectangular matrix")
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("Features must contain only finite values")
    if labels is not None and len(rows) != len(labels):
        raise ValueError("Feature and label counts must match")
    return rows


def train_test_split(features, labels, *, test_fraction=0.25, seed=0):
    rows = _dataset(features, labels)
    if len(rows) < 2 or not 0 < test_fraction < 1:
        raise ValueError("Split needs at least two rows and a test fraction between 0 and 1")
    test_count = min(len(rows) - 1, max(1, round(len(rows) * test_fraction)))
    indices = list(range(len(rows)))
    random.Random(seed).shuffle(indices)
    test_indices, train_indices = indices[:test_count], indices[test_count:]
    return ([rows[index] for index in train_indices], [labels[index] for index in train_indices],
            [rows[index] for index in test_indices], [labels[index] for index in test_indices])


def train_validation_test_split(features, labels, *, validation_fraction=0.2,
                                test_fraction=0.2, seed=0):
    rows = _dataset(features, labels)
    if (len(rows) < 3 or not 0 < validation_fraction < 1
            or not 0 < test_fraction < 1
            or validation_fraction + test_fraction >= 1):
        raise ValueError("Split needs at least three rows and positive fractions summing below 1")
    validation_count = max(1, round(len(rows) * validation_fraction))
    test_count = max(1, round(len(rows) * test_fraction))
    if validation_count + test_count >= len(rows):
        raise ValueError("Fractions leave no training rows")
    indices = list(range(len(rows)))
    random.Random(seed).shuffle(indices)
    test_indices = indices[:test_count]
    validation_indices = indices[test_count:test_count + validation_count]
    train_indices = indices[test_count + validation_count:]
    return tuple(part for selected in (train_indices, validation_indices, test_indices)
                 for part in ([rows[index] for index in selected],
                              [labels[index] for index in selected]))


def confusion_matrix(actual, predicted, *, labels=None):
    if len(actual) != len(predicted) or not actual:
        raise ValueError("Actual and predicted labels must be non-empty and equally sized")
    classes = list(labels) if labels is not None else sorted(set(actual) | set(predicted), key=str)
    if not classes or len(set(classes)) != len(classes):
        raise ValueError("Class labels must be non-empty and unique")
    lookup = {label: index for index, label in enumerate(classes)}
    matrix = [[0 for _ in classes] for _ in classes]
    for expected, observed in zip(actual, predicted):
        if expected not in lookup or observed not in lookup:
            raise ValueError("Observed label is missing from the class list")
        matrix[lookup[expected]][lookup[observed]] += 1
    return {"labels": classes, "matrix": matrix}


def classification_metrics(actual, predicted, *, positive_label=1):
    result = confusion_matrix(actual, predicted)
    labels, matrix = result["labels"], result["matrix"]
    if len(labels) != 2 or positive_label not in labels:
        raise ValueError("Binary metrics require exactly two classes and a present positive label")
    positive = labels.index(positive_label)
    tp = matrix[positive][positive]
    fp = sum(matrix[row][positive] for row in range(2) if row != positive)
    fn = sum(matrix[positive][column] for column in range(2) if column != positive)
    total = sum(sum(row) for row in matrix)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"confusion_matrix": result, "accuracy": sum(matrix[i][i] for i in range(2)) / total,
            "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def multiclass_metrics(actual, predicted):
    result = confusion_matrix(actual, predicted)
    labels, matrix = result["labels"], result["matrix"]
    total = sum(sum(row) for row in matrix)
    per_class = {}
    for index, label in enumerate(labels):
        tp = matrix[index][index]
        fp = sum(matrix[row][index] for row in range(len(labels)) if row != index)
        fn = sum(matrix[index][column] for column in range(len(labels)) if column != index)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        per_class[str(label)] = {"precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}
    return {"confusion_matrix": result,
            "accuracy": sum(matrix[i][i] for i in range(len(labels))) / total,
            "macro_precision": sum(item["precision"] for item in per_class.values()) / len(labels),
            "macro_recall": sum(item["recall"] for item in per_class.values()) / len(labels),
            "macro_f1": sum(item["f1"] for item in per_class.values()) / len(labels),
            "per_class": per_class}


def _sigmoid(value):
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1 + exp_value)


def fit_logistic_regression(features, labels, *, learning_rate=0.1, steps=2000, l2=0.0):
    rows = _dataset(features, labels)
    if set(labels) != {0, 1}:
        raise ValueError("Binary logistic regression requires both labels 0 and 1")
    learning_rate, l2 = float(learning_rate), float(l2)
    if not math.isfinite(learning_rate) or learning_rate <= 0 or not math.isfinite(l2) or l2 < 0:
        raise ValueError("Learning rate must be positive and regularization non-negative")
    if not isinstance(steps, int) or not 1 <= steps <= 100000:
        raise ValueError("Steps must be an integer between 1 and 100000")
    weights, bias = [0.0] * len(rows[0]), 0.0
    count = len(rows)
    for _ in range(steps):
        weight_gradient = [0.0] * len(weights)
        bias_gradient = 0.0
        for row, label in zip(rows, labels):
            error = _sigmoid(sum(w * x for w, x in zip(weights, row)) + bias) - label
            bias_gradient += error
            for index, value in enumerate(row):
                weight_gradient[index] += error * value
        weights = [weight - learning_rate * (gradient / count + l2 * weight)
                   for weight, gradient in zip(weights, weight_gradient)]
        bias -= learning_rate * bias_gradient / count
        if any(not math.isfinite(value) for value in (*weights, bias)):
            raise ValueError("Logistic regression produced non-finite parameters")
    loss = -sum(label * math.log(max(1e-15, _sigmoid(sum(w*x for w,x in zip(weights,row)) + bias)))
                + (1-label) * math.log(max(1e-15, 1-_sigmoid(sum(w*x for w,x in zip(weights,row)) + bias)))
                for row, label in zip(rows, labels)) / count
    return {"weights": weights, "bias": bias, "loss": loss, "steps": steps, "l2": l2}


def predict_logistic(model, features, *, threshold=0.5):
    rows = _dataset(features)
    threshold = float(threshold)
    if not 0 <= threshold <= 1 or len(rows[0]) != len(model["weights"]):
        raise ValueError("Threshold or feature dimensions are invalid")
    return [int(_sigmoid(sum(w*x for w,x in zip(model["weights"], row)) + model["bias"]) >= threshold)
            for row in rows]


def predict_logistic_probability(model, features):
    rows = _dataset(features)
    if len(rows[0]) != len(model["weights"]):
        raise ValueError("Prediction feature dimensions do not match training")
    return [_sigmoid(sum(w*x for w,x in zip(model["weights"], row)) + model["bias"])
            for row in rows]


def knn_predict(features, labels, query, *, neighbors=3):
    rows = _dataset(features, labels)
    query = [float(value) for value in query]
    if len(query) != len(rows[0]) or any(not math.isfinite(value) for value in query):
        raise ValueError("Query dimensions and values must match the training data")
    if not isinstance(neighbors, int) or not 1 <= neighbors <= len(rows):
        raise ValueError("Neighbor count must be between 1 and training size")
    nearest = sorted((sum((a-b)**2 for a,b in zip(row,query)), index, label)
                     for index, (row, label) in enumerate(zip(rows, labels)))[:neighbors]
    counts = Counter(label for _, _, label in nearest)
    return min(counts, key=lambda label: (-counts[label], str(label)))


class DecisionTree:
    def __init__(self, *, max_depth=5, min_samples_split=2):
        if not isinstance(max_depth, int) or not 0 <= max_depth <= 16:
            raise ValueError("Tree depth must be between 0 and 16")
        if not isinstance(min_samples_split, int) or min_samples_split < 2:
            raise ValueError("min_samples_split must be at least 2")
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.root = None
        self.feature_count = None

    @staticmethod
    def _gini(labels):
        count = len(labels)
        return 1 - sum((n / count) ** 2 for n in Counter(labels).values())

    def fit(self, features, labels):
        rows = _dataset(features, labels)
        if not labels:
            raise ValueError("Decision tree needs labels")
        self.feature_count = len(rows[0])
        self.root = self._grow(rows, list(labels), 0)
        return self

    def _grow(self, rows, labels, depth):
        counts = Counter(labels)
        majority = min(counts, key=lambda label: (-counts[label], str(label)))
        node = {"label": majority}
        if depth >= self.max_depth or len(rows) < self.min_samples_split or len(set(labels)) == 1:
            return node
        parent = self._gini(labels)
        best = None
        for feature in range(self.feature_count):
            values = sorted({row[feature] for row in rows})
            for left_value, right_value in zip(values, values[1:]):
                threshold = (left_value + right_value) / 2
                left = [index for index, row in enumerate(rows) if row[feature] <= threshold]
                right = [index for index, row in enumerate(rows) if row[feature] > threshold]
                score = (len(left) * self._gini([labels[i] for i in left])
                         + len(right) * self._gini([labels[i] for i in right])) / len(labels)
                candidate = (score, feature, threshold, left, right)
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
        if best is None or parent - best[0] <= 1e-12:
            return node
        _, feature, threshold, left, right = best
        node.update(feature=feature, threshold=threshold,
                    left=self._grow([rows[i] for i in left], [labels[i] for i in left], depth+1),
                    right=self._grow([rows[i] for i in right], [labels[i] for i in right], depth+1))
        return node

    def predict(self, features):
        if self.root is None:
            raise ValueError("Fit the tree before predicting")
        rows = _dataset(features)
        if any(len(row) != self.feature_count for row in rows):
            raise ValueError("Prediction feature dimensions do not match training")
        predictions = []
        for row in rows:
            node = self.root
            while "feature" in node:
                node = node["left"] if row[node["feature"]] <= node["threshold"] else node["right"]
            predictions.append(node["label"])
        return predictions


def kmeans(features, clusters, *, seed=0, max_iterations=100):
    rows = _dataset(features)
    if not isinstance(clusters, int) or not 1 <= clusters <= len(rows):
        raise ValueError("Cluster count must be between 1 and sample count")
    if not isinstance(max_iterations, int) or not 1 <= max_iterations <= 10000:
        raise ValueError("max_iterations must be between 1 and 10000")
    randomizer = random.Random(seed)
    centers = [list(rows[index]) for index in randomizer.sample(range(len(rows)), clusters)]
    assignments = [-1] * len(rows)
    for iteration in range(1, max_iterations + 1):
        new_assignments = [min(range(clusters),
            key=lambda index: sum((value-center)**2 for value,center in zip(row,centers[index])))
            for row in rows]
        groups = [[row for row, label in zip(rows, new_assignments) if label == index]
                  for index in range(clusters)]
        new_centers = [([sum(row[column] for row in group) / len(group)
                         for column in range(len(rows[0]))] if group else centers[index])
                       for index, group in enumerate(groups)]
        if new_assignments == assignments and new_centers == centers:
            break
        assignments, centers = new_assignments, new_centers
    inertia = sum(sum((value-center)**2 for value,center in zip(row,centers[label]))
                  for row, label in zip(rows, assignments))
    return {"centers": centers, "labels": assignments,
            "inertia": inertia, "iterations": iteration, "seed": seed}
