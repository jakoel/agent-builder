from __future__ import annotations

import json as _json
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

    async def list_models(self) -> list[dict[str, Any]]:
        resp = await self._client.get("/api/tags")
        resp.raise_for_status()
        return resp.json().get("models", [])

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Non-streaming chat completion. Returns the assistant message content."""
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion. Yields content chunks as they arrive."""
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = _json.loads(line)
                except _json.JSONDecodeError:
                    continue
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
