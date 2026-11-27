# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from ...conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "agent_with_2_tools_confirmation.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "3x6": {"tool_call": {"name": "multiplication_tool", "args": {"a": 3, "b": 6}}},
        "3*3": {"tool_call": {"name": "multiplication_tool", "args": {"a": 3, "b": 3}}},
        "3+3": {"tool_call": {"name": "summation_tool", "args": {"a": 3, "b": 3}}},
        "2+1": {"tool_call": {"name": "summation_tool", "args": {"a": 2, "b": 1}}},
    }


def _create_tools_with_spy(spy: Mock):
    def multiplication_tool(a, b):
        spy("product", a, b)
        return {"product": a * b}

    def summation_tool(a, b):
        spy("sum", a, b)
        return {"sum": a + b}

    return multiplication_tool, summation_tool


@pytest.fixture
def tool_calling_spy():
    return Mock()


@pytest.fixture
def agentspec_component(load_agentspec_config: AgentSpecConfigLoaderType, tool_calling_spy) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    multiplication_tool, summation_tool = _create_tools_with_spy(tool_calling_spy)
    tool_registry = {
        "multiplication_tool": multiplication_tool,
        "summation_tool": summation_tool,
    }
    component = load_agentspec_config(agentspec_configuration, tool_registry=tool_registry)
    return component


@pytest.mark.parametrize(
    "user_message, expected_llm_output, tool",
    [
        ("3x6", "18", "multiplication_tool"),
        ("3*3", "9", "multiplication_tool"),
        ("3+3", "6", "summation_tool"),
        ("2+1", "3", "summation_tool"),
    ],
)
def test_agent_with_2_tools_can_be_executed_with_confirmation(
    agentspec_component,
    user_message,
    expected_llm_output,
    tool,
    local_deterministic_llm_server,
    tool_calling_spy,
) -> None:
    agentspec_component.start()
    _ = agentspec_component.run()
    agentspec_component.append_user_message(user_message=user_message)
    result = agentspec_component.run()

    assert hasattr(
        result, "tool_requests"
    ), "Expected result to have attribute 'tool_requests' for Tool Confirmation"
    assert len(result.tool_requests) == 1

    # No tool call should occur before user confirmation
    tool_calling_spy.assert_not_called()

    # Accept the confirmation and then expect the tool to be executed exactly once
    requested_tool = result.tool_requests[0]
    agentspec_component.confirm_or_reject_tool_confirmation(requested_tool, decision="accept")
    result = agentspec_component.run()

    # Validate expected tool invocation via spy
    expected_label = "product" if tool == "multiplication_tool" else "sum"
    tool_calling_spy.assert_called_once_with(
        expected_label, requested_tool.args["a"], requested_tool.args["b"]
    )

    # Validate final answer formatting/content
    if hasattr(result, "outputs"):
        assert (
            expected_llm_output in result.outputs["llm_output"]
        ), f"Expected {expected_llm_output} for {user_message}"
    elif hasattr(result, "agent_messages"):
        assert expected_llm_output in result.agent_messages[-1]
    else:
        raise AssertionError(f"Test did not return expected output message. Got: {result}")


@pytest.mark.parametrize(
    "user_message, tool",
    [
        ("3x6", "multiplication_tool"),
        ("3*3", "multiplication_tool"),
        ("3+3", "summation_tool"),
        ("2+1", "summation_tool"),
    ],
)
def test_agent_with_2_tools_confirmation_reject_flow(
    agentspec_component, user_message, tool, local_deterministic_llm_server, tool_calling_spy
) -> None:
    agentspec_component.start()
    _ = agentspec_component.run()
    agentspec_component.append_user_message(user_message=user_message)
    result = agentspec_component.run()

    # The agent must propose a tool call and request confirmation
    assert hasattr(
        result, "tool_requests"
    ), "Expected result to have attribute 'tool_requests' for Tool Confirmation"
    assert len(result.tool_requests) == 1

    # No tool call before confirmation
    tool_calling_spy.assert_not_called()

    # Reject the confirmation
    agentspec_component.confirm_or_reject_tool_confirmation(
        result.tool_requests[0], decision="reject"
    )
    result = agentspec_component.run()

    # Tool must not be executed after rejection
    tool_calling_spy.assert_not_called()

    # After rejecting, the agent must not proceed with executing the server tool.
    # If tool_requests attribute exists, it must be empty; otherwise, the agent should continue the conversation.
    if hasattr(result, "tool_requests"):
        assert (
            not result.tool_requests
        ), "Agent must not request ServerTool execution after rejection"
    else:
        assert hasattr(result, "agent_messages") or hasattr(
            result, "outputs"
        ), "Agent should continue conversation after rejection (agent_messages or outputs expected)"
