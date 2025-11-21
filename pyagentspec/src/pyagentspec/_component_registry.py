# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines a registry of the available Agent Spec Components."""

from typing import Mapping

from pyagentspec.a2aagent import A2AAgent, A2AConnectionConfig
from pyagentspec.agent import Agent
from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.component import Component, ComponentWithIO
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import (
    AgentNode,
    ApiNode,
    BranchingNode,
    EndNode,
    FlowNode,
    InputMessageNode,
    LlmNode,
    MapNode,
    OutputMessageNode,
    ParallelFlowNode,
    ParallelMapNode,
    StartNode,
    ToolNode,
)
from pyagentspec.llms import (
    OciGenAiConfig,
    OllamaConfig,
    OpenAiCompatibleConfig,
    OpenAiConfig,
    VllmConfig,
)
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.llms.ociclientconfig import (
    OciClientConfig,
    OciClientConfigWithApiKey,
    OciClientConfigWithInstancePrincipal,
    OciClientConfigWithResourcePrincipal,
    OciClientConfigWithSecurityToken,
)
from pyagentspec.managerworkers import ManagerWorkers
from pyagentspec.mcp.clienttransport import (
    ClientTransport,
    RemoteTransport,
    SSEmTLSTransport,
    SSETransport,
    StdioTransport,
    StreamableHTTPmTLSTransport,
    StreamableHTTPTransport,
)
from pyagentspec.mcp.tools import MCPTool, MCPToolBox, MCPToolSpec
from pyagentspec.ociagent import OciAgent
from pyagentspec.remoteagent import RemoteAgent
from pyagentspec.specialized_agent import AgentSpecializationParameters, SpecializedAgent
from pyagentspec.swarm import Swarm
from pyagentspec.tools.builtintool import BuiltinTool
from pyagentspec.tools.clienttool import ClientTool
from pyagentspec.tools.remotetool import RemoteTool
from pyagentspec.tools.servertool import ServerTool
from pyagentspec.tools.tool import Tool
from pyagentspec.tools.toolbox import ToolBox

BUILTIN_CLASS_MAP: Mapping[str, type[Component]] = {
    "A2AAgent": A2AAgent,
    "A2AConnectionConfig": A2AConnectionConfig,
    "Agent": Agent,
    "AgenticComponent": AgenticComponent,
    "AgentNode": AgentNode,
    "AgentSpecializationParameters": AgentSpecializationParameters,
    "ApiNode": ApiNode,
    "BranchingNode": BranchingNode,
    "ClientTransport": ClientTransport,
    "Component": Component,
    "ComponentWithIO": ComponentWithIO,
    "ClientTool": ClientTool,
    "BuiltinTool": BuiltinTool,
    "ControlFlowEdge": ControlFlowEdge,
    "DataFlowEdge": DataFlowEdge,
    "EndNode": EndNode,
    "Flow": Flow,
    "FlowNode": FlowNode,
    "InputMessageNode": InputMessageNode,
    "LlmConfig": LlmConfig,
    "LlmNode": LlmNode,
    "MapNode": MapNode,
    "MCPTool": MCPTool,
    "MCPToolBox": MCPToolBox,
    "MCPToolSpec": MCPToolSpec,
    "Node": Node,
    "OciAgent": OciAgent,
    "OciClientConfig": OciClientConfig,
    "OciClientConfigWithApiKey": OciClientConfigWithApiKey,
    "OciClientConfigWithInstancePrincipal": OciClientConfigWithInstancePrincipal,
    "OciClientConfigWithResourcePrincipal": OciClientConfigWithResourcePrincipal,
    "OciClientConfigWithSecurityToken": OciClientConfigWithSecurityToken,
    "OciGenAiConfig": OciGenAiConfig,
    "OllamaConfig": OllamaConfig,
    "OpenAiCompatibleConfig": OpenAiCompatibleConfig,
    "OpenAiConfig": OpenAiConfig,
    "OutputMessageNode": OutputMessageNode,
    "RemoteTool": RemoteTool,
    "RemoteTransport": RemoteTransport,
    "RemoteAgent": RemoteAgent,
    "ServerTool": ServerTool,
    "SpecializedAgent": SpecializedAgent,
    "SSETransport": SSETransport,
    "SSEmTLSTransport": SSEmTLSTransport,
    "StartNode": StartNode,
    "StdioTransport": StdioTransport,
    "StreamableHTTPTransport": StreamableHTTPTransport,
    "StreamableHTTPmTLSTransport": StreamableHTTPmTLSTransport,
    "Tool": Tool,
    "ToolBox": ToolBox,
    "ToolNode": ToolNode,
    "VllmConfig": VllmConfig,
    "Swarm": Swarm,
    "ManagerWorkers": ManagerWorkers,
    "ParallelFlowNode": ParallelFlowNode,
    "ParallelMapNode": ParallelMapNode,
}
