from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from pydub import AudioSegment

from common import ensure_parent, get_nested, load_config, parse_args, timestamp_to_ms


NOISE_MARKERS = {"[Music]", "[Human Sounds]", "[Human sounds]", "[Silence]"}


def is_noise_only(text: str) -> bool:
    stripped = text.strip()
    return stripped in NOISE_MARKERS or bool(re.match(r"^\[[^\]]+\]$", stripped))


def find_chunk(chunk_dir: str | os.PathLike[str], seg_id: int | str) -> str | None:
    for prefix in ("raw", "dub"):
        candidate = Path(chunk_dir) / f"{prefix}_{seg_id}.wav"
        if candidate.exists():
            return str(candidate)
    return None


def run_atempo(input_wav: str, ratio: float, output_wav: str) -> None:
    filters: list[str] = []
    tmp = ratio
    while tmp > 2.0:
        filters.append("atempo=2.0")
        tmp /= 2.0
    while tmp < 0.5:
        filters.append("atempo=0.5")
        tmp /= 0.5
    filters.append(f"atempo={tmp}")
    subprocess.run(["ffmpeg", "-y", "-i", input_wav, "-filter:a", ",".join(filters), output_wav], check=True)


def adjust_speed_smart(input_wav: str, target_dur_sec: float, output_wav: str, min_speed_ratio: float) -> bool:
    audio = AudioSegment.from_file(input_wav)
    current_dur = len(audio) / 1000.0
    if current_dur <= 0 or target_dur_sec <= 0:
        shutil.copyfile(input_wav, output_wav)
        return False
    ratio = current_dur / target_dur_sec
    final_ratio = ratio if ratio > 1.0 else max(min_speed_ratio, ratio)
    if 0.98 < final_ratio < 1.02:
        shutil.copyfile(input_wav, output_wav)
        return False
    run_atempo(input_wav, final_ratio, output_wav)
    return True


def main() -> None:
    args = parse_args("Assemble generated chunks and mux with source video")
    cfg = load_config(args.config)
    json_file = get_nested(cfg, "paths.refined_json")
    bgm_path = get_nested(cfg, "paths.instrumental_audio")
    chunk_dir = get_nested(cfg, "paths.dub_chunk_dir")
    output_video = get_nested(cfg, "paths.final_video")
    video_source = get_nested(cfg, "paths.input_video")
    temp_mixed_wav = get_nested(cfg, "paths.temp_mixed_wav")
    min_speed_ratio = float(get_nested(cfg, "assembly.min_speed_ratio", 0.70))
    bitrate = get_nested(cfg, "assembly.audio_bitrate", "192k")
    missing_policy = get_nested(cfg, "assembly.missing_chunk_policy", "error")

    with open(json_file, "r", encoding="utf-8") as f:
        segments = json.load(f)

    ensure_parent(temp_mixed_wav)
    ensure_parent(output_video)
    final_audio = AudioSegment.from_wav(bgm_path)
    missing: list[int | str] = []
    skipped_noise = 0
    used_chunks = 0
    adjusted_chunks = 0

    for seg in segments:
        seg_id = seg["id"]
        if is_noise_only(seg.get("en", "")):
            skipped_noise += 1
            continue
        raw_wav = find_chunk(chunk_dir, seg_id)
        if not raw_wav:
            missing.append(seg_id)
            if missing_policy == "warn":
                print(f"Missing chunk: ID_{seg_id}")
                continue
            if missing_policy == "skip":
                continue
            continue
        start_ms = timestamp_to_ms(seg["start"])
        end_ms = timestamp_to_ms(seg["end"])
        fixed_wav = os.path.join(chunk_dir, f"fixed_{seg_id}.wav")
        was_adjusted = adjust_speed_smart(raw_wav, (end_ms - start_ms) / 1000.0, fixed_wav, min_speed_ratio)
        adjusted_chunks += int(was_adjusted)
        used_chunks += 1
        final_audio = final_audio.overlay(AudioSegment.from_wav(fixed_wav), position=start_ms)

    if missing and missing_policy == "error":
        raise FileNotFoundError(
            "Missing required audio chunks: " + ", ".join(f"ID_{seg_id}" for seg_id in missing)
        )

    final_audio.export(temp_mixed_wav, format="wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_source, "-i", temp_mixed_wav,
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", bitrate, output_video,
    ], check=True)
    print(
        "Assembly summary: "
        f"segments={len(segments)}, used_chunks={used_chunks}, "
        f"adjusted_chunks={adjusted_chunks}, skipped_noise={skipped_noise}, missing_chunks={len(missing)}"
    )
    print(f"Done: {output_video}")


if __name__ == "__main__":
    main()
