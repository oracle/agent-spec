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
YAML_FILE_NAME = "simple_flow_with_llmnode.yaml"
YAML_FILE_NAME_STRING = "simple_flow_with_llmnode_string.yaml"


@pytest.fixture
def prompt_to_result_mappings():
    return {
        "You are a multiplier agent.\n    Multiply 5 with 1.\n    Your answer should be a single integer. Return only the result.\n    Do not include any reasoning or extra text.": "5",
        "You are a multiplier agent.\n    Multiply 5 with 2.\n    Your answer should be a single integer. Return only the result.\n    Do not include any reasoning or extra text.": "10",
        "You are a multiplier agent.\n    Multiply 5 with 3.\n    Your answer should be a single integer. Return only the result.\n    Do not include any reasoning or extra text.": "15",
        "You are a weight comparison agent.\n    Which is likely heavier, a dog or whale?\n    Your answer should be a single word: the name of the heavier animal.\n    Return only the result.\n    Do not include any reasoning or extra text.": "whale",
        "You are a weight comparison agent.\n    Which is likely heavier, a dog or mouse?\n    Your answer should be a single word: the name of the heavier animal.\n    Return only the result.\n    Do not include any reasoning or extra text.": "dog",
    }


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()

    component = load_agentspec_config(agentspec_config=agentspec_configuration)
    return component


@pytest.fixture
def agentspec_component_string(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> AgentSpecConfigLoaderType:
    with open(CONFIG_DIR / YAML_FILE_NAME_STRING) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()

    component = load_agentspec_config(agentspec_config=agentspec_configuration)
    return component


def test_valid_configuration_of_flow_with_llmnode_can_be_loaded(
    agentspec_component,
) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


def test_valid_configuration_of_flow_with_llmnode_string_can_be_loaded(
    agentspec_component_string,
) -> None:
    assert agentspec_component_string is not None, "valid string file, should be loaded"


@pytest.mark.parametrize(
    "input_number, expected_result",
    [
        (1, 5),
        (2, 10),
        (3, 15),
    ],
)
def test_valid_configuration_of_flow_with_llmnode_can_be_executed(
    agentspec_component, input_number, expected_result
) -> None:
    agentspec_component.start({"input_number": input_number})
    result = agentspec_component.run()
    assert result.outputs == {
        "result": expected_result
    }, f"Expected {expected_result} for {input_number}"


@pytest.mark.parametrize(
    "input_animal, expected_result",
    [
        ("whale", "whale"),
        ("mouse", "dog"),
    ],
)
def test_valid_configuration_of_flow_with_llmnode_string_can_be_executed(
    agentspec_component_string, input_animal, expected_result
) -> None:
    agentspec_component_string.start({"input_animal": input_animal})
    result = agentspec_component_string.run()
    assert result.outputs == {
        "heavier_animal": expected_result
    }, f"Expected {expected_result} for {input_animal}"
