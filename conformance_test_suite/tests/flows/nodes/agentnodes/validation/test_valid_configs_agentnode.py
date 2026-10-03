# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
from pathlib import Path
from typing import Any

import pytest

from .....conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "simple_agentnode_with_tool.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "Alice": {"tool_call": {"name": "search_tool", "args": {"query": "Alice"}}},
        "Karim": {"tool_call": {"name": "search_tool", "args": {"query": "Karim"}}},
        "Khalid": {"tool_call": {"name": "search_tool", "args": {"query": "Khalid"}}},
    }


# Track if search_tool was called
search_tool_called = False


def get_person_info(query):
    global search_tool_called
    search_tool_called = True
    people_info = {
        "Alice": ["Alice", "No", "USA"],
        "Karim": ["Karim", "Yes", "Morocco"],
    }
    return people_info.get(query, [query, "Unknown", "Unknown"])


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    tool_registry = {"search_tool": get_person_info}
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    component = load_agentspec_config(agentspec_configuration, tool_registry=tool_registry)
    return component


def test_valid_configuration_agentnode_with_tool_can_be_loaded(agentspec_component) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "query, expected_search_results",
    [
        ("Alice", ["Alice", "No", "USA"]),
        ("Karim", ["Karim", "Yes", "Morocco"]),
        ("Khalid", ["Khalid", "Unknown", "Unknown"]),
    ],
)
def test_agentnode_with_tool_can_be_executed(
    agentspec_component, query, expected_search_results, local_deterministic_llm_server
) -> None:
    global search_tool_called
    search_tool_called = False  # Reset before test

    agentspec_component.start()
    agentspec_component.append_user_message(user_message=query)
    result = agentspec_component.run()

    # Assert search_tool was called
    assert search_tool_called is True, "The tool was not called as expected."
    if hasattr(result, "outputs"):
        assert result.outputs == {
            "search_results": expected_search_results
        }, f"Expected {expected_search_results} for {query}"
    elif hasattr(result, "agent_messages"):
        agent_message_raw = result.agent_messages[-1]
        for val in expected_search_results:
            assert (
                str(val) in agent_message_raw
            ), f"Expected value {val} not found in agent message ({agent_message_raw}) for {query}"
    else:
        raise AssertionError(f"Test did not return expected output or message. Got: {result}")
