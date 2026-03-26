# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum


@pytest.fixture
def openai_compatible_config_with_certificates() -> OpenAiCompatibleConfig:
    return OpenAiCompatibleConfig(
        name="openai-compatible-config",
        id="openai-compatible-config-id",
        url="https://api.closedai.com/v2",
        model_id="gpt-7",
        key_file="/etc/certs/client.key",
        cert_file="/etc/certs/client.pem",
        ca_file="/etc/certs/ca.pem",
    )


@pytest.fixture
def openai_compatible_config_without_certificates() -> OpenAiCompatibleConfig:
    return OpenAiCompatibleConfig(
        name="openai-compatible-config",
        id="openai-compatible-config-id",
        url="https://api.closedai.com/v2",
        model_id="gpt-7",
    )


def test_openaicompatible_config_with_certificates_has_min_version_26_2_0(
    openai_compatible_config_with_certificates: OpenAiCompatibleConfig,
) -> None:
    assert (
        openai_compatible_config_with_certificates.min_agentspec_version
        == AgentSpecVersionEnum.v26_2_0
    )


def test_can_serialize_and_deserialize_openaicompatible_config_with_certificates(
    openai_compatible_config_with_certificates: OpenAiCompatibleConfig,
) -> None:
    serialized = AgentSpecSerializer().to_json(openai_compatible_config_with_certificates)
    deserialized = AgentSpecDeserializer().from_json(
        serialized,
        components_registry={
            "openai-compatible-config-id.key_file": "/etc/certs/client.key",
            "openai-compatible-config-id.cert_file": "/etc/certs/client.pem",
            "openai-compatible-config-id.ca_file": "/etc/certs/ca.pem",
        },
    )

    assert isinstance(deserialized, OpenAiCompatibleConfig)
    assert deserialized == openai_compatible_config_with_certificates


def test_export_config_without_certificates_to_version_26_1_0_works(
    openai_compatible_config_without_certificates: OpenAiCompatibleConfig,
) -> None:
    serialized = AgentSpecSerializer().to_yaml(
        component=openai_compatible_config_without_certificates,
        agentspec_version=AgentSpecVersionEnum.v26_1_0,
    )

    assert "key_file" not in serialized
    assert "cert_file" not in serialized
    assert "ca_file" not in serialized


def test_export_config_with_certificates_to_version_26_1_0_raises(
    openai_compatible_config_with_certificates: OpenAiCompatibleConfig,
) -> None:
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_yaml(
            component=openai_compatible_config_with_certificates,
            agentspec_version=AgentSpecVersionEnum.v26_1_0,
        )


def test_deserializing_config_with_certificates_and_unsupported_version_raises(
    openai_compatible_config_with_certificates: OpenAiCompatibleConfig,
) -> None:
    import yaml

    serialized = AgentSpecSerializer().to_yaml(openai_compatible_config_with_certificates)
    loaded = yaml.safe_load(serialized)
    loaded["agentspec_version"] = AgentSpecVersionEnum.v26_1_0

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecDeserializer().from_dict(
            loaded,
            components_registry={
                "openai-compatible-config-id.key_file": "/etc/certs/client.key",
                "openai-compatible-config-id.cert_file": "/etc/certs/client.pem",
                "openai-compatible-config-id.ca_file": "/etc/certs/ca.pem",
            },
        )
