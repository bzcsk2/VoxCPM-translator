from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class StageContract:
    id: int
    name: str
    command: tuple[str, ...]
    output_keys: tuple[str, ...]
    description: str
    auto_resumable: bool = True
    optional: bool = False

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["command"] = list(self.command)
        payload["output_keys"] = list(self.output_keys)
        return payload


STAGE_CONTRACTS: tuple[StageContract, ...] = (
    StageContract(
        id=0,
        name="extract-audio",
        command=(sys.executable, str(SCRIPT_DIR / "00_extract_audio.py")),
        output_keys=("paths.input_wav",),
        description="Extract WAV audio from the configured source video.",
    ),
    StageContract(
        id=1,
        name="process-vocals",
        command=("bash", str(SCRIPT_DIR / "01_process_vocals.sh")),
        output_keys=("paths.vocal_source_for_asr", "paths.instrumental_audio"),
        description="Separate vocals and instrumental audio for ASR and final assembly.",
    ),
    StageContract(
        id=2,
        name="transcribe",
        command=(sys.executable, str(SCRIPT_DIR / "02_transcribe_vibe.py")),
        output_keys=("paths.asr_json",),
        description="Run VibeVoice-ASR and write timestamped Chinese transcript JSON.",
    ),
    StageContract(
        id=3,
        name="refine-translate",
        command=(sys.executable, str(SCRIPT_DIR / "03_refine_and_translate.py")),
        output_keys=("paths.refined_json",),
        description="Correct ASR text and translate each segment for dubbing.",
    ),
    StageContract(
        id=4,
        name="verify",
        command=(sys.executable, str(SCRIPT_DIR / "04_verify_translation.py")),
        output_keys=(),
        description="Verify ASR/refined JSON alignment and required refined fields.",
        auto_resumable=False,
    ),
    StageContract(
        id=5,
        name="generate-audio-chunks",
        command=(sys.executable, str(SCRIPT_DIR / "05_generate_audio_chunks.py")),
        output_keys=("paths.dub_chunk_dir",),
        description="Generate or validate one WAV chunk per spoken segment.",
    ),
    StageContract(
        id=6,
        name="assemble",
        command=(sys.executable, str(SCRIPT_DIR / "06_assemble_final.py")),
        output_keys=("paths.final_video",),
        description="Overlay generated chunks on the instrumental track and mux final video.",
    ),
    StageContract(
        id=7,
        name="latentsync",
        command=(sys.executable, str(SCRIPT_DIR / "07_latentsync_lipsync.py")),
        output_keys=("paths.lipsync_video",),
        description="Optionally run LatentSync mouth-shape synchronization.",
        optional=True,
    ),
    StageContract(
        id=8,
        name="burn-subtitles",
        command=(sys.executable, str(SCRIPT_DIR / "burn_subtitles.py")),
        output_keys=("paths.subtitled_video",),
        description="Optionally burn generated ASS subtitles into the final video.",
        optional=True,
    ),
)


def all_stage_contracts() -> tuple[StageContract, ...]:
    return STAGE_CONTRACTS


def get_stage_contract(stage_id: int) -> StageContract:
    for contract in STAGE_CONTRACTS:
        if contract.id == stage_id:
            return contract
    raise KeyError(f"unknown stage id: {stage_id}")


def selected_stage_contracts(from_stage: int, to_stage: int) -> list[StageContract]:
    return [contract for contract in STAGE_CONTRACTS if from_stage <= contract.id <= to_stage]


def legacy_stage_tuples() -> list[tuple[int, str, list[str]]]:
    """Return the historical run_pipeline.STAGES shape for compatibility."""
    return [(contract.id, contract.name, list(contract.command)) for contract in STAGE_CONTRACTS]


def stage_output_key_map() -> dict[int, list[str]]:
    return {contract.id: list(contract.output_keys) for contract in STAGE_CONTRACTS}


def validate_stage_contracts(contracts: tuple[StageContract, ...] = STAGE_CONTRACTS) -> list[str]:
    errors: list[str] = []
    ids = [contract.id for contract in contracts]
    names = [contract.name for contract in contracts]

    if ids != sorted(ids):
        errors.append("stage IDs must be sorted")
    if len(ids) != len(set(ids)):
        errors.append("stage IDs must be unique")
    if len(names) != len(set(names)):
        errors.append("stage names must be unique")

    for contract in contracts:
        if contract.id < 0:
            errors.append(f"stage {contract.name}: id must be non-negative")
        if not contract.name:
            errors.append(f"stage {contract.id}: name is empty")
        if not contract.command:
            errors.append(f"stage {contract.name}: command is empty")
        if contract.auto_resumable and not contract.output_keys:
            errors.append(f"stage {contract.name}: auto-resumable stages need output keys")

    return errors
