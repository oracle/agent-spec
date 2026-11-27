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
YAML_FILE_NAME = "agent_with_clienttools_and_servertools.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "31+61": {"tool_call": {"name": "sum_tool", "args": {"a": 31, "b": 61}}},
        '{"result": 92.0}': '{"result": 92.0}',
        "61-41": {"tool_call": {"name": "subtract_tool", "args": {"a": 61, "b": 41}}},
        '{"result": 20.0}': '{"result": 20.0}',
        "6*5": {"tool_call": {"name": "multiply_tool", "args": {"a": 6, "b": 5}}},
        "30": "30",
        "8/2": {"tool_call": {"name": "divide_tool", "args": {"a": 8, "b": 2}}},
        "4.0": "4.0",
    }


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


@pytest.fixture
def tool_call_tracker():
    """Provides fresh tracking and tools for each test."""
    # Track if multiply_tool and divide_tool were called
    called = {"multiply_tool": False, "divide_tool": False}

    def multiply_tool(a, b):
        called["multiply_tool"] = True
        return a * b

    def divide_tool(a, b):
        called["divide_tool"] = True
        return a / b

    return called, {"multiply_tool": multiply_tool, "divide_tool": divide_tool}


@pytest.fixture
def agentspec_component_fixture(
    load_agentspec_config: AgentSpecConfigLoaderType, tool_call_tracker
):
    called, tool_registry = tool_call_tracker
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(
        agentspec_configuration, tool_registry=tool_registry
    )
    return agentspec_component, called


def interact_with_agent(agentspec_component, user_message):
    agentspec_component.start()
    agentspec_component.append_user_message(user_message=user_message)
    return agentspec_component.run()


def test_valid_configuration_agent_with_clienttools_and_servertools_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Test that the configuration can be loaded successfully."""
    agentspec_component, _ = agentspec_component_fixture
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_message, expected_llm_output, tool_name, tool_arguments",
    [
        ("31+61", "92", "sum_tool", {"a": 31, "b": 61}),
        ("61-41", "20", "subtract_tool", {"a": 61, "b": 41}),
    ],
)
def test_valid_configuration_agent_with_clienttools_and_servertools_can_execute_clienttools(
    agentspec_component_fixture,
    user_message,
    expected_llm_output,
    tool_name,
    tool_arguments,
    local_deterministic_llm_server,
):
    # Unpack agentspec_component and called dict
    agentspec_component, called = agentspec_component_fixture

    # Begin message interaction
    result = interact_with_agent(agentspec_component, user_message)

    assert hasattr(
        result, "tool_requests"
    ), "Returned result does not have the expected 'tool_requests' attribute"
    assert result.tool_requests[0].name == tool_name
    assert result.tool_requests[0].args == tool_arguments

    # Provide tool result and run again
    agentspec_component.append_tool_results(
        ToolResult(
            content={"result": float(expected_llm_output)},
            tool_request_id=result.tool_requests[0].tool_request_id,
        )
    )
    result = agentspec_component.run()

    # Servertools should not be called
    assert not called["multiply_tool"], "multiply_tool should not be called."
    assert not called["divide_tool"], "divide_tool should not be called."

    # Check output result
    assert expected_llm_output in result.agent_messages[-1]


@pytest.mark.parametrize(
    "user_message, expected_llm_output, expected_servertool",
    [
        ("6*5", "30", "multiply_tool"),
        ("8/2", "4", "divide_tool"),
    ],
)
def test_valid_configuration_agent_with_clienttools_and_servertools_can_execute_servertools(
    agentspec_component_fixture,
    user_message,
    expected_llm_output,
    expected_servertool,
    local_deterministic_llm_server,
):
    # Unpack agentspec_component and called dict
    agentspec_component, called = agentspec_component_fixture
    result = interact_with_agent(agentspec_component, user_message)

    # Check if expected tool was called
    assert called[expected_servertool] is True, f"{expected_servertool} was not called as expected."

    # Check output result
    assert expected_llm_output in result.agent_messages[-1]
