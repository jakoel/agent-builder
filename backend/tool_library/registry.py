"""Tool library registry — discovers and serves pre-built tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

TOOL_DIR = Path(__file__).parent

# Each entry: (filename, function_name, display_name, description, category, parameters schema)
TOOL_CATALOG: list[dict[str, Any]] = [
    # --- Web & Data Fetching ---
    {
        "name": "fetch_url",
        "display_name": "Fetch URL",
        "description": "Fetch a URL and return status code + body. Auto-detects JSON responses.",
        "category": "Web & Data Fetching",
        "filename": "fetch_url.py",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
                "method": {"type": "string", "description": "HTTP method", "default": "GET"},
                "headers": {"type": "object", "description": "Custom headers"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 15},
            },
            "required": ["url"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "integer", "description": "HTTP status code"},
                "url": {"type": "string"},
                "body": {"type": "string", "description": "Raw response body"},
                "json": {"type": "object", "description": "Parsed JSON if response was JSON"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "fetch_json_api",
        "display_name": "Fetch JSON API",
        "description": "Call a REST API endpoint and return parsed JSON response.",
        "category": "Web & Data Fetching",
        "filename": "fetch_json_api.py",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "API endpoint URL"},
                "method": {"type": "string", "default": "GET"},
                "headers": {"type": "object"},
                "params": {"type": "object", "description": "Query parameters"},
                "body": {"type": "object", "description": "JSON request body"},
                "timeout": {"type": "integer", "default": 15},
            },
            "required": ["url"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "integer"},
                "data": {"description": "Parsed JSON response body"},
                "headers": {"type": "object"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "scrape_page_text",
        "display_name": "Scrape Page Text",
        "description": "Fetch a URL and extract clean readable text from the HTML.",
        "category": "Web & Data Fetching",
        "filename": "scrape_page_text.py",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "selector": {"type": "string", "description": "CSS selector to target"},
                "max_length": {"type": "integer", "default": 10000},
            },
            "required": ["url"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Extracted plain text"},
                "url": {"type": "string"},
                "char_count": {"type": "integer"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "scrape_links",
        "display_name": "Scrape Links",
        "description": "Fetch a URL and extract all hyperlinks with their labels.",
        "category": "Web & Data Fetching",
        "filename": "scrape_links.py",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "filter_pattern": {"type": "string", "description": "Regex to filter URLs"},
                "absolute_only": {"type": "boolean", "default": True},
                "selector": {"type": "string", "description": "CSS selector to scope"},
            },
            "required": ["url"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "links": {"type": "array", "description": "List of {url, text} dicts"},
                "count": {"type": "integer"},
                "url": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    # --- Text Extraction & Analysis ---
    {
        "name": "extract_with_regex",
        "display_name": "Extract with Regex",
        "description": "Apply a regex pattern to text and return all matches.",
        "category": "Text Extraction & Analysis",
        "filename": "extract_with_regex.py",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "pattern": {"type": "string", "description": "Regex pattern"},
                "flags": {"type": "string", "description": "Flags: i, m, s"},
                "group": {"type": "integer", "default": 0},
                "max_matches": {"type": "integer", "default": 100},
            },
            "required": ["text", "pattern"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "matches": {"type": "array", "description": "List of matched strings"},
                "count": {"type": "integer"},
                "pattern": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "extract_emails_urls",
        "display_name": "Extract Emails & URLs",
        "description": "Pull all email addresses and URLs from text.",
        "category": "Text Extraction & Analysis",
        "filename": "extract_emails_urls.py",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "deduplicate": {"type": "boolean", "default": True},
            },
            "required": ["text"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "emails": {"type": "array", "description": "Extracted email addresses"},
                "urls": {"type": "array", "description": "Extracted URLs"},
                "email_count": {"type": "integer"},
                "url_count": {"type": "integer"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "text_statistics",
        "display_name": "Text Statistics",
        "description": "Compute word count, sentence count, character count, top keywords.",
        "category": "Text Extraction & Analysis",
        "filename": "text_statistics.py",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "top_n": {"type": "integer", "default": 10},
                "stop_words": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["text"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "word_count": {"type": "integer"},
                "sentence_count": {"type": "integer"},
                "char_count": {"type": "integer"},
                "avg_word_length": {"type": "number"},
                "top_keywords": {"type": "array", "description": "List of {word, count} dicts"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "keyword_search",
        "display_name": "Keyword Search",
        "description": "Search text for keywords and return surrounding context snippets.",
        "category": "Text Extraction & Analysis",
        "filename": "keyword_search.py",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "context_chars": {"type": "integer", "default": 100},
                "case_sensitive": {"type": "boolean", "default": False},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["text", "keywords"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "results": {"type": "array", "description": "List of {keyword, snippet, position} dicts"},
                "total_matches": {"type": "integer"},
                "keywords_found": {"type": "array"},
                "keywords_missing": {"type": "array"},
                "error": {"type": "string"},
            },
        },
    },
    # --- Data Transformation ---
    {
        "name": "csv_parse",
        "display_name": "CSV Parse",
        "description": "Parse CSV to JSON or convert JSON to CSV.",
        "category": "Data Transformation",
        "filename": "csv_parse.py",
        "parameters": {
            "type": "object",
            "properties": {
                "csv_text": {"type": "string"},
                "data": {"type": "array"},
                "delimiter": {"type": "string", "default": ","},
                "has_header": {"type": "boolean", "default": True},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "array", "description": "Parsed rows as list of dicts (CSV→JSON mode)"},
                "csv_text": {"type": "string", "description": "CSV string (JSON→CSV mode)"},
                "row_count": {"type": "integer"},
                "columns": {"type": "array", "description": "Column names"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "json_transform",
        "display_name": "JSON Transform",
        "description": "Filter, select fields, sort, or group a JSON array.",
        "category": "Data Transformation",
        "filename": "json_transform.py",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
                "select_fields": {"type": "array", "items": {"type": "string"}},
                "filter_field": {"type": "string"},
                "filter_value": {},
                "filter_op": {"type": "string", "default": "eq"},
                "sort_by": {"type": "string"},
                "sort_desc": {"type": "boolean", "default": False},
                "group_by": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["data"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "data": {"description": "Filtered/transformed records (array) or grouped dict"},
                "count": {"type": "integer", "description": "Total number of records"},
                "grouped": {"type": "boolean"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "merge_datasets",
        "display_name": "Merge Datasets",
        "description": "Join two lists of dicts on a shared key.",
        "category": "Data Transformation",
        "filename": "merge_datasets.py",
        "parameters": {
            "type": "object",
            "properties": {
                "left": {"type": "array"},
                "right": {"type": "array"},
                "left_key": {"type": "string"},
                "right_key": {"type": "string"},
                "how": {"type": "string", "default": "inner"},
            },
            "required": ["left", "right", "left_key"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "array", "description": "Merged records"},
                "count": {"type": "integer"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "deduplicate",
        "display_name": "Deduplicate",
        "description": "Remove duplicate entries from a list by specified fields.",
        "category": "Data Transformation",
        "filename": "deduplicate.py",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
                "fields": {"type": "array", "items": {"type": "string"}},
                "keep": {"type": "string", "default": "first"},
            },
            "required": ["data"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "array", "description": "Deduplicated records"},
                "original_count": {"type": "integer"},
                "deduplicated_count": {"type": "integer"},
                "duplicates_removed": {"type": "integer"},
                "error": {"type": "string"},
            },
        },
    },
    # --- Math & Analytics ---
    {
        "name": "calculate_stats",
        "display_name": "Calculate Stats",
        "description": "Compute min, max, mean, median, std dev, percentiles on numeric data.",
        "category": "Math & Analytics",
        "filename": "calculate_stats.py",
        "parameters": {
            "type": "object",
            "properties": {
                "values": {"type": "array", "items": {"type": "number"}},
                "data": {"type": "array"},
                "field": {"type": "string"},
                "percentiles": {"type": "array", "items": {"type": "number"}},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "min": {"type": "number"},
                "max": {"type": "number"},
                "mean": {"type": "number"},
                "median": {"type": "number"},
                "std_dev": {"type": "number"},
                "variance": {"type": "number"},
                "sum": {"type": "number"},
                "count": {"type": "integer"},
                "percentiles": {"type": "object", "description": "Requested percentile values keyed by percentile"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "compare_values",
        "display_name": "Compare Values",
        "description": "Compare two datasets or values and return differences.",
        "category": "Math & Analytics",
        "filename": "compare_values.py",
        "parameters": {
            "type": "object",
            "properties": {
                "old": {},
                "new": {},
                "key_field": {"type": "string"},
            },
            "required": ["old", "new"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "dict | list | scalar"},
                "added": {"type": "array", "description": "Keys/records present in new but not old"},
                "removed": {"type": "array", "description": "Keys/records present in old but not new"},
                "modified": {"type": "array", "description": "Keys/records changed between old and new"},
                "unchanged_count": {"type": "integer"},
                "summary": {"type": "string", "description": "Human-readable change summary"},
                "error": {"type": "string"},
            },
        },
    },
    # --- Encoding, Hashing & Validation ---
    {
        "name": "hash_data",
        "display_name": "Hash Data",
        "description": "Compute SHA256/MD5/SHA1 hash of input string or data.",
        "category": "Encoding & Hashing",
        "filename": "hash_data.py",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "data": {},
                "algorithm": {"type": "string", "default": "sha256"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "hash": {"type": "string", "description": "Hex digest"},
                "algorithm": {"type": "string"},
                "input_length": {"type": "integer"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "encode_decode",
        "display_name": "Encode / Decode",
        "description": "Base64 and URL encode/decode operations.",
        "category": "Encoding & Hashing",
        "filename": "encode_decode.py",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "operation": {"type": "string", "description": "base64_encode, base64_decode, url_encode, url_decode"},
            },
            "required": ["text", "operation"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "Encoded or decoded string"},
                "operation": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "validate_schema",
        "display_name": "Validate Schema",
        "description": "Validate a dict against expected types, required fields, and patterns.",
        "category": "Encoding & Hashing",
        "filename": "validate_schema.py",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {"type": "object"},
                "schema": {"type": "object"},
            },
            "required": ["data", "schema"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "valid": {"type": "boolean"},
                "errors": {"type": "array", "description": "List of validation error messages"},
                "error": {"type": "string"},
            },
        },
    },
    # --- Date & Time ---
    {
        "name": "date_calc",
        "display_name": "Date Calculator",
        "description": "Parse dates, compute differences, add/subtract durations, format output.",
        "category": "Date & Time",
        "filename": "date_calc.py",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "format": {"type": "string"},
                "operation": {"type": "string", "default": "parse"},
                "date2": {"type": "string"},
                "days": {"type": "integer"},
                "hours": {"type": "integer"},
                "minutes": {"type": "integer"},
                "output_format": {"type": "string", "default": "%Y-%m-%d %H:%M:%S"},
            },
            "required": ["date"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "Formatted date/time result"},
                "iso": {"type": "string", "description": "ISO 8601 representation"},
                "timestamp": {"type": "number", "description": "Unix timestamp"},
                "diff": {"type": "object", "description": "For diff operation: {days, hours, minutes, seconds, total_seconds}"},
                "error": {"type": "string"},
            },
        },
    },
    # --- Formatting & Output ---
    {
        "name": "format_markdown_report",
        "display_name": "Format Markdown Report",
        "description": "Generate structured markdown from data (tables, headers, lists).",
        "category": "Formatting & Output",
        "filename": "format_markdown_report.py",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "sections": {"type": "array"},
                "summary": {"type": "string"},
            },
            "required": ["title", "sections"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "markdown": {"type": "string", "description": "Rendered markdown document"},
                "char_count": {"type": "integer"},
                "section_count": {"type": "integer"},
                "error": {"type": "string"},
            },
        },
    },
    {
        "name": "render_template",
        "display_name": "Render Template",
        "description": "String template rendering with variable substitution and conditionals.",
        "category": "Formatting & Output",
        "filename": "render_template.py",
        "parameters": {
            "type": "object",
            "properties": {
                "template": {"type": "string"},
                "variables": {"type": "object"},
            },
            "required": ["template", "variables"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "Rendered template string"},
                "error": {"type": "string"},
            },
        },
    },
    # --- PDF ---
    {
        "name": "extract_pdf_text",
        "display_name": "Extract PDF Text",
        "description": "Extract text content from a PDF file or URL.",
        "category": "PDF Processing",
        "filename": "extract_pdf_text.py",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to download PDF from"},
                "file_path": {"type": "string", "description": "Local path to PDF"},
                "pages": {"type": "array", "items": {"type": "integer"}},
                "max_pages": {"type": "integer", "default": 50},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Extracted text content"},
                "pages_extracted": {"type": "integer"},
                "total_pages": {"type": "integer"},
                "error": {"type": "string"},
            },
        },
    },
]


def get_catalog() -> list[dict[str, Any]]:
    """Return the tool catalog metadata (without code)."""
    return TOOL_CATALOG


def get_tool_code(name: str) -> str | None:
    """Read the source code for a tool by name."""
    for entry in TOOL_CATALOG:
        if entry["name"] == name:
            path = TOOL_DIR / entry["filename"]
            if path.exists():
                return path.read_text()
            return None
    return None


def get_tool_detail(name: str) -> dict[str, Any] | None:
    """Return full tool detail including code."""
    for entry in TOOL_CATALOG:
        if entry["name"] == name:
            result = dict(entry)
            path = TOOL_DIR / entry["filename"]
            if path.exists():
                result["code"] = path.read_text()
            return result
    return None
