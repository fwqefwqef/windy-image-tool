from __future__ import annotations

import json
from pathlib import Path

DEFAULT_SETTINGS = {
    "font_size": 12,
    "background_color": "#f2f2f2",
    "text_color": "#1a1a1a",
}

SETTINGS_DIR = Path.home() / ".windy-image-tool"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)
    merged = dict(DEFAULT_SETTINGS)
    merged.update({key: data[key] for key in DEFAULT_SETTINGS if key in data})
    merged["font_size"] = max(8, min(24, int(merged["font_size"])))
    for color_key in ("background_color", "text_color"):
        color = str(merged[color_key]).strip()
        if not is_valid_color(color):
            merged[color_key] = DEFAULT_SETTINGS[color_key]
    return merged


def save_settings(settings: dict) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "font_size": max(8, min(24, int(settings["font_size"]))),
        "background_color": settings["background_color"],
        "text_color": settings["text_color"],
    }
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def is_valid_color(value: str) -> bool:
    if not value.startswith("#") or len(value) not in {4, 7}:
        return False
    digits = value[1:]
    return all(ch in "0123456789abcdefABCDEF" for ch in digits)


def dim_color(value: str, factor: float = 0.62) -> str:
    red, green, blue = hex_to_rgb(value)
    return f"#{int(red * factor):02x}{int(green * factor):02x}{int(blue * factor):02x}"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
