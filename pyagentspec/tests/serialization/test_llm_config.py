# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.llms import (
    LlmConfig,
    OllamaConfig,
    OpenAiCompatibleConfig,
    OpenAiConfig,
    VllmConfig,
)
from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

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
        LlmConfig(
            id="generic",
            name="agi5",
            model_id="gpt-4o",
            provider="openai",
            api_provider="openai",
        ),
    ],
)
def test_can_serialize_and_deserialize_llm_config(llm_config: LlmConfig) -> None:
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


def test_bare_llmconfig_instantiation_all_fields() -> None:
    config = LlmConfig(
        id="test",
        name="test_llm",
        model_id="gpt-4o",
        provider="openai",
        api_provider="openai",
        api_type="chat_completions",
        url="https://api.openai.com/v1",
        api_key="sk-test-key",
    )
    assert config.model_id == "gpt-4o"
    assert config.provider == "openai"
    assert config.api_provider == "openai"
    assert config.api_type == "chat_completions"
    assert config.url == "https://api.openai.com/v1"
    assert config.api_key == "sk-test-key"
    assert config.component_type == "LlmConfig"


def test_bare_llmconfig_instantiation_minimal() -> None:
    config = LlmConfig(
        name="minimal",
        model_id="some-model",
    )
    assert config.model_id == "some-model"
    assert config.provider is None
    assert config.api_provider is None
    assert config.api_type is None
    assert config.url is None
    assert config.api_key is None


def test_bare_llmconfig_serialization_roundtrip() -> None:
    config = LlmConfig(
        id="generic_llm",
        name="generic",
        model_id="gpt-4o",
        provider="openai",
        api_provider="openai",
        api_type="chat_completions",
    )
    serializer = AgentSpecSerializer()
    serialized = serializer.to_yaml(config)
    assert "component_type: LlmConfig" in serialized
    assert "model_id: gpt-4o" in serialized
    assert "provider: openai" in serialized
    assert "api_provider: openai" in serialized
    assert "api_type: chat_completions" in serialized

    deserialized = AgentSpecDeserializer().from_yaml(serialized)
    assert config == deserialized


def test_bare_llmconfig_serialization_with_url_and_api_key() -> None:
    config = LlmConfig(
        id="custom_endpoint",
        name="custom",
        model_id="gpt-4o",
        api_provider="openai",
        url="https://my-proxy.example.com/v1",
        api_key="sk-test-key",
    )
    serializer = AgentSpecSerializer()
    serialized = serializer.to_yaml(config)
    assert "url: https://my-proxy.example.com/v1" in serialized
    # api_key is a SensitiveField, should be replaced by a reference
    assert "api_key:" in serialized
    assert "sk-test-key" not in serialized

    deserialized = AgentSpecDeserializer().from_yaml(
        serialized,
        components_registry={"custom_endpoint.api_key": "sk-test-key"},
    )
    assert config == deserialized


def test_frozen_fields_not_serialized_on_subclasses() -> None:
    openai_config = OpenAiConfig(
        id="openai",
        name="openai_llm",
        model_id="gpt-4o",
    )
    serializer = AgentSpecSerializer()
    serialized = serializer.to_yaml(openai_config)
    # provider and api_provider are frozen on OpenAiConfig, should not be serialized
    assert "provider:" not in serialized
    assert "api_provider:" not in serialized
    # url is excluded from subclasses (they have their own URL fields)
    assert "url:" not in serialized

    vllm_config = VllmConfig(
        id="vllm",
        name="vllm_llm",
        model_id="some-model",
        url="http://localhost:8000",
    )
    serialized_vllm = serializer.to_yaml(vllm_config)
    # api_provider is frozen on VllmConfig, provider is not meaningful
    assert "api_provider:" not in serialized_vllm
    assert "provider:" not in serialized_vllm

    ollama_config = OllamaConfig(
        id="ollama",
        name="ollama_llm",
        model_id="llama3",
        url="http://localhost:11434",
    )
    serialized_ollama = serializer.to_yaml(ollama_config)
    # api_provider is frozen on OllamaConfig, provider is not meaningful
    assert "api_provider:" not in serialized_ollama
    assert "provider:" not in serialized_ollama


def test_version_inference_bare_llmconfig_always_requires_v26_2_0() -> None:
    # Bare LlmConfig is a v26_2_0 feature (it was abstract before),
    # regardless of which fields are set
    config_minimal = LlmConfig(
        name="basic",
        model_id="some-model",
    )
    assert config_minimal.min_agentspec_version == AgentSpecVersionEnum.v26_2_0

    config_with_fields = LlmConfig(
        name="with_provider",
        model_id="some-model",
        provider="openai",
        api_provider="openai",
        api_type="chat_completions",
    )
    assert config_with_fields.min_agentspec_version == AgentSpecVersionEnum.v26_2_0
