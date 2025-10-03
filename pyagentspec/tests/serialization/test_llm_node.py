# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.serialization import AgentSpecSerializer

from .conftest import assert_serialized_representations_are_equal


def test_can_serialize_llm_node(example_serialized_llm_node: str) -> None:
    vllmconfig = VllmConfig(
        id="vllm",
        name="agi1",
        model_id="agi_model1",
        url="http://some.where",
        default_generation_parameters=LlmGenerationConfig(),
    )
    node = LlmNode(
        id="DUMMY_NODE",
        name="dummy",
        llm_config=vllmconfig,
        prompt_template="reply to this questions: {{question}}",
        metadata={
            "metadata_field_1": 1,
            "metadata_field_2": [1, 2],
            "metadata_field_3": {"a": 1, "b": "c", "d": [5, 6]},
        },
    )
    serializer = AgentSpecSerializer()
    serialized_node = serializer.to_yaml(node)
    assert_serialized_representations_are_equal(serialized_node, example_serialized_llm_node)
