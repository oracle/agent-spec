# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
Type aliases for OpenAI Agents SDK classes used by the adapter.

We keep these in a dedicated module to centralize the unions used for
runtime isinstance checks and for type hints in converter modules.
"""

from typing import TYPE_CHECKING, TypeAlias, Union

from pyagentspec._lazy_loader import LazyLoader, LazyType

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as OpenAI Agents is an optional dependency.
    # Otherwise, importing the module when they are not installed would lead to an import error.

    # Import OpenAI Agents SDK classes
    import agents
    from agents.agent import Agent as OAAgent
    from agents.models.openai_chatcompletions import (
        OpenAIChatCompletionsModel as OAChatCompletionsModel,
    )
    from agents.models.openai_provider import OpenAIProvider as OAOpenAIProvider
    from agents.models.openai_responses import OpenAIResponsesModel as OAResponsesModel
    from agents.tool import CodeInterpreterTool as OACodeInterpreterTool
    from agents.tool import ComputerTool as OAComputerTool
    from agents.tool import FileSearchTool as OAFileSearchTool
    from agents.tool import FunctionTool as OAFunctionTool
    from agents.tool import HostedMCPTool as OAHostedMCPTool
    from agents.tool import ImageGenerationTool as OAImageGenerationTool
    from agents.tool import LocalShellTool as OALocalShellTool
    from agents.tool import WebSearchTool as OAWebSearchTool
    from agents.tool import function_tool as function_tool
    from agents.tool_context import ToolContext as OAToolContext
else:
    agents = LazyLoader("agents")
    OAAgent = LazyType("agents.agent", "Agent")
    OACodeInterpreterTool = LazyType("agents.tool", "CodeInterpreterTool")
    OAComputerTool = LazyType("agents.tool", "ComputerTool")
    OAFileSearchTool = LazyType("agents.tool", "FileSearchTool")
    OAFunctionTool = LazyType("agents.tool", "FunctionTool")
    OAHostedMCPTool = LazyType("agents.tool", "HostedMCPTool")
    OAImageGenerationTool = LazyType("agents.tool", "ImageGenerationTool")
    OALocalShellTool = LazyType("agents.tool", "LocalShellTool")
    OAWebSearchTool = LazyType("agents.tool", "WebSearchTool")
    OAToolContext = LazyType("agents.tool_context", "ToolContext")
    function_tool = LazyLoader("agents.tool", "function_tool")
    OAOpenAIProvider = LazyType("agents.models.openai_provider", "OpenAIProvider")
    OAChatCompletionsModel = LazyType(
        "agents.models.openai_chatcompletions", "OpenAIChatCompletionsModel"
    )
    OAResponsesModel = LazyType("agents.models.openai_responses", "OpenAIResponsesModel")

# An OpenAI Agents component we support exporting (agent or function tool)
OAComponent: TypeAlias = Union[OAAgent, OAFunctionTool]

# Hosted/built-in tools exposed by the OpenAI Agents SDK
OAHostedTool: TypeAlias = Union[
    OAFileSearchTool,
    OAWebSearchTool,
    OAComputerTool,  # type: ignore
    OAHostedMCPTool,
    OALocalShellTool,
    OAImageGenerationTool,
    OACodeInterpreterTool,
]

__all__ = [
    "agents",
    "OAAgent",
    "OAFunctionTool",
    "OAComponent",
    "OAHostedTool",
    "OAToolContext",
    "OAOpenAIProvider",
    "OAChatCompletionsModel",
    "OAResponsesModel",
    "function_tool",
]
