"""Deduplicate tool: remove duplicate entries from a list by specified fields."""

import hashlib
import json
from typing import Any, Dict, List


def deduplicate(input_data: dict) -> dict:
    """Remove duplicate entries from a list by specified fields.

    Parameters:
        data (list[dict]): Input data.
        fields (list[str], optional): Fields to check for duplicates. If empty, compare all fields.
        keep (str, optional): "first" or "last", default "first".

    Returns:
        dict with data, original_count, deduplicated_count, duplicates_removed, and optional error.
    """
    try:
        data = input_data.get("data")
        if not isinstance(data, list):
            return _error_result("Parameter 'data' is required and must be a list of dicts.")

        fields = input_data.get("fields")
        if fields is not None and not isinstance(fields, list):
            return _error_result("Parameter 'fields' must be a list of strings.")

        keep = str(input_data.get("keep", "first")).lower()
        if keep not in ("first", "last"):
            return _error_result("Parameter 'keep' must be 'first' or 'last'.")

        # Use all fields when fields is None or empty
        use_all = fields is None or len(fields) == 0

        original_count = len(data)

        if keep == "first":
            result = _deduplicate_first(data, fields, use_all)
        else:
            result = _deduplicate_last(data, fields, use_all)

        deduplicated_count = len(result)

        return {
            "data": result,
            "original_count": original_count,
            "deduplicated_count": deduplicated_count,
            "duplicates_removed": original_count - deduplicated_count,
        }

    except Exception as exc:
        return _error_result(f"Unexpected error: {str(exc)}")


def _record_hash(record: Any, fields: Any, use_all: bool) -> str:
    """Create a deterministic hash for the relevant parts of a record."""
    if not isinstance(record, dict):
        # For non-dict items, hash the JSON representation
        raw = json.dumps(record, sort_keys=True, default=str)
    elif use_all:
        raw = json.dumps(record, sort_keys=True, default=str)
    else:
        subset = {f: record.get(f) for f in fields}
        raw = json.dumps(subset, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _deduplicate_first(data: List[Any], fields: Any, use_all: bool) -> List[Any]:
    """Keep the first occurrence of each unique record."""
    seen: Dict[str, bool] = {}
    result: List[Any] = []
    for record in data:
        h = _record_hash(record, fields, use_all)
        if h not in seen:
            seen[h] = True
            result.append(record)
    return result


def _deduplicate_last(data: List[Any], fields: Any, use_all: bool) -> List[Any]:
    """Keep the last occurrence of each unique record."""
    # Walk in reverse, keep first seen (which is actually last in original order),
    # then reverse the result to preserve relative ordering.
    seen: Dict[str, bool] = {}
    result: List[Any] = []
    for record in reversed(data):
        h = _record_hash(record, fields, use_all)
        if h not in seen:
            seen[h] = True
            result.append(record)
    result.reverse()
    return result


def _error_result(message: str) -> dict:
    """Return a standardised error response."""
    return {
        "data": [],
        "original_count": 0,
        "deduplicated_count": 0,
        "duplicates_removed": 0,
        "error": message,
    }
