# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


"""This module defines the main interfaces of AutoGen Agent Spec Runtime."""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional, Union

from autogen_agentchat.agents import AssistantAgent as AutogenAssistantAgent
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_core.tools import FunctionTool as AutogenFunctionTool

from pyagentspec.adapters.autogen import AgentSpecLoader
from pyagentspec.serialization import AgentSpecDeserializer

logger = logging.getLogger(__name__)


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


# Convenient types definition
ToolRegistryType = Dict[str, Callable[..., Any]]
AutogenToolRegistryType = Dict[str, Union[AutogenFunctionTool, Callable[..., Any]]]


class AutogenAgentSpecRunnableComponent:
    """
    RunnableComponent handle the execution of Flows or Agents.

    RunnableComponent are the interface between a system or end user and the execution of a Flow or
    Agent. RunnableComponents are stateful and will live through multiple interactions with the
    system or end-user such as exchanging messages or requesting the execution of client-side
    tools.
    """

    def __init__(self, component: AutogenAssistantAgent):
        """Initialize a AutoGen-based RunnableComponent."""
        self.component = component

    def start(
        self, inputs: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None
    ) -> None:
        """Initialize the inputs of the RunnableComponent."""
        if inputs is None:
            self.inputs = []
        elif isinstance(inputs, BaseChatMessage):
            self.inputs = [inputs]
        elif isinstance(inputs, str):
            self.inputs = [TextMessage(source="User", content=inputs)]
        elif isinstance(inputs, Sequence) and not isinstance(inputs, (str, bytes)):
            if all(isinstance(x, BaseChatMessage) for x in inputs):
                self.inputs = list(inputs)
            else:
                raise TypeError("All items in the sequence must be BaseChatMessage")
        else:
            raise TypeError("Unsupported input type for start().")

    # Public sync method expected by the CTS tests
    def run(self) -> AgentSpecExecutionStatus:
        """
        Run the RunnableComponent synchronously.
        Wraps the internal async execution to match specs of other runtimes and CTS expectations.
        """
        return asyncio.run(self._run_async())

    # Internal async execution
    async def _run_async(self) -> AgentSpecExecutionStatus:
        """
        Run the RunnableComponent asynchronously.

        Calling this method executes the Agent Spec Flow or Agent, then return an execution status.
        """
        # AutoGen rejects an empty list for tasks; pass None instead.
        task = self.inputs if (hasattr(self, "inputs") and self.inputs) else None

        result = await self.component.run(task=task)
        agent_messages: List[str] = [
            message.content for message in result.messages if message.source != "user"  # type: ignore
        ]
        return AgentSpecUserMessageRequestExecutionStatus(
            agent_messages=agent_messages,
        )

    def append_user_message(self, user_message: str) -> None:
        """
        Append a user message.

        This should be called after the RunnableComponent ran and returned a
        UserMessageRequestExecutionStatus.
        """
        self.inputs.append(TextMessage(source="User", content=user_message))

    def confirm_or_reject_tool_confirmation(
        self, tool_request: ToolRequest, decision: Literal["accept", "reject"]
    ) -> None:
        raise NotImplementedError("Tool Confirmation is not supported in the Autogen adapter")


class AutogenAgentSpecLoader:
    """
    Load an Agent Spec Configuration.

    The loader produces a runnable components for Flows or Agents relying on AutoGen as the
    backend system for the execution.
    """

    @staticmethod
    def _validate_and_wrap_component(
        component: AutogenAssistantAgent,
    ) -> AutogenAgentSpecRunnableComponent:
        if not isinstance(component, AutogenAssistantAgent):
            raise ValueError(
                f"Unexpected component configuration received. "
                f"A runnable component was expected, "
                f"received {type(component)} instead."
            )
        return AutogenAgentSpecRunnableComponent(component)

    @staticmethod
    def load(
        agentspec_config: str,
        tool_registry: Optional[AutogenToolRegistryType] = None,
        components_registry: Optional[Dict[str, Any]] = None,
    ) -> AutogenAgentSpecRunnableComponent:
        """Load an Agent Spec Configuration."""
        agentspec_component = AgentSpecDeserializer().from_yaml(
            agentspec_config, components_registry=components_registry
        )
        autogen_component = AgentSpecLoader(tool_registry=tool_registry).load_component(
            agentspec_component
        )
        return AutogenAgentSpecLoader._validate_and_wrap_component(autogen_component)
