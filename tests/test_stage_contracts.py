import json

import list_stages
from stage_contracts import (
    STAGE_CONTRACTS,
    get_stage_contract,
    legacy_stage_tuples,
    stage_output_key_map,
    validate_stage_contracts,
)


def test_stage_contracts_are_valid() -> None:
    assert validate_stage_contracts() == []


def test_stage_contract_ids_and_names_are_unique() -> None:
    ids = [contract.id for contract in STAGE_CONTRACTS]
    names = [contract.name for contract in STAGE_CONTRACTS]

    assert ids == list(range(0, 9))
    assert len(names) == len(set(names))


def test_get_stage_contract_returns_expected_stage() -> None:
    contract = get_stage_contract(6)

    assert contract.name == "assemble"
    assert contract.output_keys == ("paths.final_video",)


def test_legacy_stage_tuples_preserve_run_pipeline_shape() -> None:
    stages = legacy_stage_tuples()

    assert stages[0][0] == 0
    assert stages[0][1] == "extract-audio"
    assert isinstance(stages[0][2], list)
    assert stages[1][2][0] == "bash"


def test_stage_output_key_map_matches_contracts() -> None:
    output_map = stage_output_key_map()

    assert output_map[0] == ["paths.input_wav"]
    assert output_map[4] == []
    assert output_map[8] == ["paths.subtitled_video"]


def test_list_stages_renders_markdown_table() -> None:
    rendered = list_stages.render_table()

    assert "| ID | Name | Optional | Auto-resumable | Outputs | Description |" in rendered
    assert "`extract-audio`" in rendered
    assert "`burn-subtitles`" in rendered


def test_stage_contracts_serialize_to_json() -> None:
    payload = [contract.to_dict() for contract in STAGE_CONTRACTS]
    encoded = json.dumps(payload)

    assert "extract-audio" in encoded
    assert "output_keys" in encoded
