"""Calculate stats tool: compute statistical measures on numeric data."""

import math
from typing import Any, Dict, List, Optional


def calculate_stats(input_data: dict) -> dict:
    """Compute statistical measures on numeric data.

    Parameters:
        values (list[number]): Numeric values.
            OR
        data (list[dict]): Array of objects.
        field (str): Field to compute stats on (used with data).
        percentiles (list[number], optional): Percentiles to compute, e.g. [25, 50, 75, 90, 95, 99].

    Returns:
        dict with min, max, mean, median, std_dev, variance, sum, count, percentiles, and optional error.
    """
    try:
        values = input_data.get("values")
        data = input_data.get("data")
        field = input_data.get("field")
        requested_percentiles = input_data.get("percentiles")

        # --- Extract numeric values --------------------------------------------
        nums: List[float] = []

        if values is not None:
            if not isinstance(values, list):
                return _error_result("Parameter 'values' must be a list of numbers.")
            for v in values:
                parsed = _to_number(v)
                if parsed is not None:
                    nums.append(parsed)
        elif data is not None:
            if not isinstance(data, list):
                return _error_result("Parameter 'data' must be a list of dicts.")
            if not isinstance(field, str) or field == "":
                return _error_result("Parameter 'field' is required when using 'data'.")
            for rec in data:
                if isinstance(rec, dict):
                    parsed = _to_number(rec.get(field))
                    if parsed is not None:
                        nums.append(parsed)
        else:
            return _error_result("Either 'values' or 'data'+'field' must be provided.")

        if len(nums) == 0:
            return _error_result("No valid numeric values found.")

        # --- Compute core statistics -------------------------------------------
        nums_sorted = sorted(nums)
        count = len(nums_sorted)
        total = math.fsum(nums_sorted)
        mean = total / count
        min_val = nums_sorted[0]
        max_val = nums_sorted[-1]
        median = _compute_percentile(nums_sorted, 50.0)

        # Variance (population) and std_dev
        variance = math.fsum((x - mean) ** 2 for x in nums_sorted) / count
        std_dev = math.sqrt(variance)

        result: Dict[str, Any] = {
            "min": min_val,
            "max": max_val,
            "mean": round(mean, 10),
            "median": median,
            "std_dev": round(std_dev, 10),
            "variance": round(variance, 10),
            "sum": total,
            "count": count,
        }

        # --- Compute requested percentiles -------------------------------------
        if isinstance(requested_percentiles, list) and requested_percentiles:
            pct_results: Dict[str, float] = {}
            for p in requested_percentiles:
                p_num = _to_number(p)
                if p_num is not None and 0 <= p_num <= 100:
                    pct_results[str(p)] = _compute_percentile(nums_sorted, p_num)
            result["percentiles"] = pct_results

        return result

    except Exception as exc:
        return _error_result(f"Unexpected error: {str(exc)}")


def _compute_percentile(sorted_data: List[float], percentile: float) -> float:
    """Compute a percentile value using linear interpolation."""
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]

    # Rank (0-indexed fractional position)
    rank = (percentile / 100.0) * (n - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))

    if lower == upper:
        return sorted_data[lower]

    fraction = rank - lower
    return sorted_data[lower] + fraction * (sorted_data[upper] - sorted_data[lower])


def _to_number(value: Any) -> Optional[float]:
    """Try to convert a value to float. Return None on failure."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, bool):
            return None
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, OverflowError):
            return None
    return None


def _error_result(message: str) -> dict:
    """Return a standardised error response."""
    return {
        "min": None,
        "max": None,
        "mean": None,
        "median": None,
        "std_dev": None,
        "variance": None,
        "sum": None,
        "count": 0,
        "error": message,
    }
