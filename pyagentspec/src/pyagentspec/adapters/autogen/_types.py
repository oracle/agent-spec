# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING, Any, Callable, Union

from pyagentspec._lazy_loader import LazyLoader

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as autogen is an optional dependency.
    # Otherwise, importing the module when they are not installed would lead to an import error.

    import autogen_agentchat
    import autogen_core
    import autogen_ext
    from autogen_agentchat.agents import AssistantAgent as AutogenAssistantAgent
    from autogen_agentchat.agents import BaseChatAgent as AutogenBaseAgent
    from autogen_agentchat.teams import GraphFlow as AutogenGraphFlow
    from autogen_core import Component as AutogenComponent
    from autogen_core.code_executor._func_with_reqs import Import as AutogenImport
    from autogen_core.models import ChatCompletionClient as AutogenChatCompletionClient
    from autogen_core.models import ModelFamily as AutogenModelFamily
    from autogen_core.models import ModelInfo as AutogenModelInfo
    from autogen_core.tools import BaseTool as AutogenBaseTool
    from autogen_core.tools import FunctionTool as AutogenFunctionTool
    from autogen_ext.models.ollama import (
        OllamaChatCompletionClient as AutogenOllamaChatCompletionClient,
    )
    from autogen_ext.models.openai import (
        OpenAIChatCompletionClient as AutogenOpenAIChatCompletionClient,
    )
else:
    autogen_core = LazyLoader("autogen_core")
    autogen_agentchat = LazyLoader("autogen_agentchat")
    autogen_ext = LazyLoader("autogen_ext")
    # We need to import the classes this way because it's the only one accepted by the lazy loader
    AutogenComponent = autogen_core.Component
    AutogenChatCompletionClient = LazyLoader("autogen_core.models").ChatCompletionClient
    AutogenBaseTool = LazyLoader("autogen_core.tools").BaseTool
    AutogenFunctionTool = LazyLoader("autogen_core.tools").FunctionTool
    AutogenModelInfo = LazyLoader("autogen_core.models").ModelInfo
    AutogenModelFamily = LazyLoader("autogen_core.models").ModelFamily
    AutogenAssistantAgent = LazyLoader("autogen_agentchat.agents").AssistantAgent
    AutogenBaseAgent = LazyLoader("autogen_agentchat.agents").BaseChatAgent
    AutogenGraphFlow = LazyLoader("autogen_agentchat.teams").GraphFlow
    AutogenOllamaChatCompletionClient = LazyLoader(
        "autogen_ext.models.ollama"
    ).OllamaChatCompletionClient
    AutogenOpenAIChatCompletionClient = LazyLoader(
        "autogen_ext.models.openai"
    ).OpenAIChatCompletionClient
    AutogenImport = LazyLoader("autogen_core.code_executor._func_with_reqs").Import

AutoGenTool = Union[AutogenFunctionTool, Callable[..., Any]]

__all__ = [
    "autogen_core",
    "autogen_agentchat",
    "autogen_ext",
    "AutogenComponent",
    "AutogenChatCompletionClient",
    "AutogenBaseTool",
    "AutogenFunctionTool",
    "AutogenModelInfo",
    "AutogenModelFamily",
    "AutogenAssistantAgent",
    "AutogenBaseAgent",
    "AutogenGraphFlow",
    "AutogenOllamaChatCompletionClient",
    "AutogenOpenAIChatCompletionClient",
    "AutogenImport",
]
