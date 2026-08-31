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
YAML_FILE_NAME = "parallel_agentnodes_with_tools.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "Bob": {"tool_call": {"name": "search_person_info_tool", "args": {"query": "Bob"}}},
        'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_info_tool", "description": "This tool runs a web search with the given query and returns the number of employees", "parameters": {"type": "object", "properties": {"query": {"type": "string", "title": "query", "default": ""}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_number_employees_info_results": {"type": "array", "items": {"type": "string"}, "title": "search_number_employees_info_results", "default": ["name", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: Bob results are retrieved in the form [name, number_employees]. if user not in DB, tool returns Unknown for number_employees. Do not attempt to answer yourself—simply return the tool response exactly as it is.': {
            "tool_call": {"name": "search_number_employees_info_tool", "args": {"query": "Bob"}}
        },
        "Samir": {"tool_call": {"name": "search_person_info_tool", "args": {"query": "Samir"}}},
        'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_info_tool", "description": "This tool runs a web search with the given query and returns the number of employees", "parameters": {"type": "object", "properties": {"query": {"type": "string", "title": "query", "default": ""}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_number_employees_info_results": {"type": "array", "items": {"type": "string"}, "title": "search_number_employees_info_results", "default": ["name", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: Samir results are retrieved in the form [name, number_employees]. if user not in DB, tool returns Unknown for number_employees. Do not attempt to answer yourself—simply return the tool response exactly as it is.': {
            "tool_call": {"name": "search_number_employees_info_tool", "args": {"query": "Samir"}}
        },
        "Mark": {"tool_call": {"name": "search_person_info_tool", "args": {"query": "Mark"}}},
        'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_info_tool", "description": "This tool runs a web search with the given query and returns the number of employees", "parameters": {"type": "object", "properties": {"query": {"type": "string", "title": "query", "default": ""}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_number_employees_info_results": {"type": "array", "items": {"type": "string"}, "title": "search_number_employees_info_results", "default": ["name", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: Mark results are retrieved in the form [name, number_employees]. if user not in DB, tool returns Unknown for number_employees. Do not attempt to answer yourself—simply return the tool response exactly as it is.': {
            "tool_call": {"name": "search_number_employees_info_tool", "args": {"query": "Mark"}}
        },
    }


# Track if tools were called
search_person_tool_called = False
search_number_employees_tool_called = False


def get_person_info(query):
    global search_person_tool_called
    search_person_tool_called = True
    people_info = {
        "Bob": ["Bob", "No", "USA"],
        "Samir": ["Samir", "Yes", "Morocco"],
    }
    return people_info.get(query, [query, "Unknown", "Unknown"])


def get_number_employees_info(query):
    global search_number_employees_tool_called
    search_number_employees_tool_called = True
    people_info = {
        "Bob": ["Bob", "1000"],
        "Samir": ["Samir", "3000"],
    }
    return people_info.get(query, [query, "Unknown"])


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    tool_registry = {
        "search_person_info_tool": get_person_info,
        "search_number_employees_info_tool": get_number_employees_info,
    }
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    component = load_agentspec_config(agentspec_configuration, tool_registry=tool_registry)
    return component


def test_valid_configuration_parallel_agentnodes_with_tools_can_be_loaded(
    agentspec_component,
) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "query, expected_search_person_info_results, expected_search_number_employees_info_results",
    [
        ("Bob", ["Bob", "No", "USA"], ["Bob", "1000"]),
        ("Samir", ["Samir", "Yes", "Morocco"], ["Samir", "3000"]),
        ("Mark", ["Mark", "Unknown", "Unknown"], ["Mark", "Unknown"]),
    ],
)
def test_parallel_agentnodes_with_tools_can_be_executed(
    agentspec_component,
    query,
    expected_search_person_info_results,
    expected_search_number_employees_info_results,
    local_deterministic_llm_server,
) -> None:
    global search_person_tool_called, search_number_employees_tool_called
    search_person_tool_called = False
    search_number_employees_tool_called = False

    agentspec_component.start({"query": query})
    agentspec_component.append_user_message(user_message=query)
    result = agentspec_component.run()

    # Assert tools were called
    assert (
        search_person_tool_called is True
    ), "The tool search_person_tool was not called as expected."
    assert (
        search_number_employees_tool_called is True
    ), "The tool search_number_employees_tool was not called as expected."

    assert (
        result.outputs["search_person_info_results"] == expected_search_person_info_results
        and result.outputs["search_number_employees_info_results"]
        == expected_search_number_employees_info_results
    ), f"Expected {expected_search_person_info_results} and {expected_search_number_employees_info_results} for {query}"
