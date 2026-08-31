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
YAML_FILE_NAME = "simple_flow_with_flownode_passthrough.yaml"


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()

    component = load_agentspec_config(agentspec_config=agentspec_configuration)
    return component


def test_valid_configuration_of_flow_with_flownode_can_be_loaded(
    agentspec_component,
) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "input, expected_output",
    [
        (1, 1),
        (5, 5),
    ],
)
def test_valid_configuration_of_flow_with_flownode_can_be_executed(
    agentspec_component, input, expected_output
) -> None:

    agentspec_component.start({"input": input})
    result = agentspec_component.run()
    assert result.outputs == {
        "passthrough_input": expected_output
    }, f"Expected {expected_output} for {input}"
