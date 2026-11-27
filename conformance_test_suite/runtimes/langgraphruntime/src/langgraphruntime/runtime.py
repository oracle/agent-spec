# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


"""This modules define the main interfaces of LangGraph AgentSpec Runtime."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional, Union, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import add_messages
from langgraph.graph.message import Messages
from langgraph.types import Command, Interrupt

from pyagentspec.adapters.langgraph import AgentSpecLoader
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.serialization import AgentSpecDeserializer

logger = logging.getLogger(__name__)


ToolRegistryType = Dict[str, Callable[..., Any]]


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


class AgentSpecExecutionStatus:
    """The status returned when running a RunnableComponent."""


@dataclass
class AgentSpecFinishedExecutionStatus(AgentSpecExecutionStatus):
    """The status returned when a RunnableComponent conclude the interaction."""

    outputs: Dict[str, Any]
    agent_messages: List[str]


@dataclass
class ToolRequest:
    name: str
    args: Dict[str, Any]
    tool_request_id: str


@dataclass
class AgentSpecToolRequestExecutionStatus(AgentSpecExecutionStatus):
    """The status returned when a RunnableComponent waits for a tool response."""

    tool_requests: List[ToolRequest]


@dataclass
class AgentSpecToolExecutionConfirmationStatus(AgentSpecExecutionStatus):
    tool_requests: List[ToolRequest]


@dataclass
class AgentSpecUserMessageRequestExecutionStatus(AgentSpecExecutionStatus):
    """The status returned when a RunnableComponent pauses to receive a message from the user."""

    agent_messages: List[str]


class LanggraphAgentSpecRunnableComponent:
    """
    RunnableComponent handle the execution of Flows or Agents.

    RunnableComponent are the interface between a system or end user and the execution of a Flow or
    Agent. RunnableComponents are stateful and will live through multiple interactions with the
    system or end-user such as exchanging messages or requesting the execution of client-side
    tools.
    """

    def __init__(
        self,
        component: Component,
        tool_registry: Optional[ToolRegistryType],
        config: Optional[RunnableConfig] = None,
    ) -> None:
        """Initialize a LangGraph-based RunnableComponent."""
        self.inputs: Union[Dict[str, Any], Command[Any]] = {}
        self.messages: Messages = []
        self.tool_registry = tool_registry or {}
        self.component = component
        self.state_graph = AgentSpecLoader(
            self.tool_registry, checkpointer=MemorySaver()
        ).load_component(component)
        self.config = config or RunnableConfig(
            {"configurable": {"thread_id": "1"}, "recursion_limit": 800}
        )
        if not isinstance(component, (AgentSpecAgent, AgentSpecFlow)):
            raise NotImplementedError(
                f"Component of type {type(component)} is not yet supported in LangGraph runtime."
            )

    def start(self, inputs: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the inputs of the RunnableComponent."""
        self.inputs = inputs or {}

    def run(self) -> AgentSpecExecutionStatus:
        """
        Run the RunnableComponent.

        Calling this method executes the AgentSpec Flow or Agent, then return an execution status.
        """
        result = self.state_graph.invoke(
            (
                self.inputs
                if isinstance(self.inputs, Command)
                else {"inputs": self.inputs, "messages": self.messages}
            ),
            config=self.config,
        )
        agent_messages: List[str] = [
            message.content for message in result["messages"] if message.type == "ai"
        ]
        self.messages = result["messages"]
        # Reset inputs if we sent a resume command before
        if isinstance(self.inputs, Command):
            self.inputs = {}

        if "__interrupt__" in result:
            tool_requests: List[ToolRequest] = []
            interrupts = cast(List[Interrupt], result["__interrupt__"])
            for interrupt in interrupts:
                tool_request = interrupt.value
                # Normalize inputs for the test expectations
                normalized_args = _normalize_tool_inputs(tool_request)
                tool_requests.append(
                    ToolRequest(
                        name=tool_request["name"],
                        args=normalized_args,
                        # This helps us map the tool results to the corresponding interrupt
                        tool_request_id=interrupt.id,
                    )
                )
            return AgentSpecToolRequestExecutionStatus(
                tool_requests=tool_requests,
            )

        if isinstance(self.component, AgentSpecAgent):
            return AgentSpecUserMessageRequestExecutionStatus(
                agent_messages=agent_messages,
            )
        else:
            return AgentSpecFinishedExecutionStatus(
                outputs=result["outputs"],
                agent_messages=agent_messages,
            )

    def append_user_message(self, user_message: str) -> None:
        """
        Append a user message.

        This should be called after the RunnableComponent ran and returned a
        UserMessageRequestExecutionStatus.
        """
        self.messages = add_messages(self.messages, {"role": "user", "content": user_message})

    def append_tool_results(self, tool_result: Union[ToolResult, list[ToolResult]]) -> None:
        """
        Append a tool result.

        This should be called after the RunnableComponent ran and returned a
        ToolRequestExecutionStatus.
        """
        if isinstance(tool_result, list):
            # map interrupt id -> content
            resume_map = {tool_res.tool_request_id: tool_res.content for tool_res in tool_result}
            self.inputs = Command(resume=resume_map)
        else:
            self.inputs = Command(resume={tool_result.tool_request_id: tool_result.content})

    def confirm_or_reject_tool_confirmation(
        self, tool_request: ToolRequest, decision: Literal["accept", "reject"]
    ) -> None:
        raise NotImplementedError("Tool Confirmation is not supported in the LangGraph adapter")


class LanggraphAgentSpecLoader:
    """
    Load an AgentSpec Configuration.

    The loader produces a runnable components for Flows or Agents relying on LangGraph as the
    backend system for the execution.
    """

    @staticmethod
    def load(
        agentspec_config: str,
        tool_registry: Optional[ToolRegistryType] = None,
        config: Optional[RunnableConfig] = None,
        components_registry: Optional[Dict[str, Any]] = None,
    ) -> LanggraphAgentSpecRunnableComponent:
        """Load an AgentSpec Configuration."""
        agentspec_component = AgentSpecDeserializer().from_yaml(
            agentspec_config, components_registry=components_registry
        )
        return LanggraphAgentSpecRunnableComponent(agentspec_component, tool_registry, config)


def _normalize_tool_inputs(raw: Any) -> Dict[str, Any]:
    """
    Normalize various tool input shapes to a flat dict of arguments.
    Supported shapes:
      - {"inputs": {"kwargs": {...}, "args": [...]}}
      - {"inputs": {"a": 1, "b": 2}}
      - {"kwargs": {...}, "args": [...]}
      - {"arguments": "<json string>"}
      - {"a": 1, "b": 2}
    """

    def _from_inputs(v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            return {}
        if "kwargs" in v or "args" in v:
            kwargs = v.get("kwargs") or {}
            if isinstance(kwargs, dict) and kwargs:
                return kwargs
            args = v.get("args") or []
            # Fall back to exposing args if kwargs is empty
            return {"args": args} if args else {}
        return v

    if not isinstance(raw, dict):
        return {}

    # Case 1: wrapper with "inputs"
    if "inputs" in raw:
        return _from_inputs(raw["inputs"])

    # Case 2: OpenAI-style "arguments" as JSON string
    if "arguments" in raw and isinstance(raw["arguments"], str):
        try:
            parsed = json.loads(raw["arguments"])
            if isinstance(parsed, dict):
                return parsed
        except Exception:  # nosec
            pass

    # Case 3: direct kwargs/args dict
    if "kwargs" in raw or "args" in raw:
        return _from_inputs(raw)

    # Case 4: already a flat dict of params
    return raw
