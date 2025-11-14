# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode
from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.flows.nodes.mapnode import ReductionMethod
from pyagentspec.flows.nodes.parallelmapnode import ParallelMapNode
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum


@pytest.fixture
def default_parallel_map_node() -> ParallelMapNode:
    vllmconfig = VllmConfig(id="vllm", name="agi1", model_id="agi_model1", url="http://some.where")
    start_node = StartNode(id="START_NODE", name="start_node")
    end_node = EndNode(id="end_node1", name="end node 1", outputs=[])
    sub_node = LlmNode(
        name="node_name",
        llm_config=vllmconfig,
        prompt_template="How much is 6x7?",
        outputs=[StringProperty(title="text")],
    )
    subflow = Flow(
        name="flow_name",
        start_node=start_node,
        nodes=[start_node, sub_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(
                id="starttosub", name="start->sub", from_node=start_node, to_node=sub_node
            ),
            ControlFlowEdge(id="subtoend", name="sub->end", from_node=sub_node, to_node=end_node),
        ],
    )

    return ParallelMapNode(
        name="map_step", id="map_step", subflow=subflow, reducers={"text": ReductionMethod.APPEND}
    )


def test_can_serialize_and_deserialize_parallel_map_node(
    default_parallel_map_node: ParallelMapNode,
) -> None:
    serialized_node = AgentSpecSerializer().to_yaml(default_parallel_map_node)
    deserialized_node = AgentSpecDeserializer().from_yaml(serialized_node)
    assert isinstance(deserialized_node, ParallelMapNode)
    assert deserialized_node.reducers is not None and len(deserialized_node.reducers) == 1
    assert deserialized_node.reducers["text"] == ReductionMethod.APPEND
    assert deserialized_node._is_equal(
        default_parallel_map_node, fields_to_exclude=["min_agentspec_version"]
    )


def test_serializing_parallel_map_node_with_unsupported_version_raises(
    default_parallel_map_node: ParallelMapNode,
) -> None:
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecSerializer().to_yaml(
            default_parallel_map_node, agentspec_version=AgentSpecVersionEnum.v25_4_1
        )
