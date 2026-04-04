import hashlib
import json


def hash_data(input_data: dict) -> dict:
    """Compute cryptographic hash of input string or data.

    Parameters:
        text (str, optional): Text to hash.
        data (any, optional): Data to serialize to JSON then hash.
        algorithm (str, optional): "sha256", "md5", "sha1", "sha512". Default "sha256".

    Returns:
        dict with keys: hash, algorithm, input_length, error (optional).
    """
    try:
        if not isinstance(input_data, dict):
            return {"hash": None, "algorithm": None, "input_length": 0, "error": "input_data must be a dict"}

        text = input_data.get("text")
        data = input_data.get("data")
        algorithm = input_data.get("algorithm", "sha256").lower()

        supported_algorithms = {"sha256", "md5", "sha1", "sha512"}
        if algorithm not in supported_algorithms:
            return {
                "hash": None,
                "algorithm": algorithm,
                "input_length": 0,
                "error": f"Unsupported algorithm '{algorithm}'. Supported: {', '.join(sorted(supported_algorithms))}",
            }

        if text is None and data is None:
            return {
                "hash": None,
                "algorithm": algorithm,
                "input_length": 0,
                "error": "Either 'text' or 'data' must be provided",
            }

        # Determine the raw string to hash
        if text is not None:
            raw = str(text)
        else:
            try:
                raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
            except (TypeError, ValueError) as exc:
                return {
                    "hash": None,
                    "algorithm": algorithm,
                    "input_length": 0,
                    "error": f"Failed to serialize data to JSON: {exc}",
                }

        encoded = raw.encode("utf-8")
        hasher = hashlib.new(algorithm)
        hasher.update(encoded)

        return {
            "hash": hasher.hexdigest(),
            "algorithm": algorithm,
            "input_length": len(encoded),
        }

    except Exception as exc:
        return {
            "hash": None,
            "algorithm": input_data.get("algorithm", "sha256") if isinstance(input_data, dict) else None,
            "input_length": 0,
            "error": f"Unexpected error: {exc}",
        }
