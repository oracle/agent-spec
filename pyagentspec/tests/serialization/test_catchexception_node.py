# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import CatchExceptionNode, EndNode, StartNode
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer


def test_can_serialize_and_deserialize_catchexception_node() -> None:
    in_property = StringProperty(title="in_prop")
    out_property = StringProperty(title="out_prop", default="")
    start_node = StartNode(name="start", inputs=[in_property])
    end_node = EndNode(name="end", outputs=[out_property])
    subflow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_end", from_node=start_node, to_node=end_node)
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="edge",
                source_node=start_node,
                source_output=in_property.title,
                destination_node=end_node,
                destination_input=out_property.title,
            ),
        ],
    )
    node = CatchExceptionNode(name="catch_node", subflow=subflow)
    serialized = AgentSpecSerializer().to_yaml(node)
    assert "component_type: CatchExceptionNode" in serialized
    deserialized = AgentSpecDeserializer().from_yaml(serialized)
    assert isinstance(deserialized, CatchExceptionNode)
    # Ignore min_agentspec_version in equality
    assert deserialized._is_equal(node, fields_to_exclude=["min_agentspec_version"])
