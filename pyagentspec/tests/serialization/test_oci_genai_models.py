# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import pytest

from pyagentspec.llms import OciGenAiConfig
from pyagentspec.llms.ociclientconfig import (
    OciClientConfig,
    OciClientConfigWithApiKey,
    OciClientConfigWithInstancePrincipal,
    OciClientConfigWithResourcePrincipal,
    OciClientConfigWithSecurityToken,
)
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer


@pytest.mark.parametrize(
    "client_config",
    [
        OciClientConfigWithApiKey(
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
            auth_profile="DEFAULT",
            auth_file_location="~/.oci/config",
        ),
        OciClientConfigWithInstancePrincipal(
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
        ),
        OciClientConfigWithResourcePrincipal(
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
        ),
        OciClientConfigWithSecurityToken(
            name="oci_client_config",
            service_endpoint="SERVICE_ENDPOINT",
            auth_profile="DEFAULT",
            auth_file_location="~/.oci/config",
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
    deserialized_llm = AgentSpecDeserializer().from_yaml(serialized_llm)
    assert llm == deserialized_llm
