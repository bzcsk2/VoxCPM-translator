from __future__ import annotations

import importlib.util
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from common import get_nested


OK = "OK"
WARN = "WARN"
FAIL = "FAIL"

REQUIRED_PATH_KEYS = [
    "models.audio_separator_model_dir",
    "models.vibevoice_repo",
    "models.vibevoice_asr_path",
    "models.qwen_asr_path",
]

OPTIONAL_PATH_KEYS = [
    "models.latentsync_dir",
]

REQUIRED_PATH_VALUE_KEYS = [
    "paths.input_video",
    "paths.input_wav",
    "paths.output_dir",
    "paths.vocal_source_for_asr",
    "paths.instrumental_audio",
    "paths.asr_json",
    "paths.refined_json",
    "paths.dub_chunk_dir",
    "paths.temp_mixed_wav",
    "paths.final_video",
]

SUPPORTED_TTS_BACKENDS = {"manual", "custom_command", "voxcpm"}


@dataclass(frozen=True)
class CheckResult:
    level: str
    name: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def is_placeholder(value: Any) -> bool:
    return value is None or value == "" or str(value).startswith("/path/to/")


def as_path(value: Any) -> Path:
    return Path(str(value)).expanduser()


def check_executable(results: list[CheckResult], exe: str, required: bool = True) -> None:
    if shutil.which(exe):
        results.append(CheckResult(OK, exe, f"found {exe}"))
    elif required:
        results.append(CheckResult(FAIL, exe, f"missing executable: {exe}"))
    else:
        results.append(CheckResult(WARN, exe, f"optional executable not found: {exe}"))


def check_path(results: list[CheckResult], key: str, value: Any, required: bool = True) -> bool:
    if is_placeholder(value):
        level = FAIL if required else WARN
        results.append(CheckResult(level, key, f"placeholder or empty path: {value}"))
        return False
    path = as_path(value)
    if path.exists():
        results.append(CheckResult(OK, key, f"found {path}"))
        return True
    level = FAIL if required else WARN
    results.append(CheckResult(level, key, f"path does not exist: {path}"))
    return False


def check_path_value(results: list[CheckResult], cfg: dict[str, Any], key: str, required: bool = True) -> bool:
    value = get_nested(cfg, key)
    if is_placeholder(value):
        level = FAIL if required else WARN
        results.append(CheckResult(level, key, f"missing or placeholder value: {value}"))
        return False
    results.append(CheckResult(OK, key, f"configured: {value}"))
    return True


def check_file(results: list[CheckResult], key: str, path: Path, required: bool = True) -> bool:
    if path.is_file():
        results.append(CheckResult(OK, key, f"found {path}"))
        return True
    level = FAIL if required else WARN
    results.append(CheckResult(level, key, f"file does not exist: {path}"))
    return False


def check_module(results: list[CheckResult], key: str, module_name: str | None, required: bool = True) -> bool:
    if not module_name:
        level = FAIL if required else WARN
        results.append(CheckResult(level, key, "empty Python module name"))
        return False
    if importlib.util.find_spec(str(module_name)) is not None:
        results.append(CheckResult(OK, key, f"importable module: {module_name}"))
        return True
    level = FAIL if required else WARN
    results.append(CheckResult(level, key, f"module is not importable: {module_name}"))
    return False


def check_required_config_values(results: list[CheckResult], cfg: dict[str, Any]) -> None:
    for key in REQUIRED_PATH_VALUE_KEYS:
        check_path_value(results, cfg, key)


def check_audio_separator_model(results: list[CheckResult], cfg: dict[str, Any]) -> None:
    model_dir_value = get_nested(cfg, "models.audio_separator_model_dir")
    model_name = get_nested(cfg, "models.audio_separator_model", "")
    model_dir_ok = check_path(results, "models.audio_separator_model_dir", model_dir_value)
    if not model_name:
        results.append(CheckResult(FAIL, "models.audio_separator_model", "empty model filename"))
        return
    if not model_dir_ok:
        results.append(
            CheckResult(
                WARN,
                "models.audio_separator_model",
                f"cannot verify model file until model directory is valid: {model_name}",
            )
        )
        return
    model_path = as_path(model_dir_value) / str(model_name)
    check_file(results, "models.audio_separator_model", model_path)


def check_model_paths(results: list[CheckResult], cfg: dict[str, Any]) -> None:
    check_audio_separator_model(results, cfg)
    for key in REQUIRED_PATH_KEYS:
        if key == "models.audio_separator_model_dir":
            continue
        check_path(results, key, get_nested(cfg, key))
    for key in OPTIONAL_PATH_KEYS:
        check_path(results, key, get_nested(cfg, key), required=False)


def check_llm(results: list[CheckResult], cfg: dict[str, Any]) -> None:
    api_base = get_nested(cfg, "llm.api_base")
    model = get_nested(cfg, "llm.model")
    api_env = get_nested(cfg, "llm.api_key_env", "NVIDIA_API_KEY")

    if api_base:
        results.append(CheckResult(OK, "llm.api_base", f"configured: {api_base}"))
    else:
        results.append(CheckResult(FAIL, "llm.api_base", "missing LLM API base URL"))

    if model:
        results.append(CheckResult(OK, "llm.model", f"configured: {model}"))
    else:
        results.append(CheckResult(FAIL, "llm.model", "missing LLM model"))

    if os.environ.get(api_env):
        results.append(CheckResult(OK, "LLM API key", f"{api_env} is set"))
    else:
        results.append(CheckResult(WARN, "LLM API key", f"{api_env} is not set; translation stage will fail"))


def check_tts(results: list[CheckResult], cfg: dict[str, Any]) -> None:
    backend = get_nested(cfg, "tts.backend", "manual")
    command = get_nested(cfg, "tts.custom_command", "")
    adapter = get_nested(cfg, "tts.voxcpm_adapter", "")

    if backend not in SUPPORTED_TTS_BACKENDS:
        results.append(
            CheckResult(
                FAIL,
                "tts.backend",
                f"unsupported backend: {backend!r}; expected manual, custom_command, or voxcpm",
            )
        )
        return

    results.append(CheckResult(OK, "tts.backend", f"configured backend: {backend}"))

    if backend == "custom_command":
        if command:
            results.append(CheckResult(OK, "tts.custom_command", "custom command template configured"))
        else:
            results.append(
                CheckResult(
                    FAIL,
                    "tts.custom_command",
                    "backend is custom_command but no command template is configured",
                )
            )
    elif backend == "voxcpm":
        check_path(results, "models.voxcpm_model_path", get_nested(cfg, "models.voxcpm_model_path"))
        check_module(results, "tts.voxcpm_adapter", adapter)


def check_outputs(results: list[CheckResult], cfg: dict[str, Any]) -> None:
    output_dir = get_nested(cfg, "paths.output_dir")
    if not output_dir:
        results.append(CheckResult(FAIL, "paths.output_dir", "missing output directory"))
        return
    try:
        as_path(output_dir).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        results.append(CheckResult(FAIL, "paths.output_dir", f"cannot create output directory: {exc}"))
        return
    results.append(CheckResult(OK, "output directory", f"ready {output_dir}"))


def run_environment_checks(cfg: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    check_executable(results, "ffmpeg")
    check_executable(results, "ffprobe")
    check_executable(results, "audio-separator", required=False)
    check_required_config_values(results, cfg)
    check_outputs(results, cfg)
    check_model_paths(results, cfg)
    check_llm(results, cfg)
    check_tts(results, cfg)
    return results


def summarize_results(results: Iterable[CheckResult]) -> dict[str, int]:
    summary = {OK: 0, WARN: 0, FAIL: 0}
    for result in results:
        summary[result.level] = summary.get(result.level, 0) + 1
    return summary


def has_failures(results: Iterable[CheckResult]) -> bool:
    return any(result.level == FAIL for result in results)


def render_results(results: Iterable[CheckResult], include_summary: bool = True) -> str:
    materialized = list(results)
    lines = [f"[{result.level}] {result.name}: {result.message}" for result in materialized]
    if include_summary:
        summary = summarize_results(materialized)
        lines.append(f"[SUMMARY] OK={summary.get(OK, 0)} WARN={summary.get(WARN, 0)} FAIL={summary.get(FAIL, 0)}")
    return "\n".join(lines)
