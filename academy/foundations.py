"""Small deterministic mathematics used by Academy exercises and ML baselines."""

import math


def _vector(values, label="vector"):
    result = [float(value) for value in values]
    if not result or any(not math.isfinite(value) for value in result):
        raise ValueError(f"{label} must contain finite values")
    return result


def _matrix(values):
    rows = [_vector(row, "matrix row") for row in values]
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("Matrix must be non-empty and rectangular")
    return rows


def dot(left, right):
    left, right = _vector(left), _vector(right)
    if len(left) != len(right):
        raise ValueError("Vector lengths must match")
    return sum(a * b for a, b in zip(left, right))


def matrix_multiply(left, right):
    left, right = _matrix(left), _matrix(right)
    if len(left[0]) != len(right):
        raise ValueError("Matrix inner dimensions must match")
    columns = list(zip(*right))
    return [[dot(row, column) for column in columns] for row in left]


def mean(values):
    values = _vector(values, "values")
    return sum(values) / len(values)


def variance(values, *, sample=False):
    values = _vector(values, "values")
    denominator = len(values) - 1 if sample else len(values)
    if denominator <= 0:
        raise ValueError("Sample variance requires at least two values")
    center = sum(values) / len(values)
    return sum((value - center) ** 2 for value in values) / denominator


def conditional_probability(joint, condition):
    joint, condition = float(joint), float(condition)
    if not all(math.isfinite(value) and 0 <= value <= 1 for value in (joint, condition)):
        raise ValueError("Probabilities must be finite and between 0 and 1")
    if joint > condition or condition == 0:
        raise ValueError("Joint probability must not exceed a positive condition probability")
    return joint / condition


def bayes(prior, likelihood, false_positive_rate):
    prior, likelihood, false_positive_rate = map(float, (prior, likelihood, false_positive_rate))
    if not all(math.isfinite(value) and 0 <= value <= 1
               for value in (prior, likelihood, false_positive_rate)):
        raise ValueError("Probabilities must be finite and between 0 and 1")
    evidence = likelihood * prior + false_positive_rate * (1 - prior)
    if evidence == 0:
        raise ValueError("Observed evidence has zero probability under this model")
    return likelihood * prior / evidence


def derivative(function, x, *, step=1e-5):
    x, step = float(x), float(step)
    if not math.isfinite(x) or not math.isfinite(step) or step <= 0:
        raise ValueError("Derivative point and step must be finite; step must be positive")
    result = (float(function(x + step)) - float(function(x - step))) / (2 * step)
    if not math.isfinite(result):
        raise ValueError("Derivative estimate is not finite")
    return result


def gradient_descent(objective, gradient, initial, *, learning_rate=0.05, steps=1000):
    parameters = _vector(initial, "initial parameters")
    learning_rate = float(learning_rate)
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("Learning rate must be finite and positive")
    if not isinstance(steps, int) or not 1 <= steps <= 100000:
        raise ValueError("Steps must be an integer between 1 and 100000")
    initial_loss = float(objective(parameters))
    if not math.isfinite(initial_loss):
        raise ValueError("Initial objective must be finite")
    for _ in range(steps):
        direction = _vector(gradient(parameters), "gradient")
        if len(direction) != len(parameters):
            raise ValueError("Gradient size must match parameter size")
        parameters = [value - learning_rate * delta
                      for value, delta in zip(parameters, direction)]
        if any(not math.isfinite(value) for value in parameters):
            raise ValueError("Optimization produced non-finite parameters")
    final_loss = float(objective(parameters))
    if not math.isfinite(final_loss):
        raise ValueError("Final objective must be finite")
    return {"parameters": parameters, "initial_loss": initial_loss,
            "loss": final_loss, "steps": steps}
