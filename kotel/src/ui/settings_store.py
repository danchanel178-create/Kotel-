"""Сохранение настроек UI (рядом с проектом)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "label_mode": "full",  # "full" | "compact"
}


def settings_path(project_root: Path) -> Path:
    return project_root / "settings.json"


def load_settings(project_root: Path) -> dict[str, Any]:
    path = settings_path(project_root)
    data = dict(DEFAULTS)
    if not path.is_file():
        return data
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data.update({k: loaded[k] for k in DEFAULTS if k in loaded})
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    if data.get("label_mode") not in ("full", "compact"):
        data["label_mode"] = DEFAULTS["label_mode"]
    return data


def save_settings(project_root: Path, settings: dict[str, Any]) -> None:
    path = settings_path(project_root)
    payload = dict(DEFAULTS)
    payload.update({k: settings[k] for k in DEFAULTS if k in settings})
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
