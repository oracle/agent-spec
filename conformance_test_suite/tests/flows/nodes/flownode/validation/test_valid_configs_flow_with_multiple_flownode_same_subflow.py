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
YAML_FILE_NAME = "flow_with_multiple_flownode_same_subflow.yaml"


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()

    tool_registry = {
        "square_tool": lambda input: input * input,
    }

    component = load_agentspec_config(
        agentspec_config=agentspec_configuration, tool_registry=tool_registry
    )
    return component


def test_valid_configuration_of_flow_with_multiple_flownode_same_subflow_can_be_loaded(
    agentspec_component,
) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "input, expected_input_square",
    [
        (1, 1),
        (
            2,
            256,
        ),  # it's ((2^2)^2)^2, the flow is start -> tool -> flown1(tool) -> flown2(tool) -> end
        (3, 6561),
    ],
)
def test_valid_configuration_of_flow_with_multiple_flownode_same_subflow_can_be_executed(
    agentspec_component, input, expected_input_square
) -> None:

    agentspec_component.start({"input": input})
    result = agentspec_component.run()
    assert result.outputs == {
        "input_square": expected_input_square
    }, f"Expected {expected_input_square} for {input}"
