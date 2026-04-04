"""Extract all email addresses and URLs from text."""

import re
from typing import List


def extract_emails_urls(input_data: dict) -> dict:
    """Extract all email addresses and URLs from text.

    Parameters:
        text (str): Text to search
        deduplicate (bool, optional): Remove duplicates, default true

    Returns:
        dict with keys: emails, urls, email_count, url_count, and optionally error.
    """
    text = input_data.get("text")
    if not isinstance(text, str):
        return {"error": "Missing or invalid required parameter: text"}

    deduplicate = input_data.get("deduplicate", True)

    # Robust email pattern
    email_pattern = re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    )

    # Robust URL pattern covering http, https, ftp, and common formats
    url_pattern = re.compile(
        r"https?://[^\s<>\"'\)\]\}]+|"
        r"ftp://[^\s<>\"'\)\]\}]+|"
        r"www\.[a-zA-Z0-9\-]+\.[^\s<>\"'\)\]\}]+",
    )

    try:
        raw_emails: List[str] = email_pattern.findall(text)
        raw_urls: List[str] = url_pattern.findall(text)
    except Exception as exc:
        return {"error": f"Error during extraction: {str(exc)}"}

    # Clean trailing punctuation from URLs (common in natural text)
    cleaned_urls: List[str] = []
    for u in raw_urls:
        # Strip common trailing punctuation that gets captured
        u = u.rstrip(".,;:!?")
        # Balance parentheses: if URL has unmatched trailing ), strip it
        while u.endswith(")") and u.count(")") > u.count("("):
            u = u[:-1]
        cleaned_urls.append(u)

    if deduplicate:
        emails = _deduplicate_preserve_order(raw_emails)
        urls = _deduplicate_preserve_order(cleaned_urls)
    else:
        emails = raw_emails
        urls = cleaned_urls

    return {
        "emails": emails,
        "urls": urls,
        "email_count": len(emails),
        "url_count": len(urls),
    }


def _deduplicate_preserve_order(items: List[str]) -> List[str]:
    """Remove duplicates while preserving first-occurrence order."""
    seen = set()
    result = []
    for item in items:
        normalized = item.lower()
        if normalized not in seen:
            seen.add(normalized)
            result.append(item)
    return result
