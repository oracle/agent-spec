# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.nodes import AgentNode
from pyagentspec.llms.ociclientconfig import OciClientConfigWithInstancePrincipal
from pyagentspec.ociagent import OciAgent
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer

from .conftest import read_agentspec_config_file


@pytest.fixture
def oci_agent() -> OciAgent:
    return OciAgent(
        name="oci_agent",
        description="my remote oci agent",
        id="agent_123",
        client_config=OciClientConfigWithInstancePrincipal(
            service_endpoint="my_service_endpoint", name="my_oci_config"
        ),
        agent_endpoint_id="my_agent_endpoint",
    )


def test_can_instantiate_oci_agent(oci_agent: OciAgent) -> None:
    assert oci_agent.name == "oci_agent"
    assert oci_agent.description == "my remote oci agent"
    assert oci_agent.client_config.service_endpoint == "my_service_endpoint"
    assert oci_agent.client_config.name == "my_oci_config"
    assert oci_agent.agent_endpoint_id == "my_agent_endpoint"


def test_can_use_oci_agent_inside_agent_node(oci_agent: OciAgent) -> None:
    node = AgentNode(
        name="agent_node",
        agent=oci_agent,
    )
    serialized_assistant = AgentSpecSerializer().to_yaml(node)
    assert len(serialized_assistant.strip()) > 0
    deserialized_node = AgentSpecDeserializer().from_yaml(serialized_assistant)
    assert deserialized_node == node


def test_can_serialize_and_deserialize_oci_agent(oci_agent: OciAgent) -> None:
    serialized_assistant = AgentSpecSerializer().to_yaml(oci_agent)
    assert len(serialized_assistant.strip()) > 0
    deserialized_assistant = AgentSpecDeserializer().from_yaml(serialized_assistant)
    assert isinstance(deserialized_assistant, OciAgent)
    assert deserialized_assistant == oci_agent


def test_deserialize_oci_agent_from_file(oci_agent: OciAgent) -> None:
    serialized_agent = read_agentspec_config_file("ociagent.yaml")
    deserialized_assistant = AgentSpecDeserializer().from_yaml(serialized_agent)
    assert deserialized_assistant.name == oci_agent.name
