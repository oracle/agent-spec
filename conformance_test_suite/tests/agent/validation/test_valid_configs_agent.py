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
YAML_FILE_NAME = "simple_agent_component.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "30x6": "180",
        "30+60": "90",
        "30": "30",
    }


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> AgentSpecRunnableComponent:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    component = load_agentspec_config(agentspec_configuration)
    return component


def test_valid_configuration_agent_can_be_loaded(agentspec_component) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_message, expected_llm_output",
    [
        ("30x6", "180"),
        ("30+60", "90"),
        ("30", "30"),
    ],
)
def test_agent_can_be_executed(
    agentspec_component, user_message, expected_llm_output, local_deterministic_llm_server
) -> None:

    agentspec_component.start()
    result = agentspec_component.run()
    agentspec_component.append_user_message(user_message=user_message)
    result = agentspec_component.run()

    if hasattr(result, "outputs"):
        assert result.outputs == {
            "llm_output": expected_llm_output
        }, f"Expected {expected_llm_output} for {user_message}"
    elif hasattr(result, "agent_messages"):
        assert (
            expected_llm_output in result.agent_messages[-1]
        ), f"Expected {expected_llm_output} for {user_message}"
    else:
        raise AssertionError(f"Test did not return expected output or message. Got: {result}")
