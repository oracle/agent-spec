# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
from pathlib import Path

import pytest
from agentspec_cts_sdk import AgentSpecRunnableComponent

from ...conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "agent_with_2_tools.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "3x6": {"tool_call": {"name": "multiplication_tool", "args": {"a": 3, "b": 6}}},
        "3*3": {"tool_call": {"name": "multiplication_tool", "args": {"a": 3, "b": 3}}},
        "3+3": {"tool_call": {"name": "summation_tool", "args": {"a": 3, "b": 3}}},
        "2+1": {"tool_call": {"name": "summation_tool", "args": {"a": 2, "b": 1}}},
    }


# Track if multiplication_tool and summation_tool were called
multiplication_tool_called = False
summation_tool_called = False


def multiplication_tool(a, b):
    global multiplication_tool_called
    multiplication_tool_called = True
    return {"product": a * b}


def summation_tool(a, b):
    global summation_tool_called
    summation_tool_called = True
    return {"sum": a + b}


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> AgentSpecRunnableComponent:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    tool_registry = {
        "multiplication_tool": multiplication_tool,
        "summation_tool": summation_tool,
    }
    component = load_agentspec_config(agentspec_configuration, tool_registry=tool_registry)
    return component


def test_valid_configuration_agent_with_2_tools_can_be_loaded(agentspec_component) -> None:
    assert agentspec_component is not None, "Valid file, should be loaded"


@pytest.mark.parametrize(
    "user_message, expected_llm_output, tool",
    [
        ("3x6", "18", "multiplication_tool"),
        ("3*3", "9", "multiplication_tool"),
        ("3+3", "6", "summation_tool"),
        ("2+1", "3", "summation_tool"),
    ],
)
def test_agent_with_2_tools_can_be_executed(
    agentspec_component, user_message, expected_llm_output, tool, local_deterministic_llm_server
) -> None:
    global multiplication_tool_called, summation_tool_called
    multiplication_tool_called = False
    summation_tool_called = False

    agentspec_component.start()
    result = agentspec_component.run()
    agentspec_component.append_user_message(user_message=user_message)
    result = agentspec_component.run()

    # Assert expected tool was called
    if tool == "multiplication_tool":
        assert multiplication_tool_called is True, f"The tool {tool} was not called as expected."
    elif tool == "summation_tool":
        assert summation_tool_called is True, f"The tool {tool} was not called as expected."

    if hasattr(result, "outputs"):
        assert (
            expected_llm_output in result.outputs["llm_output"]
        ), f"Expected {expected_llm_output} for {user_message}"
    elif hasattr(result, "agent_messages"):
        assert expected_llm_output in result.agent_messages[-1]
    else:
        raise AssertionError(f"Test did not return expected output message. Got: {result}")
