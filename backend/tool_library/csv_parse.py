"""CSV parse tool: convert between CSV strings and lists of dicts."""

import csv
import io
from typing import Any, Dict, List


def csv_parse(input_data: dict) -> dict:
    """Parse CSV string to list of dicts, or convert list of dicts to CSV string.

    Parameters:
        csv_text (str, optional): CSV text to parse (CSV -> JSON).
        data (list[dict], optional): Data to convert (JSON -> CSV).
        delimiter (str, optional): CSV delimiter, default ",".
        has_header (bool, optional): Whether CSV has header row, default true.

    Returns:
        dict with data or csv_text, row_count, columns, and optional error.
    """
    try:
        csv_text = input_data.get("csv_text")
        data = input_data.get("data")
        delimiter = str(input_data.get("delimiter", ","))
        has_header = bool(input_data.get("has_header", True))

        if csv_text is not None and data is not None:
            return {"error": "Provide either 'csv_text' or 'data', not both."}

        if csv_text is None and data is None:
            return {"error": "Either 'csv_text' or 'data' must be provided."}

        # --- CSV text -> list of dicts -----------------------------------------
        if csv_text is not None:
            if not isinstance(csv_text, str):
                return {"error": "Parameter 'csv_text' must be a string."}

            reader_file = io.StringIO(csv_text)
            reader = csv.reader(reader_file, delimiter=delimiter)

            rows: List[List[str]] = []
            for row in reader:
                rows.append(row)

            if not rows:
                return {"data": [], "row_count": 0, "columns": []}

            if has_header:
                columns = rows[0]
                data_rows = rows[1:]
                parsed: List[Dict[str, Any]] = []
                for row in data_rows:
                    record: Dict[str, Any] = {}
                    for i, col in enumerate(columns):
                        record[col] = row[i] if i < len(row) else ""
                    parsed.append(record)
                return {
                    "data": parsed,
                    "row_count": len(parsed),
                    "columns": columns,
                }
            else:
                # No header: use numeric column names
                max_cols = max(len(r) for r in rows) if rows else 0
                columns = [f"col_{i}" for i in range(max_cols)]
                parsed = []
                for row in rows:
                    record = {}
                    for i, col in enumerate(columns):
                        record[col] = row[i] if i < len(row) else ""
                    parsed.append(record)
                return {
                    "data": parsed,
                    "row_count": len(parsed),
                    "columns": columns,
                }

        # --- List of dicts -> CSV string ---------------------------------------
        if data is not None:
            if not isinstance(data, list):
                return {"error": "Parameter 'data' must be a list of dicts."}

            if len(data) == 0:
                return {"csv_text": "", "row_count": 0, "columns": []}

            if not all(isinstance(item, dict) for item in data):
                return {"error": "All items in 'data' must be dicts."}

            # Collect all columns in insertion order across all records
            columns_seen: Dict[str, bool] = {}
            for item in data:
                for key in item:
                    columns_seen[key] = True
            columns = list(columns_seen.keys())

            output = io.StringIO()
            writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
            writer.writerow(columns)

            for item in data:
                writer.writerow([item.get(col, "") for col in columns])

            return {
                "csv_text": output.getvalue(),
                "row_count": len(data),
                "columns": columns,
            }

        # Unreachable but defensive
        return {"error": "No valid operation determined."}

    except Exception as exc:
        return {"error": f"Unexpected error: {str(exc)}"}
