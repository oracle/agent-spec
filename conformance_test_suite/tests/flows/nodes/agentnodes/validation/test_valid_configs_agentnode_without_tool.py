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
YAML_FILE_NAME = "simple_agentnode_without_tool.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {"30x20": "600", "30+40": "70"}


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    component = load_agentspec_config(agentspec_configuration)
    return component


def test_valid_configuration_agentnode_without_tool_can_be_loaded(agentspec_component) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "query, expected_search_results",
    [
        ("30x20", "600"),
        ("30+40", "70"),
    ],
)
def test_agentnode_without_tool_can_be_executed(
    agentspec_component, query, expected_search_results, local_deterministic_llm_server
) -> None:
    agentspec_component.start()
    agentspec_component.append_user_message(user_message=query)
    result = agentspec_component.run()

    if hasattr(result, "outputs"):
        assert result.outputs == {
            "search_results": expected_search_results
        }, f"Expected {expected_search_results} for {query}"
    elif hasattr(result, "agent_messages"):
        assert (
            expected_search_results in result.agent_messages[-1]
        ), f"Expected {expected_search_results} for {query}"
    else:
        raise AssertionError(f"Test did not return expected output or message. Got: {result}")
