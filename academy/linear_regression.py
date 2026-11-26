"""Small standard-library ordinary least-squares baseline for 1D synthetic data."""

import math


def _points(points):
    result = [(float(x), float(y)) for x, y in points]
    if len(result) < 2 or any(not math.isfinite(value) for row in result for value in row):
        raise ValueError("Provide at least two finite (x, y) observations")
    return result


def fit_line(points):
    """Return (slope, intercept) for the least-squares line through points."""
    points = _points(points)
    mean_x = sum(x for x, _ in points) / len(points)
    mean_y = sum(y for _, y in points) / len(points)
    variance_x = sum((x - mean_x) ** 2 for x, _ in points)
    if variance_x == 0:
        raise ValueError("At least two distinct x values are required")
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / variance_x
    return slope, mean_y - slope * mean_x


def fit_gradient_descent(points, *, learning_rate=0.05, steps=5000):
    """Fit 1D MSE regression by batch gradient descent; return parameters and losses."""
    points = _points(points)
    learning_rate = float(learning_rate)
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("Learning rate must be finite and positive")
    if not isinstance(steps, int) or not 1 <= steps <= 100000:
        raise ValueError("Steps must be an integer between 1 and 100000")
    slope, intercept = 0.0, 0.0
    count = len(points)

    def loss(m, b):
        return sum((y - (m * x + b)) ** 2 for x, y in points) / count

    initial_loss = loss(slope, intercept)
    for _ in range(steps):
        slope_gradient = sum(-2 * x * (y - (slope * x + intercept))
                             for x, y in points) / count
        intercept_gradient = sum(-2 * (y - (slope * x + intercept))
                                 for x, y in points) / count
        slope -= learning_rate * slope_gradient
        intercept -= learning_rate * intercept_gradient
        if not math.isfinite(slope) or not math.isfinite(intercept):
            raise ValueError("Optimization diverged to non-finite parameters")
    return {"slope": slope, "intercept": intercept,
            "initial_loss": initial_loss, "loss": loss(slope, intercept),
            "steps": steps}


def evaluate_line(points, slope, intercept):
    """Return MSE, MAE and R²; R² is undefined for constant target values."""
    points = _points(points)
    slope, intercept = float(slope), float(intercept)
    if not math.isfinite(slope) or not math.isfinite(intercept):
        raise ValueError("Model parameters must be finite")
    residuals = [y - (slope * x + intercept) for x, y in points]
    mse = sum(error ** 2 for error in residuals) / len(residuals)
    mae = sum(abs(error) for error in residuals) / len(residuals)
    mean_y = sum(y for _, y in points) / len(points)
    total = sum((y - mean_y) ** 2 for _, y in points)
    return {"mse": mse, "mae": mae, "r2": 1 - sum(e ** 2 for e in residuals) / total if total else None}
