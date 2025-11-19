# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.a2aagent import A2AAgent, A2AConnectionConfig, A2ASessionParameters
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from .conftest import read_agentspec_config_file


@pytest.fixture
def a2aagent() -> A2AAgent:
    return A2AAgent(
        name="a2a_agent",
        description="client to connect remote agent using a2a protocol",
        id="agent123",
        agent_url="http://127.0.0.1:8000",
        connection_config=A2AConnectionConfig(
            name="sample_connection_config",
            timeout=100.0,
            verify=True,
            key_file="/path/to/key.pem",
            cert_file="/path/to/cert.pem",
            ssl_ca_cert="/path/to/ca.pem",
        ),
        session_parameters=A2ASessionParameters(timeout=20.0, poll_interval=3.0, max_retries=4),
    )


def test_can_instantiate_a2aagent(a2aagent: A2AAgent) -> None:
    assert a2aagent.name == "a2a_agent"
    assert a2aagent.description == "client to connect remote agent using a2a protocol"
    assert a2aagent.id == "agent123"
    assert a2aagent.agent_url == "http://127.0.0.1:8000"
    assert isinstance(a2aagent.connection_config, A2AConnectionConfig)
    assert isinstance(a2aagent.session_parameters, A2ASessionParameters)


def test_a2aagent_connection_config_parameters(a2aagent: A2AAgent) -> None:
    config = a2aagent.connection_config
    assert config.timeout == 100.0
    assert config.verify is True
    assert config.key_file == "/path/to/key.pem"
    assert config.cert_file == "/path/to/cert.pem"
    assert config.ssl_ca_cert == "/path/to/ca.pem"


def test_a2aagent_session_parameters(a2aagent: A2AAgent) -> None:
    params = a2aagent.session_parameters
    assert params.timeout == 20.0
    assert params.poll_interval == 3.0
    assert params.max_retries == 4


def test_can_serialize_and_deserialize_a2aagent(a2aagent: A2AAgent) -> None:
    serialized_assistant = AgentSpecSerializer().to_yaml(a2aagent)
    assert len(serialized_assistant.strip()) > 0
    deserialized_assistant = AgentSpecDeserializer().from_yaml(serialized_assistant)
    assert deserialized_assistant == a2aagent
    with pytest.raises(
        ValueError, match="Invalid agentspec_version:.*but the minimum allowed version is.*"
    ):
        _ = AgentSpecSerializer().to_json(a2aagent, agentspec_version=AgentSpecVersionEnum.v25_4_1)
    assert isinstance(deserialized_assistant, A2AAgent)
    assert deserialized_assistant == a2aagent


def test_deserialize_a2aagent_from_file(a2aagent: A2AAgent) -> None:
    serialized_agent = read_agentspec_config_file("a2aagent.yaml")
    deserialized_assistant = AgentSpecDeserializer().from_yaml(serialized_agent)
    assert deserialized_assistant.name == a2aagent.name
