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
YAML_FILE_NAME = "nested_agentnodes_with_tools.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "Jack": {"tool_call": {"name": "search_person_tool", "args": {"query_person": "Jack"}}},
        'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_tool", "description": "This tool runs a web search for the given person_results and adds number of employees. If not found we return Unknown", "parameters": {"type": "object", "properties": {"search_person_results": {"type": "array", "items": {"type": "string"}, "title": "search_person_results", "default": ["name", "CEO", "country"]}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_results": {"type": "array", "items": {"type": "string"}, "title": "search_results", "default": ["name", "CEO", "country", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: [\'Jack\', \'No\', \'USA\'] results are retrieved in the form [name, CEO, country, number_employees] where CEO value is No or Yes. if user not in DB, tool returns Unknown for CEO, country, and number_employees values. Do not attempt to answer yourself—simply return the tool response.': {
            "tool_call": {
                "name": "search_number_employees_tool",
                "args": {"search_person_results": ["Jack", "No", "USA"]},
            }
        },
        "Soufiane": {
            "tool_call": {"name": "search_person_tool", "args": {"query_person": "Soufiane"}}
        },
        'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_tool", "description": "This tool runs a web search for the given person_results and adds number of employees. If not found we return Unknown", "parameters": {"type": "object", "properties": {"search_person_results": {"type": "array", "items": {"type": "string"}, "title": "search_person_results", "default": ["name", "CEO", "country"]}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_results": {"type": "array", "items": {"type": "string"}, "title": "search_results", "default": ["name", "CEO", "country", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: [\'Soufiane\', \'Yes\', \'Morocco\'] results are retrieved in the form [name, CEO, country, number_employees] where CEO value is No or Yes. if user not in DB, tool returns Unknown for CEO, country, and number_employees values. Do not attempt to answer yourself—simply return the tool response.': {
            "tool_call": {
                "name": "search_number_employees_tool",
                "args": {"search_person_results": ["Soufiane", "Yes", "Morocco"]},
            }
        },
        "Haroun": {"tool_call": {"name": "search_person_tool", "args": {"query_person": "Haroun"}}},
        'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_tool", "description": "This tool runs a web search for the given person_results and adds number of employees. If not found we return Unknown", "parameters": {"type": "object", "properties": {"search_person_results": {"type": "array", "items": {"type": "string"}, "title": "search_person_results", "default": ["name", "CEO", "country"]}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_results": {"type": "array", "items": {"type": "string"}, "title": "search_results", "default": ["name", "CEO", "country", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: [\'Haroun\', \'Unknown\', \'Unknown\'] results are retrieved in the form [name, CEO, country, number_employees] where CEO value is No or Yes. if user not in DB, tool returns Unknown for CEO, country, and number_employees values. Do not attempt to answer yourself—simply return the tool response.': {
            "tool_call": {
                "name": "search_number_employees_tool",
                "args": {"search_person_results": ["Haroun", "Unknown", "Unknown"]},
            }
        },
    }


# Track if tools were called
search_person_tool_called = False
search_number_employees_tool_called = False


def get_person_info(query_person):
    global search_person_tool_called
    search_person_tool_called = True
    people_info = {
        "Jack": ["Jack", "No", "USA"],
        "Soufiane": ["Soufiane", "Yes", "Morocco"],
    }
    return people_info.get(query_person, [query_person, "Unknown", "Unknown"])


def get_number_employees_info(search_person_results):
    global search_number_employees_tool_called
    search_number_employees_tool_called = True
    people_info = {
        "Jack": ["Jack", "No", "USA", "1000"],
        "Soufiane": ["Soufiane", "Yes", "Morocco", "3000"],
    }
    return people_info.get(
        search_person_results[0], [search_person_results[0], "Unknown", "Unknown", "Unknown"]
    )


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    tool_registry = {
        "search_person_tool": get_person_info,
        "search_number_employees_tool": get_number_employees_info,
    }
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    component = load_agentspec_config(agentspec_configuration, tool_registry=tool_registry)
    return component


def test_valid_configuration_nested_agentnodes_with_tools_can_be_loaded(
    agentspec_component,
) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "query_person, expected_search_results",
    [
        ("Jack", ["Jack", "No", "USA", "1000"]),
        ("Soufiane", ["Soufiane", "Yes", "Morocco", "3000"]),
        ("Haroun", ["Haroun", "Unknown", "Unknown", "Unknown"]),
    ],
)
def test_nested_agentnodes_with_tools_can_be_executed(
    agentspec_component, query_person, expected_search_results, local_deterministic_llm_server
) -> None:
    global search_person_tool_called, search_number_employees_tool_called
    search_person_tool_called = False
    search_number_employees_tool_called = False

    agentspec_component.start()
    agentspec_component.append_user_message(user_message=query_person)
    result = agentspec_component.run()

    # Assert tools were called
    assert (
        search_person_tool_called is True
    ), "The tool search_person_tool was not called as expected."
    assert (
        search_number_employees_tool_called is True
    ), "The tool search_number_employees_tool was not called as expected."

    if hasattr(result, "outputs"):
        assert (
            result.outputs["search_results"] == expected_search_results
        ), f"Expected {expected_search_results} for {query_person}"
    elif hasattr(result, "agent_messages"):
        assert (
            expected_search_results in result.agent_messages[-1]
        ), f"Expected {expected_search_results} for {query_person}"
    else:
        raise AssertionError(f"Test did not return expected output or message. Got: {result}")
