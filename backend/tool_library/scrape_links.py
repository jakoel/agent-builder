"""Fetch a URL and extract all hyperlinks with their labels."""

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from typing import Any, Dict, List


def scrape_links(input_data: dict) -> dict:
    """Fetch a URL and extract all hyperlinks with their labels.

    Parameters:
        url (str): URL to scrape
        filter_pattern (str, optional): Regex to filter link URLs
        absolute_only (bool, optional): Only return absolute URLs, default true
        selector (str, optional): CSS selector to scope link extraction

    Returns:
        dict with keys: links (list of {url, text, title?}), count, source_url,
        and optionally error.
    """
    url = input_data.get("url")
    if not url or not isinstance(url, str):
        return {"error": "Missing or invalid required parameter: url"}

    filter_pattern = input_data.get("filter_pattern")
    absolute_only = input_data.get("absolute_only", True)
    selector = input_data.get("selector")

    # Validate filter_pattern if provided
    compiled_filter = None
    if filter_pattern:
        try:
            compiled_filter = re.compile(filter_pattern)
        except re.error as exc:
            return {"error": f"Invalid filter_pattern regex: {str(exc)}"}

    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out", "source_url": url, "links": [], "count": 0}
    except requests.exceptions.ConnectionError as exc:
        return {"error": f"Connection error: {str(exc)}", "source_url": url, "links": [], "count": 0}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"HTTP error: {str(exc)}", "source_url": url, "links": [], "count": 0}
    except requests.exceptions.RequestException as exc:
        return {"error": f"Request failed: {str(exc)}", "source_url": url, "links": [], "count": 0}

    try:
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        return {"error": f"Failed to parse HTML: {str(exc)}", "source_url": url, "links": [], "count": 0}

    # Scope to selector if provided
    if selector:
        containers = soup.select(selector)
        anchors: List[Any] = []
        for container in containers:
            anchors.extend(container.find_all("a", href=True))
    else:
        anchors = soup.find_all("a", href=True)

    links: List[Dict[str, str]] = []
    seen_urls = set()

    for anchor in anchors:
        href = anchor["href"].strip()

        # Skip fragment-only and javascript links
        if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
            continue

        # Resolve relative URLs
        resolved_url = urljoin(url, href)

        # Filter: absolute only
        if absolute_only:
            parsed = urlparse(resolved_url)
            if not parsed.scheme or not parsed.netloc:
                continue

        # Deduplicate
        if resolved_url in seen_urls:
            continue
        seen_urls.add(resolved_url)

        # Apply filter pattern
        if compiled_filter and not compiled_filter.search(resolved_url):
            continue

        link_text = anchor.get_text(strip=True)
        link_entry: Dict[str, str] = {
            "url": resolved_url,
            "text": link_text,
        }

        title_attr = anchor.get("title")
        if title_attr:
            link_entry["title"] = title_attr.strip()

        links.append(link_entry)

    return {
        "links": links,
        "count": len(links),
        "source_url": url,
    }
