import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_translation", ROOT / "scripts" / "04_verify_translation.py")
verify_translation = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(verify_translation)


def test_verify_alignment_accepts_valid_rows() -> None:
    asr = [{"id": 0, "start": "00:00:00.000", "end": "00:00:01.000", "speaker": "A", "text_zh": "你好"}]
    refined = [{**asr[0], "zh_fixed": "你好。", "en": "Hello."}]
    assert verify_translation.verify_alignment(asr, refined) == []


def test_verify_alignment_rejects_mutated_immutable_field() -> None:
    asr = [{"id": 0, "start": "00:00:00.000", "end": "00:00:01.000", "speaker": "A", "text_zh": "你好"}]
    refined = [{**asr[0], "speaker": "B", "zh_fixed": "你好。", "en": "Hello."}]
    errors = verify_translation.verify_alignment(asr, refined)
    assert errors
    assert "speaker" in errors[0]
