"""Native persistent memory tools — key-value store per agent, survives across runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _save(path: Path, store: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2))


def memory_read(input_data: dict, storage_path: Path, agent_id: str) -> dict:
    key = input_data.get("key", "")
    store = _load(storage_path / "memory" / f"{agent_id}.json")
    return {"value": store.get(key), "found": key in store}


def memory_write(input_data: dict, storage_path: Path, agent_id: str) -> dict:
    key = input_data.get("key", "")
    value = input_data.get("value")
    path = storage_path / "memory" / f"{agent_id}.json"
    store = _load(path)
    store[key] = value
    _save(path, store)
    return {"ok": True, "key": key}


def memory_list(input_data: dict, storage_path: Path, agent_id: str) -> dict:
    store = _load(storage_path / "memory" / f"{agent_id}.json")
    return {"keys": list(store.keys()), "count": len(store)}
