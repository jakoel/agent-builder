"""Unified LLM client. Routes calls to Ollama / OpenAI / Anthropic based on settings."""

from __future__ import annotations

import json as _json
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional

import httpx

from . import settings_service
from .llm_pricing import compute_cost


@dataclass
class ChatResult:
    content: str
    provider: str = "ollama"
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class LLMService:
    """Provider-agnostic LLM client. Reads settings on every call so
    provider switches take effect immediately."""

    def __init__(self) -> None:
        self._http: Optional[httpx.AsyncClient] = None
        self._anthropic_client: Any = None  # lazy-init

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0)
            )
        return self._http

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def list_models(self) -> list[dict[str, Any]]:
        """Return Ollama-local models. Cloud providers don't support listing here."""
        cfg = settings_service.load()
        base = cfg.get("ollama_base_url", "http://localhost:11434").rstrip("/")
        resp = await self._client().get(f"{base}/api/tags")
        resp.raise_for_status()
        return resp.json().get("models", [])

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        cfg = settings_service.load()
        provider = cfg.get("model_provider", "ollama")
        if temperature is None:
            temperature = cfg.get("default_temperature", 0.7)
        if max_tokens is None:
            max_tokens = cfg.get("default_max_tokens", 2048)

        start = time.monotonic()
        if provider == "openai":
            result = await self._chat_openai(cfg, model, messages, system, temperature, max_tokens)
        elif provider == "anthropic":
            result = await self._chat_anthropic(cfg, model, messages, system, temperature, max_tokens)
        else:
            result = await self._chat_ollama(cfg, model, messages, system, temperature, max_tokens)

        result.latency_ms = (time.monotonic() - start) * 1000
        result.provider = provider
        result.model = model
        result.cost_usd = compute_cost(provider, model, result.prompt_tokens, result.completion_tokens)
        return result

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[tuple[str, Optional[ChatResult]], None]:
        """Yield (chunk, final_result?). final_result is None until the last yield."""
        cfg = settings_service.load()
        provider = cfg.get("model_provider", "ollama")
        if temperature is None:
            temperature = cfg.get("default_temperature", 0.7)
        if max_tokens is None:
            max_tokens = cfg.get("default_max_tokens", 2048)

        start = time.monotonic()
        if provider == "openai":
            stream = self._stream_openai(cfg, model, messages, system, temperature, max_tokens)
        elif provider == "anthropic":
            stream = self._stream_anthropic(cfg, model, messages, system, temperature, max_tokens)
        else:
            stream = self._stream_ollama(cfg, model, messages, system, temperature, max_tokens)

        async for chunk, final in stream:
            if final is not None:
                final.latency_ms = (time.monotonic() - start) * 1000
                final.provider = provider
                final.model = model
                final.cost_usd = compute_cost(provider, model, final.prompt_tokens, final.completion_tokens)
            yield chunk, final

    # ------------------------------------------------------------------
    # Ollama
    # ------------------------------------------------------------------

    async def _chat_ollama(self, cfg, model, messages, system, temperature, max_tokens) -> ChatResult:
        base = cfg.get("ollama_base_url", "http://localhost:11434").rstrip("/")
        payload = self._ollama_payload(model, messages, system, temperature, max_tokens, stream=False)
        resp = await self._client().post(f"{base}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        prompt_tok = int(data.get("prompt_eval_count", 0))
        completion_tok = int(data.get("eval_count", 0))
        return ChatResult(
            content=content,
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=prompt_tok + completion_tok,
        )

    async def _stream_ollama(self, cfg, model, messages, system, temperature, max_tokens):
        base = cfg.get("ollama_base_url", "http://localhost:11434").rstrip("/")
        payload = self._ollama_payload(model, messages, system, temperature, max_tokens, stream=True)
        accumulated = ""
        prompt_tok = 0
        completion_tok = 0
        async with self._client().stream("POST", f"{base}/api/chat", json=payload) as resp:
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
                    accumulated += content
                    yield content, None
                if chunk.get("done"):
                    prompt_tok = int(chunk.get("prompt_eval_count", 0))
                    completion_tok = int(chunk.get("eval_count", 0))
        yield "", ChatResult(
            content=accumulated,
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=prompt_tok + completion_tok,
        )

    @staticmethod
    def _ollama_payload(model, messages, system, temperature, max_tokens, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "messages": list(messages), "stream": stream}
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options
        return payload

    # ------------------------------------------------------------------
    # OpenAI (and OpenAI-compatible endpoints)
    # ------------------------------------------------------------------

    async def _chat_openai(self, cfg, model, messages, system, temperature, max_tokens) -> ChatResult:
        api_key = cfg.get("openai_api_key", "")
        base = cfg.get("openai_base_url", "https://api.openai.com/v1").rstrip("/")
        if not api_key:
            raise RuntimeError("OpenAI API key is not set in Settings")

        payload = {
            "model": model,
            "messages": ([{"role": "system", "content": system}] if system else []) + list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = await self._client().post(
            f"{base}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ChatResult(
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

    async def _stream_openai(self, cfg, model, messages, system, temperature, max_tokens):
        api_key = cfg.get("openai_api_key", "")
        base = cfg.get("openai_base_url", "https://api.openai.com/v1").rstrip("/")
        if not api_key:
            raise RuntimeError("OpenAI API key is not set in Settings")

        payload = {
            "model": model,
            "messages": ([{"role": "system", "content": system}] if system else []) + list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        accumulated = ""
        prompt_tok = 0
        completion_tok = 0
        async with self._client().stream(
            "POST",
            f"{base}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        ) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise RuntimeError(f"OpenAI {resp.status_code}: {body.decode()[:300]}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload_str = line[len("data:"):].strip()
                if payload_str == "[DONE]":
                    break
                try:
                    obj = _json.loads(payload_str)
                except _json.JSONDecodeError:
                    continue
                choices = obj.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {}).get("content")
                    if delta:
                        accumulated += delta
                        yield delta, None
                if obj.get("usage"):
                    u = obj["usage"]
                    prompt_tok = u.get("prompt_tokens", prompt_tok)
                    completion_tok = u.get("completion_tokens", completion_tok)
        yield "", ChatResult(
            content=accumulated,
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=prompt_tok + completion_tok,
        )

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------

    def _get_anthropic(self, cfg):
        api_key = cfg.get("anthropic_api_key", "")
        base = cfg.get("anthropic_base_url", "https://api.anthropic.com")
        if not api_key:
            raise RuntimeError("Anthropic API key is not set in Settings")
        # Lazy-import + cache by (key, base) so settings changes don't get stale
        cache_key = (api_key, base)
        if self._anthropic_client is None or self._anthropic_client[0] != cache_key:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key, base_url=base)
            self._anthropic_client = (cache_key, client)
        return self._anthropic_client[1]

    async def _chat_anthropic(self, cfg, model, messages, system, temperature, max_tokens) -> ChatResult:
        client = self._get_anthropic(cfg)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or 2048,
            "temperature": temperature if temperature is not None else 0.7,
        }
        if system:
            kwargs["system"] = system
        resp = await client.messages.create(**kwargs)
        content = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return ChatResult(
            content=content,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
        )

    async def _stream_anthropic(self, cfg, model, messages, system, temperature, max_tokens):
        client = self._get_anthropic(cfg)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or 2048,
            "temperature": temperature if temperature is not None else 0.7,
        }
        if system:
            kwargs["system"] = system

        accumulated = ""
        prompt_tok = 0
        completion_tok = 0
        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                accumulated += text
                yield text, None
            final = await stream.get_final_message()
            prompt_tok = final.usage.input_tokens
            completion_tok = final.usage.output_tokens
        yield "", ChatResult(
            content=accumulated,
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=prompt_tok + completion_tok,
        )
