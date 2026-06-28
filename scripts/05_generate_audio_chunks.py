from __future__ import annotations

import importlib
import shlex
import subprocess
import sys
from pathlib import Path
from string import Template
from typing import Any, Callable

from common import ensure_dir, get_nested, load_config, parse_args, require_nested
from data_contracts import (
    expected_chunk_paths,
    has_errors,
    is_non_spoken_segment,
    load_json_array,
    missing_tts_chunk_ids,
    render_issues,
    segment_text,
    validate_segment_list,
)


NOISE_MARKERS = {"[Music]", "[Human Sounds]", "[Human sounds]", "[Silence]"}


def expected_chunk_path(chunk_dir: Path, seg_id: Any) -> Path:
    raw_path, dub_path = expected_chunk_paths(chunk_dir, seg_id)
    if raw_path.exists():
        return raw_path
    return dub_path


def _segment_text(segment: dict[str, Any]) -> str:
    return segment_text(segment)


def _render_command(template: str, segment: dict[str, Any], output_path: Path) -> list[str]:
    mapping = {
        "id": str(segment.get("id")),
        "speaker": str(segment.get("speaker", "")),
        "text": _segment_text(segment),
        "output": str(output_path),
        "start": str(segment.get("start", "")),
        "end": str(segment.get("end", "")),
    }
    rendered = Template(template).safe_substitute(mapping)
    return shlex.split(rendered)


def validate_manual_chunks(segments: list[dict[str, Any]], chunk_dir: Path) -> list[Any]:
    return missing_tts_chunk_ids(segments, chunk_dir)


def run_custom_command(segments: list[dict[str, Any]], chunk_dir: Path, command_template: str, overwrite: bool) -> None:
    for segment in segments:
        text = _segment_text(segment)
        if not text or is_non_spoken_segment(segment):
            continue
        seg_id = segment.get("id")
        output_path = chunk_dir / f"raw_{seg_id}.wav"
        if output_path.exists() and not overwrite:
            print(f"Skipping existing chunk: {output_path}")
            continue
        cmd = _render_command(command_template, segment, output_path)
        print(f"Generating chunk ID {seg_id}: {output_path}")
        subprocess.run(cmd, check=True)
        if not output_path.exists():
            raise FileNotFoundError(f"Custom TTS command completed but did not create: {output_path}")


def _load_adapter(module_name: str, function_name: str) -> Callable[[dict[str, Any], Path, dict[str, Any]], None]:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Could not import TTS adapter module {module_name!r}. "
            "Install it, add it to PYTHONPATH, or use tts.backend=custom_command/manual."
        ) from exc

    function = getattr(module, function_name, None)
    if function is None or not callable(function):
        raise RuntimeError(f"Adapter module {module_name!r} does not define callable {function_name!r}.")
    return function


def run_python_adapter(
    segments: list[dict[str, Any]],
    chunk_dir: Path,
    cfg: dict[str, Any],
    adapter_module: str,
    function_name: str,
    overwrite: bool,
) -> None:
    generate_audio = _load_adapter(adapter_module, function_name)
    for segment in segments:
        text = _segment_text(segment)
        if not text or is_non_spoken_segment(segment):
            continue
        seg_id = segment.get("id")
        output_path = chunk_dir / f"raw_{seg_id}.wav"
        if output_path.exists() and not overwrite:
            print(f"Skipping existing chunk: {output_path}")
            continue
        print(f"Generating chunk ID {seg_id} with adapter {adapter_module}.{function_name}: {output_path}")
        generate_audio(segment, output_path, cfg)
        if not output_path.exists():
            raise FileNotFoundError(f"Adapter completed but did not create: {output_path}")


def run_voxcpm_adapter(segments: list[dict[str, Any]], chunk_dir: Path, cfg: dict[str, Any], overwrite: bool) -> None:
    adapter_module = get_nested(cfg, "tts.voxcpm_adapter", "")
    function_name = get_nested(cfg, "tts.voxcpm_adapter_function", "generate_audio")
    if not adapter_module:
        raise RuntimeError(
            "tts.backend is 'voxcpm', but tts.voxcpm_adapter is empty. "
            "Set it to a Python module that exposes generate_audio(segment, output_path, config), "
            "or use tts.backend=custom_command for a CLI-based VoxCPM runner."
        )
    run_python_adapter(segments, chunk_dir, cfg, adapter_module, function_name, overwrite=overwrite)


def main() -> int:
    args = parse_args("Generate or validate per-segment audio chunks")
    cfg = load_config(args.config)

    refined_json = Path(require_nested(cfg, "paths.refined_json"))
    chunk_dir = ensure_dir(require_nested(cfg, "paths.dub_chunk_dir"))
    backend = get_nested(cfg, "tts.backend", "manual")
    overwrite = bool(get_nested(cfg, "tts.overwrite", False))

    segments = load_json_array(refined_json)
    segment_issues = validate_segment_list(segments, "refined", refined=True)
    if segment_issues:
        print(render_issues(segment_issues))
    if has_errors(segment_issues):
        return 1

    if backend == "manual":
        missing = validate_manual_chunks(segments, chunk_dir)
        if missing:
            print("Manual TTS backend selected, but audio chunks are missing.")
            print(f"Place WAV files in {chunk_dir} named raw_<id>.wav or dub_<id>.wav.")
            print("Missing segment IDs: " + ", ".join(map(str, missing)))
            return 1
        print(f"SUCCESS: all required chunks are present in {chunk_dir}")
        return 0

    if backend == "custom_command":
        command_template = get_nested(cfg, "tts.custom_command", "")
        if not command_template:
            raise RuntimeError("tts.backend is custom_command but tts.custom_command is empty")
        run_custom_command(segments, Path(chunk_dir), command_template, overwrite=overwrite)
        return 0

    if backend == "voxcpm":
        run_voxcpm_adapter(segments, Path(chunk_dir), cfg, overwrite=overwrite)
        return 0

    raise RuntimeError(f"Unsupported tts.backend: {backend!r}. Supported: manual, custom_command, voxcpm")


if __name__ == "__main__":
    sys.exit(main())
