"""Compare values tool: compare two datasets or values and return differences."""

from typing import Any, Dict, List, Optional


def compare_values(input_data: dict) -> dict:
    """Compare two datasets or values and return differences.

    Parameters:
        old (any): Previous value (dict, list, or scalar).
        new (any): Current value (dict, list, or scalar).
        key_field (str, optional): For list comparison, field to match records on.

    Returns:
        dict with type, added, removed, modified, unchanged_count, summary, and optional error.
    """
    try:
        if "old" not in input_data or "new" not in input_data:
            return _error_result("Both 'old' and 'new' parameters are required.")

        old = input_data.get("old")
        new = input_data.get("new")
        key_field = input_data.get("key_field")

        # --- Determine comparison type -----------------------------------------
        if isinstance(old, dict) and isinstance(new, dict):
            return _compare_dicts(old, new)
        elif isinstance(old, list) and isinstance(new, list):
            return _compare_lists(old, new, key_field)
        else:
            return _compare_scalars(old, new)

    except Exception as exc:
        return _error_result(f"Unexpected error: {str(exc)}")


def _compare_dicts(old: dict, new: dict) -> dict:
    """Compare two dicts and report added, removed, and changed keys."""
    old_keys = set(old.keys())
    new_keys = set(new.keys())

    added_keys = sorted(new_keys - old_keys)
    removed_keys = sorted(old_keys - new_keys)
    common_keys = old_keys & new_keys

    added = [{"key": k, "value": new[k]} for k in added_keys]
    removed = [{"key": k, "value": old[k]} for k in removed_keys]

    modified: List[Dict[str, Any]] = []
    unchanged_count = 0

    for k in sorted(common_keys):
        if old[k] != new[k]:
            modified.append({"key": k, "old_value": old[k], "new_value": new[k]})
        else:
            unchanged_count += 1

    parts: List[str] = []
    if added:
        parts.append(f"{len(added)} added")
    if removed:
        parts.append(f"{len(removed)} removed")
    if modified:
        parts.append(f"{len(modified)} modified")
    parts.append(f"{unchanged_count} unchanged")
    summary = ", ".join(parts)

    return {
        "type": "dict",
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged_count": unchanged_count,
        "summary": summary,
    }


def _compare_lists(old: list, new: list, key_field: Optional[str]) -> dict:
    """Compare two lists. Use key_field for record matching if provided."""
    # If key_field is provided and items are dicts, do keyed comparison
    if key_field is not None:
        return _compare_lists_keyed(old, new, key_field)

    # Without key_field, do a positional / set-based comparison
    return _compare_lists_positional(old, new)


def _compare_lists_keyed(old: list, new: list, key_field: str) -> dict:
    """Compare two lists of dicts using a shared key field."""
    old_map: Dict[Any, Dict] = {}
    for rec in old:
        if isinstance(rec, dict):
            k = rec.get(key_field)
            if k is not None:
                old_map[k] = rec

    new_map: Dict[Any, Dict] = {}
    for rec in new:
        if isinstance(rec, dict):
            k = rec.get(key_field)
            if k is not None:
                new_map[k] = rec

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    added_keys = sorted(new_keys - old_keys, key=str)
    removed_keys = sorted(old_keys - new_keys, key=str)
    common_keys = old_keys & new_keys

    added = [new_map[k] for k in added_keys]
    removed = [old_map[k] for k in removed_keys]

    modified: List[Dict[str, Any]] = []
    unchanged_count = 0

    for k in sorted(common_keys, key=str):
        if old_map[k] != new_map[k]:
            changes = _diff_record(old_map[k], new_map[k])
            modified.append({
                "key": k,
                "changes": changes,
                "old": old_map[k],
                "new": new_map[k],
            })
        else:
            unchanged_count += 1

    parts: List[str] = []
    if added:
        parts.append(f"{len(added)} added")
    if removed:
        parts.append(f"{len(removed)} removed")
    if modified:
        parts.append(f"{len(modified)} modified")
    parts.append(f"{unchanged_count} unchanged")
    summary = ", ".join(parts)

    return {
        "type": "list",
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged_count": unchanged_count,
        "summary": summary,
    }


def _compare_lists_positional(old: list, new: list) -> dict:
    """Compare two lists without a key field, using positional comparison."""
    added: List[Any] = []
    removed: List[Any] = []
    modified: List[Dict[str, Any]] = []
    unchanged_count = 0

    max_len = max(len(old), len(new))
    for i in range(max_len):
        if i >= len(old):
            added.append(new[i])
        elif i >= len(new):
            removed.append(old[i])
        elif old[i] != new[i]:
            modified.append({"index": i, "old_value": old[i], "new_value": new[i]})
        else:
            unchanged_count += 1

    parts: List[str] = []
    if added:
        parts.append(f"{len(added)} added")
    if removed:
        parts.append(f"{len(removed)} removed")
    if modified:
        parts.append(f"{len(modified)} modified")
    parts.append(f"{unchanged_count} unchanged")
    summary = ", ".join(parts)

    return {
        "type": "list",
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged_count": unchanged_count,
        "summary": summary,
    }


def _compare_scalars(old: Any, new: Any) -> dict:
    """Compare two scalar values."""
    modified: List[Dict[str, Any]] = []
    unchanged_count = 0

    if old == new:
        unchanged_count = 1
        summary = "Values are identical."
    else:
        change: Dict[str, Any] = {"old_value": old, "new_value": new}
        # Add numeric diff if both are numeric
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            if not isinstance(old, bool) and not isinstance(new, bool):
                change["numeric_change"] = new - old
                change["percent_change"] = (
                    round(((new - old) / old) * 100, 4) if old != 0 else None
                )
        modified.append(change)
        summary = f"Value changed from {_repr(old)} to {_repr(new)}."

    return {
        "type": "scalar",
        "added": [],
        "removed": [],
        "modified": modified,
        "unchanged_count": unchanged_count,
        "summary": summary,
    }


def _diff_record(old: dict, new: dict) -> List[Dict[str, Any]]:
    """Return a list of field-level changes between two dicts."""
    changes: List[Dict[str, Any]] = []
    all_keys = set(old.keys()) | set(new.keys())
    for k in sorted(all_keys):
        old_val = old.get(k)
        new_val = new.get(k)
        if old_val != new_val:
            changes.append({"field": k, "old_value": old_val, "new_value": new_val})
    return changes


def _repr(value: Any) -> str:
    """Produce a short human-readable representation of a value."""
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)


def _error_result(message: str) -> dict:
    """Return a standardised error response."""
    return {
        "type": "unknown",
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged_count": 0,
        "summary": "",
        "error": message,
    }
