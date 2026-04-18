"""Keyword search tool: find keywords in text with surrounding context snippets."""

import re
from typing import Any, Dict, List


def keyword_search(input_data: dict) -> dict:
    """Search text for keywords and return surrounding context snippets.

    Parameters:
        text (str): Text to search.
        keywords (list[str]): Keywords to find.
        context_chars (int, optional): Characters of context around each match, default 100.
        case_sensitive (bool, optional): Default false.
        max_results (int, optional): Max results per keyword, default 10.

    Returns:
        dict with results, total_matches, keywords_found, keywords_missing, and optional error.
    """
    try:
        # --- Validate inputs ---------------------------------------------------
        text = input_data.get("text")
        if not isinstance(text, str):
            return {"results": [], "total_matches": 0, "keywords_found": [],
                    "keywords_missing": [], "error": "Parameter 'text' is required and must be a string."}

        keywords = input_data.get("keywords")
        if not isinstance(keywords, list) or len(keywords) == 0:
            return {"results": [], "total_matches": 0, "keywords_found": [],
                    "keywords_missing": [], "error": "Parameter 'keywords' is required and must be a non-empty list of strings."}

        context_chars = int(input_data.get("context_chars", 100))
        if context_chars < 0:
            context_chars = 0

        case_sensitive = bool(input_data.get("case_sensitive", False))
        max_results = int(input_data.get("max_results", 10))
        if max_results < 1:
            max_results = 1

        # --- Search ------------------------------------------------------------
        results: List[Dict[str, Any]] = []
        keywords_found: List[str] = []
        keywords_missing: List[str] = []

        for keyword in keywords:
            if not isinstance(keyword, str) or keyword == "":
                continue

            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.escape(keyword)
            matches = list(re.finditer(pattern, text, flags))

            if not matches:
                keywords_missing.append(keyword)
                continue

            keywords_found.append(keyword)

            for match in matches[:max_results]:
                start = match.start()
                end = match.end()

                snippet_start = max(0, start - context_chars)
                snippet_end = min(len(text), end + context_chars)

                snippet = text[snippet_start:snippet_end]

                # Add ellipsis indicators when the snippet is truncated
                if snippet_start > 0:
                    snippet = "..." + snippet
                if snippet_end < len(text):
                    snippet = snippet + "..."

                results.append({
                    "keyword": keyword,
                    "snippet": snippet,
                    "position": start,
                })

        return {
            "results": results,
            "total_matches": len(results),
            "keywords_found": keywords_found,
            "keywords_missing": keywords_missing,
        }

    except Exception as exc:
        return {
            "results": [],
            "total_matches": 0,
            "keywords_found": [],
            "keywords_missing": [],
            "error": f"Unexpected error: {str(exc)}",
        }
