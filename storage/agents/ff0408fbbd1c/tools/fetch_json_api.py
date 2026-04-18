"""Call a REST API endpoint and return parsed JSON response."""

import requests
from typing import Any, Dict


def fetch_json_api(input_data: dict) -> dict:
    """Call a REST API endpoint and return parsed JSON response.

    Parameters:
        url (str): API endpoint URL
        method (str, optional): GET/POST/PUT/DELETE, default "GET"
        headers (dict, optional): Request headers
        params (dict, optional): Query parameters
        body (dict, optional): JSON request body (for POST/PUT)
        timeout (int, optional): Timeout in seconds, default 15

    Returns:
        dict with keys: status_code, data, headers (subset), and optionally error.
    """
    url = input_data.get("url")
    if not url or not isinstance(url, str):
        return {"error": "Missing or invalid required parameter: url"}

    method = input_data.get("method", "GET").upper()
    custom_headers = input_data.get("headers") or {}
    params = input_data.get("params") or {}
    body = input_data.get("body")
    timeout = input_data.get("timeout", 15)

    if not isinstance(custom_headers, dict):
        return {"error": "Parameter 'headers' must be a dict"}
    if not isinstance(params, dict):
        return {"error": "Parameter 'params' must be a dict"}
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        return {"error": "Parameter 'timeout' must be a positive number"}
    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        return {"error": f"Unsupported HTTP method: {method}"}

    headers: Dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    headers.update(custom_headers)

    request_kwargs: Dict[str, Any] = {
        "method": method,
        "url": url,
        "headers": headers,
        "params": params if params else None,
        "timeout": timeout,
    }

    if body is not None and method in ("POST", "PUT", "PATCH"):
        request_kwargs["json"] = body

    try:
        response = requests.request(**request_kwargs)
    except requests.exceptions.Timeout:
        return {"error": f"Request timed out after {timeout} seconds", "status_code": None, "data": None, "headers": {}}
    except requests.exceptions.ConnectionError as exc:
        return {"error": f"Connection error: {str(exc)}", "status_code": None, "data": None, "headers": {}}
    except requests.exceptions.RequestException as exc:
        return {"error": f"Request failed: {str(exc)}", "status_code": None, "data": None, "headers": {}}

    # Extract a useful subset of response headers
    header_keys = ("Content-Type", "Content-Length", "Date", "Server",
                   "X-Request-Id", "X-RateLimit-Limit", "X-RateLimit-Remaining",
                   "Retry-After", "ETag", "Cache-Control", "Location")
    response_headers = {
        k: response.headers[k]
        for k in header_keys
        if k in response.headers
    }

    result: Dict[str, Any] = {
        "status_code": response.status_code,
        "headers": response_headers,
    }

    try:
        result["data"] = response.json()
    except ValueError:
        result["data"] = None
        result["error"] = (
            "Response body is not valid JSON. "
            f"Content-Type: {response.headers.get('Content-Type', 'unknown')}"
        )

    return result
