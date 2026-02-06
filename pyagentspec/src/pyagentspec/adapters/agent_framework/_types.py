# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING, Any, Callable, MutableMapping, Sequence, TypeAlias

from pyagentspec._lazy_loader import LazyLoader

if TYPE_CHECKING:
    from agent_framework import (
        AIFunction,
        BaseChatClient,
        ChatAgent,
        ChatClientProtocol,
        ChatOptions,
        MCPStdioTool,
        MCPStreamableHTTPTool,
        MCPWebsocketTool,
        ToolProtocol,
    )
    from agent_framework.openai import OpenAIChatClient
else:
    ChatOptions = LazyLoader("agent_framework").ChatOptions
    AIFunction = LazyLoader("agent_framework").AIFunction
    BaseChatClient = LazyLoader("agent_framework").BaseChatClient
    ChatAgent = LazyLoader("agent_framework").ChatAgent
    ChatClientProtocol = LazyLoader("agent_framework").ChatClientProtocol
    MCPStdioTool = LazyLoader("agent_framework").MCPStdioTool
    MCPStreamableHTTPTool = LazyLoader("agent_framework").MCPStreamableHTTPTool
    MCPWebsocketTool = LazyLoader("agent_framework").MCPWebsocketTool
    ToolProtocol = LazyLoader("agent_framework").ToolProtocol
    OpenAIChatClient = LazyLoader("agent_framework.openai").OpenAIChatClient

AgentFrameworkComponent: TypeAlias = ChatAgent
AgentFrameworkTool: TypeAlias = (
    ToolProtocol
    | AIFunction[Any, Any]
    | Callable[..., Any]
    | MutableMapping[str, Any]
    | Sequence[ToolProtocol | Callable[..., Any] | MutableMapping[str, Any]]
)
AgentFrameworkLlmConfig: TypeAlias = BaseChatClient | ChatClientProtocol
AgentFrameworkMCPTool: TypeAlias = MCPStdioTool | MCPStreamableHTTPTool | MCPWebsocketTool

__all__ = [
    "BaseChatClient",
    "AIFunction",
    "ChatAgent",
    "ChatClientProtocol",
    "MCPStdioTool",
    "MCPStreamableHTTPTool",
    "MCPWebsocketTool",
    "ToolProtocol",
    "OpenAIChatClient",
    "ChatOptions",
]
