# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json

import pytest

from pyagentspec.flows.edges import DataFlowEdge
from pyagentspec.flows.flowbuilder import FlowBuilder
from pyagentspec.flows.nodes import BranchingNode, EndNode, InputMessageNode, LlmNode, StartNode
from pyagentspec.property import StringProperty


def test_build_simple_flow_with_single_llm_node(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="llm", llm_config=default_llm_config, prompt_template="Hello"))
    builder.set_entry_point("llm")
    builder.set_finish_points("llm")
    flow = builder.build()

    # Basic structure checks
    node_names = {n.name for n in flow.nodes}
    assert "StartNode" in node_names
    assert "llm" in node_names
    assert any(n.name.startswith("EndNode_") for n in flow.nodes)
    # Should have: StartNode->llm and llm->EndNode
    assert len(flow.control_flow_connections) == 2
    assert len(flow.data_flow_connections) == 0


def test_build_linear_flow_with_explicit_edge(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="llm", llm_config=default_llm_config, prompt_template="Hello"))
    builder.add_node(LlmNode(name="llm2", llm_config=default_llm_config, prompt_template="Hello"))
    builder.add_edge("llm", "llm2")
    builder.set_entry_point("llm")
    # Mirrors the example: finish at 'llm' even though there is an edge to 'llm2'
    builder.set_finish_points("llm2")
    flow = builder.build()

    node_names = {n.name for n in flow.nodes}
    assert {"StartNode", "llm", "llm2", "EndNode_1"} == node_names
    assert any(n.name.startswith("EndNode_") for n in flow.nodes)
    # Edges: StartNode->llm, llm->llm2, llm2->EndNode
    assert len(flow.control_flow_connections) == 3


def test_add_sequence_builds_linear_flow(default_llm_config):
    builder = FlowBuilder()
    builder.add_sequence(
        [
            LlmNode(name="llm", llm_config=default_llm_config, prompt_template="Hello"),
            LlmNode(name="llm2", llm_config=default_llm_config, prompt_template="Hello"),
        ]
    )
    builder.set_entry_point("llm")
    builder.set_finish_points("llm2")
    flow = builder.build()

    node_names = {n.name for n in flow.nodes}
    assert "StartNode" in node_names
    assert "llm" in node_names
    assert "llm2" in node_names
    assert any(n.name.startswith("EndNode_") for n in flow.nodes)


def test_build_spec_returns_valid_json(default_llm_config):
    builder = FlowBuilder()
    builder.add_sequence(
        [
            LlmNode(name="llm", llm_config=default_llm_config, prompt_template="Hello"),
            LlmNode(name="llm2", llm_config=default_llm_config, prompt_template="Hello"),
        ]
    )
    builder.set_entry_point("llm")
    builder.set_finish_points("llm2")
    spec_json = builder.build_spec()
    parsed = json.loads(spec_json)
    assert isinstance(parsed, dict)
    assert parsed.get("name") == "Flow"


def test_flow_with_conditional_transition(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="llm", llm_config=default_llm_config, prompt_template="Hello"))
    builder.add_node(LlmNode(name="fail", llm_config=default_llm_config, prompt_template="FAIL"))
    builder.add_node(
        LlmNode(name="success", llm_config=default_llm_config, prompt_template="SUCCESS")
    )
    builder.add_conditional(
        "llm",
        LlmNode.DEFAULT_OUTPUT,
        {"success": "success", "fail": "fail"},
        default_destination="fail",
    )
    builder.set_entry_point("llm")
    builder.set_finish_points(["success", "fail"])
    flow = builder.build()

    # There should be a BranchingNode injected
    branch_nodes = [n for n in flow.nodes if isinstance(n, BranchingNode)]
    assert len(branch_nodes) == 1
    # Control edges include:
    # StartNode->llm, llm->branch, branch->success, branch->fail, branch->default(fail),
    # plus finish edges from success/fail (2)
    assert len(flow.control_flow_connections) == 7


def test_flow_with_data_connections(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(
        LlmNode(name="producer", llm_config=default_llm_config, prompt_template="Hello")
    )
    builder.add_node(
        LlmNode(
            name="consumer1", llm_config=default_llm_config, prompt_template="{{generated_text}}"
        )
    )
    builder.add_node(
        LlmNode(name="consumer2", llm_config=default_llm_config, prompt_template="{{also_value}}")
    )
    builder.add_edge("producer", "consumer1")
    builder.add_edge("producer", "consumer2")

    # Using the default output name for LlmNode.DEFAULT_OUTPUT
    builder.add_data_edge("producer", "consumer1", LlmNode.DEFAULT_OUTPUT)
    builder.add_data_edge("producer", "consumer2", (LlmNode.DEFAULT_OUTPUT, "also_value"))

    builder.set_entry_point("producer")
    builder.set_finish_points(["consumer1", "consumer2"])
    flow = builder.build()

    assert len(flow.data_flow_connections) == 2
    data_edges = {
        (e.source_node.name, e.destination_node.name, e.source_output, e.destination_input)
        for e in flow.data_flow_connections
    }
    assert ("producer", "consumer1", LlmNode.DEFAULT_OUTPUT, LlmNode.DEFAULT_OUTPUT) in data_edges
    assert ("producer", "consumer2", LlmNode.DEFAULT_OUTPUT, "also_value") in data_edges


def test_add_edge_raises_when_end_node_missing(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="a", llm_config=default_llm_config, prompt_template="x"))
    with pytest.raises(ValueError, match="End node 'b' not found"):
        builder.add_edge("a", "b")


def test_add_edge_raises_when_start_node_missing(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="b", llm_config=default_llm_config, prompt_template="x"))
    with pytest.raises(ValueError, match="Start node 'a' not found"):
        builder.add_edge("a", "b")


def test_add_edge_raises_on_length_mismatch_between_starts_and_branches(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="a", llm_config=default_llm_config, prompt_template="x"))
    builder.add_node(LlmNode(name="b", llm_config=default_llm_config, prompt_template="x"))
    # source_node has 2 entries; from_branch has 1
    with pytest.raises(ValueError, match="source_node and from_branch must have the same length"):
        builder.add_edge(source_node=["a", "a"], dest_node="b", from_branch=[None])


def test_add_node_raises_on_duplicate_name(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="dup", llm_config=default_llm_config, prompt_template="x"))
    with pytest.raises(ValueError, match="Node with name 'dup' already exists"):
        builder.add_node(LlmNode(name="dup", llm_config=default_llm_config, prompt_template="y"))


def test_add_data_edge_raises_when_source_missing(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="dst", llm_config=default_llm_config, prompt_template="x"))
    with pytest.raises(ValueError, match="Source node 'src' not found"):
        builder.add_data_edge("src", "dst", "out")


def test_add_data_edge_raises_when_destination_missing(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="src", llm_config=default_llm_config, prompt_template="x"))
    with pytest.raises(ValueError, match="Destination node 'dst' not found"):
        builder.add_data_edge("src", "dst", "out")


def test_add_sequence_works_in_combination_with_add_node(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="x", llm_config=default_llm_config, prompt_template="x"))
    builder.add_sequence([LlmNode(name="y", llm_config=default_llm_config, prompt_template="y")])
    # Explicitly connect x -> y since add_sequence doesn't link previously added nodes
    builder.add_edge("x", "y")
    builder.set_entry_point("x")
    builder.set_finish_points("y")
    flow = builder.build()
    # Ensure there is an edge from x to y (plus start and finish)
    edges = {(e.from_node.name, e.to_node.name) for e in flow.control_flow_connections}
    assert ("x", "y") in edges


def test_set_finish_points_raises_on_length_mismatch(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="x", llm_config=default_llm_config, prompt_template="x"))
    builder.set_entry_point("x")
    # One source, two outputs
    with pytest.raises(ValueError, match="Number of finish sources and outputs must match"):
        builder.set_finish_points(["x"], outputs=[[], []])


def test_build_raises_when_start_node_missing(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="x", llm_config=default_llm_config, prompt_template="x"))
    with pytest.raises(ValueError, match="Missing start node"):
        builder.build()


def test_set_entry_point_raises_when_target_node_missing():
    builder = FlowBuilder()
    # set_entry_point will try to add an edge StartNode->unknown and should raise via add_edge
    with pytest.raises(ValueError, match="End node 'unknown' not found"):
        builder.set_entry_point("unknown")


def test_add_conditional_edges_raises_when_source_missing(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="success", llm_config=default_llm_config, prompt_template="x"))
    with pytest.raises(ValueError, match="Start node 'llm' not found"):
        builder.add_conditional(
            "llm", "result", {"success": "success"}, default_destination="success"
        )


def test_add_conditional_edges_raises_when_destination_missing(default_llm_config):
    builder = FlowBuilder()
    builder.add_node(LlmNode(name="llm", llm_config=default_llm_config, prompt_template="x"))
    # Destination 'missing' doesn't exist
    with pytest.raises(ValueError, match="End node 'missing' not found"):
        builder.add_conditional(
            "llm", "result", {"missing": "missing"}, default_destination="missing"
        )


def test_add_conditional_with_tuple_source_value(default_llm_config):
    # Build a small graph where the conditional takes value from another node
    builder = FlowBuilder()
    builder.add_node(
        LlmNode(name="producer", llm_config=default_llm_config, prompt_template="Hello")
    )
    builder.add_node(LlmNode(name="llm", llm_config=default_llm_config, prompt_template="Hello"))
    builder.add_node(
        LlmNode(name="false_branch", llm_config=default_llm_config, prompt_template="Hello")
    )
    builder.add_node(
        LlmNode(name="true_branch", llm_config=default_llm_config, prompt_template="Hello")
    )
    # Use tuple (node, output_name)
    builder.add_conditional(
        source_node="llm",
        source_value=("producer", LlmNode.DEFAULT_OUTPUT),
        destination_map={"true": "true_branch"},
        default_destination="false_branch",
    )
    builder.add_edge("producer", "llm")
    builder.set_entry_point("producer")
    builder.set_finish_points(["true_branch", "false_branch"])  # alias method
    flow = builder.build()
    # Ensure data edge from producer to the branching node exists
    assert any(
        e.source_node.name == "producer" and e.destination_node.name.startswith("ConditionalNode_")
        for e in flow.data_flow_connections
    )


def test_build_linear_flow_wires_edges(default_llm_config):
    n1 = LlmNode(name="n1", llm_config=default_llm_config, prompt_template="a")
    n2 = LlmNode(name="n2", llm_config=default_llm_config, prompt_template="b")
    n3 = LlmNode(name="n3", llm_config=default_llm_config, prompt_template="c")
    flow = FlowBuilder.build_linear_flow([n1, n2, n3])
    # Expect Start->n1, n1->n2, n2->n3, n3->End = 4 edges
    assert len(flow.control_flow_connections) == 4


def test_build_linear_flow_with_data_flow_edges_variants(default_llm_config):
    # n2 expects 'generated_text' as input (3-tuple edge), n3 expects 'forward' as input (4-tuple edge)
    n1 = LlmNode(name="n1", llm_config=default_llm_config, prompt_template="a")
    n2 = LlmNode(name="n2", llm_config=default_llm_config, prompt_template="{{generated_text}}")
    n3 = LlmNode(name="n3", llm_config=default_llm_config, prompt_template="{{forward}}")
    flow = FlowBuilder.build_linear_flow(
        [n1, n2, n3],
        data_flow_edges=[
            ("n1", "n2", LlmNode.DEFAULT_OUTPUT),  # 3-tuple
            ("n1", "n3", LlmNode.DEFAULT_OUTPUT, "forward"),  # 4-tuple
        ],
    )
    # Expect two data edges with the specified wiring
    edges = {
        (e.source_node.name, e.destination_node.name, e.source_output, e.destination_input)
        for e in flow.data_flow_connections
    }
    assert ("n1", "n2", LlmNode.DEFAULT_OUTPUT, LlmNode.DEFAULT_OUTPUT) in edges
    assert ("n1", "n3", LlmNode.DEFAULT_OUTPUT, "forward") in edges


def test_build_linear_flow_accepts_DataFlowEdge_objects(default_llm_config):
    n1 = LlmNode(name="n1", llm_config=default_llm_config, prompt_template="a")
    n2 = LlmNode(name="n2", llm_config=default_llm_config, prompt_template="{{forward}}")
    # Explicit DataFlowEdge using node objects
    df = DataFlowEdge(
        name="df1",
        source_node=n1,
        source_output=LlmNode.DEFAULT_OUTPUT,
        destination_node=n2,
        destination_input="forward",
    )
    flow = FlowBuilder.build_linear_flow([n1, n2], data_flow_edges=[df])
    assert len(flow.data_flow_connections) == 1
    e = flow.data_flow_connections[0]
    assert (e.source_node.name, e.destination_node.name, e.source_output, e.destination_input) == (
        "n1",
        "n2",
        LlmNode.DEFAULT_OUTPUT,
        "forward",
    )


def test_build_linear_flow_with_explicit_inputs_outputs(default_llm_config):
    n1 = LlmNode(name="n1", llm_config=default_llm_config, prompt_template="a")
    n2 = LlmNode(name="n2", llm_config=default_llm_config, prompt_template="b")
    inp = StringProperty(title="inp")
    outp = StringProperty(title="outp")
    flow = FlowBuilder.build_linear_flow([n1, n2], inputs=[inp], outputs=[outp])
    # Start node should have that input, and one EndNode should have that output
    start_nodes = [n for n in flow.nodes if isinstance(n, StartNode)]
    assert (
        len(start_nodes) == 1 and start_nodes[0].inputs and start_nodes[0].inputs[0].title == "inp"
    )
    end_nodes = [n for n in flow.nodes if isinstance(n, EndNode)]
    assert len(end_nodes) == 1 and end_nodes[0].outputs and end_nodes[0].outputs[0].title == "outp"


def test_build_linear_flow_serialize_json_and_yaml(default_llm_config):
    n1 = LlmNode(name="n1", llm_config=default_llm_config, prompt_template="a")
    n2 = LlmNode(name="n2", llm_config=default_llm_config, prompt_template="b")
    js = FlowBuilder.build_linear_flow([n1, n2], serialize_as="JSON")
    assert isinstance(js, str)
    parsed = json.loads(js)
    assert parsed.get("name") == "Flow"
    ya = FlowBuilder.build_linear_flow([n1, n2], serialize_as="YAML")
    assert isinstance(ya, str)
    assert "name: Flow" in ya


def test_build_linear_flow_rejects_start_or_end_nodes(default_llm_config):
    # Start at position 0 not allowed
    with pytest.raises(ValueError, match="It is not necessary to add a StartNode"):
        FlowBuilder.build_linear_flow(
            [
                StartNode(name="s"),
                LlmNode(name="n", llm_config=default_llm_config, prompt_template="p"),
            ]
        )
    # End at last position not allowed
    with pytest.raises(ValueError, match="It is not necessary to add an EndNode"):
        FlowBuilder.build_linear_flow(
            [
                LlmNode(name="n", llm_config=default_llm_config, prompt_template="p"),
                EndNode(name="e"),
            ]
        )


def test_set_entry_point_cannot_be_called_twice():
    builder = FlowBuilder()
    builder.add_node(InputMessageNode(name="s", message="x"))
    builder.set_entry_point("s")
    with pytest.raises(ValueError, match="Entry point already set"):
        builder.set_entry_point("s")


def test_add_data_edge_validates_data_name_tuple_shape():
    builder = FlowBuilder()
    builder.add_node(InputMessageNode(name="src", message="x"))
    builder.add_node(InputMessageNode(name="dst", message="{{ out }}"))
    # wrong length tuple
    with pytest.raises(ValueError, match="data_name tuple must be"):
        builder.add_data_edge("src", "dst", ("a", "b", "c"))
    # wrong types
    with pytest.raises(ValueError, match="data_name tuple must be"):
        builder.add_data_edge("src", "dst", (1, "b"))  # type: ignore


def test_add_data_edge_raises_when_node_instances_not_added():
    src = InputMessageNode(name="src", message="x")
    dst = InputMessageNode(name="dst", message="{{ out }}")
    builder = FlowBuilder()
    # Add only destination
    builder.add_node(dst)
    with pytest.raises(ValueError, match="Source node 'src' not found"):
        builder.add_data_edge(src, dst, "out")
    # Now add source but not destination
    builder2 = FlowBuilder()
    builder2.add_node(src)
    with pytest.raises(ValueError, match="Destination node 'dst' not found"):
        builder2.add_data_edge(src, dst, "out")


def test_add_conditional_rejects_default_label_in_mapping():
    builder = FlowBuilder()
    builder.add_node(InputMessageNode(name="decider", message="{{ value }}"))
    builder.add_node(InputMessageNode(name="A", message="A"))
    with pytest.raises(ValueError, match="reserved branch label"):
        builder.add_conditional(
            "decider",
            InputMessageNode.DEFAULT_OUTPUT,
            {"some_value": BranchingNode.DEFAULT_BRANCH},
            default_destination="A",
        )


def test_add_conditional_raises_when_default_destination_missing():
    builder = FlowBuilder()
    builder.add_node(InputMessageNode(name="src", message="x"))
    builder.add_node(InputMessageNode(name="ok", message="ok"))
    with pytest.raises(ValueError, match="End node 'missing' not found"):
        builder.add_conditional(
            "src", InputMessageNode.DEFAULT_OUTPUT, {"v": "ok"}, default_destination="missing"
        )


def test_add_conditional_raises_when_one_mapping_destination_missing():
    builder = FlowBuilder()
    builder.add_node(InputMessageNode(name="src", message="x"))
    builder.add_node(InputMessageNode(name="ok", message="ok"))
    with pytest.raises(ValueError, match="End node 'missing' not found"):
        builder.add_conditional(
            "src", InputMessageNode.DEFAULT_OUTPUT, {"v": "missing"}, default_destination="ok"
        )


def test_build_linear_flow_automatically_infers_inputs_outputs_and_dataflow_edges(
    default_llm_config,
) -> None:
    """
    This test checks that when creating a sequential flow the inputs and outputs of
    the flow are correctly inferred, and that the data connections are automatically
    wired.

            user_input
          .---------------------------------.------------.
          |               generated_text    |            |
          |              .---------------.--+--------.   |
          |              |               |  |        |   |
          |              |               v  v        v   v
    +---------+     +------+           +------+     +------+              +---------+
    |  Start  |---->|  N1  |---------->|  N2  |---->|  N3  |------------->|   End   |
    +---------+     +------+           +------+     +------+              +---------+
                        |               |            |                     ^   ^  ^
                        |               |            '- generated_text3 ---'   |  |
                        |               |                                      |  |
                        |               '------------- generated_text2 --------'  |
                        '--------------------------- generated_text --------------'


    """
    USER_INPUT_NAME = "user_input"
    N1_OUTPUT_NAME = LlmNode.DEFAULT_OUTPUT
    N2_OUTPUT_NAME = "generated_text_2"
    N3_OUTPUT_NAME = "generated_text_3"
    p1_out = StringProperty(title=N1_OUTPUT_NAME)
    p2_out = StringProperty(title=N2_OUTPUT_NAME)
    p3_out = StringProperty(title=N3_OUTPUT_NAME)
    n1 = LlmNode(name="n1", llm_config=default_llm_config, prompt_template="a", outputs=[p1_out])
    n2 = LlmNode(
        name="n2",
        llm_config=default_llm_config,
        prompt_template="{{" + N1_OUTPUT_NAME + "}} {{" + USER_INPUT_NAME + "}}",
        outputs=[p2_out],
    )
    n3 = LlmNode(
        name="n3",
        llm_config=default_llm_config,
        prompt_template="{{" + N1_OUTPUT_NAME + "}} {{" + USER_INPUT_NAME + "}}",
        outputs=[p3_out],
    )
    flow = FlowBuilder.build_linear_flow([n1, n2, n3])

    node_names = {n.name for n in flow.nodes}
    assert {"StartNode", "n1", "n2", "n3", "EndNode_1"} == node_names

    # Check that inputs/outputs have been properly inferred
    assert flow.inputs == [StringProperty(title=USER_INPUT_NAME)]
    assert flow.outputs == [p1_out, p2_out, p3_out]
