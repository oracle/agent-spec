# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import pytest

from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.llms import LlmConfig, VllmConfig
from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig
from pyagentspec.property import DictProperty, IntegerProperty, Property, StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from .conftest import assert_serialized_representations_are_equal


def test_can_serialize_llm_node(example_serialized_llm_node: str) -> None:
    node = LlmNode(
        id="DUMMY_NODE",
        name="dummy",
        llm_config=VllmConfig(
            id="vllm",
            name="agi1",
            model_id="agi_model1",
            url="http://some.where",
            default_generation_parameters=LlmGenerationConfig(),
        ),
        prompt_template="reply to this questions: {{question}}",
        metadata={
            "metadata_field_1": 1,
            "metadata_field_2": [1, 2],
            "metadata_field_3": {"a": 1, "b": "c", "d": [5, 6]},
        },
    )

    assert len(node.inputs or []) == 1
    assert len(node.outputs or []) == 1
    assert node.min_agentspec_version == AgentSpecVersionEnum.v25_4_1

    serializer = AgentSpecSerializer()
    serialized_node = serializer.to_yaml(node)
    assert_serialized_representations_are_equal(serialized_node, example_serialized_llm_node)


def test_can_serialize_and_deserialize_llm_node_with_single_nonstring_output(
    default_llm_config: LlmConfig,
) -> None:
    node = LlmNode(
        name="dummy",
        llm_config=default_llm_config,
        prompt_template="What is the fastest italian car?",
        outputs=[Property(json_schema={"title": "car"})],
    )

    assert node.inputs is not None and len(node.inputs) == 0
    assert len(node.outputs or []) == 1
    assert node.min_agentspec_version == AgentSpecVersionEnum.v25_4_2

    serializer = AgentSpecSerializer()
    serialized_node = serializer.to_yaml(node)
    assert "title: car" in serialized_node
    assert "agentspec_version: 25.4.2" in serialized_node

    deserialized_node = AgentSpecDeserializer().from_yaml(serialized_node)
    # We override the min version of the component to make it equal to the one before serialization
    # This is because the version of the deserialized one is aligned to the agentspec_version of the yaml loaded.
    deserialized_node.llm_config.min_agentspec_version = AgentSpecVersionEnum.v25_4_1
    assert deserialized_node == node


def test_can_serialize_and_deserialize_llm_node_with_multiple_outputs(
    default_llm_config: LlmConfig,
) -> None:
    node = LlmNode(
        name="dummy",
        llm_config=default_llm_config,
        prompt_template="What is the fastest italian car?",
        outputs=[
            StringProperty(title="brand", description="The brand of the car"),
            StringProperty(title="model", description="The name of the car's model"),
            IntegerProperty(
                title="hp", description="The horsepower amount, which expresses the car's power"
            ),
        ],
    )

    assert node.inputs is not None and len(node.inputs) == 0
    assert len(node.outputs or []) == 3
    assert node.min_agentspec_version == AgentSpecVersionEnum.v25_4_2

    serializer = AgentSpecSerializer()
    serialized_node = serializer.to_yaml(node)
    assert "title: brand" in serialized_node
    assert "title: model" in serialized_node
    assert "title: hp" in serialized_node
    assert "agentspec_version: 25.4.2" in serialized_node

    deserialized_node = AgentSpecDeserializer().from_yaml(serialized_node)
    # We override the min version of the component to make it equal to the one before serialization
    # This is because the version of the deserialized one is aligned to the agentspec_version of the yaml loaded.
    deserialized_node.llm_config.min_agentspec_version = AgentSpecVersionEnum.v25_4_1
    assert deserialized_node == node


def test_serializing_node_with_structured_generation_and_unsupported_version_raises(
    default_llm_config: LlmConfig,
) -> None:
    node = LlmNode(
        name="dummy",
        llm_config=default_llm_config,
        prompt_template="What is the fastest italian car?",
        outputs=[
            StringProperty(title="brand", description="The brand of the car"),
            StringProperty(title="model", description="The name of the car's model"),
            IntegerProperty(
                title="hp", description="The horsepower amount, which expresses the car's power"
            ),
        ],
    )
    serializer = AgentSpecSerializer()
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = serializer.to_yaml(node, agentspec_version=AgentSpecVersionEnum.v25_4_1)


def test_deserializing_node_with_structured_generation_and_unsupported_version_raises(
    default_llm_config: LlmConfig,
) -> None:
    node = LlmNode(
        name="dummy",
        llm_config=default_llm_config,
        prompt_template="What is the fastest italian car?",
        outputs=[
            StringProperty(title="brand", description="The brand of the car"),
            StringProperty(title="model", description="The name of the car's model"),
            IntegerProperty(
                title="hp", description="The horsepower amount, which expresses the car's power"
            ),
        ],
    )
    serializer = AgentSpecSerializer()
    serialized_node = serializer.to_yaml(node)
    assert "agentspec_version: 25.4.2" in serialized_node
    serialized_node = serialized_node.replace(
        "agentspec_version: 25.4.2", "agentspec_version: 25.4.1"
    )

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecDeserializer().from_yaml(serialized_node)
