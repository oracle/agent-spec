# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode
from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.flows.nodes.mapnode import MapNode, ReductionMethod
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer


def test_can_serialize_and_deserialize_mapnode() -> None:
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

    node = MapNode(
        name="map_step", id="map_step", subflow=subflow, reducers={"text": ReductionMethod.APPEND}
    )

    serialized_node = AgentSpecSerializer().to_yaml(node)

    deserialized_node = AgentSpecDeserializer().from_yaml(serialized_node)
    assert isinstance(deserialized_node, MapNode)
    assert deserialized_node.reducers is not None and len(deserialized_node.reducers) == 1
    assert deserialized_node.reducers["text"] == ReductionMethod.APPEND
