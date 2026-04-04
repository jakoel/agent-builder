import datetime
import time as _time


_COMMON_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",   # ISO 8601 with microseconds and timezone
    "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601 with timezone
    "%Y-%m-%dT%H:%M:%S.%f",      # ISO 8601 with microseconds
    "%Y-%m-%dT%H:%M:%S",         # ISO 8601
    "%Y-%m-%d %H:%M:%S",         # Standard datetime
    "%Y-%m-%d %H:%M",            # Standard datetime without seconds
    "%Y-%m-%d",                   # ISO date
    "%m/%d/%Y %H:%M:%S",         # US datetime
    "%m/%d/%Y %H:%M",            # US datetime without seconds
    "%m/%d/%Y",                   # US date
    "%d/%m/%Y %H:%M:%S",         # European datetime
    "%d/%m/%Y %H:%M",            # European datetime without seconds
    "%d/%m/%Y",                   # European date
    "%d-%m-%Y",                   # European date with dashes
    "%B %d, %Y",                  # "January 15, 2024"
    "%b %d, %Y",                  # "Jan 15, 2024"
    "%d %B %Y",                   # "15 January 2024"
    "%d %b %Y",                   # "15 Jan 2024"
    "%Y%m%d",                     # Compact date
    "%Y%m%d%H%M%S",              # Compact datetime
]


def _parse_date(date_str: str, fmt: str = None) -> datetime.datetime:
    """Parse a date string, optionally with an explicit format."""
    if fmt:
        return datetime.datetime.strptime(date_str, fmt)

    date_str_clean = date_str.strip()

    # Try Unix timestamp (integer or float)
    try:
        ts = float(date_str_clean)
        if 1e9 < ts < 1e11:
            return datetime.datetime.fromtimestamp(ts)
    except ValueError:
        pass

    for f in _COMMON_FORMATS:
        try:
            return datetime.datetime.strptime(date_str_clean, f)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date string: '{date_str}'")


def date_calc(input_data: dict) -> dict:
    """Parse dates, compute differences, add/subtract durations, format output.

    Parameters:
        date (str): Date string to process.
        format (str, optional): Input strftime format. Auto-detects if omitted.
        operation (str, optional): "parse", "diff", "add", "subtract". Default "parse".
        date2 (str, optional): Second date for diff operation.
        days (int, optional): Days to add/subtract.
        hours (int, optional): Hours to add/subtract.
        minutes (int, optional): Minutes to add/subtract.
        output_format (str, optional): Output strftime format. Default "%Y-%m-%d %H:%M:%S".

    Returns:
        dict with keys: result, iso, timestamp (optional), diff (optional), error (optional).
    """
    try:
        if not isinstance(input_data, dict):
            return {"result": None, "iso": None, "error": "input_data must be a dict"}

        date_str = input_data.get("date")
        if date_str is None:
            return {"result": None, "iso": None, "error": "'date' is required"}

        date_str = str(date_str)
        fmt = input_data.get("format")
        operation = input_data.get("operation", "parse").lower()
        output_format = input_data.get("output_format", "%Y-%m-%d %H:%M:%S")

        valid_ops = {"parse", "diff", "add", "subtract", "format"}
        if operation not in valid_ops:
            return {
                "result": None,
                "iso": None,
                "error": f"Invalid operation '{operation}'. Valid: {', '.join(sorted(valid_ops))}",
            }

        try:
            dt = _parse_date(date_str, fmt)
        except ValueError as exc:
            return {"result": None, "iso": None, "error": str(exc)}

        # ---- parse / format ----
        if operation in ("parse", "format"):
            result_str = dt.strftime(output_format)
            out = {
                "result": result_str,
                "iso": dt.isoformat(),
                "timestamp": dt.timestamp() if dt.tzinfo or dt.year >= 1970 else None,
            }
            # Safely compute timestamp
            try:
                out["timestamp"] = dt.timestamp()
            except (OSError, OverflowError, ValueError):
                out["timestamp"] = None
            return out

        # ---- diff ----
        if operation == "diff":
            date2_str = input_data.get("date2")
            if date2_str is None:
                return {"result": None, "iso": None, "error": "'date2' is required for diff operation"}

            fmt2 = input_data.get("format2", fmt)
            try:
                dt2 = _parse_date(str(date2_str), fmt2)
            except ValueError as exc:
                return {"result": None, "iso": None, "error": f"Failed to parse date2: {exc}"}

            delta = dt2 - dt
            total_seconds = delta.total_seconds()
            abs_seconds = abs(total_seconds)

            diff_days = int(abs_seconds // 86400)
            remaining = abs_seconds % 86400
            diff_hours = int(remaining // 3600)
            remaining %= 3600
            diff_minutes = int(remaining // 60)
            diff_secs = int(remaining % 60)

            return {
                "result": f"{delta.days} days, {diff_hours}h {diff_minutes}m {diff_secs}s",
                "iso": dt.isoformat(),
                "diff": {
                    "days": diff_days,
                    "hours": diff_hours,
                    "minutes": diff_minutes,
                    "seconds": diff_secs,
                    "total_seconds": int(total_seconds),
                },
            }

        # ---- add / subtract ----
        if operation in ("add", "subtract"):
            days = int(input_data.get("days", 0))
            hours = int(input_data.get("hours", 0))
            minutes = int(input_data.get("minutes", 0))

            td = datetime.timedelta(days=days, hours=hours, minutes=minutes)
            if operation == "subtract":
                td = -td

            new_dt = dt + td
            result_str = new_dt.strftime(output_format)

            out = {
                "result": result_str,
                "iso": new_dt.isoformat(),
            }
            try:
                out["timestamp"] = new_dt.timestamp()
            except (OSError, OverflowError, ValueError):
                out["timestamp"] = None
            return out

        return {"result": None, "iso": None, "error": f"Unhandled operation '{operation}'"}

    except Exception as exc:
        return {"result": None, "iso": None, "error": f"Unexpected error: {exc}"}
