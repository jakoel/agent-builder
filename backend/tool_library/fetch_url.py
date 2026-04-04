"""Fetch a URL and return status code + body with automatic JSON detection."""

import requests
from typing import Any, Dict


def fetch_url(input_data: dict) -> dict:
    """Fetch a URL and return status code + body. Auto-detects JSON responses.

    Parameters:
        url (str): The URL to fetch
        method (str, optional): HTTP method, default "GET"
        headers (dict, optional): Custom headers
        timeout (int, optional): Timeout in seconds, default 15

    Returns:
        dict with keys: status_code, content_type, data (if JSON), text (if not JSON),
        url, and optionally error.
    """
    url = input_data.get("url")
    if not url or not isinstance(url, str):
        return {"error": "Missing or invalid required parameter: url"}

    method = input_data.get("method", "GET").upper()
    headers = input_data.get("headers") or {}
    timeout = input_data.get("timeout", 15)

    if not isinstance(headers, dict):
        return {"error": "Parameter 'headers' must be a dict"}

    if not isinstance(timeout, (int, float)) or timeout <= 0:
        return {"error": "Parameter 'timeout' must be a positive number"}

    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
        return {"error": f"Unsupported HTTP method: {method}"}

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return {"error": f"Request timed out after {timeout} seconds", "url": url}
    except requests.exceptions.ConnectionError as exc:
        return {"error": f"Connection error: {str(exc)}", "url": url}
    except requests.exceptions.RequestException as exc:
        return {"error": f"Request failed: {str(exc)}", "url": url}

    content_type = response.headers.get("Content-Type", "")
    result: Dict[str, Any] = {
        "status_code": response.status_code,
        "content_type": content_type,
        "url": url,
    }

    if "application/json" in content_type:
        try:
            result["data"] = response.json()
        except ValueError:
            result["text"] = response.text
            result["error"] = "Content-Type indicated JSON but body could not be parsed"
    else:
        result["text"] = response.text

    return result
