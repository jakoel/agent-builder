import base64
import urllib.parse


def encode_decode(input_data: dict) -> dict:
    """Base64 and URL encode/decode operations.

    Parameters:
        text (str): Text to process.
        operation (str): "base64_encode", "base64_decode", "url_encode", "url_decode".

    Returns:
        dict with keys: result, operation, error (optional).
    """
    try:
        if not isinstance(input_data, dict):
            return {"result": None, "operation": None, "error": "input_data must be a dict"}

        text = input_data.get("text")
        operation = input_data.get("operation")

        valid_operations = {"base64_encode", "base64_decode", "url_encode", "url_decode"}

        if operation is None:
            return {"result": None, "operation": None, "error": "'operation' is required"}

        if operation not in valid_operations:
            return {
                "result": None,
                "operation": operation,
                "error": f"Invalid operation '{operation}'. Valid: {', '.join(sorted(valid_operations))}",
            }

        if text is None:
            return {"result": None, "operation": operation, "error": "'text' is required"}

        text = str(text)

        if operation == "base64_encode":
            result = base64.b64encode(text.encode("utf-8")).decode("ascii")

        elif operation == "base64_decode":
            # Be lenient with padding
            padded = text + "=" * (-len(text) % 4)
            try:
                result = base64.b64decode(padded).decode("utf-8")
            except UnicodeDecodeError:
                # Return hex representation for binary data
                raw_bytes = base64.b64decode(padded)
                result = raw_bytes.hex()
            except Exception as exc:
                return {"result": None, "operation": operation, "error": f"Base64 decode failed: {exc}"}

        elif operation == "url_encode":
            result = urllib.parse.quote(text, safe="")

        elif operation == "url_decode":
            result = urllib.parse.unquote(text)

        return {"result": result, "operation": operation}

    except Exception as exc:
        return {
            "result": None,
            "operation": input_data.get("operation") if isinstance(input_data, dict) else None,
            "error": f"Unexpected error: {exc}",
        }
