# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.parallelflownode import ParallelFlowNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.property import Property


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


def test_parallel_flow_node_merges_inputs() -> None:
    flow_1 = _create_flow(
        "string", input_properties_title_suffix="_1", output_properties_title_suffix="_1"
    )
    flow_2 = _create_flow(
        "string", input_properties_title_suffix="_2", output_properties_title_suffix="_2"
    )
    flow_3 = _create_flow(
        "string", input_properties_title_suffix="_3", output_properties_title_suffix="_3"
    )
    parallel_flow_node = ParallelFlowNode(
        name="parallel_flow_node", subflows=[flow_1, flow_2, flow_3]
    )
    assert parallel_flow_node.inputs == flow_1.inputs + flow_2.inputs + flow_3.inputs
    assert parallel_flow_node.outputs == flow_1.outputs + flow_2.outputs + flow_3.outputs


def test_parallel_flow_node_deduplicates_inputs() -> None:
    flow_1 = _create_flow("string", output_properties_title_suffix="_1")
    flow_2 = _create_flow("string", output_properties_title_suffix="_2")
    flow_3 = _create_flow("string", output_properties_title_suffix="_3")
    parallel_flow_node = ParallelFlowNode(
        name="parallel_flow_node", subflows=[flow_1, flow_2, flow_3]
    )
    assert parallel_flow_node.inputs == flow_1.inputs
    assert parallel_flow_node.outputs == flow_1.outputs + flow_2.outputs + flow_3.outputs


def test_parallel_flow_node_raises_if_inputs_have_same_names_but_different_types() -> None:
    flow_1 = _create_flow("string", input_properties_title_suffix="")
    flow_2 = _create_flow("integer", input_properties_title_suffix="")
    with pytest.raises(ValueError, match="have inputs with the same name"):
        _ = ParallelFlowNode(name="parallel_flow_node", subflows=[flow_1, flow_2])


def test_parallel_flow_node_raises_if_outputs_have_same_names() -> None:
    flow_1 = _create_flow("string", output_properties_title_suffix="")
    flow_2 = _create_flow("string", output_properties_title_suffix="")
    with pytest.raises(ValueError, match="have outputs with the same name"):
        _ = ParallelFlowNode(name="parallel_flow_node", subflows=[flow_1, flow_2])
