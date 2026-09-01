# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING, Any, Callable, Dict, Hashable, Tuple, TypedDict, Union

from typing_extensions import TypeAlias

from pyagentspec._lazy_loader import LazyLoader, LazyType

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as langgraph is an optional dependency.
    # Otherwise, importing the module when they are not installed would lead to an import error.

    import langchain.agents as langchain_agents
    import langchain_ollama
    import langchain_openai
    import langgraph.graph as langgraph_graph
    import langgraph_swarm
    from langchain.agents.middleware.types import AgentState
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
    from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult
    from langchain_core.runnables import RunnableConfig, RunnableLambda
    from langchain_core.tools import BaseTool, StructuredTool
    from langgraph.graph import StateGraph
    from langgraph.graph._branch import BranchSpec
    from langgraph.graph._node import StateNodeSpec
    from langgraph.graph.message import Messages
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.types import Checkpointer, Command, interrupt

else:
    langgraph_swarm = LazyLoader("langgraph_swarm")
    langchain_ollama = LazyLoader("langchain_ollama")
    langchain_openai = LazyLoader("langchain_openai")
    langgraph_graph = LazyLoader("langgraph.graph")
    langchain_agents = LazyLoader("langchain.agents")
    BaseTool = LazyType("langchain_core.tools", "BaseTool")
    StructuredTool = LazyType("langchain_core.tools", "StructuredTool")
    Checkpointer = LazyType("langgraph.types", "Checkpointer")
    Command = LazyType("langgraph.types", "Command")
    interrupt = LazyLoader("langgraph.types", "interrupt")
    StateGraph = LazyType("langgraph.graph", "StateGraph")
    Messages = LazyLoader("langgraph.graph.message", "Messages")
    CompiledStateGraph = LazyType("langgraph.graph.state", "CompiledStateGraph")
    BaseCallbackHandler = LazyType("langchain_core.callbacks", "BaseCallbackHandler")
    RunnableConfig = LazyType("langchain_core.runnables", "RunnableConfig")
    RunnableLambda = LazyType("langchain_core.runnables", "RunnableLambda")
    StateNodeSpec = LazyType("langgraph.graph._node", "StateNodeSpec")
    BranchSpec = LazyType("langgraph.graph._branch", "BranchSpec")
    SystemMessage = LazyType("langchain_core.messages", "SystemMessage")
    BaseMessage = LazyType("langchain_core.messages", "BaseMessage")
    ToolMessage = LazyType("langchain_core.messages", "ToolMessage")
    BaseChatModel = LazyType("langchain_core.language_models", "BaseChatModel")
    ChatGenerationChunk = LazyType("langchain_core.outputs", "ChatGenerationChunk")
    GenerationChunk = LazyType("langchain_core.outputs", "GenerationChunk")
    LLMResult = LazyType("langchain_core.outputs", "LLMResult")
    AgentState = LazyType("langchain.agents.middleware.types", "AgentState")


LangGraphTool: TypeAlias = Union[BaseTool, Callable[..., Any]]
if TYPE_CHECKING:
    LangGraphComponent = Union[StateGraph[Any, Any, Any], CompiledStateGraph[Any, Any, Any]]
else:
    LangGraphComponent = Union[StateGraph, CompiledStateGraph]
LangGraphRuntimeComponent: TypeAlias = Union[LangGraphComponent, BaseChatModel, StructuredTool]
LangGraphComponentsRegistryT: TypeAlias = Dict[str, Union[LangGraphRuntimeComponent, Any]]


class NodeExecutionDetails(TypedDict, total=False):
    should_finish: bool
    branch: str
    generated_messages: Messages


NodeOutputsType: TypeAlias = Dict[str, Any]
ExecuteOutput: TypeAlias = Tuple[NodeOutputsType, NodeExecutionDetails]
NextNodeInputs: TypeAlias = Dict[str, Dict[str, Any]]


class FlowStateSchema(TypedDict):
    inputs: NextNodeInputs
    outputs: NodeOutputsType
    messages: Messages
    node_execution_details: NodeExecutionDetails


class FlowInputSchema(TypedDict):
    inputs: NextNodeInputs
    messages: Messages


class FlowOutputSchema(TypedDict):
    outputs: NodeOutputsType
    messages: Messages
    node_execution_details: NodeExecutionDetails


SourceNodeId: TypeAlias = str
BranchName: TypeAlias = Hashable
TargetNodeId: TypeAlias = str
ControlFlow: TypeAlias = Dict[SourceNodeId, Dict[BranchName, TargetNodeId]]


__all__ = [
    "langgraph_graph",
    "langchain_agents",
    "langchain_ollama",
    "langchain_openai",
    "LangGraphTool",
    "LangGraphComponent",
    "LangGraphRuntimeComponent",
    "LangGraphComponentsRegistryT",
    "NodeExecutionDetails",
    "FlowStateSchema",
    "FlowInputSchema",
    "FlowOutputSchema",
    "SourceNodeId",
    "BranchName",
    "TargetNodeId",
    "ControlFlow",
    "NodeOutputsType",
    "ExecuteOutput",
    "NextNodeInputs",
    "CompiledStateGraph",
    "StateGraph",
    "StateNodeSpec",
    "StructuredTool",
    "BaseTool",
    "RunnableLambda",
    "SystemMessage",
    "BaseMessage",
    "ToolMessage",
    "BaseChatModel",
    "AgentState",
    "Checkpointer",
    "Command",
    "interrupt",
    "RunnableConfig",
    "Messages",
    "BranchSpec",
    "BaseCallbackHandler",
    "ChatGenerationChunk",
    "GenerationChunk",
    "LLMResult",
    "langgraph_swarm",
]
