from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pydub import AudioSegment

from common import get_nested, load_config, parse_args, timestamp_to_ms
from data_contracts import (
    expected_chunk_paths,
    has_errors,
    is_non_spoken_segment,
    load_json_array,
    missing_tts_chunk_ids,
    render_issues,
    validate_segment_list,
)
from runtime_checks import ensure_parent_dir, require_choice, require_dir, require_file, require_positive_float

MISSING_POLICIES = {"error", "warn", "skip"}
NOISE_MARKERS = {"[Music]", "[Human Sounds]", "[Human sounds]", "[Silence]"}


def is_noise_only(text: str) -> bool:
    """Backward-compatible helper kept for older tests and direct callers."""
    stripped = text.strip()
    return stripped in NOISE_MARKERS or bool(re.match(r"^\[[^\]]+\]$", stripped))


def find_chunk(chunk_dir: str | Path, seg_id: int | str) -> str | None:
    """Return the first compatible chunk path as a string.

    The public helper returned ``str | None`` before the output-stage hardening
    refactor. Keep that behavior so older tests and direct callers continue to
    work while the implementation still uses the shared chunk naming contract.
    """
    raw_path, dub_path = expected_chunk_paths(chunk_dir, seg_id)
    if raw_path.exists():
        return str(raw_path)
    if dub_path.exists():
        return str(dub_path)
    return None


def atempo_filters(ratio: float) -> list[str]:
    if ratio <= 0:
        raise ValueError(f"atempo ratio must be positive, got {ratio}")
    filters: list[str] = []
    tmp = ratio
    while tmp > 2.0:
        filters.append("atempo=2.0")
        tmp /= 2.0
    while tmp < 0.5:
        filters.append("atempo=0.5")
        tmp /= 0.5
    filters.append(f"atempo={tmp}")
    return filters


def speed_adjustment_ratio(current_dur_sec: float, target_dur_sec: float, min_speed_ratio: float) -> float | None:
    if current_dur_sec <= 0 or target_dur_sec <= 0:
        return None
    ratio = current_dur_sec / target_dur_sec
    final_ratio = ratio if ratio > 1.0 else max(min_speed_ratio, ratio)
    if 0.98 < final_ratio < 1.02:
        return None
    return final_ratio


def run_atempo(input_wav: str | Path, ratio: float, output_wav: str | Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-i", str(input_wav), "-filter:a", ",".join(atempo_filters(ratio)), str(output_wav)], check=True)


def adjust_speed_smart(input_wav: str | Path, target_dur_sec: float, output_wav: str | Path, min_speed_ratio: float) -> bool:
    audio = AudioSegment.from_file(input_wav)
    current_dur = len(audio) / 1000.0
    final_ratio = speed_adjustment_ratio(current_dur, target_dur_sec, min_speed_ratio)
    if final_ratio is None:
        shutil.copyfile(input_wav, output_wav)
        return False
    run_atempo(input_wav, final_ratio, output_wav)
    return True


def validate_refined_segments(segments: list[dict[str, Any]]) -> None:
    issues = validate_segment_list(segments, "refined", refined=True)
    if has_errors(issues):
        raise ValueError("Refined JSON failed contract validation:\n" + render_issues(issues))


def validate_assembly_inputs(
    json_file: str,
    bgm_path: str,
    chunk_dir: str,
    video_source: str,
    temp_mixed_wav: str,
    output_video: str,
    min_speed_ratio: Any,
    missing_policy: Any,
) -> tuple[Path, Path, Path, Path, Path, Path, float, str]:
    refined_path = require_file(json_file, "paths.refined_json")
    instrumental_path = require_file(bgm_path, "paths.instrumental_audio")
    chunks_path = require_dir(chunk_dir, "paths.dub_chunk_dir")
    source_video_path = require_file(video_source, "paths.input_video")
    temp_path = ensure_parent_dir(temp_mixed_wav, "paths.temp_mixed_wav")
    output_path = ensure_parent_dir(output_video, "paths.final_video")
    speed_floor = require_positive_float(min_speed_ratio, "assembly.min_speed_ratio")
    policy = require_choice(missing_policy, "assembly.missing_chunk_policy", MISSING_POLICIES)
    return refined_path, instrumental_path, chunks_path, source_video_path, temp_path, output_path, speed_floor, policy


def main() -> None:
    args = parse_args("Assemble generated chunks and mux with source video")
    cfg = load_config(args.config)
    json_file = get_nested(cfg, "paths.refined_json")
    bgm_path = get_nested(cfg, "paths.instrumental_audio")
    chunk_dir = get_nested(cfg, "paths.dub_chunk_dir")
    output_video = get_nested(cfg, "paths.final_video")
    video_source = get_nested(cfg, "paths.input_video")
    temp_mixed_wav = get_nested(cfg, "paths.temp_mixed_wav")
    min_speed_ratio = get_nested(cfg, "assembly.min_speed_ratio", 0.70)
    bitrate = get_nested(cfg, "assembly.audio_bitrate", "192k")
    missing_policy = get_nested(cfg, "assembly.missing_chunk_policy", "error")

    refined_path, instrumental_path, chunks_path, source_video_path, temp_path, output_path, speed_floor, policy = validate_assembly_inputs(
        json_file,
        bgm_path,
        chunk_dir,
        video_source,
        temp_mixed_wav,
        output_video,
        min_speed_ratio,
        missing_policy,
    )

    segments = load_json_array(refined_path)
    validate_refined_segments(segments)

    missing = missing_tts_chunk_ids(segments, chunks_path)
    if missing and policy == "error":
        raise FileNotFoundError("Missing required audio chunks: " + ", ".join(f"ID_{seg_id}" for seg_id in missing))

    final_audio = AudioSegment.from_wav(instrumental_path)
    skipped_noise = 0
    used_chunks = 0
    adjusted_chunks = 0
    warned_missing = 0

    for seg in segments:
        seg_id = seg["id"]
        if is_non_spoken_segment(seg):
            skipped_noise += 1
            continue
        raw_wav = find_chunk(chunks_path, seg_id)
        if not raw_wav:
            warned_missing += 1
            if policy == "warn":
                print(f"Missing chunk: ID_{seg_id}")
            continue
        start_ms = timestamp_to_ms(seg["start"])
        end_ms = timestamp_to_ms(seg["end"])
        fixed_wav = chunks_path / f"fixed_{seg_id}.wav"
        was_adjusted = adjust_speed_smart(raw_wav, (end_ms - start_ms) / 1000.0, fixed_wav, speed_floor)
        adjusted_chunks += int(was_adjusted)
        used_chunks += 1
        final_audio = final_audio.overlay(AudioSegment.from_wav(fixed_wav), position=start_ms)

    final_audio.export(temp_path, format="wav")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_video_path),
            "-i",
            str(temp_path),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            str(bitrate),
            str(output_path),
        ],
        check=True,
    )
    print(
        "Assembly summary: "
        f"segments={len(segments)}, used_chunks={used_chunks}, "
        f"adjusted_chunks={adjusted_chunks}, skipped_noise={skipped_noise}, missing_chunks={warned_missing}"
    )
    print(f"Done: {output_path}")


if __name__ == "__main__":
    main()
