# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines a registry of the available Agent Spec Components."""

from typing import Mapping

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
from pyagentspec.mcp.clienttransport import (
    ClientTransport,
    RemoteTransport,
    SSEmTLSTransport,
    SSETransport,
    StdioTransport,
    StreamableHTTPmTLSTransport,
    StreamableHTTPTransport,
)
from pyagentspec.mcp.tools import MCPTool
from pyagentspec.ociagent import OciAgent
from pyagentspec.openaiagent import OpenAiAgent
from pyagentspec.remoteagent import RemoteAgent
from pyagentspec.tools.clienttool import ClientTool
from pyagentspec.tools.remotetool import RemoteTool
from pyagentspec.tools.servertool import ServerTool
from pyagentspec.tools.tool import Tool

BUILTIN_CLASS_MAP: Mapping[str, type[Component]] = {
    "Agent": Agent,
    "AgenticComponent": AgenticComponent,
    "AgentNode": AgentNode,
    "ApiNode": ApiNode,
    "BranchingNode": BranchingNode,
    "ClientTransport": ClientTransport,
    "Component": Component,
    "ComponentWithIO": ComponentWithIO,
    "ClientTool": ClientTool,
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
    "Node": Node,
    "OciAgent": OciAgent,
    "OciClientConfig": OciClientConfig,
    "OciClientConfigWithApiKey": OciClientConfigWithApiKey,
    "OciClientConfigWithInstancePrincipal": OciClientConfigWithInstancePrincipal,
    "OciClientConfigWithResourcePrincipal": OciClientConfigWithResourcePrincipal,
    "OciClientConfigWithSecurityToken": OciClientConfigWithSecurityToken,
    "OciGenAiConfig": OciGenAiConfig,
    "OllamaConfig": OllamaConfig,
    "OpenAiAgent": OpenAiAgent,
    "OpenAiCompatibleConfig": OpenAiCompatibleConfig,
    "OpenAiConfig": OpenAiConfig,
    "OutputMessageNode": OutputMessageNode,
    "RemoteTool": RemoteTool,
    "RemoteTransport": RemoteTransport,
    "RemoteAgent": RemoteAgent,
    "ServerTool": ServerTool,
    "SSETransport": SSETransport,
    "SSEmTLSTransport": SSEmTLSTransport,
    "StartNode": StartNode,
    "StdioTransport": StdioTransport,
    "StreamableHTTPTransport": StreamableHTTPTransport,
    "StreamableHTTPmTLSTransport": StreamableHTTPmTLSTransport,
    "Tool": Tool,
    "ToolNode": ToolNode,
    "VllmConfig": VllmConfig,
}
