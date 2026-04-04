from __future__ import annotations

from typing import Any, AsyncGenerator, Optional

import httpx

from ..config import settings


class OllamaService:
    """Async client wrapper for the Ollama HTTP API."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def list_models(self) -> list[dict[str, Any]]:
        """Return the list of locally available models from Ollama."""
        resp = await self._client.get("/api/tags")
        resp.raise_for_status()
        data = resp.json()
        return data.get("models", [])

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
    ) -> str:
        """Non-streaming chat completion. Returns the assistant message content."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]

        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion. Yields content chunks as they arrive."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]

        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                import json as _json

                try:
                    chunk = _json.loads(line)
                except _json.JSONDecodeError:
                    continue
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
