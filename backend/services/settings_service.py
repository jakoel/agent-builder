from __future__ import annotations

import json
from typing import Any

from ..config import settings as app_config

_SETTINGS_FILE = app_config.STORAGE_PATH / "settings.json"

DEFAULTS: dict[str, Any] = {
    "model_provider": "ollama",
    "ollama_base_url": "http://localhost:11434",
    "default_model": "qwen3-vl:8b",
    "openai_api_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "anthropic_api_key": "",
    "anthropic_base_url": "https://api.anthropic.com",
    "default_temperature": 0.7,
    "default_max_tokens": 2048,
}


def load() -> dict[str, Any]:
    if not _SETTINGS_FILE.exists():
        return dict(DEFAULTS)
    try:
        return json.loads(_SETTINGS_FILE.read_text())
    except Exception:
        return dict(DEFAULTS)


def save(data: dict[str, Any]) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2))
