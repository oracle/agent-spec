# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Protocol, Union


@dataclass
class ToolRequest:
    name: str
    args: Optional[Dict[str, Any]]
    tool_request_id: str


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


@dataclass
class AgentSpecFinishedExecutionStatus:
    outputs: Dict[str, Any]
    agent_messages: List[str]


@dataclass
class AgentSpecUserMessageRequestExecutionStatus:
    agent_messages: List[str]


@dataclass
class AgentSpecToolRequestExecutionStatus:
    tool_requests: List[ToolRequest]


@dataclass
class AgentSpecToolExecutionConfirmationStatus:
    tool_requests: List[ToolRequest]


class AgentSpecRunnableComponent(Protocol):

    def start(self, inputs: Dict[str, Any] | None = None) -> None:
        raise NotImplementedError("You must implement this method of the protocol")

    def run(
        self,
    ) -> Union[
        AgentSpecFinishedExecutionStatus,
        AgentSpecToolRequestExecutionStatus,
        AgentSpecUserMessageRequestExecutionStatus,
        AgentSpecToolExecutionConfirmationStatus,
    ]:
        raise NotImplementedError("You must implement this method of the protocol")

    def append_user_message(self, user_message: str) -> None:
        raise NotImplementedError("You must implement this method of the protocol")

    def append_tool_results(self, tool_result: ToolResult) -> None:
        raise NotImplementedError("You must implement this method of the protocol")

    def confirm_or_reject_tool_confirmation(
        self, tool_request: ToolRequest, decision: Literal["accept", "reject"]
    ) -> None:
        raise NotImplementedError("You must implement this method of the protocol")


class AgentSpecLoader(Protocol):

    @staticmethod
    def load(
        agentspec_config: str,
        tool_registry: Optional[Dict[str, Any]] = None,
        components_registry: Optional[Dict[str, Any]] = None,
    ) -> AgentSpecRunnableComponent:
        raise NotImplementedError("You must implement this method of the protocol")
