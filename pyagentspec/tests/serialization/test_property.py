# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.llms import LlmGenerationConfig
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import (
    BooleanProperty,
    DictProperty,
    FloatProperty,
    IntegerProperty,
    ListProperty,
    NullProperty,
    Property,
    StringProperty,
    UnionProperty,
)
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer

from .conftest import assert_serialized_representations_are_equal


def test_can_serialize_flow_with_properties(example_serialized_flow_with_properties: str) -> None:
    input_1 = StringProperty(title="Input_1", default="input_1_default")
    input_2 = DictProperty(title="Input_2", value_type=StringProperty(), default={})
    input_3 = Property(json_schema=dict(title="Input_3", type=["null", "integer"], default=None))
    input_4 = ListProperty(title="Input_4", default=[], item_type=FloatProperty())

    output_1 = BooleanProperty(title="Output_1", default=True)
    output_2 = ListProperty(title="Output_2", default=[1.0], item_type=FloatProperty())
    output_3 = UnionProperty(title="Output_3", any_of=[NullProperty(), IntegerProperty()])

    # VllmConfig is a subclass of Component, we will define it more in detail later
    # This Component does not have input/output schemas, the default should be an empty list
    vllm = VllmConfig(
        id="99asbdiugjk4b5",
        name="LLama 3.1 8b",
        description="llama 3.1 config",
        model_id="llama3.1-8b-instruct",
        url="url.to.my.llm.com/hostedllm:12345",
    )

    node_1 = StartNode(
        id="lniwuebjsdvkc",
        name="Node 1",
        inputs=[input_1, output_3],
    )

    node_2 = LlmNode(
        id="nxbcwoiauhbjv",
        name="Node 2",
        llm_config=vllm,
        prompt_template="This is the prompt! {{ Input_2 }} {{ Input_3 }}",
        inputs=[input_2, input_3],
        outputs=[output_2],
    )

    node_3 = EndNode(
        id="724893yhrj",
        name="Node 3",
        outputs=[output_2, input_3, input_2, input_4],
    )

    # Control flow edges
    control_edge_1 = ControlFlowEdge(
        id="nh32tewsaicjkl", name="ctrl_edge_1", from_node=node_1, to_node=node_2
    )
    control_edge_2 = ControlFlowEdge(
        id="28yu3egh", name="ctrl_edge_2", from_node=node_2, to_node=node_3
    )

    # Data flow edges
    data_edge_1 = DataFlowEdge(
        id="buhdgsbjmn",
        name="data_edge_1",
        source_node=node_1,
        source_output="Output_3",
        destination_node=node_2,
        destination_input="Input_3",
    )
    data_edge_2 = DataFlowEdge(
        id="67uyh5423hje",
        name="data_edge_2",
        source_node=node_2,
        source_output="Output_2",
        destination_node=node_3,
        destination_input="Input_4",
    )
    data_edge_3 = DataFlowEdge(
        id="722njqbakhcsa",
        name="data_edge_3",
        source_node=node_1,
        source_output="Output_3",
        destination_node=node_3,
        destination_input="Input_3",
    )

    flow = Flow(
        id="mmnhagawse",
        name="Example test flow",
        start_node=node_1,
        nodes=[node_1, node_2, node_3],
        control_flow_connections=[control_edge_1, control_edge_2],
        data_flow_connections=[data_edge_1, data_edge_2, data_edge_3],
        inputs=[input_1, output_3],
        outputs=[output_2, output_1],
    )

    serializer = AgentSpecSerializer()
    serialized_flow = serializer.to_yaml(flow)
    assert_serialized_representations_are_equal(
        serialized_flow, example_serialized_flow_with_properties
    )


def test_optional_property_is_correctly_serialized_and_deserialized_when_it_has_a_value() -> None:
    llm = VllmConfig(
        name="vllm",
        url="http://some.where",
        model_id="some-model",
        default_generation_parameters=LlmGenerationConfig(
            temperature=0.5,
            max_tokens=123,
        ),
    )
    serialized_llm = AgentSpecSerializer().to_yaml(llm)
    new_llm = AgentSpecDeserializer().from_yaml(serialized_llm)
    assert isinstance(new_llm, VllmConfig)
    assert new_llm.default_generation_parameters
    assert new_llm.default_generation_parameters.temperature == 0.5


def test_optional_property_is_correctly_serialized_and_deserialized_when_it_is_none() -> None:
    llm = VllmConfig(
        name="vllm",
        url="http://some.where",
        model_id="some-model",
        default_generation_parameters=None,
    )
    serialized_llm = AgentSpecSerializer().to_yaml(llm)
    new_llm = AgentSpecDeserializer().from_yaml(serialized_llm)
    assert isinstance(new_llm, VllmConfig)
    assert new_llm.default_generation_parameters is None
