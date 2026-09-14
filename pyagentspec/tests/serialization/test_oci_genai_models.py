# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.llms import OciGenAiConfig
from pyagentspec.llms.ociclientconfig import (
    OciClientConfig,
    OciClientConfigWithApiKey,
    OciClientConfigWithGenAiApiKey,
    OciClientConfigWithInstancePrincipal,
    OciClientConfigWithResourcePrincipal,
    OciClientConfigWithSecurityToken,
)
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer


@pytest.mark.parametrize(
    "client_config",
    [
        OciClientConfigWithApiKey(
            id="client_config_id",
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
            auth_profile="DEFAULT",
            auth_file_location="~/.oci/config",
        ),
        OciClientConfigWithInstancePrincipal(
            id="client_config_id",
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
        ),
        OciClientConfigWithResourcePrincipal(
            id="client_config_id",
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
        ),
        OciClientConfigWithSecurityToken(
            id="client_config_id",
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
            auth_profile="DEFAULT",
            auth_file_location="~/.oci/config",
        ),
        OciClientConfigWithGenAiApiKey(
            id="client_config_id",
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
            api_key="sk-abcdexyz",
        ),
    ],
)
def test_can_serialize_and_deserialize_oci_genai_models(client_config: OciClientConfig) -> None:
    llm = OciGenAiConfig(
        name="ocigenai",
        model_id="provider.model_id",
        compartment_id="ID2",
        client_config=client_config,
    )
    serialized_llm = AgentSpecSerializer().to_yaml(llm)
    assert "name: oci_client_config" in serialized_llm
    assert "model_id: provider.model_id" in serialized_llm
    assert "client_config:" in serialized_llm
    assert "service_endpoint: SERVICE_ENDPOINT" in serialized_llm
    assert f"component_type: {type(client_config).__name__}" in serialized_llm
    deserialized_llm = AgentSpecDeserializer().from_yaml(
        serialized_llm,
        components_registry={
            "client_config_id.auth_file_location": "~/.oci/config",
            "client_config_id.api_key": "sk-abcdexyz",
        },
    )
    # Deserialized components carry the exported version as their min version
    assert deserialized_llm._is_equal(llm, fields_to_exclude=["min_agentspec_version"])


def test_genai_api_key_is_not_exported_and_may_be_left_to_the_runtime() -> None:
    llm = OciGenAiConfig(
        name="ocigenai",
        model_id="meta.llama-3.3-70b-instruct",
        compartment_id="ID2",
        client_config=OciClientConfigWithGenAiApiKey(
            id="client_config_id",
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
            api_key="sk-abcdexyz",
        ),
    )
    serialized_llm = AgentSpecSerializer().to_yaml(llm)
    assert "sk-abcdexyz" not in serialized_llm
    assert "auth_type: GENAI_API_KEY" in serialized_llm
    assert "$component_ref: client_config_id.api_key" in serialized_llm
    # The key is a sensitive field, so it has to be provided when importing the configuration
    with pytest.raises(ValueError, match="client_config_id.api_key"):
        AgentSpecDeserializer().from_yaml(serialized_llm)
    deserialized_llm = AgentSpecDeserializer().from_yaml(
        serialized_llm, components_registry={"client_config_id.api_key": "sk-abcdexyz"}
    )
    assert isinstance(deserialized_llm, OciGenAiConfig)
    assert isinstance(deserialized_llm.client_config, OciClientConfigWithGenAiApiKey)
    assert deserialized_llm.client_config.api_key == "sk-abcdexyz"
    assert deserialized_llm._is_equal(llm, fields_to_exclude=["min_agentspec_version"])


def test_genai_api_key_client_config_without_key_round_trips() -> None:
    # Leaving the key unset lets runtimes read it from OCI_GENAI_API_KEY
    llm = OciGenAiConfig(
        name="ocigenai",
        model_id="meta.llama-3.3-70b-instruct",
        compartment_id="ID2",
        client_config=OciClientConfigWithGenAiApiKey(
            name="oci_client_config", service_endpoint="SERVICE_ENDPOINT"
        ),
    )
    serialized_llm = AgentSpecSerializer().to_json(llm)
    assert "$component_ref" not in serialized_llm
    deserialized_llm = AgentSpecDeserializer().from_json(serialized_llm)
    assert isinstance(deserialized_llm, OciGenAiConfig)
    assert isinstance(deserialized_llm.client_config, OciClientConfigWithGenAiApiKey)
    assert deserialized_llm.client_config.api_key is None
    assert deserialized_llm._is_equal(llm, fields_to_exclude=["min_agentspec_version"])
