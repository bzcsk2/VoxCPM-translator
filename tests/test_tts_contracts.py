import sys
import types
from pathlib import Path

import pytest

from tts_contracts import (
    build_chunk_request,
    ensure_chunk_created,
    iter_spoken_chunk_requests,
    load_adapter,
    render_custom_command,
    validate_backend_name,
)


def _segment(segment_id=3, en="Hello world."):
    return {
        "id": segment_id,
        "start": "00:00:00.000",
        "end": "00:00:01.000",
        "speaker": "spk1",
        "text_zh": "你好",
        "zh_fixed": "你好。",
        "en": en,
    }


def test_build_chunk_request_maps_segment_fields(tmp_path: Path) -> None:
    request = build_chunk_request(_segment(), tmp_path)

    assert request.segment_id == 3
    assert request.text == "Hello world."
    assert request.speaker == "spk1"
    assert request.output_path == tmp_path / "raw_3.wav"
    assert request.to_template_mapping()["output"] == str(tmp_path / "raw_3.wav")


def test_iter_spoken_chunk_requests_skips_non_spoken_segments(tmp_path: Path) -> None:
    requests = iter_spoken_chunk_requests([_segment(1, "[Music]"), _segment(2, "Speak.")], tmp_path)

    assert [request.segment_id for request in requests] == [2]


def test_render_custom_command_substitutes_segment_values(tmp_path: Path) -> None:
    request = build_chunk_request(_segment(en="Hello there."), tmp_path)

    cmd = render_custom_command("python tts.py --text '$text' --speaker '$speaker' --output '$output'", request)

    assert cmd[:2] == ["python", "tts.py"]
    assert "Hello there." in cmd
    assert str(tmp_path / "raw_3.wav") in cmd


def test_load_adapter_returns_callable(monkeypatch) -> None:
    module = types.ModuleType("fake_tts_adapter")

    def generate_audio(segment, output_path, config):
        output_path.write_bytes(b"wav")

    module.generate_audio = generate_audio
    monkeypatch.setitem(sys.modules, "fake_tts_adapter", module)

    adapter = load_adapter("fake_tts_adapter")

    assert adapter is generate_audio


def test_load_adapter_rejects_missing_callable(monkeypatch) -> None:
    module = types.ModuleType("bad_tts_adapter")
    monkeypatch.setitem(sys.modules, "bad_tts_adapter", module)

    with pytest.raises(RuntimeError):
        load_adapter("bad_tts_adapter")


def test_ensure_chunk_created_requires_file(tmp_path: Path) -> None:
    output = tmp_path / "raw_1.wav"
    output.write_bytes(b"wav")

    ensure_chunk_created(output, "adapter")

    with pytest.raises(FileNotFoundError):
        ensure_chunk_created(tmp_path / "missing.wav", "adapter")


def test_validate_backend_name() -> None:
    assert validate_backend_name("manual") == "manual"
    with pytest.raises(RuntimeError):
        validate_backend_name("unknown")
