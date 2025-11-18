# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


# mypy: ignore-errors

import pytest
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.ollama import OllamaChatCompletionClient

from autogen_agentspec_adapter import AgentSpecExporter

from .conftest import inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow
from .model_builders import (
    build_basic_conditional_branch_flow,
    build_basic_conditional_branch_without_loop_flow_mix_string_and_lambda_conditions,
    build_conditional_loop_flow_lambda_condition,
    build_multiple_conditional_branches_flow,
    build_parallel_agents_flow,
    build_sequential_agents_flow,
    build_simple_conditional_branch_flow,
    build_simple_conditional_loop_flow,
    build_simple_conditional_loop_two_end_nodes_flow,
)


@pytest.fixture(scope="session")
def model_client():
    # Create an llm model client
    client = OllamaChatCompletionClient(
        model="llama3.2:latest",
        host="localhost:11434",
    )
    return client


@pytest.fixture(scope="session")
def exporter() -> AgentSpecExporter:
    return AgentSpecExporter()


@pytest.fixture(scope="session")
def termination_condition():
    return MaxMessageTermination(10)


@pytest.mark.parametrize(
    "use_lambda", [True, False], ids=["lambda-conditions", "string-conditions"]
)
def test_basic_conditional_branch_without_loop_flow_can_be_converted_to_agentspec(
    model_client, exporter, termination_condition, use_lambda
):
    autogen_flow, branches = build_basic_conditional_branch_flow(
        model_client, use_lambda, termination_condition
    )
    agentspec_flow = exporter.to_component(autogen_flow)
    inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
        autogen_flow, agentspec_flow, list_branch_names=branches
    )


def test_basic_conditional_branch_without_loop_flow_mix_string_and_lambda_conditions_can_be_converted_to_agentspec(
    model_client, exporter, termination_condition
):
    autogen_flow = (
        build_basic_conditional_branch_without_loop_flow_mix_string_and_lambda_conditions(
            model_client, termination_condition
        )
    )
    agentspec_flow = exporter.to_component(autogen_flow)
    inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
        autogen_flow, agentspec_flow, list_branch_names=["generator"]
    )


def test_conditional_loop_flow_lambda_condition_can_be_converted_to_agentspec(
    model_client, exporter, termination_condition
):
    autogen_flow = build_conditional_loop_flow_lambda_condition(model_client, termination_condition)
    agentspec_flow = exporter.to_component(autogen_flow)
    inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
        autogen_flow, agentspec_flow, list_branch_names=["reviewer"]
    )


def test_parallel_agents_flow_can_be_converted_to_agentspec(model_client, exporter):
    autogen_flow = build_parallel_agents_flow(model_client)
    agentspec_flow = exporter.to_component(autogen_flow)
    inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
        autogen_flow, agentspec_flow
    )


def test_sequential_agents_flow_can_be_converted_to_agentspec(model_client, exporter):
    autogen_flow = build_sequential_agents_flow(model_client)
    agentspec_flow = exporter.to_component(autogen_flow)
    inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
        autogen_flow, agentspec_flow
    )


@pytest.mark.parametrize(
    "use_lambda", [True, False], ids=["lambda-conditions", "string-conditions"]
)
def test_simple_conditional_branch_without_loop_flow_can_be_converted_to_agentspec(
    model_client, exporter, termination_condition, use_lambda
):
    autogen_flow, branches = build_simple_conditional_branch_flow(
        model_client, use_lambda, termination_condition
    )
    agentspec_flow = exporter.to_component(autogen_flow)
    inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
        autogen_flow, agentspec_flow, list_branch_names=branches
    )


@pytest.mark.parametrize(
    "use_lambda", [True, False], ids=["lambda-conditions", "string-conditions"]
)
def test_simple_conditional_loop_2_end_nodes_flow_can_be_converted_to_agentspec(
    model_client, exporter, termination_condition, use_lambda
):
    autogen_flow, branches = build_simple_conditional_loop_two_end_nodes_flow(
        model_client, use_lambda, termination_condition
    )
    agentspec_flow = exporter.to_component(autogen_flow)
    inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
        autogen_flow, agentspec_flow, list_branch_names=branches
    )


@pytest.mark.parametrize(
    "use_lambda", [True, False], ids=["lambda-conditions", "string-conditions"]
)
def test_simple_conditional_loop_flow_can_be_converted_to_agentspec(
    model_client, exporter, termination_condition, use_lambda
):
    autogen_flow, branches = build_simple_conditional_loop_flow(
        model_client, use_lambda, termination_condition
    )
    agentspec_flow = exporter.to_component(autogen_flow)
    inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
        autogen_flow, agentspec_flow, list_branch_names=branches
    )


@pytest.mark.parametrize(
    "use_lambda", [True, False], ids=["lambda-conditions", "string-conditions"]
)
def test_multiple_conditional_branches_without_loop_can_be_converted_to_agentspec(
    model_client, exporter, termination_condition, use_lambda
):
    autogen_flow, branches = build_multiple_conditional_branches_flow(
        model_client=model_client,
        use_lambda=use_lambda,
        termination_condition=termination_condition,
    )
    agentspec_flow = exporter.to_component(autogen_flow)
    inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
        autogen_flow, agentspec_flow, list_branch_names=branches
    )
