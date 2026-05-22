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


def load_yaml_file(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str, valid: bool
) -> Any:
    config_dir = Path(__file__).parent.parent / ("valid_configs" if valid else "invalid_configs")
    with open(config_dir / yaml_file_name) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    tool_registry = {
        "wait_2_seconds_tool": lambda: time.sleep(2),
        "square_tool": lambda input: input * input,
        "division_tool": lambda numerator, denominator: numerator / denominator,
        "squared_sum_root_tool": lambda input_list: float(np.sqrt(np.sum(input_list))),
    }
    return load_agentspec_config(agentspec_configuration, tool_registry)


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_mapnode.yaml",
        "flow_with_mapnode_with_io.yaml",
        "flow_with_mapnode_with_non_iterable_io.yaml",
        "flow_with_servertool_in_mapnode.yaml",
        "flow_with_nested_mapnodes.yaml",
    ],
)
def test_valid_configuration_of_flow_with_mapnode_can_be_loaded(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name, True)
    assert agentspec_component is not None, "valid file, should be loaded"
