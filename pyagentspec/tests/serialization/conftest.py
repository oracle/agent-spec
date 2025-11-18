# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json

import pytest
import yaml

from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode
from pyagentspec.llms.vllmconfig import VllmConfig


def assert_serialized_representations_are_equal(
    str_1: str, str_2: str, serialization_format: str = "yaml"
) -> None:
    if serialization_format == "yaml":
        obj_1, obj_2 = yaml.safe_load(str_1), yaml.safe_load(str_2)
    elif serialization_format == "json":
        obj_1, obj_2 = json.loads(str_1), json.loads(str_2)
    else:
        raise ValueError(
            f"Unknown serialization format `{serialization_format}`. Only `json` and `yaml` are allowed."
        )
    assert obj_1 == obj_2


@pytest.fixture
def simplest_flow() -> Flow:
    start_node = StartNode(id="start", name="start_node")
    end_node = EndNode(id="end", name="end_node")
    return Flow(
        name="flow_name",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start::end", from_node=start_node, to_node=end_node),
        ],
    )


@pytest.fixture()
def vllmconfig():
    yield VllmConfig(id="agi1", name="agi1", model_id="agi_model1", url="http://some.where")
