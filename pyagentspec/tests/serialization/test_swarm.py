# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import pytest

from pyagentspec.agent import Agent
from pyagentspec.llms import VllmConfig
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.swarm import Swarm
from pyagentspec.versioning import AgentSpecVersionEnum

from .conftest import assert_serialized_representations_are_equal


@pytest.fixture
def example_swarm() -> Swarm:
    llm_config = VllmConfig(
        id="vllm",
        model_id="model_id",
        url="LLAMA_PLACEHOLDER_LINK",
        name="model_name",
    )

    general_practitioner = Agent(
        id="general_practitioner",
        name="GeneralPractitioner",
        description="General Practitioner. Primary point of contact for patients, handles general medical inquiries, provides initial diagnoses, and manages referrals.",
        llm_config=llm_config,
        system_prompt="You are a general practitioner",
    )

    pharmacist = Agent(
        id="pharmacist",
        name="Pharmacist",
        description="Pharmacist. Gives availability and information about specific medication.",
        llm_config=llm_config,
        system_prompt="You are a pharmacist",
    )

    dermatologist = Agent(
        id="dermatologist",
        name="Dermatologist",
        description="Dermatologist. Diagnoses and treats skin conditions.",
        llm_config=llm_config,
        system_prompt="You are a dermatologist",
    )

    return Swarm(
        id="swarm",
        name="Swarm",
        first_agent=general_practitioner,
        relationships=[
            (general_practitioner, pharmacist),
            (general_practitioner, dermatologist),
            (dermatologist, pharmacist),
        ],
    )


def test_can_serialize_and_deserialize_swarm(example_serialized_swarm: str, example_swarm: Swarm):
    swarm = example_swarm

    assert swarm.min_agentspec_version == AgentSpecVersionEnum.v25_4_2

    serialized_swarm = AgentSpecSerializer().to_yaml(swarm)
    assert_serialized_representations_are_equal(serialized_swarm, example_serialized_swarm)

    deserialized_swarm = AgentSpecDeserializer().from_yaml(serialized_swarm)
    assert deserialized_swarm.min_agentspec_version == AgentSpecVersionEnum.v25_4_2
    assert isinstance(deserialized_swarm, Swarm)

    # We override the min version of the component to make it equal to the one before serialization
    # This is because the version of the deserialized one is aligned to the agentspec_version of the yaml loaded.
    deserialized_swarm.first_agent.llm_config.min_agentspec_version = AgentSpecVersionEnum.v25_4_1
    deserialized_swarm.first_agent.min_agentspec_version = AgentSpecVersionEnum.v25_4_1
    for agent1, agent2 in deserialized_swarm.relationships:
        agent1.min_agentspec_version = AgentSpecVersionEnum.v25_4_1
        agent2.min_agentspec_version = AgentSpecVersionEnum.v25_4_1

    assert deserialized_swarm == swarm


def test_serializing_swarm_with_unsupported_version_raises_error(example_swarm: Swarm):
    swarm = example_swarm

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_yaml(swarm, agentspec_version=AgentSpecVersionEnum.v25_4_1)


def test_deserializing_swarm_with_unsupported_version_raises_error(example_serialized_swarm: str):
    serialized_swarm = example_serialized_swarm
    assert "agentspec_version: 25.4.2" in serialized_swarm
    serialized_swarm = serialized_swarm.replace(
        "agentspec_version: 25.4.2", "agentspec_version: 25.4.1"
    )

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecDeserializer().from_yaml(serialized_swarm)
