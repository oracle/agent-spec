# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.agent import Agent
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.llms import LlmConfig
from pyagentspec.managerworkers import ManagerWorkers
from pyagentspec.swarm import Swarm
from pyagentspec.tools import Tool
from pyagentspec.tracing._basemodel import _PII_MASK
from pyagentspec.tracing.events import (
    AgentExecutionEnd,
    AgentExecutionStart,
    ExceptionRaised,
    FlowExecutionEnd,
    FlowExecutionStart,
    HumanInTheLoopRequest,
    HumanInTheLoopResponse,
    LlmGenerationChunkReceived,
    LlmGenerationRequest,
    LlmGenerationResponse,
    ManagerWorkersExecutionEnd,
    ManagerWorkersExecutionStart,
    NodeExecutionEnd,
    NodeExecutionStart,
    SwarmExecutionEnd,
    SwarmExecutionStart,
    ToolConfirmationRequest,
    ToolConfirmationResponse,
    ToolExecutionRequest,
    ToolExecutionResponse,
)
from pyagentspec.tracing.messages.message import Message


# Exception events
def test_exception_event_creation():
    ev = ExceptionRaised(
        exception_type="ValueError", exception_message="bad", exception_stacktrace="trace"
    )
    assert ev.exception_type == "ValueError"
    assert str(ev.exception_message) == "bad"
    assert isinstance(ev.exception_stacktrace, str)
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["exception_message"] == _PII_MASK
    assert masked["exception_stacktrace"] == _PII_MASK
    assert unmasked["exception_message"] == "bad"
    assert unmasked["exception_stacktrace"] == "trace"
    assert masked["type"] == "ExceptionRaised"


def test_agent_execution_start_creation(dummy_agent: Agent):
    ev = AgentExecutionStart(agent=dummy_agent, inputs={"x": 1}, name="custom")
    assert ev.name == "custom"
    assert ev.agent is dummy_agent
    assert ev.inputs == {"x": 1}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["inputs"] == _PII_MASK
    assert unmasked["inputs"] == {"x": 1}
    assert masked["type"] == "AgentExecutionStart"


def test_agent_execution_end_creation(dummy_agent: Agent):
    ev = AgentExecutionEnd(agent=dummy_agent, outputs={"y": 2})
    assert ev.agent is dummy_agent
    assert ev.outputs == {"y": 2}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["outputs"] == _PII_MASK
    assert unmasked["outputs"] == {"y": 2}
    assert masked["type"] == "AgentExecutionEnd"


# Flow events
def test_flow_execution_start_creation(dummy_flow: Flow):
    ev = FlowExecutionStart(flow=dummy_flow, inputs={"a": 1}, name="flow_start_custom")
    assert ev.name == "flow_start_custom"
    assert ev.flow is dummy_flow
    assert ev.inputs == {"a": 1}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["inputs"] == _PII_MASK
    assert unmasked["inputs"] == {"a": 1}
    assert masked["type"] == "FlowExecutionStart"


def test_flow_execution_end_creation(dummy_flow: Flow):
    ev = FlowExecutionEnd(flow=dummy_flow, outputs={"b": 2}, branch_selected="next")
    assert ev.flow is dummy_flow
    assert ev.outputs == {"b": 2}
    assert ev.branch_selected == "next"
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["outputs"] == _PII_MASK
    assert unmasked["outputs"] == {"b": 2}
    assert masked["branch_selected"] == "next"
    assert unmasked["branch_selected"] == "next"
    assert masked["type"] == "FlowExecutionEnd"


# HITL events
def test_humanintheloop_request_creation():
    ev = HumanInTheLoopRequest(request_id="r1", content={"question": "ok?"})
    assert ev.request_id == "r1"
    assert ev.content == {"question": "ok?"}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["content"] == _PII_MASK
    assert unmasked["content"] == {"question": "ok?"}
    assert masked["type"] == "HumanInTheLoopRequest"


def test_humanintheloop_response_creation():
    ev = HumanInTheLoopResponse(request_id="r1", content={"answer": "yes"})
    assert ev.request_id == "r1"
    assert ev.content == {"answer": "yes"}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["content"] == _PII_MASK
    assert unmasked["content"] == {"answer": "yes"}
    assert masked["type"] == "HumanInTheLoopResponse"


# LLM generation events
def test_llm_generation_request_creation(dummy_tool: Tool, dummy_llm_config: LlmConfig):
    msgs = [Message(content="hello", role="user")]
    ev = LlmGenerationRequest(
        llm_config=dummy_llm_config,
        prompt=msgs,
        tools=[dummy_tool],
        request_id="req-1",
    )
    assert ev.llm_config is dummy_llm_config
    assert ev.prompt == msgs
    assert ev.tools == [dummy_tool]
    assert ev.request_id == "req-1"
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["prompt"] == _PII_MASK
    assert unmasked["prompt"] == [m.model_dump() for m in msgs]
    assert unmasked["tools"][0]["name"] == dummy_tool.name
    assert masked["type"] == "LlmGenerationRequest"


def test_llm_generation_response_creation(dummy_llm_config: LlmConfig):
    from pyagentspec.tracing.events.llmgeneration import ToolCall

    ev = LlmGenerationResponse(
        llm_config=dummy_llm_config,
        content="hi",
        request_id="req-1",
        completion_id="c-1",
        tool_calls=[ToolCall(call_id="a", tool_name="b", arguments="{'c': 1}")],
        input_tokens=10,
        output_tokens=2,
    )
    assert str(ev.content) == "hi"
    assert ev.request_id == "req-1"
    assert ev.completion_id == "c-1"
    assert ev.input_tokens == 10
    assert ev.output_tokens == 2
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["content"] == _PII_MASK
    assert masked["tool_calls"] == _PII_MASK
    assert unmasked["content"] == "hi"
    assert isinstance(unmasked["tool_calls"], list) and len(unmasked["tool_calls"]) == 1
    assert unmasked["request_id"] == "req-1"
    assert unmasked["completion_id"] == "c-1"
    assert unmasked["input_tokens"] == 10
    assert unmasked["output_tokens"] == 2
    assert masked["type"] == "LlmGenerationResponse"


def test_llm_generation_chunk_received_creation(dummy_llm_config: LlmConfig):
    from pyagentspec.tracing.events.llmgeneration import ToolCall

    ev = LlmGenerationChunkReceived(
        llm_config=dummy_llm_config,
        content="piece",
        tool_calls=[ToolCall(call_id="a", tool_name="b", arguments="{'c': 1}")],
        request_id="r",
        completion_id="c",
        output_tokens=1,
    )
    assert ev.llm_config is dummy_llm_config
    assert str(ev.content) == "piece"
    assert ev.request_id == "r"
    assert ev.output_tokens == 1
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["content"] == _PII_MASK
    assert masked["tool_calls"] == _PII_MASK
    assert unmasked["content"] == "piece"
    assert isinstance(unmasked["tool_calls"], list) and len(unmasked["tool_calls"]) == 1
    assert masked["type"] == "LlmGenerationChunkReceived"


# Manager-workers events
def test_managerworkers_execution_start_creation(dummy_managerworkers: ManagerWorkers):
    ev = ManagerWorkersExecutionStart(managerworkers=dummy_managerworkers, inputs={"foo": "bar"})
    assert ev.managerworkers is dummy_managerworkers
    assert ev.inputs == {"foo": "bar"}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["inputs"] == _PII_MASK
    assert unmasked["inputs"] == {"foo": "bar"}
    assert masked["type"] == "ManagerWorkersExecutionStart"


def test_managerworkers_execution_end_creation(dummy_managerworkers: ManagerWorkers):
    ev = ManagerWorkersExecutionEnd(managerworkers=dummy_managerworkers, outputs={"foo": "baz"})
    assert ev.managerworkers is dummy_managerworkers
    assert ev.outputs == {"foo": "baz"}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["outputs"] == _PII_MASK
    assert unmasked["outputs"] == {"foo": "baz"}
    assert masked["type"] == "ManagerWorkersExecutionEnd"


# Node events
def test_node_execution_start_creation(dummy_node: Node):
    ev = NodeExecutionStart(node=dummy_node, inputs={"v": 3})
    assert ev.node is dummy_node
    assert ev.inputs == {"v": 3}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["inputs"] == _PII_MASK
    assert unmasked["inputs"] == {"v": 3}
    assert masked["type"] == "NodeExecutionStart"


def test_node_execution_end_creation(dummy_node: Node):
    ev = NodeExecutionEnd(node=dummy_node, outputs={"v": 4}, branch_selected="next")
    assert ev.node is dummy_node
    assert ev.outputs == {"v": 4}
    assert ev.branch_selected == "next"
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["outputs"] == _PII_MASK
    assert unmasked["outputs"] == {"v": 4}
    assert masked["branch_selected"] == "next"
    assert unmasked["branch_selected"] == "next"
    assert masked["type"] == "NodeExecutionEnd"


# Swarm events
def test_swarm_execution_start_creation(dummy_swarm: Swarm):
    ev = SwarmExecutionStart(swarm=dummy_swarm, inputs={"q": "x"})
    assert ev.swarm is dummy_swarm
    assert ev.inputs == {"q": "x"}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["inputs"] == _PII_MASK
    assert unmasked["inputs"] == {"q": "x"}
    assert masked["type"] == "SwarmExecutionStart"


def test_swarm_execution_end_creation(dummy_swarm: Swarm):
    ev = SwarmExecutionEnd(swarm=dummy_swarm, outputs={"r": "y"})
    assert ev.swarm is dummy_swarm
    assert ev.outputs == {"r": "y"}
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["outputs"] == _PII_MASK
    assert unmasked["outputs"] == {"r": "y"}
    assert masked["type"] == "SwarmExecutionEnd"


# Tool events
def test_tool_execution_request_creation(dummy_tool: Tool):
    ev = ToolExecutionRequest(tool=dummy_tool, inputs={"x": 1}, request_id="t1")
    assert ev.tool is dummy_tool
    assert ev.inputs == {"x": 1}
    assert ev.request_id == "t1"
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["inputs"] == _PII_MASK
    assert unmasked["inputs"] == {"x": 1}
    assert unmasked["request_id"] == "t1"
    assert masked["type"] == "ToolExecutionRequest"


def test_tool_execution_response_creation(dummy_tool: Tool):
    ev = ToolExecutionResponse(tool=dummy_tool, outputs={"y": 2}, request_id="t1")
    assert ev.tool is dummy_tool
    assert ev.outputs == {"y": 2}
    assert ev.request_id == "t1"
    # Masking behavior
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked["outputs"] == _PII_MASK
    assert unmasked["outputs"] == {"y": 2}
    assert unmasked["request_id"] == "t1"
    assert masked["type"] == "ToolExecutionResponse"


def test_tool_confirmation_request_creation(dummy_tool: Tool):
    ev = ToolConfirmationRequest(tool=dummy_tool, request_id="c1", tool_execution_request_id="t1")
    assert ev.tool is dummy_tool
    assert ev.request_id == "c1"
    assert ev.tool_execution_request_id == "t1"
    # Masking behavior (no sensitive fields)
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked == unmasked
    assert masked["type"] == "ToolConfirmationRequest"


def test_tool_confirmation_response_creation(dummy_tool: Tool):
    ev = ToolConfirmationResponse(
        tool=dummy_tool, execution_confirmed=True, request_id="c1", tool_execution_request_id="t1"
    )
    assert ev.tool is dummy_tool
    assert ev.execution_confirmed is True
    assert ev.request_id == "c1"
    # Masking behavior (no sensitive fields)
    masked = ev.model_dump(mask_sensitive_information=True)
    unmasked = ev.model_dump(mask_sensitive_information=False)
    assert masked == unmasked
