# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path
from typing import Any, Dict

import pytest

from ...conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"


# Parametrized case description covering different RemoteTool data formats
CASES = [
    {
        "name": "nested_any",
        "yaml": "agent_with_1_remotetool_nested_any.yaml",
        "user_message": "Agadir forecast",
        "expected_substr": "sunny in Agadir",
        "mapping": {
            "Agadir forecast": {
                "tool_call": {
                    "name": "forecast_weather",
                    "args": {
                        "city": "Agadir",
                        "lat": "30.4",
                        "lon": "-9.6",
                        "user": "alice",
                        "suffix": "world",
                        "bin_suffix": "blob",
                    },
                }
            },
        },
    },
    {
        "name": "top_level_city",
        "yaml": "agent_with_1_remotetool_top_level_city.yaml",
        "user_message": "Agadir simple",
        "expected_substr": "sunny in Agadir",
        "mapping": {
            "Agadir simple": {
                "tool_call": {
                    "name": "forecast_weather_simple",
                    "args": {
                        "city": "Agadir",
                    },
                }
            }
        },
    },
    {
        "name": "json_array",
        "yaml": "agent_with_1_remotetool_json_array.yaml",
        "user_message": "Agadir array",
        "expected_substr": "Agadir",
        "mapping": {
            "Agadir array": {
                "tool_call": {
                    "name": "process_array",
                    "args": {
                        "city": "Agadir",
                        "temp": "25",
                        "user": "alice",
                    },
                }
            }
        },
    },
    {
        "name": "raw_body",
        "yaml": "agent_with_1_remotetool_raw.yaml",
        "user_message": "Agadir raw",
        "expected_substr": "Agadir",
        "mapping": {
            "Agadir raw": {
                "tool_call": {
                    "name": "send_raw",
                    "args": {
                        "city": "Agadir",
                        "note": "urgent",
                        "user": "alice",
                    },
                }
            }
        },
    },
    {
        "name": "form_encoded",
        "yaml": "agent_with_1_remotetool_form.yaml",
        "user_message": "Agadir form",
        "expected_substr": "sunny in Agadir",
        "mapping": {
            "Agadir form": {
                "tool_call": {
                    "name": "forecast_weather_form",
                    "args": {
                        "city": "Agadir",
                        "note": "urgent",
                        "user": "alice",
                    },
                }
            }
        },
    },
]


@pytest.fixture
def case(request) -> Dict[str, Any]:
    return request.param


@pytest.fixture
def prompt_to_result_mappings(case) -> Dict[str, Any]:
    # Each case provides the mapping driving the deterministic LLM server
    return case["mapping"]


@pytest.fixture
def agentspec_component_fixture(case, load_agentspec_config: AgentSpecConfigLoaderType) -> Any:
    yaml_path = CONFIG_DIR / case["yaml"]
    with open(yaml_path) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(agentspec_configuration, None)
    return agentspec_component


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES], indirect=True)
def test_valid_configuration_agent_with_1_remotetool_variant_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Verify that each configuration for various data formats can be loaded successfully."""
    assert agentspec_component_fixture is not None, "valid file, should be loaded"


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES], indirect=True)
def test_valid_configuration_agent_with_1_remotetool_variant_can_be_executed(
    agentspec_component_fixture,
    case,
    local_deterministic_llm_server,
    local_common_server,
) -> None:
    """
    Execute the RemoteTool for each data variant and validate final answer reduction.
    """
    agentspec_component = agentspec_component_fixture
    agentspec_component.start()
    agentspec_component.append_user_message(user_message=case["user_message"])
    result = agentspec_component.run()

    assert case["expected_substr"] in result.agent_messages[-1]
