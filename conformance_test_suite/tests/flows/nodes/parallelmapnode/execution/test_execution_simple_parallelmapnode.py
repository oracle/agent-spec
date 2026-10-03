# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import time
from pathlib import Path
from typing import Any

import pytest

from .....conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"


def load_yaml_file(load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str) -> Any:
    with open(CONFIG_DIR / yaml_file_name) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    tool_registry = {"wait_2_seconds_tool": lambda: time.sleep(2)}
    return load_agentspec_config(agentspec_configuration, tool_registry)


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_parallelmapnode.yaml",
        "flow_with_servertool_in_parallelmapnode.yaml",
    ],
)
def test_flow_with_parallelmapnode_can_be_executed(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name)
    agentspec_component.start()
    result = agentspec_component.run()
    assert result.outputs == {}, f"Expected no outputs"


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_parallelmapnode_with_io.yaml",
    ],
)
def test_flow_with_parallelmapnode_and_io_can_be_executed(
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
        "flow_with_parallelmapnode_with_non_iterable_io.yaml",
    ],
)
def test_flow_with_parallelmapnode_and_non_iterable_io_can_be_executed(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    inputs = {"iterated_fixed": 10, "iterated_nonfixed": [1, 2, 3]}
    outputs = {"collected_fixed": [10, 10, 10], "collected_nonfixed": [1, 2, 3]}
    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name)
    agentspec_component.start(inputs)
    result = agentspec_component.run()
    assert result.outputs == outputs, f"Expected outputs `{outputs}` but got `{result.outputs}`"


def test_execution_of_flow_with_server_tool_in_parallelmapnode_is_parallelized(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> None:
    # We check the time it takes to run a parallel map node flow that contains nothing, in order to set a baseline reference time
    agentspec_component = load_yaml_file(load_agentspec_config, "flow_with_parallelmapnode.yaml")
    agentspec_component.start()
    start_time = time.time()
    agentspec_component.run()
    reference_time = time.time() - start_time

    # Now we run the tools in parallel map node. If the execution is truly parallel,
    # the wait of 2 seconds per subflow should not sum up. Therefore, we assume that if the time it takes to run
    # the flow is > reference_time (which is the basic overhead of doing nothing) + 3 (i.e., the time of a single wait with some margin)
    # seconds, then the execution is not really parallel
    agentspec_component = load_yaml_file(
        load_agentspec_config, "flow_with_servertool_in_parallelmapnode.yaml"
    )
    agentspec_component.start()
    start_time = time.time()
    agentspec_component.run()
    final_time = time.time() - start_time
    assert (
        final_time <= reference_time + 3
    ), f"Execution took {final_time} seconds, parallelization not implemented or heavily suboptimal"
