import json
import sys
from pathlib import Path

import validate_artifacts


def _segment(seg_id: int, en: str = "Hello.") -> dict:
    return {
        "id": seg_id,
        "start": f"00:00:0{seg_id}.000",
        "end": f"00:00:0{seg_id + 1}.000",
        "speaker": "spk1",
        "text_zh": "你好" if en != "[Music]" else "[Music]",
        "zh_fixed": "你好。" if en != "[Music]" else "[Music]",
        "en": en,
    }


def _write_artifact_config(tmp_path: Path) -> Path:
    asr_json = tmp_path / "asr.json"
    refined_json = tmp_path / "refined.json"
    chunk_dir = tmp_path / "chunks"
    chunk_dir.mkdir()

    refined = [_segment(0), _segment(1, en="[Music]")]
    asr = [{key: row[key] for key in ["id", "start", "end", "speaker", "text_zh"]} for row in refined]
    asr_json.write_text(json.dumps(asr), encoding="utf-8")
    refined_json.write_text(json.dumps(refined), encoding="utf-8")

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
paths:
  asr_json: "{asr_json}"
  refined_json: "{refined_json}"
  dub_chunk_dir: "{chunk_dir}"
""".strip(),
        encoding="utf-8",
    )
    return config_path


def test_validate_artifacts_can_skip_chunks(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_artifact_config(tmp_path)
    monkeypatch.setattr(sys, "argv", ["validate_artifacts.py", "--config", str(config_path), "--skip-chunks"])

    assert validate_artifacts.main() == 0


def test_validate_artifacts_reports_missing_chunks(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_artifact_config(tmp_path)
    monkeypatch.setattr(sys, "argv", ["validate_artifacts.py", "--config", str(config_path)])

    assert validate_artifacts.main() == 1
