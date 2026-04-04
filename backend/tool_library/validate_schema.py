import re


_TYPE_MAP = {
    "string": str,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def validate_schema(input_data: dict) -> dict:
    """Validate a dict against expected types, required fields, and patterns.

    Parameters:
        data (dict): Data to validate.
        schema (dict): Schema definition with a "fields" mapping.

    Returns:
        dict with keys: valid, errors, checked_fields, error (optional).
    """
    try:
        if not isinstance(input_data, dict):
            return {"valid": False, "errors": [], "checked_fields": 0, "error": "input_data must be a dict"}

        data = input_data.get("data")
        schema = input_data.get("schema")

        if data is None or schema is None:
            return {
                "valid": False,
                "errors": [],
                "checked_fields": 0,
                "error": "Both 'data' and 'schema' are required",
            }

        if not isinstance(data, dict):
            return {
                "valid": False,
                "errors": [{"field": "(root)", "message": "'data' must be a dict"}],
                "checked_fields": 0,
                "error": "'data' must be a dict",
            }

        if not isinstance(schema, dict):
            return {
                "valid": False,
                "errors": [{"field": "(root)", "message": "'schema' must be a dict"}],
                "checked_fields": 0,
                "error": "'schema' must be a dict",
            }

        fields_spec = schema.get("fields", {})
        if not isinstance(fields_spec, dict):
            return {
                "valid": False,
                "errors": [],
                "checked_fields": 0,
                "error": "'schema.fields' must be a dict",
            }

        errors = []
        checked = 0

        for field_name, rules in fields_spec.items():
            if not isinstance(rules, dict):
                continue

            checked += 1
            required = rules.get("required", False)
            value = data.get(field_name)
            present = field_name in data

            # --- Required check ---
            if required and not present:
                errors.append({"field": field_name, "message": "Field is required but missing"})
                continue

            if not present:
                continue

            # --- Type check ---
            expected_type_name = rules.get("type")
            if expected_type_name and expected_type_name in _TYPE_MAP:
                expected_type = _TYPE_MAP[expected_type_name]
                # In Python, bool is a subclass of int. For "number" we want to
                # accept int/float but reject bool; for "boolean" accept only bool.
                if expected_type_name == "number" and isinstance(value, bool):
                    errors.append({
                        "field": field_name,
                        "message": f"Expected type 'number', got 'boolean'",
                        "value": value,
                    })
                    continue
                if not isinstance(value, expected_type):
                    actual = type(value).__name__
                    errors.append({
                        "field": field_name,
                        "message": f"Expected type '{expected_type_name}', got '{actual}'",
                        "value": value,
                    })
                    continue

            # --- Pattern check (strings only) ---
            pattern = rules.get("pattern")
            if pattern and isinstance(value, str):
                try:
                    if not re.search(pattern, value):
                        errors.append({
                            "field": field_name,
                            "message": f"Value does not match pattern '{pattern}'",
                            "value": value,
                        })
                except re.error as exc:
                    errors.append({
                        "field": field_name,
                        "message": f"Invalid regex pattern '{pattern}': {exc}",
                    })

            # --- Min / Max for numbers ---
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                min_val = rules.get("min")
                max_val = rules.get("max")
                if min_val is not None and value < min_val:
                    errors.append({
                        "field": field_name,
                        "message": f"Value {value} is less than minimum {min_val}",
                        "value": value,
                    })
                if max_val is not None and value > max_val:
                    errors.append({
                        "field": field_name,
                        "message": f"Value {value} is greater than maximum {max_val}",
                        "value": value,
                    })

            # --- Min / Max for arrays (length) ---
            if isinstance(value, list):
                min_len = rules.get("min")
                max_len = rules.get("max")
                if min_len is not None and len(value) < min_len:
                    errors.append({
                        "field": field_name,
                        "message": f"Array length {len(value)} is less than minimum {min_len}",
                        "value": value,
                    })
                if max_len is not None and len(value) > max_len:
                    errors.append({
                        "field": field_name,
                        "message": f"Array length {len(value)} is greater than maximum {max_len}",
                        "value": value,
                    })

            # --- Enum check ---
            enum_values = rules.get("enum")
            if enum_values is not None and isinstance(enum_values, list):
                if value not in enum_values:
                    errors.append({
                        "field": field_name,
                        "message": f"Value not in allowed values: {enum_values}",
                        "value": value,
                    })

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "checked_fields": checked,
        }

    except Exception as exc:
        return {
            "valid": False,
            "errors": [],
            "checked_fields": 0,
            "error": f"Unexpected error: {exc}",
        }
