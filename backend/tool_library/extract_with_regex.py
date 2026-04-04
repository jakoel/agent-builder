"""Apply a regex pattern to text and return all matches."""

import re
from typing import Any, Dict, List, Union


def extract_with_regex(input_data: dict) -> dict:
    """Apply a regex pattern to text and return all matches.

    Parameters:
        text (str): Text to search
        pattern (str): Regex pattern
        flags (str, optional): Flags like "i" for ignorecase, "m" for multiline, "s" for dotall
        group (int, optional): Specific group to extract, default 0 (full match)
        max_matches (int, optional): Max matches to return, default 100

    Returns:
        dict with keys: matches (list), count, pattern, and optionally error.
    """
    text = input_data.get("text")
    if not isinstance(text, str):
        return {"error": "Missing or invalid required parameter: text"}

    pattern = input_data.get("pattern")
    if not isinstance(pattern, str):
        return {"error": "Missing or invalid required parameter: pattern"}

    flags_str = input_data.get("flags", "")
    group = input_data.get("group", 0)
    max_matches = input_data.get("max_matches", 100)

    if not isinstance(group, int) or group < 0:
        return {"error": "Parameter 'group' must be a non-negative integer"}
    if not isinstance(max_matches, int) or max_matches <= 0:
        return {"error": "Parameter 'max_matches' must be a positive integer"}

    # Parse flags
    flag_map = {
        "i": re.IGNORECASE,
        "m": re.MULTILINE,
        "s": re.DOTALL,
        "x": re.VERBOSE,
    }
    re_flags = 0
    for char in str(flags_str).lower():
        if char in flag_map:
            re_flags |= flag_map[char]
        elif char.strip():
            return {"error": f"Unknown flag character: '{char}'. Supported: i, m, s, x"}

    try:
        compiled = re.compile(pattern, re_flags)
    except re.error as exc:
        return {"error": f"Invalid regex pattern: {str(exc)}", "pattern": pattern}

    has_named_groups = bool(compiled.groupindex)
    matches: List[Union[str, Dict[str, str]]] = []

    try:
        for i, match in enumerate(compiled.finditer(text)):
            if i >= max_matches:
                break

            if has_named_groups and group == 0:
                # Return named groups as a dict, plus the full match
                entry: Dict[str, Any] = {"match": match.group(0)}
                entry.update(match.groupdict())
                matches.append(entry)
            else:
                try:
                    matches.append(match.group(group))
                except IndexError:
                    return {
                        "error": f"Group {group} does not exist in pattern. "
                                 f"Pattern has {compiled.groups} group(s).",
                        "pattern": pattern,
                    }
    except Exception as exc:
        return {"error": f"Error during matching: {str(exc)}", "pattern": pattern}

    return {
        "matches": matches,
        "count": len(matches),
        "pattern": pattern,
    }
