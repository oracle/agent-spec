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
YAML_FILE_NAME = "simple_branchingnode_flow.yaml"


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()

    component = load_agentspec_config(agentspec_config=agentspec_configuration)
    return component


def test_valid_configs_branchingnode_can_be_loaded(
    agentspec_component,
) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_input, expected_access_message",
    [
        ("123456", "ACCESS_GRANTED"),  # First test of the right CODE
        ("WRONG_CODE", "ACCESS_DENIED"),  # Second test of a wrong CODE
    ],
)
def test_valid_configs_branchingnode_can_be_executed(
    agentspec_component, user_input, expected_access_message
) -> None:

    agentspec_component.start({"user_input": user_input})
    result = agentspec_component.run()
    assert result.outputs == {
        "access_message": expected_access_message
    }, f"Expected {expected_access_message} for {user_input}"
