# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
The purpose of these tests is to show that the filesystem is not accessed (read/write)
unexpectedly by the main pyagentspec functionalities.
"""
import os

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import (
    ApiNode,
    EndNode,
    LlmNode,
    StartNode,
)
from pyagentspec.llms import LlmConfig, LlmGenerationConfig, OciGenAiConfig, VllmConfig
from pyagentspec.llms.ociclientconfig import OciClientConfigWithSecurityToken
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.tools import ClientTool, RemoteTool, ServerTool


@pytest.fixture()
def default_serializer() -> AgentSpecSerializer:
    return AgentSpecSerializer()


@pytest.fixture()
def default_deserializer() -> AgentSpecDeserializer:
    return AgentSpecDeserializer()


@pytest.fixture()
def default_oci_genai_llm_config() -> LlmConfig:
    return OciGenAiConfig(
        id="oci genai llm",
        name="oci genai llm",
        model_id="model.id",
        compartment_id="compartment.id",
        client_config=OciClientConfigWithSecurityToken(
            name="oci client",
            service_endpoint="service.endpoint",
            auth_profile="user_profile",
            auth_file_location="auth/file/location.txt",
        ),
        default_generation_parameters=LlmGenerationConfig(temperature=0.6),
    )


@pytest.fixture()
def default_agent(default_llm_config: LlmConfig) -> Agent:
    return Agent(
        id="abc123",
        name="default_agent",
        llm_config=default_llm_config,
        system_prompt="You are a great agent. You are talking to {{username}}. Be kind.",
        tools=[
            ClientTool(
                id="tool1",
                name="do_nothing",
                description="do nothing",
                inputs=[StringProperty(title="x")],
                outputs=[StringProperty(title="x")],
            ),
            ServerTool(
                id="tool2",
                name="do_nothing 2",
                description="do nothing again",
                inputs=[StringProperty(title="x")],
                outputs=[StringProperty(title="x")],
            ),
            RemoteTool(
                id="tool3",
                name="do_nothing 3",
                description="do nothing another time",
                inputs=[StringProperty(title="x")],
                outputs=[StringProperty(title="x")],
                url="my.awesome.endpoint",
                http_method="GET",
                api_spec_uri=None,
                data={"x": "{{x}}", "b": "c"},
                query_params={"d": 1, "e": "c"},
            ),
        ],
        inputs=[StringProperty(title="username")],
    )


@pytest.fixture()
def default_flow(default_llm_config: LlmConfig) -> Flow:
    start_node = StartNode(
        name="start",
        inputs=[StringProperty(title="username"), StringProperty(title="user_input")],
    )
    llm_node = LlmNode(
        name="prompt",
        llm_config=default_llm_config,
        prompt_template="{{username}} is asking: {{user_input}}",
        outputs=[StringProperty(title="llm_output")],
    )
    api_node = ApiNode(
        id="api node",
        name="api call that does nothing",
        inputs=[StringProperty(title="input")],
        outputs=[StringProperty(title="output")],
        url="my.awesome.endpoint",
        http_method="POST",
        data={"input": "{{input}}"},
    )
    end_node = EndNode(name="end", outputs=[StringProperty(title="llm_output")])
    control_flow_edges = [
        ControlFlowEdge(
            name="cfe1",
            from_node=start_node,
            to_node=llm_node,
        ),
        ControlFlowEdge(
            name="cfe2",
            from_node=llm_node,
            to_node=api_node,
        ),
        ControlFlowEdge(
            name="cfe3",
            from_node=api_node,
            to_node=end_node,
        ),
    ]
    data_flow_edges = [
        DataFlowEdge(
            name="dfe1",
            source_node=start_node,
            source_output="username",
            destination_node=llm_node,
            destination_input="username",
        ),
        DataFlowEdge(
            name="dfe2",
            source_node=start_node,
            source_output="user_input",
            destination_node=llm_node,
            destination_input="user_input",
        ),
        DataFlowEdge(
            name="dfe3",
            source_node=llm_node,
            source_output="llm_output",
            destination_node=api_node,
            destination_input="input",
        ),
        DataFlowEdge(
            name="dfe4",
            source_node=api_node,
            source_output="output",
            destination_node=end_node,
            destination_input="llm_output",
        ),
    ]
    return Flow(
        start_node=start_node,
        nodes=[start_node, llm_node, api_node, end_node],
        control_flow_connections=control_flow_edges,
        data_flow_connections=data_flow_edges,
        name="default_flow",
        id="321cba",
    )


def test_serialize_and_deserialize_agent(
    default_agent: Agent,
    default_serializer: AgentSpecSerializer,
    default_deserializer: AgentSpecDeserializer,
    guard_all_filewrites,
    guard_all_network_access,
) -> None:
    serialized_agent = default_serializer.to_yaml(default_agent)
    _ = default_deserializer.from_yaml(serialized_agent)


def test_serialize_and_deserialize_flow(
    default_flow: Flow,
    default_serializer: AgentSpecSerializer,
    default_deserializer: AgentSpecDeserializer,
    guard_all_filewrites,
    guard_all_network_access,
) -> None:
    serialized_flow = default_serializer.to_yaml(default_flow)
    _ = default_deserializer.from_yaml(serialized_flow)
