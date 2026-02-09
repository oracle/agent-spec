# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, Hashable, Mapping, Tuple, TypedDict, Union

from typing_extensions import TypeAlias

from pyagentspec._lazy_loader import LazyLoader
from pyagentspec.llms.openaicompatibleconfig import OpenAIAPIType

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as langgraph is an optional dependency.
    # Otherwise, importing the module when they are not installed would lead to an import error.

    import langchain.agents as langchain_agents
    import langchain_core.messages.content as langchain_core_messages_content
    import langchain_ollama
    import langchain_openai
    import langgraph
    import langgraph.graph as langgraph_graph
    import langgraph.graph.state as langgraph_graph_state
    import langgraph.prebuilt as langgraph_prebuilt
    import langgraph.types as langgraph_types
    import langgraph_swarm
    from langchain.agents.middleware.types import AgentState
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
    from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult
    from langchain_core.runnables import RunnableBinding, RunnableConfig, RunnableLambda
    from langchain_core.tools import BaseTool, StructuredTool
    from langgraph.graph import StateGraph
    from langgraph.graph._branch import BranchSpec
    from langgraph.graph._node import StateNodeSpec
    from langgraph.graph.message import Messages
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.store.base import BaseStore
    from langgraph.types import Checkpointer, interrupt

else:
    langgraph = LazyLoader("langgraph")
    langgraph_swarm = LazyLoader("langgraph_swarm")
    langchain_ollama = LazyLoader("langchain_ollama")
    langchain_openai = LazyLoader("langchain_openai")
    langgraph_graph = LazyLoader("langgraph.graph")
    langgraph_types = LazyLoader("langgraph.types")
    langgraph_prebuilt = LazyLoader("langgraph.prebuilt")
    langgraph_graph_state = LazyLoader("langgraph.graph.state")
    langchain_agents = LazyLoader("langchain.agents")
    langchain_core_messages_content = LazyLoader("langchain_core.messages.content")
    # We need to import the classes this way because it's the only one accepted by the lazy loader
    BaseTool = LazyLoader("langchain_core.tools").BaseTool
    StructuredTool = LazyLoader("langchain_core.tools").StructuredTool
    Checkpointer = LazyLoader("langgraph.types").Checkpointer
    interrupt = LazyLoader("langgraph.types").interrupt
    StateGraph = langgraph_graph.StateGraph
    Messages = LazyLoader("langgraph.graph.message").Messages
    CompiledStateGraph = LazyLoader("langgraph.graph.state").CompiledStateGraph
    BaseCallbackHandler = LazyLoader("langchain_core.callbacks").BaseCallbackHandler
    AsyncCallbackHandler = LazyLoader("langchain_core.callbacks").AsyncCallbackHandler
    RunnableBinding = LazyLoader("langchain_core.runnables").RunnableBinding
    RunnableConfig = LazyLoader("langchain_core.runnables").RunnableConfig
    RunnableLambda = LazyLoader("langchain_core.runnables").RunnableLambda
    StateNodeSpec = LazyLoader("langgraph.graph._node").StateNodeSpec
    StateNode = LazyLoader("langgraph.graph._node").StateNode
    BranchSpec = LazyLoader("langgraph.graph._branch").BranchSpec
    SystemMessage = LazyLoader("langchain_core.messages").SystemMessage
    BaseMessage = LazyLoader("langchain_core.messages").BaseMessage
    ToolMessage = LazyLoader("langchain_core.messages").ToolMessage
    BaseChatModel = LazyLoader("langchain_core.language_models").BaseChatModel
    BaseStore = LazyLoader("langgraph.store.base").BaseStore
    ChatGenerationChunk = LazyLoader("langchain_core.outputs").ChatGenerationChunk
    GenerationChunk = LazyLoader("langchain_core.outputs").GenerationChunk
    LLMResult = LazyLoader("langchain_core.outputs").LLMResult
    AgentState = LazyLoader("langchain.agents.middleware.types").AgentState


LangGraphTool: TypeAlias = Union[BaseTool, Callable[..., Any]]
LangGraphComponent = Union[StateGraph[Any, Any, Any], CompiledStateGraph[Any, Any, Any]]
LangGraphRuntimeComponent: TypeAlias = Union[LangGraphComponent, BaseChatModel, StructuredTool]
LangGraphComponentsRegistryT: TypeAlias = Mapping[str, Union[LangGraphRuntimeComponent, Any]]


@dataclass
class LangGraphLlmConfig:
    model_type: str
    model_name: str
    base_url: str
    api_type: OpenAIAPIType = OpenAIAPIType.CHAT_COMPLETIONS


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
    "langgraph",
    "langgraph_graph",
    "langgraph_graph_state",
    "langgraph_types",
    "langchain_core_messages_content",
    "langgraph_prebuilt",
    "langchain_agents",
    "langchain_ollama",
    "langchain_openai",
    "LangGraphTool",
    "LangGraphComponent",
    "LangGraphRuntimeComponent",
    "LangGraphComponentsRegistryT",
    "LangGraphLlmConfig",
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
    "RunnableBinding",
    "StructuredTool",
    "BaseTool",
    "RunnableLambda",
    "SystemMessage",
    "BaseMessage",
    "ToolMessage",
    "BaseChatModel",
    "BaseStore",
    "AgentState",
    "Checkpointer",
    "interrupt",
    "RunnableConfig",
    "Messages",
    "BranchSpec",
    "BaseCallbackHandler",
    "AsyncCallbackHandler",
    "ChatGenerationChunk",
    "GenerationChunk",
    "LLMResult",
    "langgraph_swarm",
]
