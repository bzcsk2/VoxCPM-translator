from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from common import get_nested

ERROR = "ERROR"
WARN = "WARN"
INFO = "INFO"

Severity = Literal["ERROR", "WARN", "INFO"]
ExpectedType = Literal["str", "int", "float", "bool", "list", "dict"]


@dataclass(frozen=True)
class SchemaIssue:
    level: Severity
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class FieldSpec:
    path: str
    expected_type: ExpectedType
    required: bool = True
    choices: tuple[Any, ...] = ()
    min_value: float | None = None
    max_value: float | None = None
    allow_empty: bool = False
    description: str = ""


SUPPORTED_TTS_BACKENDS = ("manual", "custom_command", "voxcpm")
SUPPORTED_MISSING_CHUNK_POLICIES = ("error", "warn", "skip")
SUPPORTED_ASSEMBLY_BACKENDS = ("ffmpeg",)
SUPPORTED_ASR_DTYPES = ("float16", "bfloat16", "float32")

CONFIG_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("paths.input_video", "str"),
    FieldSpec("paths.input_wav", "str"),
    FieldSpec("paths.output_dir", "str"),
    FieldSpec("paths.vocal_source_for_asr", "str"),
    FieldSpec("paths.instrumental_audio", "str"),
    FieldSpec("paths.asr_json", "str"),
    FieldSpec("paths.refined_json", "str"),
    FieldSpec("paths.dub_chunk_dir", "str"),
    FieldSpec("paths.temp_mixed_wav", "str"),
    FieldSpec("paths.final_video", "str"),
    FieldSpec("paths.lipsync_video", "str", required=False),
    FieldSpec("paths.subtitle_ass", "str", required=False),
    FieldSpec("paths.subtitled_video", "str", required=False),
    FieldSpec("models.audio_separator_model", "str"),
    FieldSpec("models.audio_separator_model_dir", "str"),
    FieldSpec("models.vibevoice_repo", "str"),
    FieldSpec("models.vibevoice_asr_path", "str"),
    FieldSpec("models.qwen_asr_path", "str"),
    FieldSpec("models.voxcpm_model_path", "str", required=False),
    FieldSpec("models.latentsync_dir", "str", required=False),
    FieldSpec("llm.api_base", "str"),
    FieldSpec("llm.model", "str"),
    FieldSpec("llm.api_key_env", "str", required=False),
    FieldSpec("llm.temperature", "float", required=False, min_value=0),
    FieldSpec("llm.max_tokens", "int", required=False, min_value=1),
    FieldSpec("llm.batch_size", "int", required=False, min_value=1),
    FieldSpec("llm.split_failed_batches", "bool", required=False),
    FieldSpec("tts.backend", "str", choices=SUPPORTED_TTS_BACKENDS),
    FieldSpec("tts.overwrite", "bool", required=False),
    FieldSpec("tts.custom_command", "str", required=False, allow_empty=True),
    FieldSpec("tts.voxcpm_adapter", "str", required=False, allow_empty=True),
    FieldSpec("tts.voxcpm_adapter_function", "str", required=False),
    FieldSpec("tts.cfg_value", "float", required=False, min_value=0),
    FieldSpec("tts.inference_timesteps", "int", required=False, min_value=1),
    FieldSpec("tts.voice_prompt_prefix", "str", required=False),
    FieldSpec("runtime.asr_device", "str", required=False),
    FieldSpec("runtime.asr_dtype", "str", required=False, choices=SUPPORTED_ASR_DTYPES),
    FieldSpec("runtime.tts_devices", "list", required=False),
    FieldSpec("audio_extract.sample_rate", "int", required=False, min_value=1),
    FieldSpec("audio_extract.channels", "int", required=False, min_value=1),
    FieldSpec("vocal_extraction.output_format", "str", required=False),
    FieldSpec("vocal_extraction.mdx_overlap", "float", required=False, min_value=0, max_value=1),
    FieldSpec("vocal_extraction.enable_denoise", "bool", required=False),
    FieldSpec("vocal_extraction.noise_gate_threshold", "float", required=False, min_value=0),
    FieldSpec("vocal_extraction.noise_gate_range", "float", required=False, min_value=0),
    FieldSpec("vocal_extraction.noise_gate_attack_ms", "int", required=False, min_value=0),
    FieldSpec("vocal_extraction.noise_gate_release_ms", "int", required=False, min_value=0),
    FieldSpec("vocal_extraction.raw_vocal_name", "str", required=False),
    FieldSpec("vocal_extraction.final_vocal_name", "str", required=False),
    FieldSpec("asr.max_new_tokens", "int", required=False, min_value=1),
    FieldSpec("asr.temperature", "float", required=False, min_value=0),
    FieldSpec("asr.top_p", "float", required=False, min_value=0, max_value=1),
    FieldSpec("asr.repetition_penalty", "float", required=False, min_value=0),
    FieldSpec("asr.context_hint", "str", required=False),
    FieldSpec("assembly.backend", "str", required=False, choices=SUPPORTED_ASSEMBLY_BACKENDS),
    FieldSpec("assembly.min_speed_ratio", "float", required=False, min_value=0.01, max_value=1.0),
    FieldSpec("assembly.audio_bitrate", "str", required=False),
    FieldSpec("assembly.missing_chunk_policy", "str", required=False, choices=SUPPORTED_MISSING_CHUNK_POLICIES),
    FieldSpec("subtitles.font_name", "str", required=False),
    FieldSpec("subtitles.font_size", "float", required=False, min_value=1),
    FieldSpec("subtitles.pos_x", "float", required=False, min_value=0),
    FieldSpec("subtitles.pos_y", "float", required=False, min_value=0),
    FieldSpec("subtitles.color_text", "str", required=False),
    FieldSpec("subtitles.color_outline", "str", required=False),
    FieldSpec("subtitles.outline_size", "float", required=False, min_value=0),
    FieldSpec("subtitles.max_chars_per_line", "int", required=False, min_value=1),
    FieldSpec("subtitles.min_duration_ms", "int", required=False, min_value=1),
)

TYPE_CHECKERS = {
    "str": lambda value: isinstance(value, str),
    "int": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "float": lambda value: isinstance(value, int | float) and not isinstance(value, bool),
    "bool": lambda value: isinstance(value, bool),
    "list": lambda value: isinstance(value, list),
    "dict": lambda value: isinstance(value, dict),
}


def is_missing(value: Any) -> bool:
    return value is None


def is_empty(value: Any) -> bool:
    return isinstance(value, str) and value.strip() == ""


def type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def validate_field(cfg: dict[str, Any], spec: FieldSpec) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    value = get_nested(cfg, spec.path)

    if is_missing(value):
        if spec.required:
            issues.append(SchemaIssue("ERROR", spec.path, "missing required config key"))
        return issues

    if is_empty(value) and not spec.allow_empty:
        level: Severity = "ERROR" if spec.required else "WARN"
        issues.append(SchemaIssue(level, spec.path, "empty string value"))
        return issues

    checker = TYPE_CHECKERS[spec.expected_type]
    if not checker(value):
        issues.append(SchemaIssue("ERROR", spec.path, f"expected {spec.expected_type}, got {type_name(value)}"))
        return issues

    if spec.choices and value not in spec.choices:
        expected = ", ".join(map(str, spec.choices))
        issues.append(SchemaIssue("ERROR", spec.path, f"unsupported value {value!r}; expected one of: {expected}"))

    if isinstance(value, int | float) and not isinstance(value, bool):
        numeric = float(value)
        if spec.min_value is not None and numeric < spec.min_value:
            issues.append(SchemaIssue("ERROR", spec.path, f"value {value!r} is below minimum {spec.min_value}"))
        if spec.max_value is not None and numeric > spec.max_value:
            issues.append(SchemaIssue("ERROR", spec.path, f"value {value!r} is above maximum {spec.max_value}"))

    return issues


def validate_cross_fields(cfg: dict[str, Any]) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    backend = get_nested(cfg, "tts.backend", "manual")

    if backend == "custom_command" and not get_nested(cfg, "tts.custom_command"):
        issues.append(SchemaIssue("ERROR", "tts.custom_command", "required when tts.backend is custom_command"))

    if backend == "voxcpm":
        if not get_nested(cfg, "tts.voxcpm_adapter"):
            issues.append(SchemaIssue("ERROR", "tts.voxcpm_adapter", "required when tts.backend is voxcpm"))
        if not get_nested(cfg, "models.voxcpm_model_path"):
            issues.append(SchemaIssue("ERROR", "models.voxcpm_model_path", "required when tts.backend is voxcpm"))

    tts_devices = get_nested(cfg, "runtime.tts_devices")
    if isinstance(tts_devices, list) and any(not isinstance(item, str) or not item.strip() for item in tts_devices):
        issues.append(SchemaIssue("ERROR", "runtime.tts_devices", "all device entries must be non-empty strings"))

    return issues


def validate_config_schema(cfg: dict[str, Any], specs: tuple[FieldSpec, ...] = CONFIG_FIELD_SPECS) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    if not isinstance(cfg, dict):
        return [SchemaIssue("ERROR", "config", f"expected dict, got {type_name(cfg)}")]

    for spec in specs:
        issues.extend(validate_field(cfg, spec))
    issues.extend(validate_cross_fields(cfg))
    return issues


def has_errors(issues: list[SchemaIssue]) -> bool:
    return any(issue.level == "ERROR" for issue in issues)


def summarize_issues(issues: list[SchemaIssue]) -> dict[str, int]:
    summary = {ERROR: 0, WARN: 0, INFO: 0}
    for issue in issues:
        summary[issue.level] = summary.get(issue.level, 0) + 1
    return summary


def render_issues(issues: list[SchemaIssue], include_summary: bool = True) -> str:
    lines = [f"[{issue.level}] {issue.path}: {issue.message}" for issue in issues]
    if include_summary:
        summary = summarize_issues(issues)
        lines.append(f"[SUMMARY] ERROR={summary.get(ERROR, 0)} WARN={summary.get(WARN, 0)} INFO={summary.get(INFO, 0)}")
    return "\n".join(lines)
