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
YAML_FILE_NAME = "agent_with_1_clienttool_multiple_outputs.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "3 and 6": {"tool_call": {"name": "sum_product_tool", "args": {"a": 3, "b": 6}}},
        '{"sum": 9.0, "product": 18.0}': '{"sum": 9.0, "product": 18.0}',
    }


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


@pytest.fixture
def agentspec_component_fixture(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(agentspec_configuration)
    return agentspec_component


def test_valid_configuration_agent_with_1_clienttool_multiple_outputs_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Test that the configuration can be loaded successfully."""
    assert agentspec_component_fixture is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_message, expected_sum, expected_product",
    [
        ("3 and 6", "9", "18"),
    ],
)
def test_valid_configuration_agent_with_1_clienttool_multiple_outputs_can_be_executed(
    agentspec_component_fixture,
    user_message,
    expected_sum,
    expected_product,
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
    assert result.tool_requests[0].name == "sum_product_tool"
    assert result.tool_requests[0].args == {"a": 3, "b": 6}

    # Provide input and run
    agentspec_component.append_tool_results(
        ToolResult(
            content={"sum": float(expected_sum), "product": float(expected_product)},
            tool_request_id=result.tool_requests[0].tool_request_id,
        )
    )
    result = agentspec_component.run()

    assert (
        expected_sum in result.agent_messages[-1] and expected_product in result.agent_messages[-1]
    )
