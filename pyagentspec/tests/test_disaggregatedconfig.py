# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import cast

import pytest
import yaml

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, FlowNode, LlmNode, StartNode, ToolNode
from pyagentspec.llms import VllmConfig
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.tools import ClientTool
from pyagentspec.tools.tool import Tool

from .serialization.test_flow import get_nested_flow, timeout
from .serialization.test_serialization import outer_flow_with_complex_nested_structure  # noqa: F401


def assert_serialized_representations_are_equal(actual: str, expected: str) -> None:
    assert actual.strip() == expected.strip(), "Serialized representations do not match"


@pytest.fixture
def vllm_config() -> VllmConfig:
    return VllmConfig(id="vllm_id", name="vllm", model_id="model1", url="http://dev.llm.url")


@pytest.fixture
def client_tool() -> ClientTool:
    city_input = StringProperty(title="city_name", default="zurich")
    weather_output = StringProperty(title="forecast")
    return ClientTool(
        id="tool_id",
        name="get_weather",
        description="Gets the weather in specified city",
        inputs=[city_input],
        outputs=[weather_output],
    )


@pytest.fixture
def simple_agent(vllm_config: VllmConfig, client_tool: ClientTool) -> Agent:
    return Agent(
        id="agent_id",
        name="Simple Agent",
        llm_config=vllm_config,
        system_prompt="Be helpful",
        tools=[client_tool],
    )


@pytest.fixture
def simple_flow(vllm_config: VllmConfig, client_tool: ClientTool) -> Flow:
    node_1 = LlmNode(
        id="node1",
        name="node1",
        llm_config=vllm_config,
        prompt_template="Prompt 1",
    )
    tool_node = ToolNode(id="tool_node", name="tool_node", tool=client_tool)
    start_node = StartNode(id="start", name="start")
    end_node = EndNode(id="end", name="end", outputs=[])
    control_flow_connections = [
        ControlFlowEdge(id="e1", name="start->node1", from_node=start_node, to_node=node_1),
        ControlFlowEdge(id="e2", name="node1->tool", from_node=node_1, to_node=tool_node),
        ControlFlowEdge(id="e3", name="tool->end", from_node=tool_node, to_node=end_node),
    ]
    return Flow(
        id="flow_id",
        name="Simple Flow",
        start_node=start_node,
        nodes=[start_node, node_1, tool_node, end_node],
        control_flow_connections=control_flow_connections,
        data_flow_connections=None,
    )


def test_serialize_with_single_disaggregated_component_default_id(
    simple_agent: Agent, client_tool: ClientTool
) -> None:
    serializer = AgentSpecSerializer()
    main_serialized, disagg_serialized = serializer.to_yaml(
        simple_agent,
        disaggregated_components=[client_tool],
        # ^ just passing the component
        export_disaggregated_components=True,
    )
    # Check main has reference and not the full serialized object
    assert "$component_ref: tool_id" in main_serialized
    assert "ClientTool" not in main_serialized
    # Inspect disaggregated
    disagg_dict = yaml.safe_load(disagg_serialized)
    assert "$referenced_components" in disagg_dict
    assert "tool_id" in disagg_dict["$referenced_components"]
    assert disagg_dict["$referenced_components"]["tool_id"]["component_type"] == "ClientTool"


def test_serialize_with_disaggregated_component_custom_id(
    simple_flow: Flow, client_tool: ClientTool
) -> None:
    serializer = AgentSpecSerializer()
    main_serialized, disagg_serialized = serializer.to_yaml(
        simple_flow,
        disaggregated_components=[(client_tool, "custom_tool_id")],
        # ^ passing the component and a custom id
        export_disaggregated_components=True,
    )
    # Check main references custom ID and not the full serialized object
    assert "$component_ref: custom_tool_id" in main_serialized
    assert "ClientTool" not in main_serialized
    # Inspect disaggregated
    disagg_dict = yaml.safe_load(disagg_serialized)
    assert "$referenced_components" in disagg_dict
    assert "custom_tool_id" in disagg_dict["$referenced_components"]
    assert (
        disagg_dict["$referenced_components"]["custom_tool_id"]["id"] == "tool_id"
    )  # Internal ID preserved


def test_serialize_with_disaggregated_attribute_value_custom_id(
    simple_agent: Agent, vllm_config: VllmConfig
) -> None:
    with pytest.raises(
        NotImplementedError, match="Component field disaggregation is not supported yet"
    ):
        serializer = AgentSpecSerializer()
        main_serialized, disagg_serialized = serializer.to_yaml(
            simple_agent,
            disaggregated_components=[(vllm_config, "url", "custom_url_id")],
            export_disaggregated_components=True,
        )
        # Check main has reference for attribute
        assert "$component_ref: custom_url_id" in main_serialized  # Assuming attribute ref format
        # Inspect disaggregated
        disagg_dict = yaml.safe_load(disagg_serialized)
        assert "$referenced_components" in disagg_dict
        assert "custom_url_id" in disagg_dict["$referenced_components"]
        assert (
            disagg_dict["$referenced_components"]["custom_url_id"] == "http://dev.llm.url"
        )  # Value is string


def test_serialize_multiple_disaggregated_mixed_types(
    simple_flow: Flow, vllm_config: VllmConfig, client_tool: ClientTool
) -> None:
    serializer = AgentSpecSerializer()
    main_serialized, disagg_serialized = serializer.to_yaml(
        simple_flow,
        disaggregated_components=[
            client_tool,  # Default ID
            (vllm_config, "custom_llm_id"),  # Custom ID for component
        ],
        export_disaggregated_components=True,
    )
    # Check main has references
    assert "$component_ref: tool_id" in main_serialized
    assert "$component_ref: custom_llm_id" in main_serialized

    # Inspect disaggregated
    disagg_dict = yaml.safe_load(disagg_serialized)
    assert "$referenced_components" in disagg_dict
    assert set(disagg_dict["$referenced_components"].keys()) == {"tool_id", "custom_llm_id"}
    assert disagg_dict["$referenced_components"]["custom_llm_id"]["component_type"] == "VllmConfig"


def test_deserialization_raises_on_disaggregated_config_with_extra_fields() -> None:
    config = {
        "$referenced_components": {},
        "component_type": "Flow",  # extra
        "name": "My flow",  # extra
    }
    with pytest.raises(
        ValueError, match=("Found extra fields on disaggregated components configuration")
    ):
        AgentSpecDeserializer().from_dict(config, import_only_referenced_components=True)


def test_serialize_without_export_disaggregated_components(
    simple_agent: Agent, client_tool: ClientTool
) -> None:
    serializer = AgentSpecSerializer()
    result = serializer.to_yaml(
        simple_agent, disaggregated_components=[client_tool], export_disaggregated_components=False
    )
    assert isinstance(result, str)  # Only main returned
    assert "$component_ref: tool_id" in result  # Tool is referenced
    assert "component_type: ClientTool" not in result  # Tool is not inline


def test_serialize_empty_disaggregated_list(simple_agent: Agent) -> None:
    serializer = AgentSpecSerializer()
    main_serialized, disagg_serialized = serializer.to_yaml(
        simple_agent, disaggregated_components=[], export_disaggregated_components=True
    )
    # Main is normal
    assert "component_type: Agent" in main_serialized
    # Disaggregated is empty
    disagg_dict = yaml.safe_load(disagg_serialized)
    assert disagg_dict == {"$referenced_components": {}}


@pytest.fixture
def serialized_disaggregated_single_tool(simple_agent: Agent, client_tool: ClientTool) -> str:
    serializer = AgentSpecSerializer()
    _, disagg_serialized = serializer.to_yaml(
        simple_agent,
        disaggregated_components=[client_tool],
        export_disaggregated_components=True,
    )
    return disagg_serialized


def test_deserialize_disaggregated_only(serialized_disaggregated_single_tool: str) -> None:
    deserializer = AgentSpecDeserializer()
    result = deserializer.from_yaml(
        serialized_disaggregated_single_tool, import_only_referenced_components=True
    )
    assert isinstance(result, dict)
    assert "tool_id" in result
    assert isinstance(result["tool_id"], ClientTool)
    assert result["tool_id"].id == "tool_id"


@pytest.fixture
def serialized_main_config_with_custom_id(simple_flow: Flow, client_tool: ClientTool) -> str:
    serializer = AgentSpecSerializer()
    main_serialized, _ = serializer.to_yaml(
        simple_flow,
        disaggregated_components=[(client_tool, "custom_tool_id")],
        export_disaggregated_components=True,
    )
    return main_serialized


def test_deserialize_main_with_registry(
    serialized_main_config_with_custom_id: str, client_tool: ClientTool
) -> None:
    deserializer = AgentSpecDeserializer()
    registry = {"custom_tool_id": client_tool}
    deserialized_flow = deserializer.from_yaml(
        serialized_main_config_with_custom_id, components_registry=registry
    )
    assert isinstance(deserialized_flow, Flow)
    tool_node = next(
        n for n in deserialized_flow.nodes if n.id == "tool_node" and isinstance(n, ToolNode)
    )
    assert tool_node.tool == client_tool


def test_serialize_nested_flow_with_disaggregated_subcomponents(
    outer_flow_with_complex_nested_structure: Flow,
) -> None:
    flow = outer_flow_with_complex_nested_structure
    subflow = cast(FlowNode, flow.nodes[1]).subflow
    serializer = AgentSpecSerializer()
    main_serialized, disagg_serialized = serializer.to_yaml(
        flow,
        disaggregated_components=[(subflow, "nested_flow_id")],
        export_disaggregated_components=True,
    )
    assert "$component_ref: nested_flow_id" in main_serialized  # Reference in nested part
    disagg_dict = yaml.safe_load(disagg_serialized)
    assert "nested_flow_id" in disagg_dict["$referenced_components"]
    assert disagg_dict["$referenced_components"]["nested_flow_id"]["component_type"] == "Flow"


def test_deserialize_nested_flow_with_partial_registry(
    outer_flow_with_complex_nested_structure: Flow,
) -> None:
    # First, serialize with disaggregation
    flow = outer_flow_with_complex_nested_structure
    subflow = cast(FlowNode, flow.nodes[1]).subflow
    serializer = AgentSpecSerializer()
    main_serialized, disagg_serialized = serializer.to_yaml(
        flow,
        disaggregated_components=[(subflow, "nested_flow_id")],
        export_disaggregated_components=True,
    )
    # Deserialize disagg to get registry (partial)
    deserializer = AgentSpecDeserializer()
    partial_registry = deserializer.from_yaml(
        disagg_serialized, import_only_referenced_components=True
    )
    deserialized = deserializer.from_yaml(main_serialized, components_registry=partial_registry)
    assert isinstance(deserialized, Flow)
    # Check nested LLM node has config injected
    inner_flow_node = next(n for n in deserialized.nodes if isinstance(n, FlowNode))
    assert inner_flow_node.id == "flow_node"


def test_deserialize_disaggregated_without_flag_raises_error(
    serialized_disaggregated_single_tool: str,
) -> None:
    deserializer = AgentSpecDeserializer()
    with pytest.raises(
        ValueError,
        match=(
            "Cannot deserialize the given content, it doesn't seem to be a "
            "valid Agent Spec Component. To load a disaggregated configuration, "
            "make sure that `import_only_referenced_components` is `True`"
        ),
    ):
        deserializer.from_yaml(
            serialized_disaggregated_single_tool, import_only_referenced_components=False
        )


def test_serialize_invalid_disaggregated_tuple_raises_error(simple_agent: Agent) -> None:
    serializer = AgentSpecSerializer()
    invalid_disagg = [("invalid",)]  # Wrong arity
    with pytest.raises(ValueError, match="Invalid disaggregated_components entry"):
        serializer.to_yaml(
            simple_agent,
            disaggregated_components=invalid_disagg,  # type: ignore
            export_disaggregated_components=True,
        )


def test_deserialize_with_mismatched_registry_type_raises_error(
    serialized_main_config_with_custom_id: str,
) -> None:
    deserializer = AgentSpecDeserializer()
    mismatched_registry = {"custom_tool_id": VllmConfig(name="llm", url="url", model_id="model_id")}

    with pytest.raises(
        ValueError,
        match=(
            "Type mismatch when loading component with reference 'custom_tool_id': "
            f"expected '{Tool.__name__}', got '{VllmConfig.__name__}'. If using a "
            "component registry, make sure that the components are correct."
        ),
    ):
        deserializer.from_yaml(
            serialized_main_config_with_custom_id, components_registry=mismatched_registry
        )


def test_deserialize_with_unsupported_registry_type_raises_error(
    serialized_main_config_with_custom_id: str,
) -> None:
    deserializer = AgentSpecDeserializer()
    mismatched_registry = {"custom_tool_id": "not_a_component"}  # String instead of Component
    with pytest.raises(
        ValueError, match="Type mismatch for ID custom_tool_id: expected Component, got str"
    ):
        deserializer.from_yaml(
            serialized_main_config_with_custom_id, components_registry=mismatched_registry  # type: ignore
        )


def test_serialize_disaggregated_with_same_component_multiple_times(
    simple_flow: Flow, vllm_config: VllmConfig
) -> None:
    serializer = AgentSpecSerializer()
    main_serialized, disagg_serialized = serializer.to_yaml(
        simple_flow,
        disaggregated_components=[
            (vllm_config, "llm_id1"),
            (vllm_config, "llm_id2"),
        ],
        export_disaggregated_components=True,
    )
    assert (
        "$component_ref: llm_id1" in main_serialized or "$component_ref: llm_id2" in main_serialized
    )
    disagg_dict = yaml.safe_load(disagg_serialized)
    assert "llm_id1" in disagg_dict["$referenced_components"]
    assert "llm_id2" in disagg_dict["$referenced_components"]
    assert (
        disagg_dict["$referenced_components"]["llm_id1"]
        == disagg_dict["$referenced_components"]["llm_id2"]
    )  # Same content


def test_deserialize_empty_disaggregated_only() -> None:
    empty_disagg = yaml.safe_dump({"$referenced_components": {}})
    deserializer = AgentSpecDeserializer()
    result = deserializer.from_yaml(empty_disagg, import_only_referenced_components=True)
    assert result == {}


def test_serialize_disaggregated_component_not_in_main(simple_agent: Agent) -> None:
    unused_tool = ClientTool(
        id="unused_id", name="unused", description="Unused", inputs=[], outputs=[]
    )
    serializer = AgentSpecSerializer()
    with pytest.warns(
        UserWarning,
        match="disaggregated components are not part of the main component.*'unused_id'",
    ):
        main_serialized, disagg_serialized = serializer.to_yaml(
            simple_agent,
            disaggregated_components=[unused_tool],
            export_disaggregated_components=True,
        )
    assert "$component_ref: unused_id" not in main_serialized  # Not referenced in main
    disagg_dict = yaml.safe_load(disagg_serialized)
    assert "unused_id" in disagg_dict["$referenced_components"]


def test_deserialize_main_missing_registry_reference_raises_error(
    serialized_main_config_with_custom_id: str,
) -> None:
    deserializer = AgentSpecDeserializer()
    with pytest.raises(KeyError, match="Missing reference for ID: custom_tool_id"):
        deserializer.from_yaml(serialized_main_config_with_custom_id, components_registry=None)


def test_deserialize_main_with_empty_registry(simple_flow: Flow) -> None:
    serializer = AgentSpecSerializer()
    serialized = serializer.to_yaml(simple_flow)
    deserializer = AgentSpecDeserializer()
    deserialized = deserializer.from_yaml(serialized, components_registry={})
    assert isinstance(deserialized, Flow)
    assert len(deserialized.nodes) > 0


def test_serialize_raises_on_root_component_disaggregation() -> None:
    start = StartNode(id="start", name="start")
    end = EndNode(id="end", name="end")
    flow = Flow(
        id="flow_id",
        name="flow",
        start_node=start,
        nodes=[start, end],
        control_flow_connections=[ControlFlowEdge(name="start_end", from_node=start, to_node=end)],
    )
    # Attempt to disaggregate the flow itself
    serializer = AgentSpecSerializer()
    with pytest.raises(ValueError, match="Disaggregating the root component is not allowed"):
        serializer.to_yaml(
            flow,
            disaggregated_components=[flow],
            export_disaggregated_components=True,
        )


@timeout(
    seconds=35,
    error_message="Encountered time complexity issue when disaggregating a deeply nested component",
)
@pytest.mark.parametrize("size", [4, 30])
def test_deeply_nested_flows_can_be_disaggregated(size) -> None:
    flow_omega = get_nested_flow(size)

    # Getting subflow "Flow_1_a"
    subflow = cast(FlowNode, cast(FlowNode, flow_omega.nodes[1]).subflow.nodes[1]).subflow
    serializer = AgentSpecSerializer()
    main_serialized, disagg_serialized = serializer.to_yaml(
        flow_omega,
        disaggregated_components=[(subflow, "nested_flow_id")],
        export_disaggregated_components=True,
    )

    assert "$component_ref: nested_flow_id" in main_serialized
    assert f"$component_ref: {subflow.id}" not in main_serialized

    assert "nested_flow_id:" in disagg_serialized
    assert f"{subflow.id}:" not in disagg_serialized

    # Deserialize disagg to get registry (partial)
    deserializer = AgentSpecDeserializer()
    partial_registry = deserializer.from_yaml(
        disagg_serialized, import_only_referenced_components=True
    )
    deser_flow = deserializer.from_yaml(main_serialized, components_registry=partial_registry)
    assert isinstance(deser_flow, Flow)
    # Check nested LLM node has config injected
    new_subflow = cast(FlowNode, cast(FlowNode, deser_flow.nodes[1]).subflow.nodes[1]).subflow
    assert subflow == new_subflow
