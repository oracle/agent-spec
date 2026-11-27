# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.llms.ociclientconfig import (
    OciClientConfig,
    OciClientConfigWithGenAiApiKey,
    OciClientConfigWithInstancePrincipal,
)
from pyagentspec.llms.ocigenaiconfig import ModelProvider, OciAPIType, OciGenAiConfig, ServingMode
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from .conftest import read_agentspec_config_file


@pytest.fixture
def oci_client() -> OciClientConfig:
    return OciClientConfigWithInstancePrincipal(
        service_endpoint="my_llm_endpoint", name="my_oci_config"
    )


@pytest.fixture
def oci_llm_config(oci_client: OciClientConfig) -> OciGenAiConfig:
    return OciGenAiConfig(
        name="oci_llm",
        description="my remote oci llm",
        id="oci_llm_123",
        model_id="cohere",
        client_config=oci_client,
        serving_mode=ServingMode.DEDICATED,
        provider=ModelProvider.COHERE,
        compartment_id="my_compartment",
    )


@pytest.fixture
def oci_xai_llm_config(oci_client: OciClientConfig) -> OciGenAiConfig:
    return OciGenAiConfig(
        name="oci_llm",
        description="my remote oci llm",
        id="oci_llm_123",
        model_id="grok-fast",
        client_config=oci_client,
        serving_mode=ServingMode.DEDICATED,
        provider=ModelProvider.XAI,
        compartment_id="my_compartment",
    )


def test_can_instantiate_ocigenai_config(oci_llm_config: OciGenAiConfig) -> None:
    assert oci_llm_config.name == "oci_llm"
    assert oci_llm_config.description == "my remote oci llm"
    assert oci_llm_config.compartment_id == "my_compartment"
    assert oci_llm_config.client_config.name == "my_oci_config"
    assert oci_llm_config.client_config.service_endpoint == "my_llm_endpoint"
    assert oci_llm_config.model_id == "cohere"
    assert oci_llm_config.serving_mode.value == "DEDICATED"
    assert oci_llm_config.provider is not None and oci_llm_config.provider.value == "COHERE"


def test_can_serialize_and_deserialize_ocigenai_config(oci_llm_config: OciGenAiConfig) -> None:
    serialized_assistant = AgentSpecSerializer().to_yaml(oci_llm_config)
    assert len(serialized_assistant.strip()) > 0
    deserialized_assistant = AgentSpecDeserializer().from_yaml(serialized_assistant)
    assert isinstance(deserialized_assistant, OciGenAiConfig)
    assert deserialized_assistant == oci_llm_config


def test_deserialize_ocigenai_config_from_file(oci_llm_config: OciGenAiConfig) -> None:
    serialized_agent = read_agentspec_config_file("ocigenaiconfig.yaml")
    deserialized_assistant = AgentSpecDeserializer().from_yaml(serialized_agent)
    assert deserialized_assistant.name == oci_llm_config.name


@pytest.fixture
def oci_responses_llm_config() -> OciGenAiConfig:
    return OciGenAiConfig(
        name="oci_llm",
        description="my remote oci llm",
        id="oci_llm_123",
        model_id="cohere",
        client_config=OciClientConfigWithInstancePrincipal(
            service_endpoint="my_llm_endpoint", name="my_oci_config"
        ),
        compartment_id="my_compartment",
        api_type=OciAPIType.OPENAI_RESPONSES,
        conversation_store_id="store_1",
    )


def test_can_serialize_and_deserialize_ocigenai_responses_config(
    oci_responses_llm_config: OciGenAiConfig,
) -> None:
    serialized_assistant = AgentSpecSerializer().to_yaml(oci_responses_llm_config)
    assert len(serialized_assistant.strip()) > 0
    assert "api_type" in serialized_assistant

    deserialized_assistant = AgentSpecDeserializer().from_yaml(serialized_assistant)
    assert isinstance(deserialized_assistant, OciGenAiConfig)
    assert deserialized_assistant._is_equal(
        oci_responses_llm_config, fields_to_exclude=["min_agentspec_version"]
    )
    assert deserialized_assistant.conversation_store_id == "store_1"
    assert deserialized_assistant.api_type == OciAPIType.OPENAI_RESPONSES


def test_export_config_without_responses_api_to_old_version_works(oci_llm_config: OciGenAiConfig):
    serialized_agent = AgentSpecSerializer().to_yaml(
        component=oci_llm_config,
        agentspec_version=AgentSpecVersionEnum.v25_4_1,
    )
    assert "api_type" not in serialized_agent
    assert "conversation_store_id" not in serialized_agent


def test_export_config_with_responses_api_to_old_version_raises(
    oci_responses_llm_config: OciGenAiConfig,
):
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        serialized_agent = AgentSpecSerializer().to_yaml(
            component=oci_responses_llm_config,
            agentspec_version=AgentSpecVersionEnum.v25_4_1,
        )


def test_can_serialize_and_deserialize_xai_ocigenai_config(
    oci_xai_llm_config: OciGenAiConfig,
) -> None:
    serialized_assistant = AgentSpecSerializer().to_yaml(
        oci_xai_llm_config, agentspec_version=AgentSpecVersionEnum.v26_1_2
    )
    assert len(serialized_assistant.strip()) > 0
    assert "XAI" in serialized_assistant
    deserialized_assistant = AgentSpecDeserializer().from_yaml(serialized_assistant)
    assert isinstance(deserialized_assistant, OciGenAiConfig)
    assert deserialized_assistant._is_equal(
        oci_xai_llm_config, fields_to_exclude=["min_agentspec_version"]
    )


def test_cannot_serialize_xai_ocigenai_config_with_old_versions(
    oci_xai_llm_config: OciGenAiConfig,
) -> None:
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecSerializer().to_yaml(
            oci_xai_llm_config, agentspec_version=AgentSpecVersionEnum.v26_1_0
        )


@pytest.fixture
def oci_genai_api_key_llm_config() -> OciGenAiConfig:
    return OciGenAiConfig(
        name="oci_llm",
        id="oci_llm_123",
        model_id="meta.llama-3.3-70b-instruct",
        client_config=OciClientConfigWithGenAiApiKey(
            id="my_oci_config_id",
            name="my_oci_config",
            service_endpoint="my_llm_endpoint",
            api_key="sk-secret",
        ),
        compartment_id="my_compartment",
        api_type=OciAPIType.OPENAI_CHAT_COMPLETIONS,
    )


def test_genai_api_key_client_config_requires_agentspec_26_4_0(
    oci_genai_api_key_llm_config: OciGenAiConfig,
) -> None:
    assert (
        oci_genai_api_key_llm_config.client_config.min_agentspec_version
        == AgentSpecVersionEnum.v26_4_0
    )
    # The client configuration lower-bounds the version of the whole LLM configuration
    min_version, min_component = (
        oci_genai_api_key_llm_config._get_min_agentspec_version_and_component()
    )
    assert min_version == AgentSpecVersionEnum.v26_4_0
    assert min_component is oci_genai_api_key_llm_config.client_config


def test_can_serialize_and_deserialize_genai_api_key_ocigenai_config(
    oci_genai_api_key_llm_config: OciGenAiConfig,
) -> None:
    serialized_llm = AgentSpecSerializer().to_yaml(
        oci_genai_api_key_llm_config, agentspec_version=AgentSpecVersionEnum.v26_4_0
    )
    assert "agentspec_version: 26.4.0" in serialized_llm
    assert "component_type: OciClientConfigWithGenAiApiKey" in serialized_llm
    assert "auth_type: GENAI_API_KEY" in serialized_llm
    assert "sk-secret" not in serialized_llm
    deserialized_llm = AgentSpecDeserializer().from_yaml(
        serialized_llm, components_registry={"my_oci_config_id.api_key": "sk-secret"}
    )
    assert isinstance(deserialized_llm, OciGenAiConfig)
    assert isinstance(deserialized_llm.client_config, OciClientConfigWithGenAiApiKey)
    assert deserialized_llm.client_config.api_key == "sk-secret"
    assert deserialized_llm._is_equal(
        oci_genai_api_key_llm_config, fields_to_exclude=["min_agentspec_version"]
    )


def test_cannot_serialize_genai_api_key_ocigenai_config_with_old_versions(
    oci_genai_api_key_llm_config: OciGenAiConfig,
) -> None:
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecSerializer().to_yaml(
            oci_genai_api_key_llm_config, agentspec_version=AgentSpecVersionEnum.v26_3_1
        )


def test_cannot_deserialize_genai_api_key_client_config_from_old_versions() -> None:
    serialized_client_config = """{
      "component_type": "OciClientConfigWithGenAiApiKey",
      "id": "my_oci_config_id",
      "name": "my_oci_config",
      "service_endpoint": "my_llm_endpoint",
      "auth_type": "GENAI_API_KEY",
      "agentspec_version": "26.3.1"
    }"""
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecDeserializer().from_json(serialized_client_config)
    accepted = serialized_client_config.replace('"26.3.1"', '"26.4.0"')
    client_config = AgentSpecDeserializer().from_json(accepted)
    assert isinstance(client_config, OciClientConfigWithGenAiApiKey)
    assert client_config.api_key is None
