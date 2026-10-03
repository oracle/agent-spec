# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import ast
import asyncio
import json
import logging
import re
import uuid
from asyncio import Lock
from datetime import datetime
from functools import wraps
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union, cast

from fastapi import FastAPI, Request
from starlette.responses import StreamingResponse

# ------------------------------
# Setup & Usage Instructions
# ------------------------------
# Install dependencies (install-dev.sh already handles this):
#     $ pip install "fastapi[standard]"
#
# To run the server (from directory with main.py):
#     $ uvicorn main:app --port 5006
# For debugging or inspecting the full llm server interaction, you can run the server separately in a terminal:
#     $ UVICORN_LOG_LEVEL=debug uvicorn main:app --port 5006
#
# Testing - Stream Mode Example:
#     curl -X POST "http://localhost:5006/v1/chat/completions" \
#       -H "Content-Type: application/json" \
#       -H "Accept: text/event-stream" \
#       -d '{"messages":[{"content":"30x6"}], "stream": true}'
#
#   Example server response (chunks):
#     data: {"choices": [{"delta": {"content": "1"}}]}
#     data: {"choices": [{"delta": {"content": "8"}}]}
#     data: {"choices": [{"delta": {"content": "0"}}]}
#     data: {"choices": [{"delta": {}}]}
#
# Testing - Standard Response Example:
#     curl -X POST "http://localhost:5006/v1/chat/completions" \
#       -H "Content-Type: application/json" \
#       -d '{"messages":[{"content":"3+6"}]}'
#
#   Example server response:
#     {"choices":[{"message":{"role":"assistant","content":"9"}}]}
# ------------------------------

app = FastAPI()

# Re-use Uvicorn’s default logger.
logger = logging.getLogger("uvicorn.error")

# ------------------------------------------------------------------------------
# PROMPT_TO_RESULT_MAPPINGS: Static mapping of prompt string to response.
# Used for test automation across many use-cases, including normal string responses and tool calls.
#
#   Key: cleaned prompt string (as sent by client/test framework)
#   Value: either a string result or a dict indicating tool call(s) (see below)
#
# Note: Handles normal responses, sequential and parallel tool calls.
#       To extend/fix for more test cases, edit default entries below or at the test file level.
#       In case you use the default centralized mapping dictionary below, please make sure that prompt entries are unique between files to avoid undesired interference.
#
# Comments are added to specify the corresponding prompts of each test file.
# ------------------------------------------------------------------------------

Json = Dict[str, Any]
PromptResult = Union[str, Json]  # string or tool-call dictionary

# Default initial mappings, given as examples, which can be provided/overwritten from your test file endpoint.
PROMPT_TO_RESULT_MAPPINGS: Dict[str, PromptResult] = {
    # --- test_valid_configs_agent.py ---
    "30x6": "180",
    "30+60": "90",
    "30": "30",
    # --- test_valid_configs_agent_with_1_tool_multiple_outputs.py ---
    "3, 6": {"tool_call": {"name": "multiplication_summation_tool", "args": {"a": 3, "b": 6}}},
    "3, 3": {"tool_call": {"name": "multiplication_summation_tool", "args": {"a": 3, "b": 3}}},
    # --- test_valid_configs_agent_with_2_tools.py & test_valid_configs_agent_with_1_tool.py ---
    "3x6": {"tool_call": {"name": "multiplication_tool", "args": {"a": 3, "b": 6}}},
    "3*3": {"tool_call": {"name": "multiplication_tool", "args": {"a": 3, "b": 3}}},
    # --- test_valid_configs_agent_with_2_tools.py ---
    "3+3": {"tool_call": {"name": "summation_tool", "args": {"a": 3, "b": 3}}},
    "2+1": {"tool_call": {"name": "summation_tool", "args": {"a": 2, "b": 1}}},
    # --- test_valid_configs_2_servertools_in_cascade_with_llmnode_flow.py & test_valid_configs_llmnode_with_clienttool_in_cascade_with_servertool_flow.py ---
    "Return this user input exactly as it is provided: Morocco\n    Your answer should be a single string, without modification.\n    Do not include any units, reasoning, or extra text.": "Morocco",
    "Return this user input exactly as it is provided: Canada\n    Your answer should be a single string, without modification.\n    Do not include any units, reasoning, or extra text.": "Canada",
    # --- test_valid_configs_2_servertools_in_cascade_with_llmnode_flow.py ---
    "Return this user input exactly as it is provided: India\n    Your answer should be a single string, without modification.\n    Do not include any units, reasoning, or extra text.": "India",
    # --- test_valid_configs_branchingnode_with_llmnode.py ---
    "Your task is to understand the language spoken by the user: Hello, How are you doing?\n    Please output only the language in lowercase and submit. Your answer should be a single string.\n    Do not include any units, reasoning, or extra text.": "english",
    "Your task is to understand the language spoken by the user: Hola, como estas?\n    Please output only the language in lowercase and submit. Your answer should be a single string.\n    Do not include any units, reasoning, or extra text.": "spanish",
    "Your task is to understand the language spoken by the user: Ciao, come stai?\n    Please output only the language in lowercase and submit. Your answer should be a single string.\n    Do not include any units, reasoning, or extra text.": "italian",
    "Your task is to understand the language spoken by the user: Bonjour comment allez-vous?\n    Please output only the language in lowercase and submit. Your answer should be a single string.\n    Do not include any units, reasoning, or extra text.": "french",
    # --- test_valid_configs_agentnode_without_tool.py ---
    "30x20": "600",
    "30+40": "70",
    # --- test_valid_configs_agentnode.py ---
    "Alice": {"tool_call": {"name": "search_tool", "args": {"query": "Alice"}}},
    "Karim": {"tool_call": {"name": "search_tool", "args": {"query": "Karim"}}},
    "Khalid": {"tool_call": {"name": "search_tool", "args": {"query": "Khalid"}}},
    # --- test_valid_configs_nested_agentnodes.py ---
    "Jack": {"tool_call": {"name": "search_person_tool", "args": {"query_person": "Jack"}}},
    'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_tool", "description": "This tool runs a web search for the given person_results and adds number of employees. If not found we return Unknown", "parameters": {"type": "object", "properties": {"search_person_results": {"type": "array", "items": {}, "title": "search_person_results", "default": ["name", "CEO", "country"]}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_results": {"type": "array", "items": {}, "title": "search_results", "default": ["name", "CEO", "country", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: [\'Jack\', \'No\', \'USA\'] results are retrieved in the form [name, CEO, country, number_employees] where CEO value is No or Yes. if user not in DB, tool returns Unknown for CEO, country, and number_employees values. Do not attempt to answer yourself—simply return the tool response.': {
        "tool_call": {
            "name": "search_number_employees_tool",
            "args": {"search_person_results": ["Jack", "No", "USA"]},
        }
    },
    "Soufiane": {"tool_call": {"name": "search_person_tool", "args": {"query_person": "Soufiane"}}},
    'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_tool", "description": "This tool runs a web search for the given person_results and adds number of employees. If not found we return Unknown", "parameters": {"type": "object", "properties": {"search_person_results": {"type": "array", "items": {}, "title": "search_person_results", "default": ["name", "CEO", "country"]}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_results": {"type": "array", "items": {}, "title": "search_results", "default": ["name", "CEO", "country", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: [\'Soufiane\', \'Yes\', \'Morocco\'] results are retrieved in the form [name, CEO, country, number_employees] where CEO value is No or Yes. if user not in DB, tool returns Unknown for CEO, country, and number_employees values. Do not attempt to answer yourself—simply return the tool response.': {
        "tool_call": {
            "name": "search_number_employees_tool",
            "args": {"search_person_results": ["Soufiane", "Yes", "Morocco"]},
        }
    },
    "Haroun": {"tool_call": {"name": "search_person_tool", "args": {"query_person": "Haroun"}}},
    'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_tool", "description": "This tool runs a web search for the given person_results and adds number of employees. If not found we return Unknown", "parameters": {"type": "object", "properties": {"search_person_results": {"type": "array", "items": {}, "title": "search_person_results", "default": ["name", "CEO", "country"]}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_results": {"type": "array", "items": {}, "title": "search_results", "default": ["name", "CEO", "country", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: [\'Haroun\', \'Unknown\', \'Unknown\'] results are retrieved in the form [name, CEO, country, number_employees] where CEO value is No or Yes. if user not in DB, tool returns Unknown for CEO, country, and number_employees values. Do not attempt to answer yourself—simply return the tool response.': {
        "tool_call": {
            "name": "search_number_employees_tool",
            "args": {"search_person_results": ["Haroun", "Unknown", "Unknown"]},
        }
    },
    # --- test_valid_configs_parallel_agentnodes.py ---
    "Bob": {"tool_call": {"name": "search_person_info_tool", "args": {"query": "Bob"}}},
    'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_info_tool", "description": "This tool runs a web search with the given query and returns the number of employees", "parameters": {"type": "object", "properties": {"query": {"type": "string", "title": "query", "default": ""}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_number_employees_info_results": {"type": "array", "items": {}, "title": "search_number_employees_info_results", "default": ["name", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: Bob results are retrieved in the form [name, number_employees]. if user not in DB, tool returns Unknown for number_employees. Do not attempt to answer yourself—simply return the tool response exactly as it is.': {
        "tool_call": {"name": "search_number_employees_info_tool", "args": {"query": "Bob"}}
    },
    "Samir": {"tool_call": {"name": "search_person_info_tool", "args": {"query": "Samir"}}},
    'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_info_tool", "description": "This tool runs a web search with the given query and returns the number of employees", "parameters": {"type": "object", "properties": {"query": {"type": "string", "title": "query", "default": ""}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_number_employees_info_results": {"type": "array", "items": {}, "title": "search_number_employees_info_results", "default": ["name", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: Samir results are retrieved in the form [name, number_employees]. if user not in DB, tool returns Unknown for number_employees. Do not attempt to answer yourself—simply return the tool response exactly as it is.': {
        "tool_call": {"name": "search_number_employees_info_tool", "args": {"query": "Samir"}}
    },
    "Mark": {"tool_call": {"name": "search_person_info_tool", "args": {"query": "Mark"}}},
    'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_info_tool", "description": "This tool runs a web search with the given query and returns the number of employees", "parameters": {"type": "object", "properties": {"query": {"type": "string", "title": "query", "default": ""}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_number_employees_info_results": {"type": "array", "items": {}, "title": "search_number_employees_info_results", "default": ["name", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: Mark results are retrieved in the form [name, number_employees]. if user not in DB, tool returns Unknown for number_employees. Do not attempt to answer yourself—simply return the tool response exactly as it is.': {
        "tool_call": {"name": "search_number_employees_info_tool", "args": {"query": "Mark"}}
    },
    # --- test_valid_configs_parallel_agentnodes_with_final_toolnode.py ---
    "Steve": {"tool_call": {"name": "search_person_info_tool", "args": {"query": "Steve"}}},
    'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_info_tool", "description": "This tool runs a web search with the given query and returns the number of employees", "parameters": {"type": "object", "properties": {"query": {"type": "string", "title": "query", "default": ""}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_number_employees_info_results": {"type": "array", "items": {}, "title": "search_number_employees_info_results", "default": ["name", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: Steve Only use provided tools which you need to call and return their answers exactly as returned. results are retrieved in the form [name, number_employees]. if user not in DB, tool returns Unknown for number_employees. Do not attempt to answer yourself—simply return the tool response exactly as it is.': {
        "tool_call": {"name": "search_number_employees_info_tool", "args": {"query": "Steve"}}
    },
    "Ayoub": {"tool_call": {"name": "search_person_info_tool", "args": {"query": "Ayoub"}}},
    'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_info_tool", "description": "This tool runs a web search with the given query and returns the number of employees", "parameters": {"type": "object", "properties": {"query": {"type": "string", "title": "query", "default": ""}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_number_employees_info_results": {"type": "array", "items": {}, "title": "search_number_employees_info_results", "default": ["name", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: Ayoub Only use provided tools which you need to call and return their answers exactly as returned. results are retrieved in the form [name, number_employees]. if user not in DB, tool returns Unknown for number_employees. Do not attempt to answer yourself—simply return the tool response exactly as it is.': {
        "tool_call": {"name": "search_number_employees_info_tool", "args": {"query": "Ayoub"}}
    },
    "Brad": {"tool_call": {"name": "search_person_info_tool", "args": {"query": "Brad"}}},
    'Environment: ipython\nCutting Knowledge Date: December 2023\n\nYou are a helpful assistant with tool calling capabilities. Only reply with a tool call if the function exists in the library provided by the user. If it doesn\'t exist, just reply directly in natural language. When you receive a tool call response, use the output to format an answer to the original user question.\n\nYou have access to the following functions. To call a function, please respond with JSON for a function call.\nRespond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\nDo not use variables.\n\n[{"type": "function", "function": {"name": "search_number_employees_info_tool", "description": "This tool runs a web search with the given query and returns the number of employees", "parameters": {"type": "object", "properties": {"query": {"type": "string", "title": "query", "default": ""}}, "required": []}}}, {"type": "function", "function": {"name": "talk_to_user", "description": "Send a message to the user. This can be used either to help the user with their request or to ask them for additional information you are missing. Prioritize answering their requests when possible.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "title": "text", "description": "The message to send to the user."}}, "required": ["text"]}}}, {"type": "function", "function": {"name": "submit_result", "description": "Function to finish the conversation when you found all required outputs. Never make up outputs, before calling this function, first ask the user for any missing information, to gather all the required values, and then call this function", "parameters": {"type": "object", "properties": {"search_number_employees_info_results": {"type": "array", "items": {}, "title": "search_number_employees_info_results", "default": ["name", "number_employees"]}}, "required": []}}}]\n\nAdditional instructions:\nYour task is to gather the required information for the user: Brad Only use provided tools which you need to call and return their answers exactly as returned. results are retrieved in the form [name, number_employees]. if user not in DB, tool returns Unknown for number_employees. Do not attempt to answer yourself—simply return the tool response exactly as it is.': {
        "tool_call": {"name": "search_number_employees_info_tool", "args": {"query": "Brad"}}
    },
    # --- test_valid_configs_agent_with_1_clienttool.py ---
    "13+16": {"tool_call": {"name": "sum_tool", "args": {"a": 13, "b": 16}}},
    '{"result": 29.0}': '{"result": 29.0}',
    # --- test_valid_configs_agent_with_1_clienttool_multiple_outputs.py ---
    "3 and 6": {"tool_call": {"name": "sum_product_tool", "args": {"a": 3, "b": 6}}},
    '{"sum": 9.0, "product": 18.0}': '{"sum": 9.0, "product": 18.0}',
    # --- test_valid_configs_agent_with_2_clienttools.py & test_valid_configs_agent_with_clienttools_and_servertools.py ---
    "31+61": {"tool_call": {"name": "sum_tool", "args": {"a": 31, "b": 61}}},
    '{"result": 92.0}': '{"result": 92.0}',
    "61-41": {"tool_call": {"name": "subtract_tool", "args": {"a": 61, "b": 41}}},
    '{"result": 20.0}': '{"result": 20.0}',
    # --- test_valid_configs_agent_with_clienttools_and_servertools.py ---
    "6*5": {"tool_call": {"name": "multiply_tool", "args": {"a": 6, "b": 5}}},
    "30": "30",
    "8/2": {"tool_call": {"name": "divide_tool", "args": {"a": 8, "b": 2}}},
    "4.0": "4.0",
    # --- test_valid_configs_llmnode_with_clienttool_multiple_outputs_in_cascade_with_servertool_flow.py ---
    "Return this user input exactly as it is provided: US\n    Your answer should be a single string, without modification.\n    Do not include any units, reasoning, or extra text.": "US",
    "Return this user input exactly as it is provided: France\n    Your answer should be a single string, without modification.\n    Do not include any units, reasoning, or extra text.": "France",
    # --- test_valid_configs_llmconfig_with_agent.py ---
    "calculate 3x6 ?": "18",
}

# ------------------------------------------------------------------------------
# PROMPT_REGEX_TO_RESULT_MAPPINGS: Regex-based mapping of prompt patterns to response.
# Used for test automation with regex patterns matching prompts.
#
#   Key: regex pattern string
#   Value: either a string result or a dict indicating tool call(s)
#
# Note: Patterns are checked in order after exact string matches.
# ------------------------------------------------------------------------------

PROMPT_REGEX_TO_RESULT_MAPPINGS: Dict[str, PromptResult] = {}

# Tests may be executed in parallel (e.g., with pytest -n auto).
# asyncio.Lock guarantees that concurrent calls do not corrupt the shared PROMPT_TO_RESULT_MAPPINGS dictionary.
_prompt_lock: Lock = Lock()

# Tests may be executed in parallel (e.g., with pytest -n auto).
# asyncio.Lock guarantees that concurrent calls do not corrupt the shared PROMPT_REGEX_TO_RESULT_MAPPINGS dictionary.
_regex_lock: Lock = Lock()


# Determines the output-parameter name returned by the previous tool call
def _extract_submit_result_param(messages: List[Dict[str, Any]], fallback: str = "result") -> str:
    """
    Look at the system prompt, locate the function list, parse it and
    return the single property defined for the `submit_result` tool.

    If anything goes wrong, return *fallback*.
    """
    # 1) Grab the system message content (may be a list of content blocks)
    sys_msg_raw = next((m.get("content") for m in messages if m.get("role") == "system"), "")
    sys_msg = content_to_text(sys_msg_raw)
    if not sys_msg:
        return fallback

    # 2) find the first JSON list that looks like the function array
    list_match = re.search(r"\[\s*{.*?}\s*]", sys_msg, re.S)
    if not list_match:
        return fallback

    try:
        func_list = json.loads(list_match.group(0))
    except Exception:
        return fallback

    # 3) walk through the list, locate submit_result tool
    for entry in func_list:
        if entry.get("type") != "function":
            continue
        fn = entry.get("function", {})
        if fn.get("name") != "submit_result":
            continue
        props = fn.get("parameters", {}).get("properties", {})
        if props:
            # there should be exactly one key
            key: str = cast(str, next(iter(props)))  # <-- str for mypy
            return key
    return fallback


def add_metadata(route_handler: Callable[[Request], Any]) -> Any:
    """
    This wrapper adds metadata needed to comply with the Chat Completions API
    """

    @wraps(route_handler)
    async def wrapped_handler(request: Request) -> Any:
        response = await route_handler(request)
        if isinstance(response, dict):
            response["created"] = int(datetime.now().timestamp())
        return response

    return wrapped_handler


def _handle_outputs(
    data: Dict[str, Any], messages: List[Dict[str, Any]], output: PromptResult, is_stream: bool
) -> Union[Dict[str, Any], StreamingResponse]:
    logger.debug("## LLM server response (before any adjusting): %s", output)

    # Handle parallel tool calls (when mapped output is a `tool_call` list)
    # Not used yet in our tests so far but can be useful for parallel tool calls provided as a list.
    if isinstance(output, dict) and isinstance(output.get("tool_call"), list):
        tool_calls = output["tool_call"]
        tool_call_objs = []
        for idx, tc in enumerate(tool_calls):
            tool_call_objs.append(
                {
                    "index": idx,
                    "id": str(uuid.uuid4()),
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])},
                }
            )
        if is_stream:
            logger.debug("## parallel tool response (streamed):")

            async def stream_resp() -> AsyncGenerator[str, None]:
                # Emit all the tool calls at once as a delta in one chunk (OpenAI format)
                delta = {"role": "assistant", "tool_calls": tool_call_objs}
                chunk = {"choices": [{"delta": delta}]}
                streamed_response = f"data: {json.dumps(chunk)}\n\n"
                logger.debug("-> %s", streamed_response.strip())
                yield streamed_response
                # Emit the end of the stream
                streamed_response = 'data: {"choices": [{"delta": {}}]}\n\n'
                logger.debug("-> %s", streamed_response.strip())
                yield streamed_response

            return StreamingResponse(stream_resp(), media_type="text/event-stream")
        else:
            returned_response_multiple_tools: Dict[str, Any] = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": tool_call_objs,
                        }
                    }
                ]
            }
            logger.debug(
                "-> parallel tool response (non-streamed): %s", returned_response_multiple_tools
            )
            return returned_response_multiple_tools

    # Handle single tool call, or standard LLM response, in streaming mode
    if is_stream:
        logger.debug("## Sending streamed response")

        async def stream_resp() -> AsyncGenerator[str, None]:
            # Sequential/single tool_call handling
            if isinstance(output, dict) and "tool_call" in output:
                tc = output["tool_call"]
                tool_call_id = str(uuid.uuid4())
                # Step 1: send the tool_call as a delta
                chunk = {
                    "choices": [
                        {
                            "delta": {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": tool_call_id,
                                        "type": "function",
                                        "function": {
                                            "name": tc["name"],
                                            "arguments": json.dumps(tc["args"]),
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
                streamed_response = f"data: {json.dumps(chunk)}\n\n"
                logger.debug("-> %s", streamed_response.strip())
                yield streamed_response
            else:
                # If not a tool call, just stream the content character by character as before
                # Each chunk must be a JSON line prefixed with "data: "
                for c in str(output):
                    streamed_response = (
                        f'data: {json.dumps({"choices": [{"delta": {"content": c}}]})}\n\n'
                    )
                    logger.debug("-> %s", streamed_response.strip())
                    yield streamed_response
                    await asyncio.sleep(0.01)
            # Step 2: send closing empty delta to mark end
            final_streamed_response = 'data: {"choices": [{"delta": {}}]}\n\n'
            logger.debug("-> %s", final_streamed_response.strip())
            yield final_streamed_response

        return StreamingResponse(stream_resp(), media_type="text/event-stream")
    else:
        # Standard synchronous (non-streaming) OpenAI format
        logger.debug("## Sending non-streamed response")

        # Handle structured output requests from LangGraph/OpenAI client
        rf = data.get("response_format")
        if isinstance(rf, dict) and rf.get("type") == "json_schema":
            try:
                schema = rf.get("json_schema", {}).get("schema", {}) or {}
                props = schema.get("properties", {}) or {}
                # Pick the first property name from the schema, if present
                if props:
                    prop_name = next(iter(props))
                else:
                    # If the schema doesn't declare properties, infer from prior system tool list or use "result"
                    prop_name = _extract_submit_result_param(messages, fallback="result")
            except Exception:
                prop_name = _extract_submit_result_param(messages, fallback="result")

            # Use the latest user message if present; otherwise fallback to empty string
            user_msgs = [m for m in messages if m.get("role") == "user"]
            if user_msgs:
                last_user_content = content_to_text(user_msgs[-1].get("content", ""))
                last_user_content = unwrap_crewai_prompt(last_user_content)
                value = PROMPT_TO_RESULT_MAPPINGS.get(last_user_content, "")
            else:
                value = ""

            # IMPORTANT: content must be a JSON string matching the schema property name
            content_json = json.dumps({prop_name: str(value)})
            returned_structured = {
                "choices": [{"message": {"role": "assistant", "content": content_json}}]
            }
            logger.debug("-> returned structured response: %s", returned_structured)
            return returned_structured

        if isinstance(output, dict) and "tool_call" in output:
            logger.debug("## Tools from tool_call used.")
            tc = output["tool_call"]

            # Detect CrewAI requests (stop present or "Current Task:" in user)
            is_crewai = bool(data.get("stop")) or any(
                "Current Task:" in content_to_text(m.get("content", ""))
                for m in messages
                if m.get("role") == "user"
            )

            if is_crewai:
                # Emit ReAct-style content as per CrewAI prompt instructions
                react_text = (
                    "Thought: I should use the tool to compute the answer\n"
                    f"Action: {tc['name']}\n"
                    f"Action Input: {json.dumps(tc['args'])}"
                )
                returned_response_single_tool_text: Dict[str, Any] = {
                    "choices": [{"message": {"role": "assistant", "content": react_text}}]
                }
                logger.debug(
                    "-> returned (CrewAI ReAct) response: %s", returned_response_single_tool_text
                )
                return returned_response_single_tool_text

            # Default OpenAI-format tool_calls for other runtimes
            tool_call_id = str(uuid.uuid4())
            returned_response_single_tool: Dict[str, Any] = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": tool_call_id,
                                    "type": "function",
                                    "function": {
                                        "name": tc["name"],
                                        "arguments": json.dumps(tc["args"]),
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
            logger.debug("-> returned response: %s", returned_response_single_tool)
            return returned_response_single_tool
        else:
            logger.debug("## No tools used.")
            returned_response_no_tools: Dict[str, Any] = {
                "choices": [{"message": {"role": "assistant", "content": str(output)}}]
            }
            logger.debug("-> returned response (no tools used): %s", returned_response_no_tools)
            return returned_response_no_tools


@app.post("/v1/chat/completions")
@add_metadata
async def complete(request: Request) -> Any:
    """
    Main API endpoint to process chat completion requests.
    Supports both streaming and standard response modes, including tool call handling.
    To make debugging easy, server logs all requests and responses, including intermediate handling
    """
    data = await request.json()
    messages = data.get("messages", [])
    is_stream = data.get("stream", False)
    logger.info("Received %d message(s) – stream=%s", len(messages), is_stream)
    for idx, m in enumerate(messages):
        logger.debug(" msg[%d]=%s", idx, m)

    last_message = messages[-1] if messages else {}
    last_raw_content = last_message.get("content", "")
    logger.debug("## Request: %s", data)
    logger.debug("## Prompt: %s", last_raw_content)
    last_content = content_to_text(last_raw_content)

    # Normalize CrewAI prompts so the mapping sees just the raw task (e.g., "30x6")
    last_content = unwrap_crewai_prompt(last_content)
    logger.debug("## Normalized prompt: %r", last_content)

    last_content = remove_formatting_suffixes(last_content)
    logger.debug("## Prompt without formatting suffix: %r", last_content)

    # 1. Retrieve mapped output for prompt and use it if present
    if last_content in PROMPT_TO_RESULT_MAPPINGS:
        return _handle_outputs(data, messages, PROMPT_TO_RESULT_MAPPINGS[last_content], is_stream)

    # 1b. Check regex patterns if no exact match
    regex_result = _check_regex_mappings(messages)
    if regex_result is not None:
        return _handle_outputs(data, messages, regex_result, is_stream)

    # 2. If the last tool output exists, simply return the tool response (per instructions),
    # or wrap it per response_format if provided. This case is especially important for LangGraph
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    if tool_msgs:
        tool_raw = content_to_text(tool_msgs[-1].get("content", ""))
        # Try to parse JSON; otherwise use raw text
        try:
            tool_obj = json.loads(tool_raw)
        except Exception:
            tool_obj = tool_raw

        final_value = _final_value_from_tool_output(tool_obj)

        # response_format handling for structured output
        rf = data.get("response_format")
        if isinstance(rf, dict) and rf.get("type") == "json_schema":
            try:
                schema = rf.get("json_schema", {}).get("schema", {}) or {}
                props = schema.get("properties", {}) or {}
                prop_name = next(iter(props)) if props else "result"
            except Exception:
                prop_name = "result"

            # IMPORTANT: content must be a JSON string
            content_json = json.dumps({prop_name: final_value})

            # Honor streaming for structured output too
            if is_stream:
                logger.debug("## Returning streamed structured final answer from tool output")

                async def stream_resp() -> AsyncGenerator[str, None]:
                    for c in content_json:
                        streamed_response = (
                            f'data: {json.dumps({"choices": [{"delta": {"content": c}}]})}\n\n'
                        )
                        logger.debug("-> %s", streamed_response.strip())
                        yield streamed_response
                        await asyncio.sleep(0.004)
                    # Emit the end of the stream
                    streamed_response = 'data: {"choices": [{"delta": {}}]}\n\n'
                    logger.debug("-> %s", streamed_response.strip())
                    yield streamed_response

                return StreamingResponse(stream_resp(), media_type="text/event-stream")

            returned_structured = {
                "choices": [{"message": {"role": "assistant", "content": content_json}}]
            }
            logger.debug(
                "-> returned structured response from tool output: %s", returned_structured
            )
            return returned_structured

        # No structured output requested -> return final_value
        if is_stream:
            logger.debug("## Returning streamed final answer from tool output")

            async def stream_resp() -> AsyncGenerator[str, None]:
                for c in str(final_value):
                    streamed_response = (
                        f'data: {json.dumps({"choices": [{"delta": {"content": c}}]})}\n\n'
                    )
                    logger.debug("-> %s", streamed_response.strip())
                    yield streamed_response
                    await asyncio.sleep(0.004)
                # Emit the end of the stream
                streamed_response = 'data: {"choices": [{"delta": {}}]}\n\n'
                logger.debug("-> %s", streamed_response.strip())
                yield streamed_response

            return StreamingResponse(stream_resp(), media_type="text/event-stream")

        returned_response = {
            "choices": [{"message": {"role": "assistant", "content": final_value}}]
        }
        logger.debug("-> returned response from tool output: %s", returned_response)
        return returned_response

    # CrewAI Observation -> Final Answer (generic, robust)
    obs_value = extract_observation_value(last_content)
    if obs_value is not None:
        if isinstance(obs_value, (dict, list)):
            obs_compact = json.dumps(obs_value, separators=(",", ":"))
            final_payload = obs_compact
        else:
            # raw text or scalar
            final_payload = str(obs_value)

        final_text = "Thought: I now know the final answer\nFinal Answer: " + final_payload
        returned_response_observation: Dict[str, Any] = {
            "choices": [{"message": {"role": "assistant", "content": final_text}}]
        }
        logger.debug(
            "-> returned (CrewAI Observation -> Final Answer): %s", returned_response_observation
        )
        return returned_response_observation

    # Handle tool responses sent as raw JSON, as JSON-in-string, <tool_response>...</tool_response>, etc.:
    # Reply with the tool output in a generalizable way, no matter the tool or prompt.
    # Handle all tool output formats (single field, multi field, any structure, for any tool).
    tool_result_obj = None
    tool_response_raw = last_content.strip()
    if tool_response_raw.startswith("<tool_response>") and tool_response_raw.endswith(
        "</tool_response>"
    ):
        # Extract enclosed response
        tool_response_raw = tool_response_raw[
            len("<tool_response>") : -len("</tool_response>")
        ].strip()
        # Remove extra wrapping quotes if present (for double encoding)
        if (tool_response_raw.startswith('"') and tool_response_raw.endswith('"')) or (
            tool_response_raw.startswith("'") and tool_response_raw.endswith("'")
        ):
            try:
                # Try JSON loading (removes escapes)
                tool_response_raw = json.loads(tool_response_raw)
            except Exception:
                # If not JSON, just strip quotes
                tool_response_raw = tool_response_raw[1:-1]
        # Try decoding as JSON object
        try:
            obj = json.loads(tool_response_raw)
            tool_result_obj = obj  # Accept anything that parses as JSON
        except Exception as e:
            tool_result_obj = None

        # If tool result found, return it as compact JSON, either streaming or regular mode
        if tool_result_obj is not None:
            logger.debug("## prepare tool result")
            # Extract name of the returned variable from previous messages
            param_name = _extract_submit_result_param(messages)

            # return result value using the submit_result tool
            result_dictionary: Dict[str, Any] = {
                "name": "submit_result",
                "parameters": {param_name: tool_result_obj},
                "tool_calls": [],
            }

            result_str: str = json.dumps(result_dictionary)

            if is_stream:
                logger.debug("## tool result sent (streamed):")

                async def stream_resp() -> AsyncGenerator[str, None]:
                    for c in result_str:
                        streamed_response = (
                            f'data: {json.dumps({"choices": [{"delta": {"content": c}}]})}\n\n'
                        )
                        logger.debug("-> %s", streamed_response.strip())
                        yield streamed_response
                        await asyncio.sleep(0.004)
                    # Emit the end of the stream
                    streamed_response = 'data: {"choices": [{"delta": {}}]}\n\n'
                    logger.debug("-> %s", streamed_response.strip())
                    yield streamed_response

                return StreamingResponse(stream_resp(), media_type="text/event-stream")
            else:
                returned_response_tool_result: Dict[str, Any] = {
                    "choices": [{"message": {"role": "assistant", "content": result_str}}]
                }
                logger.debug(
                    "-> tool result sent (non-streamed): %s", returned_response_tool_result
                )
                return returned_response_tool_result

    # 3. Resort to default output "Unhandled" because entry was not found
    return _handle_outputs(data, messages, "Unhandled", is_stream)


def content_to_text(content: Any) -> str:
    """
    Convert content to plain string.
    - If content is a string, return it.
    - If content is a single-item list with {"type": "text", "text": "..."},
      return that text.
    - Otherwise, return str(content or "").
    """
    if isinstance(content, str):  # e.g., AutoGen
        return content
    elif isinstance(content, list) and len(content) == 1:  # e.g., WayFlow
        item = content[0]
        if isinstance(item, dict) and item.get("type") == "text":
            return item.get("text", "") or ""

    return str(content or "")


def unwrap_crewai_prompt(text: str) -> str:
    """
    If the text looks like CrewAI's templated prompt, extract the actual task after 'Current Task:'.
    We scan line-by-line to avoid regex corner cases and formatting surprises.
    """
    if not isinstance(text, str):
        return text

    # Example line we expect:
    # Current Task: [{'role': 'assistant', 'content': 'Unhandled'}, {'role': 'user', 'content': '30'}]
    for line in text.splitlines():
        # tolerate leading/trailing spaces
        if "Current Task:" in line:
            try:
                all_user_messages = re.findall(r"\{'role': 'user', 'content': '([^']*)'}", line)
                if all_user_messages:
                    return str(all_user_messages[-1])
            except Exception as e:
                logger.warning(
                    f"Deterministic LLM server received prompt with unexpected format: {line}\n"
                    f"Raising exception: {type(e)} {e}"
                )
            return line.split("Current Task:")[-1]

    # If no match, return text as-is
    return text


def remove_formatting_suffixes(prompt: str) -> str:
    """
    Executors may implement structured generation by appending additional instructions
    explaining the expected output format.
    We remove these here s.t. we can build executor independent tests.
    """
    # TODO SANE-14866: The approach in this helper is not very maintainable, we should improve it and
    #   avoid trying to match specific instruction strings as they may change.
    # NOTE: Add more suffixes here for other executors as necessary
    patterns = [
        # WayFlow JSON_CONSTRAINED_GENERATION_PROMPT,
        # including wildcard at the end to match the specific JSON schema that would be appended there
        r"\s*## Additional instructions:\s*At the end of your answer, finish with <final_answer>\$your_answer\$</final_answer> with \$your_answer\$ being a properly formatted json that is valid against this JSON schema\s*:\s*.*"
    ]
    for pattern in patterns:
        if re.search(pattern, prompt, re.DOTALL):
            prompt = re.sub(pattern, "", prompt, flags=re.DOTALL).rstrip()
            break  # there should be only one pattern to match (on pattern per executor)
    return prompt


def extract_observation_value(text: str) -> Any:
    """
    Extract the last 'Observation:' value from a multi-line ReAct-style block.
    Returns:
      - dict/list if parsable (via json or ast.literal_eval)
      - str (raw) otherwise
    """
    if not isinstance(text, str):
        return text

    # Find the last occurrence of 'Observation:' (case-insensitive) anywhere
    m = re.search(r"(?is)Observation\s*:\s*(.+)$", text)
    if not m:
        return None

    obs_raw = m.group(1).strip()

    # If Observation is everything to the end, but includes extra trailing narrative,
    # try to isolate a top-level JSON/Python object by simple heuristics:
    # - If it starts with { or [ and ends with } or ] on same line, try parse as whole.
    # Otherwise, still attempt lenient parsing.

    # 1) Try strict JSON first
    try:
        return json.loads(obs_raw)
    except Exception:  # nosec B110 - fallback to raw string is expected for non-JSON
        pass

    # 2) Try Python literal (handles single quotes dicts printed by some libs)
    try:
        return ast.literal_eval(obs_raw)
    except Exception:  # nosec B110 - fallback to raw string is expected for non-literal
        pass

    # 3) As-is fallback (raw string)
    return obs_raw


def _check_regex_mappings(messages: List[Dict[str, Any]]) -> Optional[PromptResult]:
    """
    Check PROMPT_REGEX_TO_RESULT_MAPPINGS for matches, handling both standard regex and suffix-based matching.
    Returns the result if a match is found, otherwise None.
    """
    contents = [
        remove_formatting_suffixes(unwrap_crewai_prompt(content_to_text(msg.get("content", ""))))
        for msg in messages
    ]

    for pattern, result in PROMPT_REGEX_TO_RESULT_MAPPINGS.items():
        if isinstance(result, dict) and "suffix_size" in result:
            # Handle suffix-based matching
            suffix_size = result["suffix_size"]
            if len(messages) < suffix_size:
                continue
            suffix_contents = contents[-suffix_size:]
            suffix_content = "".join(suffix_contents)
            if re.search(pattern, suffix_content) and isinstance(result["value"], (dict, str)):
                return result["value"]
        else:
            # Standard regex matching on last content
            if re.search(pattern, contents[-1]):
                return result
    return None


def _final_value_from_tool_output(obj: Any) -> str:
    """
    Given a parsed tool output (obj), return a string representing the final answer:
      - If obj is a scalar (str, int, float, bool): return it as str.
      - If obj is a dict with exactly one key and a scalar value: return that scalar as str.
      - Else: return compact JSON string of obj.
    This keeps behavior general and matches tests that expect plain numbers like "18".
    """
    # Scalar
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return "" if obj is None else str(obj)

    # Dict with a single scalar value
    if isinstance(obj, dict) and len(obj) == 1:
        ((only_key, only_val),) = obj.items()
        if isinstance(only_val, (str, int, float, bool)) or only_val is None:
            return "" if only_val is None else str(only_val)

    # Fallback to compact JSON string
    try:
        return json.dumps(obj, separators=(",", ":"))
    except Exception:
        # As a last resort, str()
        return str(obj)


# POST endpoint that receives a JSON object and merges it into PROMPT_TO_RESULT_MAPPINGS
@app.post("/v1/chat/set_output_mappings")
async def set_output(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add / overwrite entries in PROMPT_TO_RESULT_MAPPINGS at run-time.

    Example body:  { "30*6": "180", "3*3": { "tool_call": {...} } }
    """
    async with _prompt_lock:
        PROMPT_TO_RESULT_MAPPINGS.update(mapping)
        current_size = len(PROMPT_TO_RESULT_MAPPINGS)
    logger.info(
        "PROMPT_TO_RESULT_MAPPINGS updated with %d entry(ies) – total %d",
        len(mapping),
        current_size,
    )
    return {"status": "ok", "added": len(mapping), "total": current_size}


@app.post("/v1/chat/reset_output_mappings")
async def reset_output() -> Dict[str, Any]:
    """
    OPTIONAL utility to clear the dynamic map between tests.
    """
    async with _prompt_lock:
        PROMPT_TO_RESULT_MAPPINGS.clear()
    logger.info("PROMPT_TO_RESULT_MAPPINGS cleared by /reset_output call")
    return {"status": "ok", "total": 0}


# POST endpoint that receives a JSON object and merges it into PROMPT_REGEX_TO_RESULT_MAPPINGS
@app.post("/v1/chat/set_output_regex_mappings")
async def set_output_regex(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add / overwrite entries in PROMPT_REGEX_TO_RESULT_MAPPINGS at run-time.

    Example body:  { ".*30.*6.*": "180", ".*3.*3.*": { "tool_call": {...} } }
    """
    async with _regex_lock:
        PROMPT_REGEX_TO_RESULT_MAPPINGS.update(mapping)
        current_size = len(PROMPT_REGEX_TO_RESULT_MAPPINGS)
    logger.info(
        "PROMPT_REGEX_TO_RESULT_MAPPINGS updated with %d entry(ies) – total %d",
        len(mapping),
        current_size,
    )
    return {"status": "ok", "added": len(mapping), "total": current_size}


@app.post("/v1/chat/reset_output_regex_mappings")
async def reset_output_regex() -> Dict[str, Any]:
    """
    OPTIONAL utility to clear the dynamic regex map between tests.
    """
    async with _regex_lock:
        PROMPT_REGEX_TO_RESULT_MAPPINGS.clear()
    logger.info("PROMPT_REGEX_TO_RESULT_MAPPINGS cleared by /reset_output_regex call")
    return {"status": "ok", "total": 0}
