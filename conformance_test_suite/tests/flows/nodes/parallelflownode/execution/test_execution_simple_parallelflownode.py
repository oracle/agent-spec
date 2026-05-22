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
    tool_registry = {
        "wait_2_seconds_tool": lambda: time.sleep(2),
    }
    return load_agentspec_config(agentspec_configuration, tool_registry)


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_parallelflownode.yaml",
        "flow_with_servertool_in_parallelflownode.yaml",
    ],
)
def test_flow_with_parallelflownode_can_be_executed(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name)
    agentspec_component.start()
    result = agentspec_component.run()
    assert result.outputs == {}, f"Expected no outputs"


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_parallelflownode_with_io.yaml",
    ],
)
def test_flow_with_parallelflownode_and_io_can_be_executed(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    inputs_and_outputs = {"n1": 1, "n2": 2, "n3": 3}
    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name)
    agentspec_component.start(inputs_and_outputs)
    result = agentspec_component.run()
    assert (
        result.outputs == inputs_and_outputs
    ), f"Expected outputs `{inputs_and_outputs}` but got `{result.outputs}"


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_parallelflownode_with_overlapping_inputs.yaml",
    ],
)
def test_flow_with_parallelflownode_and_overlapping_inputs_can_be_executed(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    inputs = {"n": 1}
    outputs = {"n1": 1, "n2": 1, "n3": 1}
    agentspec_component = load_yaml_file(load_agentspec_config, yaml_file_name)
    agentspec_component.start(inputs)
    result = agentspec_component.run()
    assert result.outputs == outputs, f"Expected outputs `{outputs}` but got `{result.outputs}"


def test_execution_of_flow_with_server_tool_in_parallelflownode_is_parallelized(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> None:
    # We check the time it takes to run a parallel flow node that contains nothing, in order to set a baseline reference time
    agentspec_component = load_yaml_file(load_agentspec_config, "flow_with_parallelflownode.yaml")
    agentspec_component.start()
    start_time = time.time()
    agentspec_component.run()
    reference_time = time.time() - start_time

    # Now we run the tools in parallel flow node. If the execution is truly parallel,
    # the wait of 2 seconds per subflow should not sum up. Therefore, we assume that if the time it takes to run
    # the flow is > reference_time (which is the basic overhead of doing nothing) + 3 (i.e., the time of a single wait with some margin)
    # seconds, then the execution is not really parallel
    agentspec_component = load_yaml_file(
        load_agentspec_config, "flow_with_servertool_in_parallelflownode.yaml"
    )
    agentspec_component.start()
    start_time = time.time()
    agentspec_component.run()
    final_time = time.time() - start_time
    assert (
        final_time <= reference_time + 3
    ), f"Execution took {final_time} seconds, parallelization not implemented or heavily suboptimal"
