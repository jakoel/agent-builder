"""Settings router — read/write storage/settings.json."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsPayload(BaseModel):
    data: Dict[str, Any]


@router.get("/")
async def get_settings() -> Dict[str, Any]:
    return settings_service.load()


@router.put("/")
async def update_settings(payload: SettingsPayload) -> Dict[str, Any]:
    if not isinstance(payload.data, dict):
        raise HTTPException(status_code=422, detail="Settings must be a JSON object")
    settings_service.save(payload.data)
    return payload.data


@router.post("/reset")
async def reset_settings() -> Dict[str, Any]:
    defaults = dict(settings_service.DEFAULTS)
    settings_service.save(defaults)
    return defaults
