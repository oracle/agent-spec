# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from .....conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"


# What the flow is applying to a list of numbers
def l2_normalize(input_list):
    # 1. Square each input
    squared = [x**2 for x in input_list]
    # 2. Compute sum of squares, then take square root
    l2_norm = np.sqrt(sum(squared))
    if l2_norm == 0:
        # Return zeros if input is all zeros (to avoid division by zero)
        return [0 for _ in input_list]
    # 3. Divide each input by the L2 norm to normalize
    normalized = [float(x / l2_norm) for x in input_list]
    return normalized


def load_yaml_file(load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str) -> Any:
    with open(CONFIG_DIR / yaml_file_name) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()

    tool_registry = {
        "wait_2_seconds_tool": lambda: time.sleep(2),
        "square_tool": lambda input: input * input,
        "division_tool": lambda numerator, denominator: numerator / denominator,
        "squared_sum_root_tool": lambda input_list: float(np.sqrt(np.sum(input_list))),
    }
    return load_agentspec_config(
        agentspec_config=agentspec_configuration, tool_registry=tool_registry
    )


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_mapnode.yaml",
        "flow_with_servertool_in_mapnode.yaml",
    ],
)
def test_flow_with_mapnode_can_be_executed(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name)
    agentspec_component.start()
    result = agentspec_component.run()
    assert result.outputs == {}, f"Expected no outputs"


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_mapnode_with_io.yaml",
    ],
)
def test_flow_with_mapnode_and_io_can_be_executed(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    inputs = {"iterated_n": [1, 2, 3]}
    outputs = {"collected_n": [1, 2, 3]}
    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name)
    agentspec_component.start(inputs)
    result = agentspec_component.run()
    assert result.outputs == outputs, f"Expected outputs `{outputs}` but got `{result.outputs}`"


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_mapnode_with_non_iterable_io.yaml",
    ],
)
def test_flow_with_mapnode_and_non_iterable_io_can_be_executed(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    inputs = {"iterated_fixed": 10, "iterated_nonfixed": [1, 2, 3]}
    outputs = {"collected_fixed": [10, 10, 10], "collected_nonfixed": [1, 2, 3]}
    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name)
    agentspec_component.start(inputs)
    result = agentspec_component.run()
    assert result.outputs == outputs, f"Expected outputs `{outputs}` but got `{result.outputs}`"


@pytest.mark.parametrize("yaml_file_name", ["flow_with_nested_mapnodes.yaml"])
@pytest.mark.parametrize(
    "input_list, expected_l2_normalized_input_list",
    [
        (
            [1.0, 2.0, 2.0],
            l2_normalize([1.0, 2.0, 2.0]),
        ),  # [0.3333333333333333, 0.6666666666666666, 0.6666666666666666]
        (
            [1.0, 2.0, 3.0],
            l2_normalize([1.0, 2.0, 3.0]),
        ),  # [0.2672612419124244, 0.5345224838248488, 0.8017837257372732]
        ([5.0], l2_normalize([5.0])),  # [1.0]
    ],
)
def test_flow_with_nested_mapnodes_can_be_executed(
    load_agentspec_config: AgentSpecConfigLoaderType,
    yaml_file_name: str,
    input_list,
    expected_l2_normalized_input_list,
) -> None:

    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name)
    agentspec_component.start({"input_list": input_list})
    result = agentspec_component.run()
    assert result.outputs["collected_result"] == pytest.approx(
        expected_l2_normalized_input_list
    ), f"Expected {expected_l2_normalized_input_list} for {input_list}"
