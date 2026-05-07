# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


# mypy: ignore-errors

"""This modules define the main interfaces of AgentFramework AgentSpec Runtime."""

import asyncio
import json
import logging
from typing import Any, List, Literal, TypeAlias, final

from agent_framework import ChatAgent, ChatMessage, Role
from agentspec_cts_sdk import (
    AgentSpecFinishedExecutionStatus,
)
from agentspec_cts_sdk import AgentSpecLoader as AgentSpecLoaderProtocol
from agentspec_cts_sdk import (
    AgentSpecRunnableComponent,
    AgentSpecToolExecutionConfirmationStatus,
    AgentSpecToolRequestExecutionStatus,
    AgentSpecUserMessageRequestExecutionStatus,
    ToolRequest,
    ToolResult,
)

from pyagentspec.adapters.agent_framework import AgentSpecLoader
from pyagentspec.adapters.agent_framework._types import AgentFrameworkComponent
from pyagentspec.serialization import AgentSpecDeserializer

logger = logging.getLogger(__name__)

AgentFrameworkMessage: TypeAlias = str | ChatMessage | list[str] | list[ChatMessage] | None


@final
class AgentFrameworkRunnableComponent(AgentSpecRunnableComponent):
    def __init__(
        self,
        component: AgentFrameworkComponent,
    ) -> None:
        self.component = component
        self.inputs = {}  # type: dict[str, Any]
        self.messages = []  # type: list[ChatMessage]
        self._user_inputs_required = {}  # type: dict[str, Any]

    def start(self, inputs: dict[str, Any] | None = None) -> None:
        self.inputs = inputs or {}

    def _convert_messages_to_list(self, messages: AgentFrameworkMessage) -> list[ChatMessage]:
        if messages is None:
            return []
        elif isinstance(messages, str):
            return [ChatMessage(role="user", text=messages)]
        elif isinstance(messages, ChatMessage):
            return [messages]
        elif isinstance(messages, list):
            new_messages: list[ChatMessage] = []
            for message in messages:
                if isinstance(message, str):
                    new_messages.append(ChatMessage(role="user", text=message))
                else:
                    new_messages.append(message)
            return new_messages
        else:
            raise TypeError("Invalid message type")

    def run(
        self,
    ) -> (
        AgentSpecFinishedExecutionStatus
        | AgentSpecToolRequestExecutionStatus
        | AgentSpecUserMessageRequestExecutionStatus
        | AgentSpecToolExecutionConfirmationStatus
    ):
        return asyncio.run(self._async_run())

    async def _async_run(
        self,
    ) -> (
        AgentSpecFinishedExecutionStatus
        | AgentSpecToolRequestExecutionStatus
        | AgentSpecUserMessageRequestExecutionStatus
        | AgentSpecToolExecutionConfirmationStatus
    ):
        match self.component:
            case ChatAgent() as agent:
                result = await agent.run(self.messages)
                if result.user_input_requests:
                    tool_requests: List[ToolRequest] = []
                    for user_input_needed in result.user_input_requests:
                        function_args = user_input_needed.function_call.arguments
                        if isinstance(function_args, str):
                            function_args = json.loads(function_args)

                        if isinstance(function_args, dict) or function_args is None:
                            tool_requests.append(
                                ToolRequest(
                                    name=user_input_needed.function_call.name,
                                    args=function_args,
                                    tool_request_id=user_input_needed.id,
                                )
                            )
                            self._user_inputs_required[user_input_needed.id] = user_input_needed
                    return AgentSpecToolExecutionConfirmationStatus(tool_requests=tool_requests)

                self.messages.extend(result.messages)
                return AgentSpecUserMessageRequestExecutionStatus(
                    agent_messages=[
                        message.text
                        for message in result.messages
                        if message.role == Role.ASSISTANT
                    ],
                )
            case component:
                raise ValueError(
                    f"Component of type {component} not supported in AgentFrameworkRunnableComponent"
                )

    def append_tool_results(self, tool_result: ToolResult) -> None:
        raise NotImplementedError(f".append_tool_results() for {type(self)} is not implemented yet")

    def append_user_message(self, user_message: str) -> None:
        self.messages = self._convert_messages_to_list(self.messages)
        self.messages.append(ChatMessage(role="user", text=user_message))

    def confirm_or_reject_tool_confirmation(
        self, tool_request: ToolRequest, decision: Literal["accept", "reject"]
    ) -> None:
        approved = decision == "accept"
        self.messages = self._convert_messages_to_list(self.messages)
        self.messages.append(
            ChatMessage(
                role=Role.USER,
                contents=[
                    self._user_inputs_required[
                        tool_request.tool_request_id
                    ].to_function_approval_response(approved)
                ],
            )
        )


@final
class AgentFrameworkAgentSpecLoader(AgentSpecLoaderProtocol):

    @staticmethod
    def load(
        agentspec_config: str,
        tool_registry: dict[str, Any] | None = None,
        components_registry: dict[str, Any] | None = None,
    ) -> AgentSpecRunnableComponent:
        agentspec_component = AgentSpecDeserializer().from_yaml(
            agentspec_config, components_registry=components_registry
        )
        component = AgentSpecLoader(tool_registry).load_component(agentspec_component)
        if not isinstance(component, AgentFrameworkComponent):
            raise ValueError(f"Runnable component was expected, got: {type(component)}")
        return AgentFrameworkRunnableComponent(component=component)
