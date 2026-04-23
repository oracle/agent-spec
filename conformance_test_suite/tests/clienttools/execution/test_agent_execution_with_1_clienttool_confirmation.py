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
YAML_FILE_NAME = "agent_with_1_clienttool_confirmation.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "13+16": {"tool_call": {"name": "sum_tool", "args": {"a": 13, "b": 16}}},
        '{"result": 29.0}': '{"result": 29.0}',
    }


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


@pytest.fixture
def agentspec_component_fixture(load_agentspec_config: AgentSpecConfigLoaderType) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(agentspec_configuration, None)
    return agentspec_component


@pytest.mark.parametrize(
    "user_message, expected_llm_output",
    [
        ("13+16", "29"),
    ],
)
def test_agent_with_1_clienttool_confirmation_accept_flow(
    agentspec_component_fixture, user_message, expected_llm_output, local_deterministic_llm_server
) -> None:
    """Confirmation required for ClientTool: expect confirmation status first, then tool request after accept, then provide tool result and finish."""
    agentspec_component = agentspec_component_fixture
    agentspec_component.start()
    agentspec_component.append_user_message(user_message=user_message)
    result = agentspec_component.run()

    # First, agent must ask for confirmation (exposes intended tool call)
    assert hasattr(
        result, "tool_requests"
    ), "Expected result to have attribute 'tool_requests' for Tool Confirmation"
    assert len(result.tool_requests) == 1
    assert result.tool_requests[0].name == "sum_tool"
    assert result.tool_requests[0].args == {"a": 13, "b": 16}

    # Accept the confirmation
    agentspec_component.confirm_or_reject_tool_confirmation(
        result.tool_requests[0], decision="accept"
    )
    result = agentspec_component.run()

    # After accepting, agent should now request execution of the client tool
    assert hasattr(
        result, "tool_requests"
    ), "Expected a ToolRequest after accepting confirmation for a ClientTool"
    assert len(result.tool_requests) == 1
    assert result.tool_requests[0].name == "sum_tool"
    assert result.tool_requests[0].args == {"a": 13, "b": 16}

    # Provide tool result from the client side and run to completion
    agentspec_component.append_tool_results(
        ToolResult(
            content={"result": float(expected_llm_output)},
            tool_request_id=result.tool_requests[0].tool_request_id,
        )
    )
    result = agentspec_component.run()

    # Validate final answer formatting
    if hasattr(result, "outputs"):
        assert (
            expected_llm_output in result.outputs["llm_output"]
        ), f"Expected {expected_llm_output} for {user_message}"
    elif hasattr(result, "agent_messages"):
        assert expected_llm_output in result.agent_messages[-1]
    else:
        raise AssertionError(f"Test did not return expected output message. Got: {result}")


@pytest.mark.parametrize(
    "user_message",
    [
        ("13+16"),
    ],
)
def test_agent_with_1_clienttool_confirmation_reject_flow(
    agentspec_component_fixture, user_message, local_deterministic_llm_server
) -> None:
    """On reject, the agent must NOT execute the tool and should continue the conversation without issuing the tool request."""
    agentspec_component = agentspec_component_fixture
    agentspec_component.start()
    agentspec_component.append_user_message(user_message=user_message)
    result = agentspec_component.run()

    # First, the agent proposes a tool call and requests confirmation
    assert hasattr(
        result, "tool_requests"
    ), "Expected result to have attribute 'tool_requests' for Tool Confirmation"
    assert len(result.tool_requests) == 1
    assert result.tool_requests[0].name == "sum_tool"
    assert result.tool_requests[0].args == {"a": 13, "b": 16}

    # Reject the confirmation
    agentspec_component.confirm_or_reject_tool_confirmation(
        result.tool_requests[0], decision="reject"
    )
    result = agentspec_component.run()

    # After rejecting, the agent must not proceed with executing or requesting the client tool.
    # We accept either a user-message request or another assistant turn, but no ToolRequest should be present to execute the tool.
    if hasattr(result, "tool_requests"):
        # If the attribute exists, it must be empty or None after rejection
        assert (
            not result.tool_requests
        ), "Agent must not request ClientTool execution after rejection"
    else:
        # Preferably the agent continues the conversation (e.g., asks the user something or provides guidance)
        assert hasattr(
            result, "agent_messages"
        ), "Agent should continue conversation after rejection, but no agent messages were found"
