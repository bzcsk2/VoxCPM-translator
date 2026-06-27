from pathlib import Path

import yaml

import check_env


def _write_config(tmp_path: Path, backend: str = "manual", custom_command: str = "", adapter: str = "") -> Path:
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"video")
    input_wav = tmp_path / "input.wav"
    input_wav.write_bytes(b"wav")
    output_dir = tmp_path / "outputs"

    model_dir = tmp_path / "models" / "audio-separator"
    model_dir.mkdir(parents=True)
    (model_dir / "Kim_Vocal_2.onnx").write_bytes(b"onnx")

    vibevoice_repo = tmp_path / "repos" / "VibeVoice"
    vibevoice_repo.mkdir(parents=True)
    vibevoice_asr = tmp_path / "models" / "VibeVoice-ASR"
    vibevoice_asr.mkdir()
    qwen_asr = tmp_path / "models" / "Qwen3-ASR-1.7B"
    qwen_asr.mkdir()
    voxcpm = tmp_path / "models" / "VoxCPM2"
    voxcpm.mkdir()

    config = {
        "paths": {
            "input_video": str(input_video),
            "input_wav": str(input_wav),
            "output_dir": str(output_dir),
        },
        "models": {
            "audio_separator_model": "Kim_Vocal_2.onnx",
            "audio_separator_model_dir": str(model_dir),
            "vibevoice_repo": str(vibevoice_repo),
            "vibevoice_asr_path": str(vibevoice_asr),
            "qwen_asr_path": str(qwen_asr),
            "voxcpm_model_path": str(voxcpm),
            "latentsync_dir": str(tmp_path / "missing-latentsync"),
        },
        "llm": {"api_key_env": "TEST_LLM_KEY"},
        "tts": {
            "backend": backend,
            "custom_command": custom_command,
            "voxcpm_adapter": adapter,
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def _levels(results: list[check_env.CheckResult]) -> dict[str, str]:
    return {result.name: result.level for result in results}


def test_run_checks_validates_audio_separator_model_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_env.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    monkeypatch.setenv("TEST_LLM_KEY", "set")
    config_path = _write_config(tmp_path)

    results = check_env.run_checks(str(config_path))
    levels = _levels(results)

    assert levels["models.audio_separator_model_dir"] == "OK"
    assert levels["models.audio_separator_model"] == "OK"
    assert levels["models.vibevoice_repo"] == "OK"
    assert levels["models.vibevoice_asr_path"] == "OK"
    assert levels["models.qwen_asr_path"] == "OK"
    assert levels["tts.backend"] == "OK"


def test_run_checks_fails_missing_audio_separator_model(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_env.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    config_path = _write_config(tmp_path)
    (tmp_path / "models" / "audio-separator" / "Kim_Vocal_2.onnx").unlink()

    results = check_env.run_checks(str(config_path))
    levels = _levels(results)

    assert levels["models.audio_separator_model"] == "FAIL"


def test_run_checks_custom_command_requires_command(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_env.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    config_path = _write_config(tmp_path, backend="custom_command", custom_command="")

    results = check_env.run_checks(str(config_path))
    levels = _levels(results)

    assert levels["tts.custom_command"] == "FAIL"


def test_run_checks_voxcpm_accepts_importable_adapter(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_env.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    config_path = _write_config(tmp_path, backend="voxcpm", adapter="json")

    results = check_env.run_checks(str(config_path))
    levels = _levels(results)

    assert levels["tts.backend"] == "OK"
    assert levels["models.voxcpm_model_path"] == "OK"
    assert levels["tts.voxcpm_adapter"] == "OK"


def test_run_checks_voxcpm_requires_model_path_and_adapter(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_env.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    config_path = _write_config(tmp_path, backend="voxcpm", adapter="")
    (tmp_path / "models" / "VoxCPM2").rmdir()

    results = check_env.run_checks(str(config_path))
    levels = _levels(results)

    assert levels["tts.backend"] == "OK"
    assert levels["models.voxcpm_model_path"] == "FAIL"
    assert levels["tts.voxcpm_adapter"] == "FAIL"
