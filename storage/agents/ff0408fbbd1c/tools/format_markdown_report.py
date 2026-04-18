import textwrap


def _render_table(rows: list) -> str:
    """Render a list of dicts as an aligned markdown table."""
    if not rows or not isinstance(rows, list):
        return ""

    # Collect all column names preserving insertion order
    columns = []
    seen = set()
    for row in rows:
        if isinstance(row, dict):
            for key in row:
                if key not in seen:
                    columns.append(key)
                    seen.add(key)

    if not columns:
        return ""

    # Compute column widths (minimum 3 for the separator dashes)
    widths = {}
    for col in columns:
        widths[col] = max(len(str(col)), 3)
        for row in rows:
            if isinstance(row, dict):
                val = str(row.get(col, ""))
                widths[col] = max(widths[col], len(val))

    # Header
    header = "| " + " | ".join(str(col).ljust(widths[col]) for col in columns) + " |"
    separator = "| " + " | ".join("-" * widths[col] for col in columns) + " |"

    # Rows
    lines = [header, separator]
    for row in rows:
        if isinstance(row, dict):
            cells = []
            for col in columns:
                cells.append(str(row.get(col, "")).ljust(widths[col]))
            lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _render_list(items: list) -> str:
    """Render a list of strings as markdown bullet points."""
    lines = []
    for item in items:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _render_key_value(data: dict) -> str:
    """Render a dict as bold-key / value lines."""
    lines = []
    for key, value in data.items():
        lines.append(f"**{key}:** {value}")
    return "\n\n".join(lines)


def format_markdown_report(input_data: dict) -> dict:
    """Generate structured markdown from data (tables, headers, lists, sections).

    Parameters:
        title (str): Report title.
        sections (list[dict]): Report sections, each with heading, type, content.
        summary (str, optional): Summary text at top.

    Returns:
        dict with keys: markdown, char_count, section_count, error (optional).
    """
    try:
        if not isinstance(input_data, dict):
            return {"markdown": "", "char_count": 0, "section_count": 0, "error": "input_data must be a dict"}

        title = input_data.get("title")
        sections = input_data.get("sections")
        summary = input_data.get("summary")

        if not title:
            return {"markdown": "", "char_count": 0, "section_count": 0, "error": "'title' is required"}

        if not sections or not isinstance(sections, list):
            return {"markdown": "", "char_count": 0, "section_count": 0, "error": "'sections' must be a non-empty list"}

        parts = []

        # Title
        parts.append(f"# {title}")
        parts.append("")

        # Summary
        if summary:
            parts.append(str(summary))
            parts.append("")

        section_count = 0

        for section in sections:
            if not isinstance(section, dict):
                continue

            heading = section.get("heading", "Untitled Section")
            section_type = section.get("type", "text")
            content = section.get("content")

            parts.append(f"## {heading}")
            parts.append("")

            if content is None:
                parts.append("*No content provided.*")
                parts.append("")
                section_count += 1
                continue

            if section_type == "text":
                parts.append(str(content))

            elif section_type == "table":
                if isinstance(content, list):
                    table_md = _render_table(content)
                    if table_md:
                        parts.append(table_md)
                    else:
                        parts.append("*Empty table.*")
                else:
                    parts.append("*Table content must be a list of dicts.*")

            elif section_type == "list":
                if isinstance(content, list):
                    parts.append(_render_list(content))
                else:
                    parts.append(f"- {content}")

            elif section_type == "key_value":
                if isinstance(content, dict):
                    parts.append(_render_key_value(content))
                else:
                    parts.append("*Key-value content must be a dict.*")

            else:
                # Fallback: treat as text
                parts.append(str(content))

            parts.append("")
            section_count += 1

        markdown = "\n".join(parts).rstrip() + "\n"

        return {
            "markdown": markdown,
            "char_count": len(markdown),
            "section_count": section_count,
        }

    except Exception as exc:
        return {"markdown": "", "char_count": 0, "section_count": 0, "error": f"Unexpected error: {exc}"}
