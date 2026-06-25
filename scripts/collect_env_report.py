from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import get_nested, load_config

PATH_KEYS = [
    "paths.input_video",
    "paths.input_wav",
    "paths.output_dir",
    "paths.asr_json",
    "paths.refined_json",
    "paths.dub_chunk_dir",
    "models.audio_separator_model_dir",
    "models.vibevoice_repo",
    "models.vibevoice_asr_path",
    "models.qwen_asr_path",
    "models.latentsync_dir",
]

EXECUTABLES = ["ffmpeg", "ffprobe", "audio-separator"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect a redacted local environment report")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to YAML config file")
    parser.add_argument("--output", help="Optional JSON output path. Defaults to stdout.")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def command_first_line(command: list[str]) -> str | None:
    try:
        proc = subprocess.run(command, check=False, text=True, capture_output=True, timeout=10)
    except Exception:
        return None
    output = (proc.stdout or proc.stderr or "").strip().splitlines()
    return output[0] if output else None


def executable_report(name: str) -> dict[str, Any]:
    found = shutil.which(name) is not None
    report: dict[str, Any] = {"found": found}
    if found:
        report["version"] = command_first_line([name, "--version"])
    return report


def is_placeholder(value: Any) -> bool:
    return not value or str(value).startswith("/path/to/")


def path_report(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {"configured": False, "placeholder": True, "exists": False, "kind": None}

    text = str(value)
    placeholder = is_placeholder(text)
    path = Path(text)
    exists = path.exists() if not placeholder else False
    if path.is_file():
        kind = "file"
    elif path.is_dir():
        kind = "directory"
    else:
        kind = None
    return {
        "configured": True,
        "placeholder": placeholder,
        "exists": exists,
        "kind": kind,
    }


def python_report() -> dict[str, Any]:
    return {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "executable_name": Path(sys.executable).name,
    }


def torch_report() -> dict[str, Any]:
    try:
        import torch  # type: ignore[import-not-found]
    except Exception as exc:
        return {"installed": False, "error_type": type(exc).__name__}

    report: dict[str, Any] = {
        "installed": True,
        "version": getattr(torch, "__version__", None),
        "cuda_version": getattr(getattr(torch, "version", None), "cuda", None),
    }
    try:
        cuda_available = bool(torch.cuda.is_available())
        report["cuda_available"] = cuda_available
        report["gpu_count"] = int(torch.cuda.device_count()) if cuda_available else 0
        if cuda_available and torch.cuda.device_count() > 0:
            report["first_gpu_name"] = torch.cuda.get_device_name(0)
    except Exception as exc:
        report["cuda_probe_error_type"] = type(exc).__name__
    return report


def build_report(config_path: str) -> dict[str, Any]:
    cfg = load_config(config_path)
    api_env_name = str(get_nested(cfg, "llm.api_key_env", "NVIDIA_API_KEY"))

    return {
        "generated_at": utc_now(),
        "config_file": Path(config_path).name,
        "system": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "python": python_report(),
        "executables": {name: executable_report(name) for name in EXECUTABLES},
        "torch": torch_report(),
        "config_paths": {key: path_report(get_nested(cfg, key)) for key in PATH_KEYS},
        "llm": {
            "api_key_env": api_env_name,
            "api_key_set": bool(os.environ.get(api_env_name)),
            "model": get_nested(cfg, "llm.model"),
            "base_url_configured": bool(get_nested(cfg, "llm.base_url")),
        },
        "tts": {
            "backend": get_nested(cfg, "tts.backend", "manual"),
            "voxcpm_adapter_configured": bool(get_nested(cfg, "tts.voxcpm_adapter")),
            "custom_command_configured": bool(get_nested(cfg, "tts.custom_command")),
        },
        "privacy_note": (
            "This report intentionally omits raw configured paths, API key values, prompts, source text, "
            "translated text, model outputs, and media metadata. Review before sharing publicly."
        ),
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.config)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
