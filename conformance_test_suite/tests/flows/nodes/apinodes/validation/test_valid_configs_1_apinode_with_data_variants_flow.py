# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path
from typing import Any, Dict

import pytest

from .....conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"

CASES = [
    {
        "name": "nested_any",
        "yaml": "1_apinode_with_data_nested_any_flow.yaml",
        "inputs": {
            "city": "Agadir",
            "lat": "30.4",
            "lon": "-9.6",
            "user": "alice",
            "suffix": "world",
            "bin_suffix": "blob",
        },
        "output_key": "weather",
        "expected_contains": "sunny in Agadir",
    },
    {
        "name": "top_level_city",
        "yaml": "1_apinode_with_data_top_json_flow.yaml",
        "inputs": {
            "city": "Agadir",
        },
        "output_key": "weather",
        "expected_contains": "sunny in Agadir",
    },
    {
        "name": "json_array",
        "yaml": "1_apinode_with_data_json_array_flow.yaml",
        "inputs": {
            "city": "Agadir",
            "temp": "25",
            "user": "alice",
        },
        "output_key": "processed_city",
        "expected_equals": "Agadir",
    },
    {
        "name": "raw_body",
        "yaml": "1_apinode_with_data_raw_flow.yaml",
        "inputs": {
            "city": "Agadir",
            "note": "urgent",
        },
        "output_key": "city",
        "expected_equals": "Agadir",
    },
    {
        "name": "form_encoded",
        "yaml": "1_apinode_with_data_form_flow.yaml",
        "inputs": {
            "city": "Agadir",
            "note": "urgent",
        },
        "output_key": "weather",
        "expected_contains": "sunny in Agadir",
    },
]


@pytest.fixture
def case(request) -> Dict[str, Any]:
    return request.param


@pytest.fixture
def agentspec_component_fixture(case, load_agentspec_config: AgentSpecConfigLoaderType) -> Any:
    yaml_path = CONFIG_DIR / case["yaml"]
    with open(yaml_path) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(agentspec_configuration, None)
    return agentspec_component


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES], indirect=True)
def test_valid_configuration_1_apinode_with_data_variant_flow_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Verify that each ApiNode flow configuration for various data formats can be loaded successfully."""
    assert agentspec_component_fixture is not None, "valid file, should be loaded"


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES], indirect=True)
def test_valid_configuration_1_apinode_with_data_variant_flow_can_be_executed(
    agentspec_component_fixture,
    case,
    local_common_server,
) -> None:
    """Execute the ApiNode flow for each data variant and validate outputs."""
    agentspec_component = agentspec_component_fixture
    agentspec_component.start(case["inputs"])
    result = agentspec_component.run()

    out_key = case["output_key"]
    assert out_key in result.outputs, f"Expected output key '{out_key}' to be present"

    if "expected_equals" in case:
        assert (
            result.outputs[out_key] == case["expected_equals"]
        ), f"Expected {case['expected_equals']} for key '{out_key}' in case '{case['name']}'"
    else:
        assert (
            case["expected_contains"] in result.outputs[out_key]
        ), f"Expected '{case['expected_contains']}' to be contained in output '{out_key}' for case '{case['name']}'"
