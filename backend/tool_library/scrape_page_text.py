"""Fetch a URL and extract clean readable text from the HTML."""

import re

import requests
from bs4 import BeautifulSoup
from typing import Any, Dict


def scrape_page_text(input_data: dict) -> dict:
    """Fetch a URL and extract clean readable text from the HTML.

    Parameters:
        url (str): URL to scrape
        selector (str, optional): CSS selector to target specific elements
        max_length (int, optional): Max characters to return, default 10000

    Returns:
        dict with keys: text, title, char_count, truncated, url, and optionally error.
    """
    url = input_data.get("url")
    if not url or not isinstance(url, str):
        return {"error": "Missing or invalid required parameter: url"}

    selector = input_data.get("selector")
    max_length = input_data.get("max_length", 10000)

    if not isinstance(max_length, int) or max_length <= 0:
        return {"error": "Parameter 'max_length' must be a positive integer"}

    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out", "url": url}
    except requests.exceptions.ConnectionError as exc:
        return {"error": f"Connection error: {str(exc)}", "url": url}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"HTTP error {response.status_code}: {str(exc)}", "url": url}
    except requests.exceptions.RequestException as exc:
        return {"error": f"Request failed: {str(exc)}", "url": url}

    try:
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        return {"error": f"Failed to parse HTML: {str(exc)}", "url": url}

    # Extract title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Remove non-content tags
    for tag_name in ("script", "style", "nav", "footer", "header", "noscript", "svg"):
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Scope to selector if provided
    if selector:
        elements = soup.select(selector)
        if not elements:
            return {
                "text": "",
                "title": title,
                "char_count": 0,
                "truncated": False,
                "url": url,
                "error": f"No elements matched selector: {selector}",
            }
        text_parts = [el.get_text(separator="\n", strip=True) for el in elements]
        raw_text = "\n\n".join(text_parts)
    else:
        body = soup.find("body")
        target = body if body else soup
        raw_text = target.get_text(separator="\n", strip=True)

    # Clean up whitespace: collapse multiple blank lines and spaces
    text = re.sub(r"[ \t]+", " ", raw_text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    truncated = len(text) > max_length
    if truncated:
        text = text[:max_length]

    return {
        "text": text,
        "title": title,
        "char_count": len(text),
        "truncated": truncated,
        "url": url,
    }
