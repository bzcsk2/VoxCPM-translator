from __future__ import annotations

import importlib.util
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
    return bool(path_value) and Path(path_value).expanduser().exists()


def _placeholder(path_value: str | None) -> bool:
    return not path_value or str(path_value).startswith("/path/to/")


def _check_executable(results: list[CheckResult], exe: str, required: bool = True) -> None:
    if shutil.which(exe):
        results.append(CheckResult("OK", exe, f"found {exe}"))
    elif required:
        results.append(CheckResult("FAIL", exe, f"missing executable: {exe}"))
    else:
        results.append(CheckResult("WARN", exe, f"optional executable not found: {exe}"))


def _check_path(results: list[CheckResult], key: str, value: str | None, required: bool = True) -> bool:
    if _placeholder(value):
        level = "FAIL" if required else "WARN"
        results.append(CheckResult(level, key, f"placeholder or empty path: {value}"))
        return False
    path = Path(str(value)).expanduser()
    if path.exists():
        results.append(CheckResult("OK", key, f"found {path}"))
        return True
    level = "FAIL" if required else "WARN"
    results.append(CheckResult(level, key, f"path does not exist: {path}"))
    return False


def _check_file(results: list[CheckResult], key: str, path: Path, required: bool = True) -> bool:
    if path.is_file():
        results.append(CheckResult("OK", key, f"found {path}"))
        return True
    level = "FAIL" if required else "WARN"
    results.append(CheckResult(level, key, f"file does not exist: {path}"))
    return False


def _check_module(results: list[CheckResult], key: str, module_name: str | None, required: bool = True) -> bool:
    if not module_name:
        level = "FAIL" if required else "WARN"
        results.append(CheckResult(level, key, "empty Python module name"))
        return False
    if importlib.util.find_spec(str(module_name)) is not None:
        results.append(CheckResult("OK", key, f"importable module: {module_name}"))
        return True
    level = "FAIL" if required else "WARN"
    results.append(CheckResult(level, key, f"module is not importable: {module_name}"))
    return False


def _check_audio_separator_model(results: list[CheckResult], cfg: dict) -> None:
    model_dir_value = get_nested(cfg, "models.audio_separator_model_dir")
    model_name = get_nested(cfg, "models.audio_separator_model", "")
    model_dir_ok = _check_path(results, "models.audio_separator_model_dir", model_dir_value)
    if not model_name:
        results.append(CheckResult("FAIL", "models.audio_separator_model", "empty model filename"))
        return
    if not model_dir_ok:
        results.append(CheckResult("WARN", "models.audio_separator_model", f"cannot verify model file until model directory is valid: {model_name}"))
        return
    model_path = Path(str(model_dir_value)).expanduser() / str(model_name)
    _check_file(results, "models.audio_separator_model", model_path)


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
        Path(output_dir).expanduser().mkdir(parents=True, exist_ok=True)
        results.append(CheckResult("OK", "output directory", f"ready {output_dir}"))

    _check_audio_separator_model(results, cfg)

    model_keys = [
        "models.vibevoice_repo",
        "models.vibevoice_asr_path",
        "models.qwen_asr_path",
    ]
    for key in model_keys:
        _check_path(results, key, get_nested(cfg, key))

    latentsync_dir = get_nested(cfg, "models.latentsync_dir")
    _check_path(results, "models.latentsync_dir", latentsync_dir, required=False)

    backend = get_nested(cfg, "tts.backend", "manual")
    command = get_nested(cfg, "tts.custom_command", "")
    adapter = get_nested(cfg, "tts.voxcpm_adapter", "")

    if backend == "manual":
        results.append(CheckResult("OK", "tts.backend", "configured backend: manual"))
    elif backend == "custom_command":
        if command:
            results.append(CheckResult("OK", "tts.backend", "configured backend: custom_command"))
        else:
            results.append(CheckResult("FAIL", "tts.custom_command", "backend is custom_command but no command template is configured"))
    elif backend == "voxcpm":
        results.append(CheckResult("OK", "tts.backend", "configured backend: voxcpm"))
        _check_path(results, "models.voxcpm_model_path", get_nested(cfg, "models.voxcpm_model_path"))
        _check_module(results, "tts.voxcpm_adapter", adapter)
    else:
        results.append(CheckResult("FAIL", "tts.backend", f"unsupported backend: {backend!r}; expected manual, custom_command, or voxcpm"))

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
