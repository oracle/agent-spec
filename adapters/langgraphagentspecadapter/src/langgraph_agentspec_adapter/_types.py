# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from dataclasses import dataclass
from typing import Any, Callable, Dict, Hashable, List, Tuple, TypedDict, Union

from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.message import Messages
from langgraph.graph.state import CompiledStateGraph
from pyagentspec.tools import Tool as AgentSpecTool
from pydantic import SerializeAsAny
from typing_extensions import TypeAlias

LangGraphTool: TypeAlias = Union[BaseTool, Callable[..., Any]]
LangGraphComponent = Union[StateGraph[Any, Any, Any], CompiledStateGraph[Any, Any, Any]]


@dataclass
class LangGraphLlmConfig:
    model_type: str
    model_name: str
    base_url: str
    tools: List[SerializeAsAny[AgentSpecTool]]


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
