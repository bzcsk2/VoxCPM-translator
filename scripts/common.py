from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import yaml


def parse_args(description: str | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default="configs/default.yaml", help="Path to YAML config file")
    return parser.parse_args()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_dotenv(dotenv_path: str | os.PathLike[str] | None = None) -> None:
    """Load simple KEY=VALUE pairs from .env without overriding existing env vars."""
    path = Path(dotenv_path) if dotenv_path else project_root() / ".env"
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_config(path: str | os.PathLike[str]) -> dict[str, Any]:
    load_dotenv()
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_nested(config: dict[str, Any], key: str, default: Any = None) -> Any:
    cur: Any = config
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def require_nested(config: dict[str, Any], key: str) -> Any:
    value = get_nested(config, key)
    if value is None or value == "":
        raise KeyError(f"Missing required config key: {key}")
    return value


def ensure_dir(path: str | os.PathLike[str]) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_parent(path: str | os.PathLike[str]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def env_api_key(config: dict[str, Any]) -> str:
    env_name = get_nested(config, "llm.api_key_env", "NVIDIA_API_KEY")
    key = os.environ.get(env_name)
    if not key:
        raise RuntimeError(f"Missing API key. Set environment variable: {env_name}")
    return key


def timestamp_to_seconds(ts: str) -> float:
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def timestamp_to_ms(ts: str) -> int:
    return int(round(timestamp_to_seconds(ts) * 1000))


def seconds_to_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis == 1000:
        secs += 1
        millis = 0
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"
