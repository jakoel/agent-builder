"""Proxy router for Ollama model listing."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from ..services.llm_service import LLMService

router = APIRouter(prefix="/api/models", tags=["models"])

_llm = LLMService()


@router.get("/", response_model=List[Dict[str, Any]])
async def list_models() -> list[dict[str, Any]]:
    try:
        return await _llm.list_models()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama unavailable: {exc}")
