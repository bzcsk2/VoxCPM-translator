import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("assemble_final", ROOT / "scripts" / "06_assemble_final.py")
assemble_final = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(assemble_final)


def test_find_chunk_prefers_raw(tmp_path: Path) -> None:
    raw = tmp_path / "raw_1.wav"
    dub = tmp_path / "dub_1.wav"
    raw.write_bytes(b"raw")
    dub.write_bytes(b"dub")
    assert assemble_final.find_chunk(tmp_path, 1) == str(raw)


def test_find_chunk_falls_back_to_dub(tmp_path: Path) -> None:
    dub = tmp_path / "dub_2.wav"
    dub.write_bytes(b"dub")
    assert assemble_final.find_chunk(tmp_path, 2) == str(dub)


def test_is_noise_only() -> None:
    assert assemble_final.is_noise_only("[Music]")
    assert not assemble_final.is_noise_only("Hello [Music]")
