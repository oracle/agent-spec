# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING, Any, Callable, MutableMapping, Sequence, TypeAlias

from pyagentspec._lazy_loader import LazyLoader

if TYPE_CHECKING:
    from agent_framework import (
        Agent,
        BaseChatClient,
        ChatOptions,
        FunctionTool,
        MCPStdioTool,
        MCPStreamableHTTPTool,
        MCPWebsocketTool,
    )
    from agent_framework.openai import OpenAIChatClient, OpenAIChatCompletionClient
else:
    ChatOptions = LazyLoader("agent_framework").ChatOptions
    FunctionTool = LazyLoader("agent_framework").FunctionTool
    BaseChatClient = LazyLoader("agent_framework").BaseChatClient
    Agent = LazyLoader("agent_framework").Agent
    MCPStdioTool = LazyLoader("agent_framework").MCPStdioTool
    MCPStreamableHTTPTool = LazyLoader("agent_framework").MCPStreamableHTTPTool
    MCPWebsocketTool = LazyLoader("agent_framework").MCPWebsocketTool
    _openai = LazyLoader("agent_framework.openai")
    OpenAIChatClient = _openai.OpenAIChatClient
    OpenAIChatCompletionClient = _openai.OpenAIChatCompletionClient

AgentFrameworkMCPTool: TypeAlias = MCPStdioTool | MCPStreamableHTTPTool | MCPWebsocketTool
AgentFrameworkTool: TypeAlias = (
    FunctionTool
    | Callable[..., Any]
    | MutableMapping[str, Any]
    | Sequence[Callable[..., Any] | MutableMapping[str, Any]]
    | AgentFrameworkMCPTool
)
AgentFrameworkLlmConfig: TypeAlias = BaseChatClient
AgentFrameworkComponent: TypeAlias = Agent | AgentFrameworkTool | AgentFrameworkLlmConfig

__all__ = [
    "AgentFrameworkComponent",
    "AgentFrameworkLlmConfig",
    "AgentFrameworkMCPTool",
    "AgentFrameworkTool",
    "BaseChatClient",
    "FunctionTool",
    "Agent",
    "MCPStdioTool",
    "MCPStreamableHTTPTool",
    "MCPWebsocketTool",
    "OpenAIChatClient",
    "OpenAIChatCompletionClient",
    "ChatOptions",
]
