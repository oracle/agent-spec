# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.a2aagent import A2AAgent
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
    )


def test_can_instantiate_a2aagent(a2aagent: A2AAgent) -> None:
    assert a2aagent.name == "a2a_agent"
    assert a2aagent.description == "client to connect remote agent using a2a protocol"
    assert a2aagent.id == "agent123"
    assert a2aagent.agent_url == "http://127.0.0.1:8000"


def test_can_serialize_and_deserialize_a2aagent(a2aagent: A2AAgent) -> None:
    serialized_assistant = AgentSpecSerializer().to_yaml(a2aagent)
    assert len(serialized_assistant.strip()) > 0
    deserialized_assistant = AgentSpecDeserializer().from_yaml(serialized_assistant)
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
