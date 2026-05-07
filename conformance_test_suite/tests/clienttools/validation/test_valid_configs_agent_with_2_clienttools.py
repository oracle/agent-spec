# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from ...conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "agent_with_2_clienttools.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "31+61": {"tool_call": {"name": "sum_tool", "args": {"a": 31, "b": 61}}},
        '{"result": 92.0}': '{"result": 92.0}',
        "61-41": {"tool_call": {"name": "subtract_tool", "args": {"a": 61, "b": 41}}},
        '{"result": 20.0}': '{"result": 20.0}',
    }


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


@pytest.fixture
def agentspec_component_fixture(load_agentspec_config: AgentSpecConfigLoaderType) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(agentspec_configuration)
    return agentspec_component


def test_valid_configuration_agent_with_2_clienttools_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Test that the configuration can be loaded successfully."""
    assert agentspec_component_fixture is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_message, expected_llm_output, tool_name, tool_arguments",
    [
        ("31+61", "92", "sum_tool", {"a": 31, "b": 61}),
        ("61-41", "20", "subtract_tool", {"a": 61, "b": 41}),
    ],
)
def test_valid_configuration_agent_with_2_clienttools_can_be_executed(
    agentspec_component_fixture,
    user_message,
    expected_llm_output,
    tool_name,
    tool_arguments,
    local_deterministic_llm_server,
) -> None:
    """Test execution, assuming loading already works."""
    agentspec_component = agentspec_component_fixture
    agentspec_component.start()
    agentspec_component.append_user_message(user_message=user_message)
    result = agentspec_component.run()

    assert hasattr(
        result, "tool_requests"
    ), "Returned result does not have the expected 'tool_requests' attribute"
    assert result.tool_requests[0].name == tool_name
    assert result.tool_requests[0].args == tool_arguments

    # Provide input
    agentspec_component.append_tool_results(
        ToolResult(
            content={"result": float(expected_llm_output)},
            tool_request_id=result.tool_requests[0].tool_request_id,
        )
    )
    result = agentspec_component.run()

    assert expected_llm_output in result.agent_messages[-1]
