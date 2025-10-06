# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.
import functools
import threading
from typing import Dict, List, Literal, Optional, Set, Tuple

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, BranchingNode, FlowNode, ToolNode
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.tools import ClientTool

from ..conftest import read_agentspec_config_file
from .conftest import assert_serialized_representations_are_equal


def timeout(
    seconds: int = 2,
    error_message: str = "Test exceeded timeout limit",
):
    """
    This decorator modifies a test such that it fails if running for more than `seconds` seconds.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result, exc = [None], [None]

            def runner():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exc[0] = e

            t = threading.Thread(target=runner)
            t.start()
            t.join(seconds)
            if t.is_alive():
                pytest.fail(error_message)
            if exc[0]:
                raise exc[0]
            return result[0]

        return wrapper

    return decorator


def test_can_serialize_flow(example_serialized_flow: str) -> None:
    vllmconfig = VllmConfig(id="vllm", name="agi1", model_id="agi_model1", url="http://some.where")
    node_12 = LlmNode(
        id="DUMMY_NODE_12",
        name="node12",
        llm_config=vllmconfig,
        prompt_template="something something",
        metadata=None,
    )
    node_3 = LlmNode(
        id="DUMMY_NODE_3",
        name="node3",
        llm_config=vllmconfig,
        prompt_template="something something else",
        metadata={},
    )

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

    tool_node = ToolNode(id="tool_node", name="tool_node", tool=weather_tool)

    start_node = StartNode(id="START_NODE", name="start_node")
    end_node = EndNode(id="end_node1", name="end node 1", outputs=[])

    control_flow_connections: List[ControlFlowEdge] = [
        ControlFlowEdge(id="startto12", name="start->12", from_node=start_node, to_node=node_12),
        ControlFlowEdge(id="12to3", name="12->3", from_node=node_12, to_node=node_3),
        ControlFlowEdge(id="3to4", name="3->4", from_node=node_3, to_node=tool_node),
        ControlFlowEdge(id="4toend", name="4->end", from_node=tool_node, to_node=end_node),
    ]

    flow = Flow(
        id="DUMMY_FLOW",
        name="flow",
        start_node=start_node,
        nodes=[start_node, node_12, node_12, node_3, tool_node, end_node],
        control_flow_connections=control_flow_connections,
        data_flow_connections=None,
    )
    serializer = AgentSpecSerializer()
    serialized_flow = serializer.to_yaml(flow)
    assert_serialized_representations_are_equal(serialized_flow, example_serialized_flow)


def test_can_serialize_flow_executing_agent(example_serialized_flow_executing_agent: str) -> None:
    vllmconfig = VllmConfig(id="vllm", name="agi1", model_id="agi_model1", url="http://some.where")
    agent = Agent(
        id="agent1234",
        name="Great agent",
        llm_config=vllmconfig,
        system_prompt="Always be polite",
    )
    start_node = StartNode(id="START_NODE", name="start_node")
    node_12 = AgentNode(id="agentnode1", name="executes an agent", agent=agent)
    node_3 = LlmNode(
        id="promptnode2", name="prompt node", llm_config=vllmconfig, prompt_template="Do {{x}}:"
    )
    node_4 = LlmNode(
        id="promptnode3",
        name="prompt node 2",
        llm_config=vllmconfig,
        prompt_template="What do you think of the answer {{y}}?",
    )
    end_node = EndNode(id="end_node1", name="end node 1")

    control_flow_connections: List[ControlFlowEdge] = [
        ControlFlowEdge(id="startto12", name="start->12", from_node=start_node, to_node=node_12),
        ControlFlowEdge(id="12to3", name="12->3", from_node=node_12, to_node=node_3),
        ControlFlowEdge(id="3to4", name="3->4", from_node=node_3, to_node=node_4),
        ControlFlowEdge(id="4toend", name="4->end", from_node=node_4, to_node=end_node),
    ]

    data_flow_connections = [
        DataFlowEdge(
            id="ptoy",
            name="prompt output to y",
            source_node=node_3,
            source_output="generated_text",
            destination_node=node_4,
            destination_input="y",
        )
    ]

    flow = Flow(
        id="DUMMY_FLOW",
        name="flow",
        start_node=start_node,
        nodes=[start_node, node_12, node_3, node_4, end_node],
        control_flow_connections=control_flow_connections,
        data_flow_connections=data_flow_connections,
    )
    serializer = AgentSpecSerializer()
    serialized_flow = serializer.to_yaml(flow)
    assert_serialized_representations_are_equal(
        serialized_flow, example_serialized_flow_executing_agent
    )


def test_can_serialize_flow_with_branching_node() -> None:
    input_1 = StringProperty(title="Input_1", default="yes")
    input_2 = StringProperty(title="Input_2", default="no")

    start_node = StartNode(
        id="lniwuebjsdvkc",
        name="Node 1",
        inputs=[input_1, input_2],
    )
    branching_node_1 = BranchingNode(
        id="724oiquh3hrj",
        name="Branching Node",
        mapping={
            "yes": "Yes",
            "no": "No",
            "maybe": "Maybe",
        },
        inputs=[input_1],
    )
    branching_node_2 = BranchingNode(
        id="0892u3jkjhdas",
        name="Branching Node 2",
        mapping={
            "yes": "Yes",
            "no": "No",
        },
        inputs=[input_2],
    )
    end_node_1 = EndNode(
        id="724893yhrj",
        name="End Node 1",
        outputs=[input_1],
    )
    end_node_2 = EndNode(
        id="123724893yhrj",
        name="End Node 2",
        outputs=[input_2],
    )
    end_node_3 = EndNode(
        id="321724893yhrj",
        name="End Node 3",
        outputs=[],
    )

    nodes = [
        start_node,
        branching_node_1,
        branching_node_2,
        end_node_1,
        end_node_2,
        end_node_3,
    ]

    # Control flow edges
    control_edge_1 = ControlFlowEdge(
        id="nh32tewsaicjkl",
        name="ctrl_edge_1",
        from_node=start_node,
        to_node=branching_node_1,
    )
    control_edge_2 = ControlFlowEdge(
        id="28yu3egh",
        name="ctrl_edge_2",
        from_node=branching_node_1,
        from_branch="yes",
        to_node=end_node_1,
    )
    control_edge_3 = ControlFlowEdge(
        id="09b4h321k",
        name="ctrl_edge_3",
        from_node=branching_node_1,
        from_branch="no",
        to_node=end_node_3,
    )
    control_edge_4 = ControlFlowEdge(
        id="09b4hq2e321k",
        name="ctrl_edge_4",
        from_node=branching_node_1,
        from_branch="maybe",
        to_node=branching_node_2,
    )
    control_edge_5 = ControlFlowEdge(
        id="0980123y321k",
        name="ctrl_edge_5",
        from_node=branching_node_2,
        from_branch="yes",
        to_node=end_node_2,
    )
    control_edge_6 = ControlFlowEdge(
        id="nbhj234g23y321k",
        name="ctrl_edge_6",
        from_node=branching_node_2,
        from_branch="no",
        to_node=end_node_3,
    )
    control_edges: List[ControlFlowEdge] = [
        control_edge_1,
        control_edge_2,
        control_edge_3,
        control_edge_4,
        control_edge_5,
        control_edge_6,
    ]

    # Data flow edges
    data_edge_1 = DataFlowEdge(
        id="buhdgsbjmn",
        name="data_edge_1",
        source_node=start_node,
        source_output="Input_1",
        destination_node=branching_node_1,
        destination_input="Input_1",
    )
    data_edge_2 = DataFlowEdge(
        id="67uyh5423hje",
        name="data_edge_2",
        source_node=start_node,
        source_output="Input_2",
        destination_node=branching_node_2,
        destination_input="Input_2",
    )
    data_edge_3 = DataFlowEdge(
        id="722njqbakhcsa",
        name="data_edge_3",
        source_node=start_node,
        source_output="Input_1",
        destination_node=end_node_1,
        destination_input="Input_1",
    )
    data_edge_4 = DataFlowEdge(
        id="8h4k23jhmans",
        name="data_edge_4",
        source_node=start_node,
        source_output="Input_2",
        destination_node=end_node_2,
        destination_input="Input_2",
    )
    data_edges = [
        data_edge_1,
        data_edge_2,
        data_edge_3,
        data_edge_4,
    ]

    flow = Flow(
        id="mmnhagawse98273",
        name="Example branching test flow",
        start_node=start_node,
        nodes=nodes,
        control_flow_connections=control_edges,
        data_flow_connections=data_edges,
        inputs=[input_1, input_2],
        outputs=[input_1, input_2],
        metadata=None,
    )

    serializer = AgentSpecSerializer()
    serialized_flow = serializer.to_yaml(flow)
    example_serialized_flow = read_agentspec_config_file(
        "example_serialized_flow_with_branching_node.yaml"
    )

    assert_serialized_representations_are_equal(serialized_flow, example_serialized_flow)


def test_can_deserialize_flow(example_serialized_flow: str) -> None:
    deserializer = AgentSpecDeserializer()
    flow = deserializer.from_yaml(example_serialized_flow)
    assert isinstance(flow, Flow)
    assert len(flow.nodes) == 6
    assert flow.nodes[1] is flow.nodes[2]
    assert flow.nodes[2] is not flow.nodes[3]


def test_can_deserialized_flow_can_be_edited_with_deduplication(
    example_serialized_flow: str,
) -> None:
    flow = AgentSpecDeserializer().from_yaml(example_serialized_flow)
    assert isinstance(flow, Flow)


def test_can_deserialize_deeply_nested_flow_component(
    example_serialized_flow_executing_agent: str,
) -> None:
    flow = AgentSpecDeserializer().from_yaml(example_serialized_flow_executing_agent)
    assert isinstance(flow, Flow)
    assert len(flow.nodes) == 5
    # The below asserts ensure the correct deduplication during deserialization
    assert flow.control_flow_connections[0].from_node is flow.start_node
    assert flow.control_flow_connections[0].from_node is flow.nodes[0]
    # The below asserts ensure the correct deserialization of the deeply nested components
    assert isinstance(flow.nodes[1], AgentNode)
    assert isinstance(flow.nodes[1].agent, Agent)
    assert isinstance(flow.nodes[1].agent.llm_config, VllmConfig)
    assert flow.nodes[1].agent.llm_config.model_id == "agi_model1"


def test_can_deserialize_flow_with_properties(example_serialized_flow_with_properties: str) -> None:
    deserializer = AgentSpecDeserializer()
    flow = deserializer.from_yaml(example_serialized_flow_with_properties)
    assert isinstance(flow, Flow)
    assert len(flow.nodes) == 3
    assert len(flow.control_flow_connections) == 2
    assert flow.inputs is not None and len(flow.inputs) == 2
    assert flow.outputs is not None and len(flow.outputs) == 2


def test_can_deserialize_flow_with_branching() -> None:
    serialized_agent = read_agentspec_config_file(
        "example_serialized_flow_with_branching_node.yaml"
    )
    deserializer = AgentSpecDeserializer()
    flow = deserializer.from_yaml(serialized_agent)
    assert isinstance(flow, Flow)
    assert len(flow.nodes) == 6
    assert len(flow.control_flow_connections) == 6
    assert flow.data_flow_connections is not None and len(flow.data_flow_connections) == 4
    assert flow.inputs is not None and len(flow.inputs) == 2
    assert flow.outputs is not None and len(flow.outputs) == 2


def test_flow_inferred_outputs_is_the_set_of_outputs_available_in_all_endnodes() -> None:
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
    )
    assert isinstance(flow, Flow)
    assert isinstance(flow.outputs, list)
    assert len(flow.outputs) == 1
    assert flow.outputs[0].json_schema["title"] == "output_c"


def get_nested_flow(N: int, holder: Optional[Dict[Literal["count"], int]] = None):
    start_node = StartNode(id="ID_start_node", name="start_node")
    end_node = EndNode(id="ID_end_node", name="end_node")
    if holder is not None:
        holder["count"] = 0

    flow_node_a, flow_node_b, flow_node_c = [
        FlowNode(
            id=f"ID_FlowNode_{N}_{x}",
            name="node",
            subflow=Flow(
                id=f"ID_Flow_{N}_{x}",
                name=f"Flow_{N}_{x}",
                start_node=start_node,
                nodes=[start_node, end_node],
                control_flow_connections=[
                    ControlFlowEdge(
                        id=f"ID_edge_{N}_{x}", name="edge", from_node=start_node, to_node=end_node
                    )
                ],
                data_flow_connections=[],
            ),
        )
        for x in "abc"
    ]
    if holder is not None:
        for _ in "abc":
            holder["count"] += 3

    for i in range(N - 1, -1, -1):
        flow_node_a, flow_node_b, flow_node_c = [
            FlowNode(
                id=f"ID_FlowNode_{i}_{x}",
                name="node",
                subflow=Flow(
                    id=f"ID_Flow_{i}_{x}",
                    name=f"Flow_{i}_{x}",
                    start_node=start_node,
                    nodes=[start_node, flow_node_a, flow_node_b, flow_node_c, end_node],
                    control_flow_connections=[
                        ControlFlowEdge(
                            id=f"ID_edge_{i}_{x}_1",
                            name="edge",
                            from_node=start_node,
                            to_node=flow_node_a,
                        ),
                        ControlFlowEdge(
                            id=f"ID_edge_{i}_{x}_2",
                            name="edge",
                            from_node=flow_node_a,
                            to_node=flow_node_b,
                        ),
                        ControlFlowEdge(
                            id=f"ID_edge_{i}_{x}_3",
                            name="edge",
                            from_node=flow_node_b,
                            to_node=flow_node_c,
                        ),
                        ControlFlowEdge(
                            id=f"ID_edge_{i}_{x}_4",
                            name="edge",
                            from_node=flow_node_c,
                            to_node=end_node,
                        ),
                    ],
                    data_flow_connections=[],
                ),
            )
            for x in "abc"
        ]
        if holder is not None:
            for _ in "abc":
                holder["count"] += 6

    if holder is not None:
        holder["count"] += 6
    return Flow(
        id=f"ID_Flow_Omega",
        name=f"Flow_Omega",
        start_node=start_node,
        nodes=[start_node, flow_node_a, flow_node_b, flow_node_c, end_node],
        control_flow_connections=[
            ControlFlowEdge(
                id="ID_edge_omega_1", name="edge", from_node=start_node, to_node=flow_node_a
            ),
            ControlFlowEdge(
                id="ID_edge_omega_2", name="edge", from_node=flow_node_a, to_node=flow_node_b
            ),
            ControlFlowEdge(
                id="ID_edge_omega_3", name="edge", from_node=flow_node_b, to_node=flow_node_c
            ),
            ControlFlowEdge(
                id="ID_edge_omega_4", name="edge", from_node=flow_node_c, to_node=end_node
            ),
        ],
        data_flow_connections=[],
    )


import time


@timeout(
    seconds=20,
    error_message="Encountered time complexity issue when calling `to_yaml` and `from_yaml` on a deeply nested component",
)
@pytest.mark.parametrize("size", [4, 30])
def test_deeply_nested_flow_can_be_serde(size: int) -> None:
    flow_omega = get_nested_flow(size)
    ptime = time.time()
    serialized_flow_omega = AgentSpecSerializer().to_yaml(flow_omega)
    print(f"Serialized in {time.time()-ptime:.2f}")
    assert (
        serialized_flow_omega.count("ID_Flow_4_b") == 1
    )  # This name should appear just once in refs

    ptime = time.time()
    deserialized_flow = AgentSpecDeserializer().from_yaml(serialized_flow_omega)
    print(f"Deserialized in {time.time()-ptime:.2f}")
    assert isinstance(deserialized_flow, Flow)
    assert deserialized_flow == flow_omega


@timeout(
    error_message="Encountered time complexity issue when calling `==` on deeply nested components"
)
@pytest.mark.parametrize(
    "size_a, size_b",
    [
        (0, 0),
        (1, 1),
        (0, 1),
        (1, 0),
        (1, 2),
        (3, 3),
        (41, 41),
        (41, 43),
    ],
)
def test_deeply_nested_flows_can_be_compared(size_a: int, size_b: int) -> None:
    if size_a == size_b:
        assert get_nested_flow(size_a) == get_nested_flow(size_b)
    else:
        assert get_nested_flow(size_a) != get_nested_flow(size_b)


@timeout(
    error_message="Encountered time complexity issue when calling `repr` on a deeply nested component"
)
@pytest.mark.parametrize("size", [4, 30])
def test_deeply_nested_flows_can_be_repr(size) -> None:
    flow_repr = repr(get_nested_flow(size))
    assert "Flow_Omega" in flow_repr


@timeout(
    error_message="Encountered time complexity issue when calling `str` on a deeply nested component"
)
@pytest.mark.parametrize("size", [4, 30])
def test_deeply_nested_flows_can_be_str(size) -> None:
    flow_str = str(get_nested_flow(size))
    assert "Flow_Omega" in flow_str


@timeout(
    error_message="Encountered time complexity issue when resolving min/max agentspec_versions on deeply nested components"
)
@pytest.mark.parametrize("size", [4, 30])
def test_agentspec_version_resolution_properly_traverses_all_components(size: int) -> None:
    holder: Dict[Literal["count"], int] = {}
    flow_omega = get_nested_flow(size, holder)
    node_count = holder["count"]
    min_visited: Set[str] = set()
    max_visited: Set[str] = set()
    flow_omega._get_min_agentspec_version_and_component(min_visited)
    flow_omega._get_max_agentspec_version_and_component(max_visited)
    assert (
        len(min_visited) == node_count
    ), "min_agentspec_version resolution didn't traverse all components"
    assert (
        len(max_visited) == node_count
    ), "max_agentspec_version resolution didn't traverse all components"
