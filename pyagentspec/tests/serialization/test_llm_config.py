# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.llms import (
    OllamaConfig,
    OpenAiCompatibleConfig,
    OpenAiConfig,
    VllmConfig,
)
from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer

from .conftest import assert_serialized_representations_are_equal


def test_can_serialize_and_deserialize_llm_config_with_arbitrary_generation_config_params() -> None:
    vllm_config = VllmConfig(
        id="vllm",
        name="agi1",
        model_id="agi_model1",
        url="http://some.where",
        default_generation_parameters=LlmGenerationConfig(
            temperature=0.3,
            custom_attribute_1="custom_value_1",  # type: ignore
            custom_attribute_2=True,  # type: ignore
        ),
    )
    serializer = AgentSpecSerializer()
    serialized_llm = serializer.to_yaml(vllm_config)
    assert "component_type: VllmConfig" in serialized_llm
    assert "temperature: 0.3" in serialized_llm
    assert "custom_attribute_1: custom_value_1" in serialized_llm
    assert "custom_attribute_2: true" in serialized_llm

    deserializer = AgentSpecDeserializer()
    deserialized_llm = deserializer.from_yaml(serialized_llm)
    assert_serialized_representations_are_equal(
        serialized_llm, serializer.to_yaml(deserialized_llm)
    )


@pytest.mark.parametrize(
    "llm_config",
    [
        OllamaConfig(
            id="ollama",
            name="agi1",
            model_id="agi_model1",
            url="http://some.where",
            default_generation_parameters=LlmGenerationConfig(max_tokens=32),
        ),
        OpenAiCompatibleConfig(
            id="openai_compatible",
            name="agi2",
            model_id="agi_model2",
            url="http://some.where",
            api_key="api_key",
            default_generation_parameters=LlmGenerationConfig(top_p=3),
        ),
        VllmConfig(
            id="vllm",
            name="agi3",
            model_id="agi_model3",
            url="http://some.where",
            default_generation_parameters=LlmGenerationConfig(temperature=0.4),
        ),
        OpenAiConfig(
            id="openai",
            name="agi4",
            model_id="agi_model4",
            api_key="api_key",
            default_generation_parameters=LlmGenerationConfig(),
        ),
    ],
)
def test_can_serialize_and_deserialize_llm_config(llm_config: VllmConfig) -> None:
    serializer = AgentSpecSerializer()
    serialized_llm = serializer.to_yaml(llm_config)
    assert f"component_type: {type(llm_config).__name__}"
    assert f"name: agi"
    assert f"model_id: agi_model"
    deserialized_llm = AgentSpecDeserializer().from_yaml(
        serialized_llm,
        components_registry={"openai.api_key": "api_key", "openai_compatible.api_key": "api_key"},
    )
    assert llm_config == deserialized_llm
