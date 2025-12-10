# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.llms.ociclientconfig import OciClientConfigWithInstancePrincipal
from pyagentspec.llms.ocigenaiconfig import ModelProvider, OciAPIType, OciGenAiConfig, ServingMode
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from .conftest import read_agentspec_config_file


@pytest.fixture
def oci_llm_config() -> OciGenAiConfig:
    return OciGenAiConfig(
        name="oci_llm",
        description="my remote oci llm",
        id="oci_llm_123",
        model_id="cohere",
        client_config=OciClientConfigWithInstancePrincipal(
            service_endpoint="my_llm_endpoint", name="my_oci_config"
        ),
        serving_mode=ServingMode.DEDICATED,
        provider=ModelProvider.COHERE,
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
