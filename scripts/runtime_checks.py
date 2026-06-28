from __future__ import annotations

from pathlib import Path
from typing import Any


def require_file(path_value: Any, label: str) -> Path:
    if path_value is None or str(path_value).strip() == "":
        raise FileNotFoundError(f"{label} is not configured")
    path = Path(str(path_value))
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist or is not a file: {path}")
    return path


def require_dir(path_value: Any, label: str) -> Path:
    if path_value is None or str(path_value).strip() == "":
        raise FileNotFoundError(f"{label} is not configured")
    path = Path(str(path_value))
    if not path.is_dir():
        raise FileNotFoundError(f"{label} does not exist or is not a directory: {path}")
    return path


def ensure_parent_dir(path_value: Any, label: str) -> Path:
    if path_value is None or str(path_value).strip() == "":
        raise FileNotFoundError(f"{label} is not configured")
    path = Path(str(path_value))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def require_choice(value: Any, label: str, allowed: set[str]) -> str:
    normalized = str(value or "").strip()
    if normalized not in allowed:
        expected = ", ".join(sorted(allowed))
        raise ValueError(f"{label} must be one of: {expected}; got {normalized!r}")
    return normalized


def require_positive_float(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive number; got {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"{label} must be positive; got {parsed}")
    return parsed
