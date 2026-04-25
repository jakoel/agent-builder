"""JSON transform tool: filter, select, sort, group, and limit a JSON array."""

from typing import Any, Dict, List


def json_transform(input_data: dict) -> dict:
    """Filter, select fields, sort, or group a JSON array.

    Parameters:
        data (list[dict]): Input array of objects.
        select_fields (list[str], optional): Fields to keep.
        filter_field (str, optional): Field to filter on.
        filter_value (any, optional): Value to match.
        filter_op (str, optional): Comparison operator. Default "eq".
            Supported: "eq", "ne", "gt", "lt", "gte", "lte", "contains", "in".
        sort_by (str, optional): Field to sort by.
        sort_desc (bool, optional): Descending sort, default false.
        group_by (str, optional): Field to group by.
        limit (int, optional): Max records to return.

    Returns:
        dict with data, count, grouped flag, and optional error.
    """
    try:
        data = input_data.get("data")
        if not isinstance(data, list):
            return {"data": [], "count": 0, "error": "Parameter 'data' is required and must be a list of dicts."}

        working: List[Dict[str, Any]] = list(data)

        # --- 1. Filter ---------------------------------------------------------
        filter_field = input_data.get("filter_field")
        filter_value = input_data.get("filter_value")
        filter_op = str(input_data.get("filter_op", "eq")).lower()

        valid_ops = {"eq", "ne", "gt", "lt", "gte", "lte", "contains", "in"}
        if filter_op not in valid_ops:
            return {"data": [], "count": 0, "error": f"Invalid filter_op '{filter_op}'. Must be one of {sorted(valid_ops)}."}

        if filter_field is not None:
            filtered: List[Dict[str, Any]] = []
            for record in working:
                val = record.get(filter_field)
                if _apply_op(val, filter_op, filter_value):
                    filtered.append(record)
            working = filtered

        # --- 2. Select fields --------------------------------------------------
        select_fields = input_data.get("select_fields")
        if isinstance(select_fields, list) and select_fields:
            working = [{k: rec.get(k) for k in select_fields} for rec in working]

        # --- 3. Sort -----------------------------------------------------------
        sort_by = input_data.get("sort_by")
        sort_desc = bool(input_data.get("sort_desc", False))

        if sort_by is not None:
            def sort_key(rec: dict) -> Any:
                v = rec.get(sort_by)
                # Put None values last regardless of direction
                if v is None:
                    return (1, "")
                return (0, v)

            try:
                working.sort(key=sort_key, reverse=sort_desc)
            except TypeError:
                # Fallback: stringify values for comparison when types are mixed
                working.sort(key=lambda r: str(r.get(sort_by, "")), reverse=sort_desc)

        # --- 4. Group ----------------------------------------------------------
        group_by = input_data.get("group_by")
        grouped = False

        if group_by is not None:
            groups: Dict[str, List[Dict[str, Any]]] = {}
            for rec in working:
                key = str(rec.get(group_by, "__none__"))
                groups.setdefault(key, []).append(rec)
            grouped = True

        # --- 5. Limit ----------------------------------------------------------
        limit = input_data.get("limit")

        if grouped and group_by is not None:
            if limit is not None:
                limit = int(limit)
                # Apply limit to each group
                groups = {k: v[:limit] for k, v in groups.items()}
            total = sum(len(v) for v in groups.values())
            return {"data": groups, "count": total, "grouped": True}

        if limit is not None:
            limit = int(limit)
            working = working[:limit]

        return {"data": working, "count": len(working)}

    except Exception as exc:
        return {"data": [], "count": 0, "error": f"Unexpected error: {str(exc)}"}


def _apply_op(val: Any, op: str, target: Any) -> bool:
    """Apply a comparison operation. Returns False on type errors instead of raising."""
    try:
        if op == "eq":
            return val == target
        if op == "ne":
            return val != target
        # For ordered comparisons try numeric coercion first so that string
        # values from CSV ("92") compare correctly against numeric targets (60).
        if op in ("gt", "lt", "gte", "lte"):
            try:
                val = float(val)
                target = float(target)
            except (TypeError, ValueError):
                pass
        if op == "gt":
            return val > target
        if op == "lt":
            return val < target
        if op == "gte":
            return val >= target
        if op == "lte":
            return val <= target
        if op == "contains":
            if isinstance(val, str) and isinstance(target, str):
                return target in val
            if isinstance(val, list):
                return target in val
            return False
        if op == "in":
            if isinstance(target, (list, tuple, set)):
                return val in target
            return False
    except (TypeError, ValueError):
        return False
    return False
