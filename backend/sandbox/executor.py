"""Execute user-supplied tool code in a sandboxed subprocess."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .restrictions import generate_restriction_header

ALLOWED_IMPORTS: list[str] = [
    "json", "re", "datetime", "math", "requests", "bs4", "urllib",
    "collections", "itertools", "functools", "hashlib", "base64",
    "html", "xml", "csv", "time", "random", "string", "textwrap", "typing",
    "types", "io", "pypdf",
]

BLOCKED_MODULES: list[str] = [
    "os", "sys", "subprocess", "shutil", "socket", "importlib", "ctypes",
    "signal", "multiprocessing", "threading", "code", "compile", "eval", "exec",
]


def generate_wrapper_code(tool_code: str, input_json: str) -> str:
    """Build a complete Python script that executes *tool_code* safely.

    The script:
    1. Installs import restrictions and blocks dangerous builtins.
    2. Defines the user tool function(s).
    3. Calls the *first* function defined in tool_code with the provided input.
    4. Prints the JSON-encoded result to stdout.
    """
    header = generate_restriction_header()

    return f"""\
{header}

import json as _json

# ---- user tool code ---------------------------------------------------------
{tool_code}
# ---- end user tool code -----------------------------------------------------

# Discover the callable defined by the user code
import types as _types
_user_funcs = [
    v for k, v in dict(globals()).items()
    if isinstance(v, _types.FunctionType) and not k.startswith("_")
]
if not _user_funcs:
    raise RuntimeError("No callable function found in tool code")

_input_data = _json.loads({input_json!r})
_result = _user_funcs[0](_input_data)
print(_json.dumps(_result))
"""


def execute(
    code: str,
    input_data: dict[str, Any],
    timeout: int = 30,
) -> dict[str, Any]:
    """Write *code* to a temp file, run it in a subprocess, and return the
    parsed JSON output."""

    input_json = json.dumps(input_data)
    script = generate_wrapper_code(code, input_json)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
    ) as tmp:
        tmp.write(script)
        tmp_path = Path(tmp.name)

    try:
        proc = subprocess.run(
            [sys.executable, str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if proc.returncode != 0:
            raise RuntimeError(
                f"Tool execution failed (exit {proc.returncode}): {proc.stderr.strip()}"
            )

        stdout = proc.stdout.strip()
        if not stdout:
            return {"result": None}

        return json.loads(stdout)  # type: ignore[no-any-return]

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Tool execution timed out after {timeout}s")
    except json.JSONDecodeError:
        raise RuntimeError(f"Tool produced invalid JSON output: {proc.stdout[:500]}")
    finally:
        tmp_path.unlink(missing_ok=True)
