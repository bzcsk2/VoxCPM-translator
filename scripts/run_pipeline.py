from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run selected VoxCPM Translator stages in order")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--from-stage", type=int, default=0)
    parser.add_argument("--to-stage", type=int, default=6)
    parser.add_argument("--skip", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for stage_id, name, base_cmd in STAGES:
        if not (args.from_stage <= stage_id <= args.to_stage):
            continue
        if str(stage_id) in args.skip or name in args.skip:
            print(f"[{stage_id}] {name}: skipped")
            continue
        cmd = [*base_cmd, args.config] if name == "process-vocals" else [*base_cmd, "--config", args.config]
        print(f"[{stage_id}] {name}: {' '.join(cmd)}")
        if not args.dry_run:
            subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
