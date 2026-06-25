from pathlib import Path

from common import load_dotenv, seconds_to_timestamp, timestamp_to_ms, timestamp_to_seconds


def test_timestamp_roundtrip_helpers() -> None:
    assert timestamp_to_seconds("01:02:03.500") == 3723.5
    assert timestamp_to_ms("00:00:01.234") == 1234
    assert seconds_to_timestamp(1.234) == "00:00:01.234"


def test_seconds_to_timestamp_rolls_over_milliseconds() -> None:
    assert seconds_to_timestamp(59.9996) == "00:01:00.000"
    assert seconds_to_timestamp(3599.9996) == "01:00:00.000"


def test_load_dotenv_does_not_override_existing(monkeypatch, tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("A=from_file\nB='quoted value'\n", encoding="utf-8")
    monkeypatch.setenv("A", "from_env")
    load_dotenv(dotenv)
    assert __import__("os").environ["A"] == "from_env"
    assert __import__("os").environ["B"] == "quoted value"
