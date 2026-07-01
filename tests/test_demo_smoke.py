import json
from pathlib import Path

import run_demo_smoke


def test_prepare_demo_files_creates_expected_artifacts(tmp_path: Path) -> None:
    config_path = run_demo_smoke.prepare_demo_files(tmp_path)

    assert config_path.exists()
    assert (tmp_path / "asr_demo.json").exists()
    assert (tmp_path / "refined_demo.json").exists()
    assert (tmp_path / "chunks" / "raw_0.wav").exists()
    assert (tmp_path / "chunks" / "raw_2.wav").exists()
    assert not (tmp_path / "chunks" / "raw_1.wav").exists()
    assert (tmp_path / "instrumental.wav").exists()
    assert (tmp_path / "input_video_placeholder.mp4").exists()

    config_text = config_path.read_text(encoding="utf-8")
    assert "backend: \"manual\"" in config_text
    assert str(tmp_path / "chunks") in config_text


def test_demo_fixtures_preserve_alignment() -> None:
    asr = json.loads(run_demo_smoke.ASR_FIXTURE.read_text(encoding="utf-8"))
    refined = json.loads(run_demo_smoke.REFINED_FIXTURE.read_text(encoding="utf-8"))

    assert len(asr) == len(refined) == 3
    for asr_row, refined_row in zip(asr, refined, strict=True):
        for key in ["id", "start", "end", "speaker", "text_zh"]:
            assert asr_row[key] == refined_row[key]
        assert refined_row["zh_fixed"]
        assert refined_row["en"]


def test_run_demo_smoke_executes_expected_commands(monkeypatch, tmp_path: Path) -> None:
    commands = []

    def fake_run_command(command):
        commands.append(command)
        if "scripts/inspect_artifacts.py" in command or "scripts/diagnose.py" in command:
            output_index = command.index("--output") + 1
            Path(command[output_index]).write_text("demo report", encoding="utf-8")
        return 0

    monkeypatch.setattr(run_demo_smoke, "run_command", fake_run_command)

    assert run_demo_smoke.run_demo_smoke(tmp_path) == 0
    assert len(commands) == 5
    assert commands[0][1] == "scripts/04_verify_translation.py"
    assert commands[1][1] == "scripts/validate_artifacts.py"
    assert commands[2][1] == "scripts/05_generate_audio_chunks.py"
    assert commands[3][1] == "scripts/inspect_artifacts.py"
    assert commands[4][1] == "scripts/diagnose.py"


def test_run_demo_smoke_stops_on_failure(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run_command(command):
        calls.append(command)
        return 1

    monkeypatch.setattr(run_demo_smoke, "run_command", fake_run_command)

    assert run_demo_smoke.run_demo_smoke(tmp_path) == 1
    assert len(calls) == 1
