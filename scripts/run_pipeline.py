from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import get_nested, load_config

SCRIPT_DIR = Path(__file__).resolve().parent

STAGES = [
    (0, "extract-audio", [sys.executable, str(SCRIPT_DIR / "00_extract_audio.py")]),
    (1, "process-vocals", ["bash", str(SCRIPT_DIR / "01_process_vocals.sh")]),
    (2, "transcribe", [sys.executable, str(SCRIPT_DIR / "02_transcribe_vibe.py")]),
    (3, "refine-translate", [sys.executable, str(SCRIPT_DIR / "03_refine_and_translate.py")]),
    (4, "verify", [sys.executable, str(SCRIPT_DIR / "04_verify_translation.py")]),
    (5, "generate-audio-chunks", [sys.executable, str(SCRIPT_DIR / "05_generate_audio_chunks.py")]),
    (6, "assemble", [sys.executable, str(SCRIPT_DIR / "06_assemble_final.py")]),
    (7, "latentsync", [sys.executable, str(SCRIPT_DIR / "07_latentsync_lipsync.py")]),
    (8, "burn-subtitles", [sys.executable, str(SCRIPT_DIR / "burn_subtitles.py")]),
]

STAGE_OUTPUT_KEYS = {
    0: ["paths.input_wav"],
    1: ["paths.vocal_source_for_asr", "paths.instrumental_audio"],
    2: ["paths.asr_json"],
    3: ["paths.refined_json"],
    4: [],
    5: ["paths.dub_chunk_dir"],
    6: ["paths.final_video"],
    7: ["paths.lipsync_video"],
    8: ["paths.subtitled_video"],
}

NOISE_MARKERS = {"[Music]", "[Human Sounds]", "[Human sounds]", "[Silence]"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run selected VoxCPM Translator stages in order")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--from-stage", type=int, default=0)
    parser.add_argument("--to-stage", type=int, default=6)
    parser.add_argument("--skip", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true", help="Print expected output status for selected stages and exit")
    parser.add_argument("--resume", action="store_true", help="Skip selected stages whose expected outputs already exist")
    return parser.parse_args()


def selected_stages(from_stage: int, to_stage: int) -> list[tuple[int, str, list[str]]]:
    return [(stage_id, name, cmd) for stage_id, name, cmd in STAGES if from_stage <= stage_id <= to_stage]


def stage_command(name: str, base_cmd: list[str], config_path: str) -> list[str]:
    return [*base_cmd, config_path] if name == "process-vocals" else [*base_cmd, "--config", config_path]


def expected_paths(stage_id: int, cfg: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for key in STAGE_OUTPUT_KEYS.get(stage_id, []):
        value = get_nested(cfg, key)
        if value:
            paths.append(Path(str(value)))
    return paths


def _has_material_output(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        return any(path.iterdir())
    return path.is_file() and path.stat().st_size >= 0


def _is_noise_row(segment: dict[str, Any]) -> bool:
    text = str(segment.get("en") or segment.get("zh_fixed") or segment.get("text_zh") or "").strip()
    return text in NOISE_MARKERS or (text.startswith("[") and text.endswith("]"))


def _tts_chunks_complete(cfg: dict[str, Any]) -> tuple[str, str]:
    refined_json = Path(str(get_nested(cfg, "paths.refined_json", "")))
    chunk_dir = Path(str(get_nested(cfg, "paths.dub_chunk_dir", "")))
    if not refined_json.exists():
        return "missing", f"missing refined JSON: {refined_json}"
    if not chunk_dir.exists():
        return "missing", f"missing chunk directory: {chunk_dir}"

    try:
        segments = json.loads(refined_json.read_text(encoding="utf-8"))
    except Exception as exc:
        return "partial", f"cannot inspect refined JSON: {exc}"

    required_ids = [segment.get("id") for segment in segments if isinstance(segment, dict) and not _is_noise_row(segment)]
    missing = [
        seg_id
        for seg_id in required_ids
        if not (chunk_dir / f"raw_{seg_id}.wav").exists() and not (chunk_dir / f"dub_{seg_id}.wav").exists()
    ]
    if missing:
        preview = ", ".join(map(str, missing[:5]))
        suffix = "..." if len(missing) > 5 else ""
        return "partial", f"missing chunks: {preview}{suffix}"
    return "complete", f"{len(required_ids)} required chunks present in {chunk_dir}"


def stage_status(stage_id: int, cfg: dict[str, Any]) -> tuple[str, str]:
    if stage_id == 4:
        return "check", "validation stage has no durable output"
    if stage_id == 5:
        return _tts_chunks_complete(cfg)

    paths = expected_paths(stage_id, cfg)
    if not paths:
        return "unknown", "no expected outputs configured"

    present = [path for path in paths if _has_material_output(path)]
    if len(present) == len(paths):
        return "complete", ", ".join(str(path) for path in paths)
    if present:
        missing = [str(path) for path in paths if path not in present]
        return "partial", "missing: " + ", ".join(missing)
    return "missing", ", ".join(str(path) for path in paths)


def print_status(cfg: dict[str, Any], from_stage: int, to_stage: int) -> None:
    for stage_id, name, _base_cmd in selected_stages(from_stage, to_stage):
        state, detail = stage_status(stage_id, cfg)
        print(f"[{stage_id}] {name}: {state} - {detail}")


def should_skip_for_resume(stage_id: int, cfg: dict[str, Any]) -> bool:
    state, _detail = stage_status(stage_id, cfg)
    return state == "complete"


def manifest_dir(cfg: dict[str, Any]) -> Path:
    output_dir = Path(str(get_nested(cfg, "paths.output_dir", "outputs")))
    return output_dir / ".pipeline_state"


def manifest_path(stage_id: int, name: str, cfg: dict[str, Any]) -> Path:
    safe_name = name.replace("/", "-").replace(" ", "-")
    return manifest_dir(cfg) / f"stage_{stage_id:02d}_{safe_name}.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_stage_manifest(
    stage_id: int,
    name: str,
    cfg: dict[str, Any],
    status: str,
    started_at: str,
    finished_at: str,
    duration_seconds: float,
    returncode: int | None,
    config_path: str,
) -> None:
    directory = manifest_dir(cfg)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage_id": stage_id,
        "stage_name": name,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": round(duration_seconds, 3),
        "returncode": returncode,
        "config_file": Path(config_path).name,
    }
    manifest_path(stage_id, name, cfg).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_stage(stage_id: int, name: str, cmd: list[str], cfg: dict[str, Any], config_path: str) -> None:
    started_at = utc_now()
    started = time.monotonic()
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        finished_at = utc_now()
        write_stage_manifest(
            stage_id,
            name,
            cfg,
            status="failed",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=time.monotonic() - started,
            returncode=exc.returncode,
            config_path=config_path,
        )
        raise
    finished_at = utc_now()
    write_stage_manifest(
        stage_id,
        name,
        cfg,
        status="success",
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=time.monotonic() - started,
        returncode=0,
        config_path=config_path,
    )


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config) if args.status or args.resume or not args.dry_run else {}

    if args.status:
        print_status(cfg, args.from_stage, args.to_stage)
        return 0

    for stage_id, name, base_cmd in selected_stages(args.from_stage, args.to_stage):
        if str(stage_id) in args.skip or name in args.skip:
            print(f"[{stage_id}] {name}: skipped")
            continue
        if args.resume and should_skip_for_resume(stage_id, cfg):
            print(f"[{stage_id}] {name}: skipped (complete)")
            continue
        cmd = stage_command(name, base_cmd, args.config)
        print(f"[{stage_id}] {name}: {' '.join(cmd)}")
        if not args.dry_run:
            run_stage(stage_id, name, cmd, cfg, args.config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
