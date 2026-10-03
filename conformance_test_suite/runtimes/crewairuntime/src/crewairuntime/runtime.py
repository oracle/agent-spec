# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


"""This module defines the main interfaces of CrewAI Agent Spec Runtime."""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional, Union, cast

from crewai import Agent as CrewAIAgent
from crewai import Crew, CrewOutput, Task
from crewai.tools.base_tool import Tool as CrewAIServerTool

from pyagentspec.adapters.crewai import AgentSpecLoader

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
_CrewAIServerToolType = Union[CrewAIServerTool, Callable[..., Any]]


class CrewAIAgentSpecRunnableComponent:
    """
    RunnableComponent handle the execution of Flows or Agents.

    RunnableComponent are the interface between a system or end user and the execution of a Flow or
    Agent. RunnableComponents are stateful and will live through multiple interactions with the
    system or end-user such as exchanging messages or requesting the execution of client-side
    tools.
    """

    def __init__(self, component: Crew):
        """Initialize a CrewAI-based RunnableComponent."""
        self.component = component

    def start(self, inputs: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the inputs of the RunnableComponent.
        Accepts None or a dict.
        """
        self.inputs: Dict[str, Any] = inputs or {}
        # Ensure messages list is present for the conversation state we maintain
        if "messages" not in self.inputs or not isinstance(self.inputs["messages"], list):
            self.inputs["messages"] = []

    def run(self) -> AgentSpecExecutionStatus:
        """
        Run the RunnableComponent.

        Calling this method executes the Agent Spec Flow or Agent, then return an execution status.
        """
        if list(self.inputs) == ["messages"] and self.inputs["messages"] == []:
            result = cast(
                CrewOutput,
                self.component.kickoff(inputs={"messages": "Propose your help to the user"}),
            )
        else:
            result = cast(CrewOutput, self.component.kickoff(inputs=self.inputs))

        # Persist assistant response into our conversation state
        self.inputs["messages"].append({"role": "assistant", "content": result.raw})

        agent_messages: List[str] = [result.raw]
        return AgentSpecUserMessageRequestExecutionStatus(agent_messages=agent_messages)

    def append_user_message(self, user_message: str) -> None:
        """
        Append a user message.

        This should be called after the RunnableComponent ran and returned a
        UserMessageRequestExecutionStatus.
        """
        if "messages" not in self.inputs or not isinstance(self.inputs["messages"], list):
            self.inputs["messages"] = []
        self.inputs["messages"].append({"role": "user", "content": user_message})

    def confirm_or_reject_tool_confirmation(
        self, tool_request: ToolRequest, decision: Literal["accept", "reject"]
    ) -> None:
        raise NotImplementedError("Tool Confirmation is not supported in the CrewAI adapter")


class CrewAIAgentSpecLoader:
    """
    Load an Agent Spec Configuration.

    The loader produces a runnable components for Flows or Agents relying on CrewAI as the
    backend system for the execution.
    """

    @staticmethod
    def _create_crew_from_component(component: CrewAIAgent) -> Crew:
        if not isinstance(component, CrewAIAgent):
            raise ValueError(
                f"Unexpected component configuration received. "
                f"A runnable component was expected, "
                f"received {type(component)} instead."
            )
        task = Task(
            description="{messages}",
            expected_output="A helpful, concise reply to the user.",
            agent=component,
        )
        return Crew(agents=[component], tasks=[task])

    @staticmethod
    def load(
        agentspec_config: str,
        tool_registry: Optional[Dict[str, _CrewAIServerToolType]] = None,
        components_registry: Optional[Dict[str, Any]] = None,
    ) -> CrewAIAgentSpecRunnableComponent:
        """Load an AgentSpec Configuration."""
        if components_registry is not None:
            raise ValueError(
                "CrewAI AgentSpecLoader does not accept components registry (for disaggregated components)."
            )
        crewai_component = AgentSpecLoader(tool_registry=tool_registry).load_yaml(agentspec_config)
        crew = CrewAIAgentSpecLoader._create_crew_from_component(crewai_component)  # type: ignore
        return CrewAIAgentSpecRunnableComponent(crew)
