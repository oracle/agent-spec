# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode
from pyagentspec.flows.nodes.parallelflownode import ParallelFlowNode
from pyagentspec.property import Property
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum


def _create_flow(
    properties_type: str,
    input_properties_title_suffix: str = "_in",
    output_properties_title_suffix: str = "_out",
) -> Flow:
    in_property_1 = Property(
        json_schema={"title": "property_1" + input_properties_title_suffix, "type": properties_type}
    )
    in_property_2 = Property(
        json_schema={"title": "property_2" + input_properties_title_suffix, "type": properties_type}
    )
    out_property_2 = Property(
        json_schema={
            "title": "property_2" + output_properties_title_suffix,
            "type": properties_type,
        }
    )
    out_property_3 = Property(
        json_schema={
            "title": "property_3" + output_properties_title_suffix,
            "type": properties_type,
        }
    )
    start_node = StartNode(name="start_node", inputs=[in_property_1, in_property_2])
    end_node = EndNode(name="end_node", outputs=[out_property_2, out_property_3])
    return Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_end", from_node=start_node, to_node=end_node)
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="start_to_end",
                source_node=start_node,
                source_output="property_1" + input_properties_title_suffix,
                destination_node=end_node,
                destination_input="property_2" + output_properties_title_suffix,
            ),
            DataFlowEdge(
                name="start_to_end",
                source_node=start_node,
                source_output="property_2" + input_properties_title_suffix,
                destination_node=end_node,
                destination_input="property_3" + output_properties_title_suffix,
            ),
        ],
    )


@pytest.fixture
def default_parallel_flow_node() -> ParallelFlowNode:
    flow_1 = _create_flow("string", output_properties_title_suffix="_1")
    flow_2 = _create_flow(
        "integer", input_properties_title_suffix="_2", output_properties_title_suffix="_2"
    )
    flow_3 = _create_flow("string", output_properties_title_suffix="_3")
    return ParallelFlowNode(
        id="node_id",
        name="parallel_flow_node",
        subflows=[flow_1, flow_2, flow_3],
    )


def test_can_serialize_and_deserialize_parallel_flow_node(
    default_parallel_flow_node: ParallelFlowNode,
) -> None:

    serialized_node = AgentSpecSerializer().to_yaml(default_parallel_flow_node)
    assert "component_type: ParallelFlowNode" in serialized_node
    assert "parallel_flow_node" in serialized_node

    deserialized_node = AgentSpecDeserializer().from_yaml(serialized_node)
    assert isinstance(deserialized_node, ParallelFlowNode)
    assert deserialized_node._is_equal(
        default_parallel_flow_node, fields_to_exclude=["min_agentspec_version"]
    )


def test_serializing_parallel_flow_node_with_unsupported_version_raises(
    default_parallel_flow_node: ParallelFlowNode,
) -> None:
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecSerializer().to_yaml(
            default_parallel_flow_node, agentspec_version=AgentSpecVersionEnum.v25_4_1
        )
