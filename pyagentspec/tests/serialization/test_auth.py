# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.auth import OAuthClientConfig, OAuthConfig, OAuthEndpoints, PKCEMethod, PKCEPolicy
from pyagentspec.mcp.clienttransport import SSETransport
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from .conftest import assert_serialized_representations_are_equal


@pytest.fixture
def example_oauth_config() -> OAuthConfig:
    return OAuthConfig(
        id="oauth",
        name="OAuth",
        issuer="https://issuer.example.com",
        endpoints=OAuthEndpoints(
            authorization_endpoint="https://issuer.example.com/auth",
            token_endpoint="https://issuer.example.com/token",  # nosec B106: false positive
        ),
        client=OAuthClientConfig(
            id="client",
            name="OAuthClientConfig",
            type="pre_registered",
            client_id="client_id",
            client_secret="client_secret",  # nosec B106: false positive
        ),
        redirect_uri="https://app.example.com/callback",
        scopes=["openid", "profile"],
        pkce=PKCEPolicy(required=True, method=PKCEMethod.S256),
    )


@pytest.fixture
def example_transport_with_oauth(example_oauth_config: OAuthConfig) -> SSETransport:
    return SSETransport(
        id="transport",
        name="SSETransport",
        url="https://mcp.example.com",
        auth=example_oauth_config,
    )


def test_oauth_components_have_min_version(example_oauth_config: OAuthConfig):
    assert example_oauth_config.min_agentspec_version == AgentSpecVersionEnum.v26_2_0
    assert example_oauth_config.client.min_agentspec_version == AgentSpecVersionEnum.v26_2_0
    assert example_oauth_config.endpoints is not None
    assert example_oauth_config.pkce is not None


def test_remote_transport_infers_min_version_from_auth(example_transport_with_oauth: SSETransport):
    assert example_transport_with_oauth.min_agentspec_version == AgentSpecVersionEnum.v26_2_0


def test_can_serialize_and_deserialize_oauth_transport(example_transport_with_oauth: SSETransport):
    transport = example_transport_with_oauth

    assert transport.min_agentspec_version == AgentSpecVersionEnum.v26_2_0

    serialized = AgentSpecSerializer().to_yaml(transport)
    deserialized = AgentSpecDeserializer().from_yaml(serialized)

    assert deserialized.min_agentspec_version == AgentSpecVersionEnum.v26_2_0
    assert isinstance(deserialized, SSETransport)

    # Align versions to avoid equality mismatches due to deserialization context.
    deserialized.min_agentspec_version = transport.min_agentspec_version
    assert deserialized.auth is not None
    deserialized.auth.min_agentspec_version = transport.auth.min_agentspec_version

    assert deserialized == transport


def test_serializing_oauth_transport_with_unsupported_version_raises_error(
    example_transport_with_oauth: SSETransport,
):
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_yaml(
            example_transport_with_oauth, agentspec_version=AgentSpecVersionEnum.v26_1_0
        )


def test_deserializing_oauth_transport_with_unsupported_version_raises_error(
    example_transport_with_oauth: SSETransport,
):
    import yaml

    serialized = AgentSpecSerializer().to_yaml(example_transport_with_oauth)
    loaded = yaml.safe_load(serialized)
    loaded["agentspec_version"] = AgentSpecVersionEnum.v26_1_0

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecDeserializer().from_dict(loaded)


def test_oauth_transport_yaml_is_stable(example_transport_with_oauth: SSETransport):
    serialized = AgentSpecSerializer().to_yaml(example_transport_with_oauth)

    # Parse + re-serialize to assert stable representation.
    parsed = AgentSpecDeserializer().from_yaml(serialized)
    reserialized = AgentSpecSerializer().to_yaml(parsed)
    assert_serialized_representations_are_equal(serialized, reserialized)
