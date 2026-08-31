# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


"""This module define the main interfaces of the WayFlow AgentSpec Runtime."""

from typing import Any, Callable, Dict, List, Literal, Optional, Union, cast

from agentspec_cts_sdk import (
    AgentSpecFinishedExecutionStatus,
    AgentSpecRunnableComponent,
    AgentSpecToolExecutionConfirmationStatus,
    AgentSpecToolRequestExecutionStatus,
    AgentSpecUserMessageRequestExecutionStatus,
    ToolRequest,
    ToolResult,
)
from wayflowcore import Conversation, MessageType
from wayflowcore.agent import Agent
from wayflowcore.agentspec import AgentSpecLoader
from wayflowcore.executors.executionstatus import ExecutionStatus as WayflowExecutionStatus
from wayflowcore.executors.executionstatus import FinishedStatus as WayflowFinishedStatus
from wayflowcore.executors.executionstatus import (
    ToolExecutionConfirmationStatus as WayflowToolExecutionConfirmationStatus,
)
from wayflowcore.executors.executionstatus import ToolRequestStatus as WayflowToolRequestStatus
from wayflowcore.executors.executionstatus import (
    UserMessageRequestStatus as WayflowUserMessageRequestStatus,
)
from wayflowcore.flow import Flow
from wayflowcore.mcp import enable_mcp_without_auth
from wayflowcore.tools import ServerTool
from wayflowcore.tools import ToolResult as WayflowToolResult

# Convenient types definition
ToolRegistryType = Dict[str, Callable[..., Any]]
WayFlowToolRegistryType = Dict[str, Union[ServerTool, Callable[..., Any]]]
AgentSpecExecutionStatus = Union[
    AgentSpecFinishedExecutionStatus,
    AgentSpecToolRequestExecutionStatus,
    AgentSpecUserMessageRequestExecutionStatus,
    AgentSpecToolExecutionConfirmationStatus,
]


class WayflowAgentSpecRunnableComponent:
    """
    RunnableComponent handle the execution of Flows or Agents.

    RunnableComponent are the interface between a system or end user and the execution of a Flow or
    Agent. RunnableComponents are stateful and will live through multiple interactions with the
    system or end-user such as exchanging messages or requesting the execution of client-side tools.
    """

    def __init__(
        self, component: Union[Agent, Flow], tool_registry: Optional[WayFlowToolRegistryType] = None
    ):
        self.tool_registry = tool_registry or {}
        self.component = component
        self.conversation: Optional[Conversation] = None
        self._confirmation_tool_requests: Dict[str, Any] = {}

    def start(self, inputs: Optional[Dict[str, Any]] = None) -> None:
        self.conversation = self.component.start_conversation(inputs=inputs or {})

    def run(self) -> AgentSpecExecutionStatus:
        if self.conversation is None:
            raise RuntimeError(
                "Conversation was not started. Ensure to call the `start` method first."
            )
        return self._transform_wayflow_execution_status_to_agentspec(
            execution_status=self.conversation.execute()
        )

    def append_user_message(self, user_message: str) -> None:
        if self.conversation is None:
            raise RuntimeError(
                "Conversation was not started. Ensure to call the `start` method first."
            )
        self.conversation.append_user_message(user_input=user_message)

    def append_tool_results(self, tool_result: ToolResult) -> None:
        if self.conversation is None:
            raise RuntimeError(
                "Conversation was not started. Ensure to call the `start` method first."
            )
        self.conversation.append_tool_result(
            tool_result=WayflowToolResult(
                tool_request_id=tool_result.tool_request_id,
                content=tool_result.content,
            )
        )

    def confirm_or_reject_tool_confirmation(
        self, tool_request: ToolRequest, decision: Literal["accept", "reject"]
    ) -> None:
        if tool_request.tool_request_id in self._confirmation_tool_requests:
            wayflow_tool_request = self._confirmation_tool_requests[tool_request.tool_request_id]
            wayflow_tool_request._tool_execution_confirmed = decision == "accept"
        else:
            raise ValueError(
                f"ToolRequest {tool_request} is not in the list of Tool Requests requiring confirmation"
            )

    def _get_last_agent_messages_from_conversation(self) -> List[str]:
        if self.conversation is None:
            return []
        agent_messages = []
        for message in self.conversation.message_list.get_messages()[::-1]:
            if message.message_type != MessageType.AGENT:
                break
            agent_messages.append(message.content)
        return agent_messages[::-1]

    def _transform_wayflow_execution_status_to_agentspec(
        self, execution_status: WayflowExecutionStatus
    ) -> AgentSpecExecutionStatus:
        last_agent_messages = self._get_last_agent_messages_from_conversation()
        if isinstance(execution_status, WayflowUserMessageRequestStatus):
            return AgentSpecUserMessageRequestExecutionStatus(agent_messages=last_agent_messages)
        elif isinstance(execution_status, WayflowToolRequestStatus):
            return AgentSpecToolRequestExecutionStatus(tool_requests=execution_status.tool_requests)  # type: ignore
        elif isinstance(execution_status, WayflowFinishedStatus):
            return AgentSpecFinishedExecutionStatus(
                outputs=execution_status.output_values, agent_messages=last_agent_messages
            )
        elif isinstance(execution_status, WayflowToolExecutionConfirmationStatus):
            for tool_req in execution_status.tool_requests:
                self._confirmation_tool_requests[tool_req.tool_request_id] = tool_req
            return AgentSpecToolExecutionConfirmationStatus(tool_requests=execution_status.tool_requests)  # type: ignore
        else:
            raise RuntimeError(f"Unexpected execution status returned: {type(execution_status)}")


class WayflowAgentSpecLoader:
    """
    Load an AgentSpec Configuration.

    The loader produces a runnable components for Flows or Agents relying on WayFlow as the
    backend system for the execution.
    """

    @staticmethod
    def _validate_component(wayflow_component: Any) -> None:
        if not isinstance(wayflow_component, (Agent, Flow)):
            raise ValueError(
                f"Unexpected component configuration received. "
                f"A runnable component like Agent or Flow was expected, "
                f"received {type(wayflow_component)} instead."
            )

    @staticmethod
    def load(
        agentspec_config: str,
        tool_registry: Optional[WayFlowToolRegistryType] = None,
        components_registry: Optional[Dict[str, Any]] = None,
    ) -> AgentSpecRunnableComponent:
        """Load an AgentSpec Configuration."""
        enable_mcp_without_auth()
        wayflow_component = cast(
            Agent,
            AgentSpecLoader(tool_registry=tool_registry).load_yaml(
                agentspec_config, components_registry=components_registry
            ),
        )
        WayflowAgentSpecLoader._validate_component(wayflow_component)
        return WayflowAgentSpecRunnableComponent(
            component=wayflow_component, tool_registry=tool_registry
        )
