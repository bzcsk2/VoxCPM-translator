from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from common import get_nested, load_config, parse_args


@dataclass
class CheckResult:
    level: str
    name: str
    message: str


def _exists(path_value: str | None) -> bool:
    return bool(path_value) and Path(path_value).exists()


def _placeholder(path_value: str | None) -> bool:
    return not path_value or str(path_value).startswith("/path/to/")


def _check_executable(results: list[CheckResult], exe: str, required: bool = True) -> None:
    if shutil.which(exe):
        results.append(CheckResult("OK", exe, f"found {exe}"))
    elif required:
        results.append(CheckResult("FAIL", exe, f"missing executable: {exe}"))
    else:
        results.append(CheckResult("WARN", exe, f"optional executable not found: {exe}"))


def run_checks(config_path: str) -> list[CheckResult]:
    cfg = load_config(config_path)
    results: list[CheckResult] = []

    _check_executable(results, "ffmpeg")
    _check_executable(results, "ffprobe")
    _check_executable(results, "audio-separator", required=False)

    api_env = get_nested(cfg, "llm.api_key_env", "NVIDIA_API_KEY")
    if os.environ.get(api_env):
        results.append(CheckResult("OK", "LLM API key", f"{api_env} is set"))
    else:
        results.append(CheckResult("WARN", "LLM API key", f"{api_env} is not set; translation stage will fail"))

    input_video = get_nested(cfg, "paths.input_video")
    input_wav = get_nested(cfg, "paths.input_wav")
    output_dir = get_nested(cfg, "paths.output_dir")
    if _exists(input_video):
        results.append(CheckResult("OK", "input video", f"found {input_video}"))
    else:
        results.append(CheckResult("WARN", "input video", f"not found: {input_video}"))

    if _exists(input_wav):
        results.append(CheckResult("OK", "input wav", f"found {input_wav}"))
    else:
        results.append(CheckResult("WARN", "input wav", f"not found: {input_wav}; run scripts/00_extract_audio.py"))

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        results.append(CheckResult("OK", "output directory", f"ready {output_dir}"))

    model_keys = [
        "models.audio_separator_model_dir",
        "models.vibevoice_repo",
        "models.vibevoice_asr_path",
        "models.qwen_asr_path",
    ]
    for key in model_keys:
        value = get_nested(cfg, key)
        if _placeholder(value):
            results.append(CheckResult("WARN", key, f"placeholder or empty path: {value}"))
        elif Path(value).exists():
            results.append(CheckResult("OK", key, f"found {value}"))
        else:
            results.append(CheckResult("FAIL", key, f"path does not exist: {value}"))

    latentsync_dir = get_nested(cfg, "models.latentsync_dir")
    if _placeholder(latentsync_dir):
        results.append(CheckResult("WARN", "models.latentsync_dir", f"optional placeholder path: {latentsync_dir}"))
    elif Path(latentsync_dir).exists():
        results.append(CheckResult("OK", "models.latentsync_dir", f"found {latentsync_dir}"))
    else:
        results.append(CheckResult("WARN", "models.latentsync_dir", f"optional path not found: {latentsync_dir}"))

    backend = get_nested(cfg, "tts.backend", "manual")
    command = get_nested(cfg, "tts.custom_command", "")
    if backend == "custom_command" and not command:
        results.append(CheckResult("FAIL", "tts.custom_command", "backend is custom_command but no command template is configured"))
    else:
        results.append(CheckResult("OK", "tts.backend", f"configured backend: {backend}"))

    return results


def main() -> int:
    args = parse_args("Check local environment and config before running the pipeline")
    results = run_checks(args.config)
    has_fail = False
    for result in results:
        print(f"[{result.level}] {result.name}: {result.message}")
        has_fail = has_fail or result.level == "FAIL"
    return 1 if has_fail else 0


if __name__ == "__main__":
    sys.exit(main())
