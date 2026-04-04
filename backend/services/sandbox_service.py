from __future__ import annotations

from typing import Any

from ..sandbox.executor import execute


class SandboxService:
    """High-level interface for executing tool code in a sandboxed subprocess."""

    async def execute_tool(
        self, code: str, input_data: dict[str, Any], timeout: int = 30
    ) -> dict[str, Any]:
        """Execute *code* with *input_data* in an isolated subprocess.

        Returns the parsed JSON result dict from stdout.
        """
        return execute(code=code, input_data=input_data, timeout=timeout)
