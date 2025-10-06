# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.
from typing import Any, Dict, List, Union
from unittest.mock import patch

import pytest
import yaml

from pyagentspec.agent import Agent
from pyagentspec.component import Component
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import FlowNode, MapNode
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from ..conftest import read_agentspec_config_file
from .conftest import assert_serialized_representations_are_equal


def test_components_ids_are_different_by_default() -> None:
    config_1 = VllmConfig(name="some_config", model_id="some_id", url="http://some.where")
    config_2 = VllmConfig(name="some_config", model_id="some_id", url="http://some.where")
    assert config_1.id != config_2.id


def test_deserialization_raises_on_self_referencing_component() -> None:
    with pytest.raises(
        ValueError,
        match="Found a circular dependency during deserialization of object with id: '.*'",
    ):
        AgentSpecDeserializer().from_yaml(
            read_agentspec_config_file("invalid/self_referencing_flow.yaml")
        )


def test_can_deserialize_flow_with_multiple_levels_of_reference_component() -> None:
    serialized_flow = read_agentspec_config_file("flow_with_multiple_levels_of_references.yaml")
    flow = AgentSpecDeserializer().from_yaml(serialized_flow)
    assert isinstance(flow, Flow)
    assert isinstance(flow.nodes[1], FlowNode)
    assert isinstance(flow.nodes[1].subflow.nodes[1], LlmNode)
    assert flow.nodes[1].subflow.nodes[1].prompt_template == "Do {{x}}:"
    assert flow.nodes[2] is flow.nodes[1].subflow.nodes[1]


def test_can_deserialize_flow_with_all_reference_at_the_root() -> None:
    serialized_flow = read_agentspec_config_file("flow_with_all_references_at_root.yaml")
    flow = AgentSpecDeserializer().from_yaml(serialized_flow)
    assert isinstance(flow, Flow)
    assert isinstance(flow.nodes[1], FlowNode)
    assert isinstance(flow.nodes[1].subflow.nodes[1], LlmNode)
    assert flow.nodes[1].subflow.nodes[1].prompt_template == "Do {{x}}:"
    assert flow.nodes[2] is flow.nodes[1].subflow.nodes[1]


def test_deserialization_raises_on_repeated_referenced_id() -> None:
    serialized_flow = read_agentspec_config_file(
        "invalid/flow_with_multiple_levels_of_references_with_repeated_key.yaml"
    )
    with pytest.raises(
        ValueError,
        match="The objects: .* appear multiple times at different levels in referenced components.",
    ):
        AgentSpecDeserializer().from_yaml(serialized_flow)


def test_component_are_not_referenced_if_used_only_once() -> None:
    llm_config = VllmConfig(
        id="vllm", name="model_name", model_id="some_model", url="http://some.where"
    )
    llm_node = LlmNode(
        id="llm_node",
        name="node_name",
        llm_config=llm_config,
        prompt_template="How much is 6x7?",
    )
    serialized_node = AgentSpecSerializer().to_yaml(llm_node)
    assert "referenced_components" not in serialized_node
    assert "$component_ref" not in serialized_node


@pytest.fixture
def outer_flow_with_complex_nested_structure() -> Flow:
    # In the test below:
    #
    #       o---------------- outermost_flow
    #       |                       |
    #   flow_node              flow_node_2
    #       |                       |
    #       |        o--------- outer_flow -------o
    #       |        |              |             |
    #       |  inner_flow_node   map_node         |
    #       |        |              |             |
    #       o-- inner_flow_1    inner_flow_2      |
    #                |              |             |
    #           llm_node_1      llm_node_2     llm_node_3
    #                |              |             |
    #                o------- llm_config ---------o
    #
    # Based on these dependencies:
    # - `outermost_flow` is the root, not in any reference
    # - `outer_flow` is used only by `outermost_flow`, thus is not referenced
    # - `inner_flow_node` is used in `outer_flow` both in nodes and edges, thus is in the referenced
    #   components for `outer_flow`
    # - `map_node`, same as `inner_flow_node`
    # - `llm_node_3`, same as `inner_flow_node` and `map_node`
    # - `inner_flow_1` is used both by `outermost_flow` and by `flow_node`, this is in the referenced
    #   components of `outermost_flow`
    # - `inner_flow_2` is used only in `map_node`, thus is not referenced
    # - `llm_node_1` is used in `inner_flow_1` in nodes and as start node, thus is referenced
    #   by `inner_flow_1`
    # - `llm_node_2` is used in `inner_flow_2` in nodes and as start node, thus is referenced
    #   by `inner_flow_2`
    # - `llm_node_3` is used in `outer_flow` in nodes and in edges, thus is referenced
    #   by `outer_flow`
    # - `llm_config` is used in all LlmNodes, thus is referenced by `outer_flow`
    start_node = StartNode(id="start_node", name="start_node")
    end_node = EndNode(id="end_node", name="end_node")
    llm_config = VllmConfig(
        id="llm_config", name="llm_config", model_id="some_model", url="http://some.where"
    )
    llm_node_1 = LlmNode(
        id="llm_node_1",
        name="llm_node_1",
        llm_config=llm_config,
        prompt_template="How much is 6x7?",
    )
    llm_node_2 = LlmNode(
        id="llm_node_2",
        name="llm_node_2",
        llm_config=llm_config,
        prompt_template="How much is 6x7?",
    )
    llm_node_3 = LlmNode(
        id="llm_node_3",
        name="llm_node_3",
        llm_config=llm_config,
        prompt_template="How much is 6x7?",
    )
    inner_flow_1 = Flow(
        id="inner_flow_1",
        name="inner_flow_1",
        nodes=[start_node, llm_node_1, end_node],
        start_node=start_node,
        control_flow_connections=[
            ControlFlowEdge(name="edge", from_node=start_node, to_node=llm_node_1),
            ControlFlowEdge(name="edge", from_node=llm_node_1, to_node=end_node),
        ],
        data_flow_connections=[],
    )
    inner_flow_node = FlowNode(
        id="inner_flow_node",
        name="inner_flow_node",
        subflow=inner_flow_1,
    )
    inner_flow_2 = Flow(
        id="inner_flow_2",
        name="inner_flow_2",
        nodes=[start_node, llm_node_2, end_node],
        start_node=start_node,
        control_flow_connections=[
            ControlFlowEdge(name="edge", from_node=start_node, to_node=llm_node_2),
            ControlFlowEdge(name="edge", from_node=llm_node_2, to_node=end_node),
        ],
        data_flow_connections=[],
    )
    map_node = MapNode(
        id="map_node",
        name="map_node",
        subflow=inner_flow_2,
    )
    outer_flow = Flow(
        id="outer_flow",
        name="outer_flow",
        nodes=[start_node, llm_node_3, inner_flow_node, map_node, end_node],
        start_node=start_node,
        control_flow_connections=[
            ControlFlowEdge(name="edge", from_node=start_node, to_node=llm_node_3),
            ControlFlowEdge(name="edge", from_node=llm_node_3, to_node=inner_flow_node),
            ControlFlowEdge(name="edge", from_node=inner_flow_node, to_node=map_node),
            ControlFlowEdge(name="edge", from_node=map_node, to_node=end_node),
        ],
        data_flow_connections=[],
    )
    flow_node = FlowNode(
        id="flow_node",
        name="flow_node",
        subflow=inner_flow_1,
    )
    flow_node_2 = FlowNode(
        id="flow_node_2",
        name="flow_node_2",
        subflow=outer_flow,
    )
    outermost_flow = Flow(
        id="outermost_flow",
        name="outermost_flow",
        start_node=start_node,
        nodes=[start_node, flow_node, flow_node_2, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="edge", from_node=start_node, to_node=flow_node),
            ControlFlowEdge(name="edge", from_node=flow_node, to_node=flow_node_2),
            ControlFlowEdge(name="edge", from_node=flow_node_2, to_node=end_node),
        ],
    )
    return outermost_flow


def test_references_are_at_at_the_right_level_with_nested_subflows(
    outer_flow_with_complex_nested_structure: Agent,
) -> None:
    serialized_agent = AgentSpecSerializer().to_yaml(outer_flow_with_complex_nested_structure)
    outermost_flow_as_dict = yaml.safe_load(serialized_agent)
    assert "$referenced_components" in outermost_flow_as_dict
    assert "flow_node" in outermost_flow_as_dict["$referenced_components"]
    # `outer_flow` should be inlined
    assert "name" in outermost_flow_as_dict["$referenced_components"]["flow_node_2"]["subflow"]
    assert (
        outermost_flow_as_dict["$referenced_components"]["flow_node_2"]["subflow"]["name"]
        == "outer_flow"
    )
    # `outermost_flow` should reference `inner_flow_1` and start and end node used in flows
    assert set(outermost_flow_as_dict["$referenced_components"]) == {
        "inner_flow_1",
        "start_node",
        "end_node",
        "flow_node",
        "flow_node_2",
        "llm_config",
    }
    # `inner_flow_1` should be a reference
    assert outermost_flow_as_dict["$referenced_components"]["flow_node"]["subflow"] == {
        "$component_ref": "inner_flow_1"
    }
    # `outer_flow` should be inlined inside flow_node_2
    outer_flow_as_dict = outermost_flow_as_dict["$referenced_components"]["flow_node_2"]["subflow"]
    assert "$component_ref" not in outer_flow_as_dict
    # `outer_flow` should reference
    assert set(outer_flow_as_dict["$referenced_components"]) == {
        "inner_flow_node",
        "map_node",
        "llm_node_3",
    }
    # `inner_flow_node` should use `inner_flow_1` as ref
    inner_flow_node_as_dict = outer_flow_as_dict["$referenced_components"]["inner_flow_node"]
    assert inner_flow_node_as_dict["subflow"] == {"$component_ref": "inner_flow_1"}
    # `map_node` should have `inner_flow_2` inlined
    map_node_as_dict = outer_flow_as_dict["$referenced_components"]["map_node"]
    assert "$component_ref" not in map_node_as_dict["subflow"]
    # `inner_flow_1` should reference `llm_node_1`
    inner_flow_1_as_dict = outermost_flow_as_dict["$referenced_components"]["inner_flow_1"]
    assert set(inner_flow_1_as_dict["$referenced_components"]) == {"llm_node_1"}
    # `inner_flow_2` should reference `llm_node_2`
    inner_flow_2_as_dict = map_node_as_dict["subflow"]
    assert set(inner_flow_2_as_dict["$referenced_components"]) == {"llm_node_2"}


def test_outer_flow_with_complex_nested_structure_can_be_serde_and_back(
    outer_flow_with_complex_nested_structure: Agent,
) -> None:
    serialized_agent = AgentSpecSerializer().to_yaml(outer_flow_with_complex_nested_structure)
    deserialized_agent = AgentSpecDeserializer().from_yaml(serialized_agent)
    new_serialized_agent = AgentSpecSerializer().to_yaml(deserialized_agent)
    assert_serialized_representations_are_equal(serialized_agent, new_serialized_agent)


def test_json_serialization_and_deserialization(simplest_flow: Flow) -> None:
    serializer = AgentSpecSerializer()
    serialized_flow = serializer.to_json(simplest_flow)
    deserializer = AgentSpecDeserializer()
    deserialized_flow = deserializer.from_json(serialized_flow)
    assert deserialized_flow == simplest_flow


@patch.object(Component, "_get_min_agentspec_version_and_component")
def test_deserialization_and_serialization_preserves_older_min_version(
    test_get_min_agentspec_version_and_component, simplest_flow: Flow
) -> None:
    test_get_min_agentspec_version_and_component.return_value = (
        AgentSpecVersionEnum.v25_3_0,
        simplest_flow,
    )
    serializer = AgentSpecSerializer()
    deserializer = AgentSpecDeserializer()

    serialized_flow_v25_3_0 = serializer.to_json(
        simplest_flow, agentspec_version=AgentSpecVersionEnum.v25_3_0
    )
    deserialized_flow_v25_3_0 = deserializer.from_json(serialized_flow_v25_3_0)
    assert (
        deserialized_flow_v25_3_0._get_min_agentspec_version_and_component()[0]
        == AgentSpecVersionEnum.v25_3_0
    )


def test_deserialization_and_serialization_preserves_min_version(simplest_flow: Flow) -> None:
    serializer = AgentSpecSerializer()
    deserializer = AgentSpecDeserializer()

    serialized_flow = serializer.to_json(
        simplest_flow, agentspec_version=AgentSpecVersionEnum.current_version
    )
    deserialized_flow = deserializer.from_json(serialized_flow)
    assert (
        deserialized_flow._get_min_agentspec_version_and_component()[0]
        == AgentSpecVersionEnum.current_version
    )


def test_dict_serialization_and_deserialization(simplest_flow: Flow) -> None:
    serializer = AgentSpecSerializer()
    serialized_flow = serializer.to_dict(simplest_flow)
    deserializer = AgentSpecDeserializer()
    deserialized_flow = deserializer.from_dict(serialized_flow)
    assert deserialized_flow == simplest_flow


def test_json_and_yaml_serializations_have_the_right_order(
    outer_flow_with_complex_nested_structure: Agent,
) -> None:
    import json

    priority_keys = ["component_type", "id", "name", "description"]

    def assert_is_in_right_order(obj_dump: Union[Dict[str, Any], List[Any], Any]) -> None:
        "Recursively checks that every dict in obj has priority_keys fisrt."
        if isinstance(obj_dump, dict):
            # Check if it is a dict of a component
            if "component_type" in obj_dump:
                # The first keys should follow the order as in priority keys
                assert list(obj_dump.keys())[: len(priority_keys)] == priority_keys

            for v in obj_dump.values():
                assert_is_in_right_order(v)
        elif isinstance(obj_dump, list):
            for i in obj_dump:
                assert_is_in_right_order(i)

    serialized_yaml = AgentSpecSerializer().to_yaml(outer_flow_with_complex_nested_structure)
    loaded_yaml = yaml.safe_load(serialized_yaml)

    serialized_json = AgentSpecSerializer().to_json(outer_flow_with_complex_nested_structure)
    loaded_json = json.loads(serialized_json)

    assert_is_in_right_order(loaded_yaml)
    assert_is_in_right_order(loaded_json)
