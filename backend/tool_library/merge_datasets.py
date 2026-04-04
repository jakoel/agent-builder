"""Merge datasets tool: join two lists of dicts on a shared key."""

from collections import OrderedDict
from typing import Any, Dict, List, Optional


def merge_datasets(input_data: dict) -> dict:
    """Join two lists of dicts on a shared key.

    Parameters:
        left (list[dict]): Left dataset.
        right (list[dict]): Right dataset.
        left_key (str): Key field in left dataset.
        right_key (str, optional): Key field in right dataset (defaults to left_key).
        how (str, optional): Join type - "inner", "left", "right", "outer". Default "inner".

    Returns:
        dict with data, count, left_count, right_count, matched_count, and optional error.
    """
    try:
        left = input_data.get("left")
        right = input_data.get("right")
        left_key = input_data.get("left_key")
        right_key = input_data.get("right_key")
        how = str(input_data.get("how", "inner")).lower()

        # --- Validation --------------------------------------------------------
        if not isinstance(left, list):
            return _error_result("Parameter 'left' is required and must be a list of dicts.")
        if not isinstance(right, list):
            return _error_result("Parameter 'right' is required and must be a list of dicts.")
        if not isinstance(left_key, str) or left_key == "":
            return _error_result("Parameter 'left_key' is required and must be a non-empty string.")

        if right_key is None:
            right_key = left_key

        valid_joins = {"inner", "left", "right", "outer"}
        if how not in valid_joins:
            return _error_result(f"Invalid join type '{how}'. Must be one of {sorted(valid_joins)}.")

        # --- Build index on right dataset (group by key) -----------------------
        right_index: Dict[Any, List[Dict[str, Any]]] = {}
        for rec in right:
            if not isinstance(rec, dict):
                continue
            key_val = rec.get(right_key)
            right_index.setdefault(key_val, []).append(rec)

        # --- Build index on left dataset (for right/outer) ---------------------
        left_index: Dict[Any, List[Dict[str, Any]]] = {}
        for rec in left:
            if not isinstance(rec, dict):
                continue
            key_val = rec.get(left_key)
            left_index.setdefault(key_val, []).append(rec)

        result: List[Dict[str, Any]] = []
        matched_keys: set = set()

        # --- Process left rows -------------------------------------------------
        for l_rec in left:
            if not isinstance(l_rec, dict):
                continue
            l_val = l_rec.get(left_key)
            right_matches = right_index.get(l_val, [])

            if right_matches:
                matched_keys.add(l_val)
                for r_rec in right_matches:
                    merged = {**l_rec, **r_rec}
                    result.append(merged)
            elif how in ("left", "outer"):
                result.append(dict(l_rec))

        # --- Process unmatched right rows (for right/outer) --------------------
        if how in ("right", "outer"):
            for r_rec in right:
                if not isinstance(r_rec, dict):
                    continue
                r_val = r_rec.get(right_key)
                if r_val not in matched_keys:
                    # Check if there are left matches for right join
                    if r_val not in left_index:
                        result.append(dict(r_rec))

        matched_count = len(matched_keys)

        return {
            "data": result,
            "count": len(result),
            "left_count": len(left),
            "right_count": len(right),
            "matched_count": matched_count,
        }

    except Exception as exc:
        return _error_result(f"Unexpected error: {str(exc)}")


def _error_result(message: str) -> dict:
    """Return a standardised error response."""
    return {
        "data": [],
        "count": 0,
        "left_count": 0,
        "right_count": 0,
        "matched_count": 0,
        "error": message,
    }
