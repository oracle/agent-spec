# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import pytest

from pyagentspec.agent import Agent
from pyagentspec.llms import VllmConfig
from pyagentspec.managerworkers import ManagerWorkers
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from ..conftest import read_agentspec_config_file
from .conftest import assert_serialized_representations_are_equal


@pytest.fixture
def example_managerworkers() -> ManagerWorkers:
    llm_config = VllmConfig(
        id="vllm",
        model_id="model_id",
        url="LLAMA_PLACEHOLDER_LINK",
        name="model_name",
    )

    refund_specialist_agent = Agent(
        id="refund_specialist",
        name="RefundSpecialist",
        description="Specializes in processing customer refund requests by verifying eligibility and executing the refund transaction using available tools.",
        llm_config=llm_config,
        system_prompt="You are a Refund Specialist agent whose objective is to process customer refund requests accurately and efficiently based on company policy.",
    )

    surveyor_agent = Agent(
        id="satisfaction_surveyor",
        name="SatisfactionSurveyor",
        description="Conducts brief surveys to gather feedback on customer satisfaction following service interactions.",
        llm_config=llm_config,
        system_prompt="You are a Customer Service Manager agent tasked with handling incoming customer interactions and orchestrating the resolution process efficiently.",
    )

    customer_service_manager = Agent(
        id="customer_service_manager",
        name="CustomerServiceManager",
        description="Acts as the primary contact point for customer inquiries, analyzes the request, routes tasks to specialized agents (Refund Specialist, Satisfaction Surveyor), and ensures resolution.",
        llm_config=llm_config,
        system_prompt="You are a Customer Service Manager agent tasked with handling incoming customer interactions and orchestrating the resolution process efficiently.",
    )

    return ManagerWorkers(
        id="managerworkers",
        name="managerworkers",
        group_manager=customer_service_manager,
        workers=[refund_specialist_agent, surveyor_agent],
    )


@pytest.fixture
def example_serialized_managerworkers() -> str:
    return read_agentspec_config_file("example_serialized_managerworkers.yaml")


def test_can_serialize_and_deserialize_managerworkers(
    example_serialized_managerworkers: str, example_managerworkers: ManagerWorkers
):
    group = example_managerworkers
    assert group.min_agentspec_version == AgentSpecVersionEnum.v25_4_2

    serialized_managerworkers = AgentSpecSerializer().to_yaml(group)
    assert_serialized_representations_are_equal(
        serialized_managerworkers, example_serialized_managerworkers
    )

    deserialized_managerworkers = AgentSpecDeserializer().from_yaml(serialized_managerworkers)
    assert deserialized_managerworkers.min_agentspec_version == AgentSpecVersionEnum.v25_4_2
    assert isinstance(deserialized_managerworkers, ManagerWorkers)

    # We override the min version of the component to make it equal to the one before serialization
    # This is because the version of the deserialized one is aligned to the agentspec_version of the yaml loaded.
    deserialized_managerworkers.group_manager.min_agentspec_version = AgentSpecVersionEnum.v25_4_1
    deserialized_managerworkers.group_manager.llm_config.min_agentspec_version = (
        AgentSpecVersionEnum.v25_4_1
    )
    for worker in deserialized_managerworkers.workers:
        worker.min_agentspec_version = AgentSpecVersionEnum.v25_4_1

    assert deserialized_managerworkers == group


def test_serializing_managerworkers_with_unsupported_version_raises_error(
    example_managerworkers: ManagerWorkers,
):
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_yaml(
            example_managerworkers, agentspec_version=AgentSpecVersionEnum.v25_4_1
        )


def test_deserializing_managerworkers_with_unsupported_version_raises_error(
    example_serialized_managerworkers: str,
):
    serialized_managerworkers = example_serialized_managerworkers
    assert "agentspec_version: 25.4.2" in example_serialized_managerworkers
    serialized_managerworkers = serialized_managerworkers.replace(
        "agentspec_version: 25.4.2", "agentspec_version: 25.4.1"
    )

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecDeserializer().from_yaml(serialized_managerworkers)
