from __future__ import annotations

from config_schema import has_errors, render_issues, validate_config_schema


def valid_config() -> dict:
    return {
        "paths": {
            "input_video": "input.mp4",
            "input_wav": "input.wav",
            "output_dir": "outputs",
            "vocal_source_for_asr": "outputs/vocals.wav",
            "instrumental_audio": "outputs/instrumental.wav",
            "asr_json": "outputs/asr.json",
            "refined_json": "outputs/refined.json",
            "dub_chunk_dir": "outputs/chunks",
            "temp_mixed_wav": "outputs/temp.wav",
            "final_video": "outputs/final.mp4",
        },
        "models": {
            "audio_separator_model": "Kim_Vocal_2.onnx",
            "audio_separator_model_dir": "models/separator",
            "vibevoice_repo": "repos/VibeVoice",
            "vibevoice_asr_path": "models/VibeVoice-ASR",
            "qwen_asr_path": "models/Qwen3-ASR",
        },
        "llm": {
            "api_base": "https://example.invalid/v1/chat/completions",
            "model": "demo-model",
            "api_key_env": "DEMO_API_KEY",
        },
        "tts": {
            "backend": "manual",
            "overwrite": False,
        },
        "runtime": {
            "asr_device": "cpu",
            "asr_dtype": "float32",
            "tts_devices": ["cpu"],
        },
        "assembly": {
            "backend": "ffmpeg",
            "min_speed_ratio": 0.7,
            "audio_bitrate": "192k",
            "missing_chunk_policy": "error",
        },
        "subtitles": {
            "font_name": "Arial",
            "font_size": 48,
            "margin_v": 40,
            "outline": 2,
        },
    }


def messages(issues):
    return {(issue.level, issue.path, issue.message) for issue in issues}


def test_valid_config_has_no_schema_errors() -> None:
    issues = validate_config_schema(valid_config())

    assert issues == []
    assert has_errors(issues) is False


def test_missing_required_key_is_error() -> None:
    cfg = valid_config()
    del cfg["paths"]["input_video"]

    issues = validate_config_schema(cfg)

    assert any(issue.level == "ERROR" and issue.path == "paths.input_video" for issue in issues)


def test_type_mismatch_is_error() -> None:
    cfg = valid_config()
    cfg["tts"]["overwrite"] = "false"

    issues = validate_config_schema(cfg)

    assert any(issue.path == "tts.overwrite" and "expected bool" in issue.message for issue in issues)


def test_enum_value_is_error() -> None:
    cfg = valid_config()
    cfg["assembly"]["missing_chunk_policy"] = "explode"

    issues = validate_config_schema(cfg)

    assert any(issue.path == "assembly.missing_chunk_policy" and "unsupported value" in issue.message for issue in issues)


def test_numeric_range_is_error() -> None:
    cfg = valid_config()
    cfg["assembly"]["min_speed_ratio"] = 1.5

    issues = validate_config_schema(cfg)

    assert any(issue.path == "assembly.min_speed_ratio" and "above maximum" in issue.message for issue in issues)


def test_custom_command_backend_requires_command() -> None:
    cfg = valid_config()
    cfg["tts"]["backend"] = "custom_command"

    issues = validate_config_schema(cfg)

    assert any(issue.path == "tts.custom_command" and "required" in issue.message for issue in issues)


def test_voxcpm_backend_requires_adapter_and_model_path() -> None:
    cfg = valid_config()
    cfg["tts"]["backend"] = "voxcpm"

    issues = validate_config_schema(cfg)

    assert any(issue.path == "tts.voxcpm_adapter" for issue in issues)
    assert any(issue.path == "models.voxcpm_model_path" for issue in issues)


def test_runtime_tts_devices_must_be_non_empty_strings() -> None:
    cfg = valid_config()
    cfg["runtime"]["tts_devices"] = ["cuda:0", ""]

    issues = validate_config_schema(cfg)

    assert any(issue.path == "runtime.tts_devices" for issue in issues)


def test_render_issues_includes_summary() -> None:
    cfg = valid_config()
    cfg["tts"]["backend"] = "bad"
    issues = validate_config_schema(cfg)

    rendered = render_issues(issues)

    assert "[ERROR] tts.backend" in rendered
    assert "[SUMMARY]" in rendered
