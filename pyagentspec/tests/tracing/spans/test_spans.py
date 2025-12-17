# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.llms import LlmConfig
from pyagentspec.managerworkers import ManagerWorkers
from pyagentspec.swarm import Swarm
from pyagentspec.tools import Tool
from pyagentspec.tracing.events import Event
from pyagentspec.tracing.spans import (
    AgentExecutionSpan,
    FlowExecutionSpan,
    LlmGenerationSpan,
    ManagerWorkersExecutionSpan,
    NodeExecutionSpan,
    SwarmExecutionSpan,
    ToolExecutionSpan,
)


@pytest.fixture
def dummy_event() -> Event:
    return Event(id="dummy_event_id", name="dummy_event")


def test_agent_execution_span_creation(dummy_agent: Agent, dummy_event: Event):
    span = AgentExecutionSpan(agent=dummy_agent, name="custom_agent_span")
    assert span.name == "custom_agent_span"
    assert span.agent is dummy_agent
    span.add_event(dummy_event)
    assert len(span.events) == 1
    assert span.events[0] is dummy_event
    # Masking behavior (no sensitive fields in spans)
    masked = span.model_dump(mask_sensitive_information=True)
    unmasked = span.model_dump(mask_sensitive_information=False)
    assert masked == unmasked


def test_flow_execution_span_creation(dummy_flow: Flow, dummy_event: Event):
    span = FlowExecutionSpan(flow=dummy_flow, name="custom_flow_span")
    assert span.name == "custom_flow_span"
    assert span.flow is dummy_flow
    span.add_event(dummy_event)
    assert len(span.events) == 1
    assert span.events[0] is dummy_event
    # Masking behavior (no sensitive fields in spans)
    masked = span.model_dump(mask_sensitive_information=True)
    unmasked = span.model_dump(mask_sensitive_information=False)
    assert masked == unmasked


def test_llm_generation_span_creation(dummy_llm_config: LlmConfig, dummy_event: Event):
    span = LlmGenerationSpan(llm_config=dummy_llm_config, name="custom_llm_span")
    assert span.name == "custom_llm_span"
    assert span.llm_config is dummy_llm_config
    span.add_event(dummy_event)
    assert len(span.events) == 1
    assert span.events[0] is dummy_event
    # Masking behavior (no sensitive fields in spans)
    masked = span.model_dump(mask_sensitive_information=True)
    unmasked = span.model_dump(mask_sensitive_information=False)
    assert masked == unmasked


def test_managerworkers_execution_span_creation(
    dummy_managerworkers: ManagerWorkers, dummy_event: Event
):
    span = ManagerWorkersExecutionSpan(managerworkers=dummy_managerworkers, name="custom_mw_span")
    assert span.name == "custom_mw_span"
    assert span.managerworkers is dummy_managerworkers
    span.add_event(dummy_event)
    assert len(span.events) == 1
    assert span.events[0] is dummy_event
    # Masking behavior (no sensitive fields in spans)
    masked = span.model_dump(mask_sensitive_information=True)
    unmasked = span.model_dump(mask_sensitive_information=False)
    assert masked == unmasked


def test_node_execution_span_creation(dummy_node: Node, dummy_event: Event):
    span = NodeExecutionSpan(node=dummy_node, name="custom_node_span")
    assert span.name == "custom_node_span"
    assert span.node is dummy_node
    span.add_event(dummy_event)
    assert len(span.events) == 1
    assert span.events[0] is dummy_event
    # Masking behavior (no sensitive fields in spans)
    masked = span.model_dump(mask_sensitive_information=True)
    unmasked = span.model_dump(mask_sensitive_information=False)
    assert masked == unmasked


def test_swarm_execution_span_creation(dummy_swarm: Swarm, dummy_event: Event):
    span = SwarmExecutionSpan(swarm=dummy_swarm, name="custom_swarm_span")
    assert span.name == "custom_swarm_span"
    assert span.swarm is dummy_swarm
    span.add_event(dummy_event)
    assert len(span.events) == 1
    assert span.events[0] is dummy_event
    # Masking behavior (no sensitive fields in spans)
    masked = span.model_dump(mask_sensitive_information=True)
    unmasked = span.model_dump(mask_sensitive_information=False)
    assert masked == unmasked


def test_tool_execution_span_creation(dummy_tool: Tool, dummy_event: Event):
    span = ToolExecutionSpan(tool=dummy_tool, name="custom_tool_span")
    assert span.name == "custom_tool_span"
    assert span.tool is dummy_tool
    span.add_event(dummy_event)
    assert len(span.events) == 1
    assert span.events[0] is dummy_event
    # Masking behavior (no sensitive fields in spans)
    masked = span.model_dump(mask_sensitive_information=True)
    unmasked = span.model_dump(mask_sensitive_information=False)
    assert masked == unmasked
