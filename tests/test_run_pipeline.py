import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_pipeline", ROOT / "scripts" / "run_pipeline.py")
run_pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(run_pipeline)


def write_config(path: Path, body: str) -> Path:
    path.write_text(body.strip(), encoding="utf-8")
    return path


def test_run_pipeline_dry_run_selects_stage_range(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_pipeline.py", "--config", "cfg.yaml", "--from-stage", "4", "--to-stage", "5", "--dry-run"],
    )
    assert run_pipeline.main() == 0
    output = capsys.readouterr().out
    assert "[4] verify:" in output
    assert "[5] generate-audio-chunks:" in output
    assert "[3] refine-translate:" not in output
    assert "[6] assemble:" not in output


def test_run_pipeline_skip_accepts_id_and_name(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_pipeline.py",
            "--config",
            "cfg.yaml",
            "--from-stage",
            "0",
            "--to-stage",
            "2",
            "--skip",
            "1",
            "--skip",
            "transcribe",
            "--dry-run",
        ],
    )
    assert run_pipeline.main() == 0
    output = capsys.readouterr().out
    assert "[0] extract-audio:" in output
    assert "[1] process-vocals: skipped" in output
    assert "[2] transcribe: skipped" in output


def test_run_pipeline_executes_commands_with_expected_config(monkeypatch) -> None:
    calls = []

    def fake_run(cmd, check):
        calls.append(cmd)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_pipeline.py", "--config", "cfg.yaml", "--from-stage", "1", "--to-stage", "2"],
    )
    assert run_pipeline.main() == 0
    assert calls[0][-1] == "cfg.yaml"
    assert calls[0][0] == "bash"
    assert calls[1][-2:] == ["--config", "cfg.yaml"]


def test_status_reports_complete_and_missing_outputs(tmp_path: Path, monkeypatch, capsys) -> None:
    input_wav = tmp_path / "input.wav"
    asr_json = tmp_path / "asr.json"
    input_wav.write_bytes(b"wav")
    config_path = write_config(
        tmp_path / "config.yaml",
        f"""
paths:
  input_wav: "{input_wav}"
  asr_json: "{asr_json}"
""",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_pipeline.py", "--config", str(config_path), "--from-stage", "0", "--to-stage", "2", "--status"],
    )
    assert run_pipeline.main() == 0
    output = capsys.readouterr().out
    assert "[0] extract-audio: complete" in output
    assert "[2] transcribe: missing" in output


def test_resume_skips_complete_stage_and_runs_missing_stage(tmp_path: Path, monkeypatch, capsys) -> None:
    calls = []
    input_wav = tmp_path / "input.wav"
    asr_json = tmp_path / "asr.json"
    input_wav.write_bytes(b"wav")
    config_path = write_config(
        tmp_path / "config.yaml",
        f"""
paths:
  input_wav: "{input_wav}"
  asr_json: "{asr_json}"
""",
    )

    def fake_run(cmd, check):
        calls.append(cmd)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_pipeline.py", "--config", str(config_path), "--from-stage", "0", "--to-stage", "2", "--resume"],
    )
    assert run_pipeline.main() == 0
    output = capsys.readouterr().out
    assert "[0] extract-audio: skipped (complete)" in output
    assert all("00_extract_audio.py" not in " ".join(call) for call in calls)
    assert any("02_transcribe_vibe.py" in " ".join(call) for call in calls)


def test_tts_stage_status_checks_required_chunks(tmp_path: Path) -> None:
    refined_json = tmp_path / "refined.json"
    chunk_dir = tmp_path / "chunks"
    chunk_dir.mkdir()
    refined_json.write_text(
        json.dumps(
            [
                {"id": 0, "en": "Hello."},
                {"id": 1, "en": "[Music]"},
            ]
        ),
        encoding="utf-8",
    )
    cfg = {
        "paths": {
            "refined_json": str(refined_json),
            "dub_chunk_dir": str(chunk_dir),
        }
    }
    assert run_pipeline.stage_status(5, cfg)[0] == "partial"
    (chunk_dir / "raw_0.wav").write_bytes(b"wav")
    assert run_pipeline.stage_status(5, cfg)[0] == "complete"


def test_verify_stage_is_not_auto_resumable() -> None:
    assert run_pipeline.stage_status(4, {})[0] == "check"
    assert run_pipeline.should_skip_for_resume(4, {}) is False
