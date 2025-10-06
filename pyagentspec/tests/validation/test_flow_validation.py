# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

from typing import List, Tuple

import pytest

from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes.branchingnode import BranchingNode
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.flows.nodes.toolnode import ToolNode
from pyagentspec.property import (
    BooleanProperty,
    DictProperty,
    FloatProperty,
    IntegerProperty,
    ListProperty,
    ObjectProperty,
    Property,
    StringProperty,
    UnionProperty,
)
from pyagentspec.tools.clienttool import ClientTool


@pytest.fixture
def nodes() -> Tuple[Node, Node, Node, Node]:
    city_input = StringProperty(
        title="city_name",
        default="zurich",
    )
    weather_output = StringProperty(title="forecast")

    weather_tool = ClientTool(
        id="weather_tool",
        name="get_weather",
        description="Gets the weather in specified city",
        inputs=[city_input],
        outputs=[weather_output],
    )

    start_node = StartNode(inputs=[city_input], name="TheNameOfTheStartNode")
    tool_node = ToolNode(name="TheNameOfTheToolNode", tool=weather_tool)
    other_tool_node = ToolNode(name="TheNameOfTheOtherToolNode", tool=weather_tool)
    end_node = EndNode(outputs=[weather_output], name="TheNameOfTheEndNode")
    return (start_node, tool_node, other_tool_node, end_node)


def test_flow_init_raises_when_control_edge_source_node_is_missing(
    nodes: Tuple[Node, Node, Node, Node],
) -> None:
    start_node, tool_node, other_tool_node, end_node = nodes
    with pytest.raises(
        ValueError,
        match=(
            "A control flow edge was defined, but the flow does not contain"
            " the source node 'TheNameOfTheOtherToolNode'"
        ),
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, tool_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node),
                # EXTRA EDGE
                ControlFlowEdge(name="edge", from_node=other_tool_node, to_node=end_node),
            ],
            data_flow_connections=[
                DataFlowEdge(
                    name="edge",
                    source_node=start_node,
                    source_output="city_name",
                    destination_node=tool_node,
                    destination_input="city_name",
                ),
                DataFlowEdge(
                    name="edge",
                    source_node=tool_node,
                    source_output="forecast",
                    destination_node=end_node,
                    destination_input="forecast",
                ),
            ],
        )


def test_flow_init_raises_when_control_edge_destination_node_is_missing(
    nodes: Tuple[Node, Node, Node, Node],
) -> None:
    start_node, tool_node, other_tool_node, end_node = nodes
    with pytest.raises(
        ValueError,
        match=(
            "A control flow edge was defined, but the flow does not contain"
            " the destination node 'TheNameOfTheOtherToolNode'"
        ),
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, tool_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node),
                # EXTRA EDGE
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=other_tool_node),
            ],
            data_flow_connections=[
                DataFlowEdge(
                    name="edge",
                    source_node=start_node,
                    source_output="city_name",
                    destination_node=tool_node,
                    destination_input="city_name",
                ),
                DataFlowEdge(
                    name="edge",
                    source_node=tool_node,
                    source_output="forecast",
                    destination_node=end_node,
                    destination_input="forecast",
                ),
            ],
        )


def test_flow_init_raises_when_data_edge_source_node_is_missing(
    nodes: Tuple[Node, Node, Node, Node],
) -> None:
    start_node, tool_node, other_tool_node, end_node = nodes
    with pytest.raises(
        ValueError,
        match=(
            "A data flow edge was defined, but the flow does not contain"
            " the source node 'TheNameOfTheOtherToolNode'"
        ),
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, tool_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node),
            ],
            data_flow_connections=[
                DataFlowEdge(
                    name="edge",
                    source_node=start_node,
                    source_output="city_name",
                    destination_node=tool_node,
                    destination_input="city_name",
                ),
                DataFlowEdge(
                    name="edge",
                    source_node=tool_node,
                    source_output="forecast",
                    destination_node=end_node,
                    destination_input="forecast",
                ),
                # EXTRA EDGE
                DataFlowEdge(
                    name="edge",
                    source_node=other_tool_node,
                    source_output="forecast",
                    destination_node=end_node,
                    destination_input="forecast",
                ),
            ],
        )


def test_flow_init_raises_when_data_edge_destination_node_is_missing(
    nodes: Tuple[Node, Node, Node, Node],
) -> None:
    start_node, tool_node, other_tool_node, end_node = nodes
    with pytest.raises(
        ValueError,
        match=(
            "A data flow edge was defined, but the flow does not contain"
            " the destination node 'TheNameOfTheOtherToolNode'"
        ),
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, tool_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node),
            ],
            data_flow_connections=[
                DataFlowEdge(
                    name="edge",
                    source_node=start_node,
                    source_output="city_name",
                    destination_node=tool_node,
                    destination_input="city_name",
                ),
                DataFlowEdge(
                    name="edge",
                    source_node=tool_node,
                    source_output="forecast",
                    destination_node=end_node,
                    destination_input="forecast",
                ),
                # EXTRA EDGE
                DataFlowEdge(
                    name="edge",
                    source_node=start_node,
                    source_output="city_name",
                    destination_node=other_tool_node,
                    destination_input="city_name",
                ),
            ],
        )


@pytest.fixture
def start_tool_end_nodes() -> Tuple[StartNode, ToolNode, EndNode]:
    city_input = StringProperty(
        title="city_name",
        default="zurich",
    )
    weather_output = StringProperty(title="forecast")

    weather_tool = ClientTool(
        id="weather_tool",
        name="get_weather",
        description="Gets the weather in specified city",
        inputs=[city_input],
        outputs=[weather_output],
    )

    start_node = StartNode(inputs=[city_input], name="Start")
    tool_node = ToolNode(name="Tool", tool=weather_tool)
    end_node = EndNode(outputs=[weather_output], name="End")
    return start_node, tool_node, end_node


def test_flow_raises_if_no_startnode(
    start_tool_end_nodes: Tuple[StartNode, ToolNode, EndNode],
) -> None:
    start_node, tool_node, end_node = start_tool_end_nodes
    # Remove StartNode from list
    with pytest.raises(
        ValueError,
        match="A Flow should be composed of exactly one StartNode,.*contains 0",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[tool_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node),
            ],
            data_flow_connections=[],
        )


def test_flow_raises_if_multiple_startnodes(
    start_tool_end_nodes: Tuple[StartNode, ToolNode, EndNode],
) -> None:
    start_node, tool_node, end_node = start_tool_end_nodes
    another_start_node = StartNode(inputs=None, name="OtherStartNode")
    with pytest.raises(
        ValueError,
        match="A Flow should be composed of exactly one StartNode,.*contains 2",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, another_start_node, tool_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node),
            ],
            data_flow_connections=[],
        )


def test_flow_raises_if_start_node_instance_does_not_match_list(
    start_tool_end_nodes: Tuple[StartNode, ToolNode, EndNode],
) -> None:
    start_node, tool_node, end_node = start_tool_end_nodes
    # In start_node param pass a different StartNode instance than in the nodes list
    another_start_node = StartNode(inputs=start_node.inputs, name="Start")
    with pytest.raises(
        ValueError,
        match=(
            "The ``start_node`` node is not matching the start node from the "
            "list of nodes in the flow ``nodes``"
        ),
    ):
        Flow(
            name="Flow",
            start_node=another_start_node,
            nodes=[start_node, tool_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=another_start_node, to_node=tool_node),
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node),
            ],
            data_flow_connections=[],
        )


def test_flow_raises_if_start_node_has_not_exactly_one_outgoing_cf_edge(
    start_tool_end_nodes: Tuple[StartNode, ToolNode, EndNode],
) -> None:
    start_node, tool_node, end_node = start_tool_end_nodes
    # No edges from start_node
    with pytest.raises(
        ValueError,
        match="The ``start_node`` should have exactly one outgoing control flow edge, found 0",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, tool_node, end_node],
            control_flow_connections=[
                # No edge from the start_node
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node)
            ],
            data_flow_connections=[],
        )
    # Two outgoing edges from start_node
    with pytest.raises(
        ValueError,
        match="The ``start_node`` should have exactly one outgoing control flow edge, found 2",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, tool_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
                ControlFlowEdge(name="edge", from_node=start_node, to_node=end_node),
            ],
            data_flow_connections=[],
        )


def test_flow_raises_if_cf_edge_points_to_startnode(
    start_tool_end_nodes: Tuple[StartNode, ToolNode, EndNode],
) -> None:
    start_node, _, end_node = start_tool_end_nodes
    branching = BranchingNode(name="node_name", mapping={"1": "default", "2": "default"})
    with pytest.raises(
        ValueError,
        match="Transitions to StartNode is not accepted",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, branching, end_node],
            control_flow_connections=[
                # Edge to StartNode is forbidden
                ControlFlowEdge(name="edge", from_node=start_node, to_node=branching),
                ControlFlowEdge(name="edge", from_node=branching, to_node=start_node),
                ControlFlowEdge(name="edge", from_node=branching, to_node=end_node),
            ],
            data_flow_connections=[],
        )


def test_flow_raises_if_no_endnode(
    start_tool_end_nodes: Tuple[StartNode, ToolNode, EndNode],
) -> None:
    start_node, tool_node, end_node = start_tool_end_nodes
    with pytest.raises(
        ValueError,
        match="A Flow should be composed of at least one EndNode but didn't find any in ``nodes``",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, tool_node],  # no end node
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
            ],
            data_flow_connections=[],
        )


def test_flow_raises_if_endnode_has_no_incoming_cf_edge(
    start_tool_end_nodes: Tuple[StartNode, ToolNode, EndNode],
) -> None:
    start_node, tool_node, end_node = start_tool_end_nodes
    with pytest.raises(
        ValueError,
        match=(
            "Found an end node without any incoming control flow edge, "
            r"which is not permitted \(node is.*End"
        ),
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, tool_node, end_node],
            control_flow_connections=[
                # No edge to end_node at all
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
            ],
            data_flow_connections=[],
        )


def test_flow_raises_if_cf_edge_starts_from_endnode(
    start_tool_end_nodes: Tuple[StartNode, ToolNode, EndNode],
) -> None:
    start_node, tool_node, end_node = start_tool_end_nodes
    with pytest.raises(
        ValueError,
        match="Transitions from EndNode is not accepted.",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, tool_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
                ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node),
                # Bad: edge from EndNode
                ControlFlowEdge(name="edge", from_node=end_node, to_node=tool_node),
            ],
            data_flow_connections=[],
        )


def test_flow_raises_if_output_name_is_not_in_any_endnode() -> None:
    start_node = StartNode(name="start")
    end_node = EndNode(name="end", outputs=[StringProperty(title="output_a")])
    with pytest.raises(
        ValueError,
        match="Flow output named `output_b` does not have a default value "
        "and it does not appear in every EndNode with the expected type",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=end_node),
            ],
            data_flow_connections=[],
            outputs=[StringProperty(title="output_b")],
        )


def test_flow_raises_if_output_type_does_not_match_endnode() -> None:
    start_node = StartNode(name="start")
    end_node = EndNode(name="end", outputs=[StringProperty(title="output_a")])
    with pytest.raises(
        ValueError,
        match="Flow output named `output_a` does not have a default value "
        "and it does not appear in every EndNode with the expected type",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, end_node],
            control_flow_connections=[
                ControlFlowEdge(name="edge", from_node=start_node, to_node=end_node),
            ],
            data_flow_connections=[],
            outputs=[FloatProperty(title="output_a")],
        )


def test_flow_raises_if_types_of_output_with_same_name_do_not_match_in_all_endnodes() -> None:
    start_node = StartNode(name="start")
    branching_node = BranchingNode(name="branching", mapping={"1": "branch_1", "2": "branch_2"})
    end_node_1 = EndNode(name="end_1", outputs=[StringProperty(title="output_a")])
    end_node_2 = EndNode(name="end_2", outputs=[FloatProperty(title="output_a")])
    with pytest.raises(
        ValueError,
        match="Two EndNode outputs have the same name `output_a`, but different types",
    ):
        Flow(
            name="Flow",
            start_node=start_node,
            nodes=[start_node, branching_node, end_node_1, end_node_2],
            control_flow_connections=[
                ControlFlowEdge(name="edge1", from_node=start_node, to_node=branching_node),
                ControlFlowEdge(
                    name="edge2",
                    from_node=branching_node,
                    from_branch="branch_1",
                    to_node=end_node_1,
                ),
                ControlFlowEdge(
                    name="edge3",
                    from_node=branching_node,
                    from_branch="branch_2",
                    to_node=end_node_2,
                ),
            ],
            data_flow_connections=[],
            outputs=[FloatProperty(title="output_a")],
        )


def test_flow_with_output_that_does_not_appear_in_all_endnodes_can_be_created() -> None:
    start_node = StartNode(name="start")
    branching_node = BranchingNode(name="branching", mapping={"1": "branch_1", "2": "branch_2"})
    end_node_1 = EndNode(name="end_1", outputs=[StringProperty(title="output_a")])
    end_node_2 = EndNode(name="end_2", outputs=[StringProperty(title="output_b")])
    end_node_3 = EndNode(name="end_3", outputs=[StringProperty(title="output_c")])
    flow = Flow(
        name="Flow",
        start_node=start_node,
        nodes=[start_node, branching_node, end_node_1, end_node_2, end_node_3],
        control_flow_connections=[
            ControlFlowEdge(name="edge1", from_node=start_node, to_node=branching_node),
            ControlFlowEdge(
                name="edge2", from_node=branching_node, from_branch="branch_1", to_node=end_node_1
            ),
            ControlFlowEdge(
                name="edge3", from_node=branching_node, from_branch="branch_2", to_node=end_node_2
            ),
            ControlFlowEdge(
                name="edge4", from_node=branching_node, from_branch="default", to_node=end_node_3
            ),
        ],
        data_flow_connections=[],
        outputs=[StringProperty(title="output_a", default="a")],
    )
    assert isinstance(flow, Flow)
    assert isinstance(flow.outputs, list)
    assert len(flow.outputs) == 1
    assert flow.outputs[0] == StringProperty(title="output_a", default="a")


def test_flow_with_output_that_appears_in_all_endnodes_does_not_require_default() -> None:
    start_node = StartNode(name="start")
    branching_node = BranchingNode(name="branching", mapping={"1": "branch_1", "2": "branch_2"})
    end_node_1 = EndNode(
        name="end_1", outputs=[StringProperty(title="output_a"), StringProperty(title="output_c")]
    )
    end_node_2 = EndNode(
        name="end_2", outputs=[StringProperty(title="output_b"), StringProperty(title="output_c")]
    )
    end_node_3 = EndNode(name="end_3", outputs=[StringProperty(title="output_c")])
    flow = Flow(
        name="Flow",
        start_node=start_node,
        nodes=[start_node, branching_node, end_node_1, end_node_2, end_node_3],
        control_flow_connections=[
            ControlFlowEdge(name="edge1", from_node=start_node, to_node=branching_node),
            ControlFlowEdge(
                name="edge2", from_node=branching_node, from_branch="branch_1", to_node=end_node_1
            ),
            ControlFlowEdge(
                name="edge3", from_node=branching_node, from_branch="branch_2", to_node=end_node_2
            ),
            ControlFlowEdge(
                name="edge4", from_node=branching_node, from_branch="default", to_node=end_node_3
            ),
        ],
        data_flow_connections=[],
        outputs=[StringProperty(title="output_c")],
    )
    assert isinstance(flow, Flow)
    assert isinstance(flow.outputs, list)
    assert len(flow.outputs) == 1
    assert flow.outputs[0] == StringProperty(title="output_c")


def build_flow_with_given_data_edge_info(
    edge_name: str, source_output: str, destination_input: str
) -> Flow:
    attribute_1_property = StringProperty(title="attribute_1")
    attribute_2_property = FloatProperty(title="attribute_2")
    attribute_3_property = UnionProperty(
        title="attribute_3", any_of=[FloatProperty(), IntegerProperty()], default=2.0
    )
    start_node = StartNode(name="start", inputs=[attribute_1_property, attribute_2_property])
    end_node = EndNode(
        name="end", outputs=[attribute_1_property, attribute_2_property, attribute_3_property]
    )
    return Flow(
        name="Flow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="edge1", from_node=start_node, to_node=end_node)
        ],
        data_flow_connections=[
            DataFlowEdge(
                name=edge_name,
                source_node=start_node,
                source_output=source_output,
                destination_node=end_node,
                destination_input=destination_input,
            )
        ],
    )


def test_wrong_data_flow_connection_property_name_raise() -> None:
    with pytest.raises(
        ValueError,
        match=(
            f"Flow data connection named `wrong_source_property_name` is connected to a property "
            f"named `nonexisting_attribute` of the source node `start`, "
            f"but the node does not have any property with that name."
        ),
    ):
        build_flow_with_given_data_edge_info(
            edge_name="wrong_source_property_name",
            source_output="nonexisting_attribute",
            destination_input="attribute_1",
        )

    with pytest.raises(
        ValueError,
        match=(
            f"Flow data connection named `wrong_destination_property_name` is connected to a property "
            f"named `nonexisting_attribute` of the destination node `end`, "
            f"but the node does not have any property with that name."
        ),
    ):
        build_flow_with_given_data_edge_info(
            edge_name="wrong_destination_property_name",
            source_output="attribute_1",
            destination_input="nonexisting_attribute",
        )


def test_source_data_flow_connection_property_type_contained_in_destination_property_type_works() -> (
    None
):
    # Attribute 2 has a type contained in attribute 3
    flow = build_flow_with_given_data_edge_info(
        edge_name="correct_connection",
        source_output="attribute_2",
        destination_input="attribute_3",
    )
    assert flow.data_flow_connections is not None
    assert len(flow.data_flow_connections) == 1
    assert flow.data_flow_connections[0].name == "correct_connection"


def test_wrong_data_flow_connection_property_type_raise() -> None:
    with pytest.raises(
        ValueError,
        match=(
            f"Flow data connection named `wrong_property_type` connects "
            f"two properties with incompatible types."
        ),
    ):
        # Type of attribute 1 is not in the types of attribute 3
        build_flow_with_given_data_edge_info(
            edge_name="wrong_property_type",
            source_output="attribute_1",
            destination_input="attribute_3",
        )

    with pytest.raises(
        ValueError,
        match=(
            f"Flow data connection named `wrong_property_type` connects "
            f"two properties with incompatible types."
        ),
    ):
        # Type of attribute 1 and attribute 2 are different
        build_flow_with_given_data_edge_info(
            edge_name="wrong_property_type",
            source_output="attribute_1",
            destination_input="attribute_2",
        )


@pytest.mark.parametrize(
    "from_property, to_property",
    [
        (StringProperty(title="A"), StringProperty(title="B")),
        (IntegerProperty(title="C"), StringProperty(title="D")),
        (FloatProperty(title="E"), FloatProperty(title="F")),
        (IntegerProperty(title="E"), FloatProperty(title="F")),
        (FloatProperty(title="A"), IntegerProperty(title="B")),
        (BooleanProperty(title="C"), BooleanProperty(title="D")),
        (BooleanProperty(title="C"), IntegerProperty(title="D")),
        (FloatProperty(title="C"), BooleanProperty(title="D")),
        (
            ListProperty(item_type=BooleanProperty(title="G")),
            ListProperty(item_type=BooleanProperty(title="H")),
        ),
        (
            ListProperty(item_type=BooleanProperty(title="G")),
            ListProperty(item_type=StringProperty(title="H")),
        ),
        (
            DictProperty(value_type=ListProperty(item_type=BooleanProperty(title="G"))),
            StringProperty(title="H"),
        ),
        (
            DictProperty(value_type=ListProperty(item_type=BooleanProperty(title="I"))),
            DictProperty(value_type=StringProperty(title="J")),
        ),
        (
            DictProperty(value_type=ListProperty(item_type=BooleanProperty(title="K"))),
            DictProperty(value_type=ListProperty(item_type=IntegerProperty(title="L"))),
        ),
        (
            ObjectProperty(
                properties={
                    "a": StringProperty(title="A"),
                    "b": StringProperty(title="B"),
                    "c": StringProperty(title="C"),
                }
            ),
            ObjectProperty(properties={"a": StringProperty(title="A")}),
        ),
        (
            ObjectProperty(
                properties={
                    "a": BooleanProperty(title="A"),
                    "b": StringProperty(title="B"),
                    "c": StringProperty(title="C"),
                }
            ),
            ObjectProperty(properties={"a": StringProperty(title="A")}),
        ),
        (
            UnionProperty(any_of=[StringProperty(title="A"), BooleanProperty(title="B")]),
            StringProperty(title="C"),
        ),
        (
            StringProperty(title="C"),
            UnionProperty(any_of=[StringProperty(title="A"), BooleanProperty(title="B")]),
        ),
        (
            IntegerProperty(title="I"),
            Property(json_schema={}),
        ),
        (
            IntegerProperty(title="I"),
            Property(json_schema={"description": "some description"}),
        ),
    ],
)
def test_data_flow_edge_accepts_connecting_castable_types(from_property, to_property):
    start_node = StartNode(name="start", inputs=[from_property])
    end_node = EndNode(name="end", outputs=[to_property])
    edge = DataFlowEdge(
        name="edge",
        source_node=start_node,
        source_output=from_property.title,
        destination_node=end_node,
        destination_input=to_property.title,
    )
    assert edge


@pytest.mark.parametrize(
    "from_property, to_property",
    [
        (StringProperty(title="A"), IntegerProperty(title="B")),
        (StringProperty(title="A"), FloatProperty(title="B")),
        (StringProperty(title="A"), BooleanProperty(title="B")),
        (
            ListProperty(item_type=StringProperty(title="G")),
            ListProperty(item_type=BooleanProperty(title="H")),
        ),
        (
            DictProperty(value_type=ListProperty(item_type=StringProperty(title="K"))),
            DictProperty(value_type=ListProperty(item_type=IntegerProperty(title="L"))),
        ),
        (
            DictProperty(value_type=ListProperty(item_type=StringProperty(title="K"))),
            DictProperty(value_type=BooleanProperty(title="L")),
        ),
        (
            ObjectProperty(
                properties={
                    "a": BooleanProperty(title="A"),
                    "b": StringProperty(title="B"),
                    "c": StringProperty(title="C"),
                }
            ),
            ObjectProperty(properties={"d": StringProperty(title="A")}),
        ),
        (
            UnionProperty(any_of=[StringProperty(title="A"), BooleanProperty(title="B")]),
            BooleanProperty(title="C"),
        ),
    ],
)
def test_data_flow_edge_rejects_connecting_non_castable_types(from_property, to_property):
    start_node = StartNode(name="start", inputs=[from_property])
    end_node = EndNode(name="end", outputs=[to_property])
    with pytest.raises(ValueError, match=f"Flow data connection named `edge` connects ..."):
        DataFlowEdge(
            name="edge",
            source_node=start_node,
            source_output=from_property.title,
            destination_node=end_node,
            destination_input=to_property.title,
        )
