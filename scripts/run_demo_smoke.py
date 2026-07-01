from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "examples" / "demo"
ASR_FIXTURE = DEMO_DIR / "asr_demo.json"
REFINED_FIXTURE = DEMO_DIR / "refined_demo.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and validate the no-model demo fixtures")
    parser.add_argument("--work-dir", default="outputs/demo_smoke", help="Directory for generated demo artifacts")
    parser.add_argument("--keep-going", action="store_true", help="Run all checks even if one fails")
    return parser.parse_args()


def timestamp_to_ms(value: str) -> int:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(".")
    return ((int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000) + int(millis)


def load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array: {path}")
    return data


def write_silence_wav(path: Path, duration_ms: int, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = max(1, int(sample_rate * duration_ms / 1000))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frame_count)


def is_non_spoken_marker(text: str) -> bool:
    return text.strip() in {"[Music]", "[Human Sounds]", "[Human sounds]", "[Silence]"}


def prepare_demo_files(work_dir: Path) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    chunk_dir = work_dir / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    asr_path = work_dir / "asr_demo.json"
    refined_path = work_dir / "refined_demo.json"
    shutil.copyfile(ASR_FIXTURE, asr_path)
    shutil.copyfile(REFINED_FIXTURE, refined_path)

    refined = load_json(refined_path)
    end_ms = 0
    for segment in refined:
        start_ms = timestamp_to_ms(str(segment["start"]))
        segment_end_ms = timestamp_to_ms(str(segment["end"]))
        end_ms = max(end_ms, segment_end_ms)
        if is_non_spoken_marker(str(segment.get("en", ""))):
            continue
        duration_ms = max(200, segment_end_ms - start_ms)
        write_silence_wav(chunk_dir / f"raw_{segment['id']}.wav", duration_ms)

    write_silence_wav(work_dir / "instrumental.wav", max(end_ms, 1000))
    (work_dir / "input_video_placeholder.mp4").write_bytes(b"demo placeholder; not a real video\n")

    config_path = work_dir / "config.yaml"
    config_path.write_text(
        f"""
paths:
  output_dir: "{work_dir}"
  asr_json: "{asr_path}"
  refined_json: "{refined_path}"
  dub_chunk_dir: "{chunk_dir}"
  instrumental_audio: "{work_dir / 'instrumental.wav'}"
  input_video: "{work_dir / 'input_video_placeholder.mp4'}"
  temp_mixed_wav: "{work_dir / 'temp_full_audio.wav'}"
  final_video: "{work_dir / 'final_dubbing.mp4'}"
tts:
  backend: "manual"
  overwrite: false
assembly:
  min_speed_ratio: 0.70
  audio_bitrate: "192k"
  missing_chunk_policy: "error"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return config_path


def run_command(command: list[str]) -> int:
    print("$ " + " ".join(command))
    completed = subprocess.run(command, cwd=ROOT)
    return completed.returncode


def run_demo_smoke(work_dir: Path, keep_going: bool = False) -> int:
    config_path = prepare_demo_files(work_dir)
    commands = [
        [sys.executable, "scripts/04_verify_translation.py", "--config", str(config_path)],
        [sys.executable, "scripts/validate_artifacts.py", "--config", str(config_path)],
        [sys.executable, "scripts/05_generate_audio_chunks.py", "--config", str(config_path)],
        [sys.executable, "scripts/inspect_artifacts.py", "--config", str(config_path), "--output", str(work_dir / "artifact_report.md")],
        [sys.executable, "scripts/diagnose.py", "--config", str(config_path), "--include-artifacts", "--output", str(work_dir / "diagnostic_report.md")],
    ]

    failed = False
    for command in commands:
        returncode = run_command(command)
        if returncode != 0:
            failed = True
            if not keep_going:
                break

    if failed:
        print(f"Demo smoke failed. Work dir: {work_dir}")
        return 1

    print(f"Demo smoke passed. Work dir: {work_dir}")
    print(f"Generated config: {config_path}")
    print(f"Artifact report: {work_dir / 'artifact_report.md'}")
    print(f"Diagnostic report: {work_dir / 'diagnostic_report.md'}")
    return 0


def main() -> int:
    args = parse_args()
    return run_demo_smoke(Path(args.work_dir), keep_going=args.keep_going)


if __name__ == "__main__":
    sys.exit(main())
