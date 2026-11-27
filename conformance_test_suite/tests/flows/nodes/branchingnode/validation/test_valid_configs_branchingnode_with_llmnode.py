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
YAML_FILE_NAME = "branchingnode_flow_with_llmnode.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "Your task is to understand the language spoken by the user: Hello, How are you doing?\n    Please output only the language in lowercase and submit. Your answer should be a single string.\n    Do not include any units, reasoning, or extra text.": "english",
        "Your task is to understand the language spoken by the user: Hola, como estas?\n    Please output only the language in lowercase and submit. Your answer should be a single string.\n    Do not include any units, reasoning, or extra text.": "spanish",
        "Your task is to understand the language spoken by the user: Ciao, come stai?\n    Please output only the language in lowercase and submit. Your answer should be a single string.\n    Do not include any units, reasoning, or extra text.": "italian",
        "Your task is to understand the language spoken by the user: Bonjour comment allez-vous?\n    Please output only the language in lowercase and submit. Your answer should be a single string.\n    Do not include any units, reasoning, or extra text.": "french",
    }


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()

    component = load_agentspec_config(agentspec_config=agentspec_configuration)
    return component


def test_valid_configs_branchingnode_with_llmnode_can_be_loaded(
    agentspec_component,
) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_input, expected_detected_language",
    [
        ("Hello, How are you doing?", "ENGLISH_LANGUAGE"),
        ("Hola, como estas?", "SPANISH_LANGUAGE"),
        ("Ciao, come stai?", "ITALIAN_LANGUAGE"),
        (
            "Bonjour comment allez-vous?",
            "UNKNOWN_LANGUAGE",
        ),  # should return UNKNOWN_LANGUAGE as French is not in the list of branches
    ],
)
def test_valid_configs_branchingnode_with_llmnode_can_be_executed(
    agentspec_component,
    user_input,
    expected_detected_language,
    local_deterministic_llm_server,
) -> None:
    agentspec_component.start({"user_input": user_input})
    result = agentspec_component.run()
    assert result.outputs == {
        "detected_language": expected_detected_language
    }, f"Expected {expected_detected_language} for {user_input}"
