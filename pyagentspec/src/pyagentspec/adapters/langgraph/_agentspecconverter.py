# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import datetime
from types import FunctionType
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Union, cast

from pyagentspec import Property
from pyagentspec.adapters.langgraph._agentspec_converter_flow import (
    _langgraph_graph_convert_to_agentspec,
)
from pyagentspec.adapters.langgraph._types import (
    BaseChatModel,
    CompiledStateGraph,
    LangGraphComponent,
    LangGraphRuntimeComponent,
    StateNodeSpec,
    StructuredTool,
    SystemMessage,
    langchain_ollama,
    langchain_openai,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms import OllamaConfig as AgentSpecOllamaConfig
from pyagentspec.llms import OpenAiCompatibleConfig as AgentSpecOpenAiCompatibleConfig
from pyagentspec.llms import OpenAiConfig as AgentSpecOpenAiConfig
from pyagentspec.llms.ociclientconfig import (
    OciClientConfigWithApiKey as AgentSpecOciClientConfigWithApiKey,
)
from pyagentspec.llms.ociclientconfig import (
    OciClientConfigWithInstancePrincipal as AgentSpecOciClientConfigWithInstancePrincipal,
)
from pyagentspec.llms.ociclientconfig import (
    OciClientConfigWithResourcePrincipal as AgentSpecOciClientConfigWithResourcePrincipal,
)
from pyagentspec.llms.ociclientconfig import (
    OciClientConfigWithSecurityToken as AgentSpecOciClientConfigWithSecurityToken,
)
from pyagentspec.llms.ocigenaiconfig import ModelProvider as AgentSpecModelProvider
from pyagentspec.llms.ocigenaiconfig import OciAPIType as AgentSpecOciAPIType
from pyagentspec.llms.ocigenaiconfig import OciGenAiConfig as AgentSpecOciGenAiConfig
from pyagentspec.llms.openaicompatibleconfig import OpenAIAPIType as AgentSpecOpenAIAPIType
from pyagentspec.mcp import MCPTool as AgentSpecMCPTool
from pyagentspec.mcp.clienttransport import (
    ClientTransport,
    SessionParameters,
    SSETransport,
    StdioTransport,
    StreamableHTTPTransport,
)
from pyagentspec.tools import ServerTool
from pyagentspec.tools import Tool as AgentSpecTool

if TYPE_CHECKING:
    from langchain_mcp_adapters.sessions import (
        SSEConnection,
        StdioConnection,
        StreamableHttpConnection,
    )


class LangGraphToAgentSpecConverter:
    def convert(
        self,
        langgraph_component: LangGraphRuntimeComponent,
        referenced_objects: Optional[Dict[str, AgentSpecComponent]] = None,
    ) -> AgentSpecComponent:
        """Convert the given LangGraph component object into the corresponding PyAgentSpec component"""
        if referenced_objects is None:
            referenced_objects = {}

        # Reuse the same object multiple times in order to exploit the referencing system
        object_reference = self._get_obj_reference(langgraph_component)
        if object_reference in referenced_objects:
            return referenced_objects[object_reference]

        referenced_objects[object_reference] = self._convert(
            langgraph_component=langgraph_component,
            referenced_objects=referenced_objects,
        )
        return referenced_objects[object_reference]

    def _convert(
        self,
        langgraph_component: LangGraphRuntimeComponent,
        referenced_objects: Dict[str, AgentSpecComponent],
    ) -> AgentSpecComponent:
        agentspec_component: Optional[AgentSpecComponent] = None
        if isinstance(langgraph_component, StructuredTool):
            agentspec_component = self._langgraph_any_tool_to_agentspec_tool(langgraph_component)
        elif isinstance(langgraph_component, BaseChatModel):
            agentspec_component = self._basechatmodel_convert_to_agentspec(langgraph_component)
        elif self._is_react_agent(langgraph_component):
            agentspec_component = self._langgraph_agent_convert_to_agentspec(
                langgraph_component, referenced_objects
            )
        else:
            agentspec_component = _langgraph_graph_convert_to_agentspec(
                self, langgraph_component, referenced_objects
            )
        if agentspec_component is None:
            raise NotImplementedError(f"Conversion for {langgraph_component} not implemented yet")
        return agentspec_component

    def _is_react_agent(
        self,
        langgraph_component: LangGraphComponent,
    ) -> bool:
        if isinstance(langgraph_component, CompiledStateGraph):
            langgraph_component = langgraph_component.builder
        node = langgraph_component.nodes.get("model")
        return node is not None and hasattr(node.runnable, "get_graph")

    def _get_closure_cells(self, model_node: StateNodeSpec[Any, Any]) -> list[Any]:
        """Extract and return the cell contents from the function's closure, or raise if invalid."""
        runnable = getattr(model_node, "runnable", None)
        func = getattr(runnable, "func", None)
        if not isinstance(func, FunctionType) or func.__closure__ is None:
            raise ValueError("Unsupported runnable shape when extracting from closure")
        return [cl.cell_contents for cl in func.__closure__]

    def _extract_basechatmodel_from_model_node(
        self, model_node: StateNodeSpec[Any, Any]
    ) -> BaseChatModel:
        cells = self._get_closure_cells(model_node)
        return next(cl for cl in cells if isinstance(cl, BaseChatModel))

    def _extract_prompt_from_model_node(self, model_node: StateNodeSpec[Any, Any]) -> str:
        try:
            cells = self._get_closure_cells(model_node)
            system_message = next(cl for cl in cells if isinstance(cl, SystemMessage))
            return str(system_message.content)
        except (ValueError, StopIteration):
            return ""

    def _langgraph_server_tool_to_agentspec_tool(self, tool: StructuredTool) -> AgentSpecTool:
        return ServerTool(
            name=tool.name,
            description=tool.description,
            inputs=[
                Property(json_schema=property_json_schema, title=property_title)
                for property_title, property_json_schema in tool.args.items()
            ],
        )

    def _basechatmodel_convert_to_agentspec(self, model: BaseChatModel) -> AgentSpecLlmConfig:
        """
        Convert a LangChain BaseChatModel into the closest Agent Spec LLM config.
        """
        try:
            from langchain_oci import ChatOCIGenAI as _ChatOCIGenAI  # type: ignore
        except ImportError:
            _ChatOCIGenAI = None

        if _ChatOCIGenAI is not None and isinstance(model, _ChatOCIGenAI):
            auth_type = model.auth_type
            service_endpoint = model.service_endpoint
            if auth_type == "INSTANCE_PRINCIPAL":
                client_cfg: Any = AgentSpecOciClientConfigWithInstancePrincipal(
                    name="oci_client", service_endpoint=service_endpoint
                )
            elif auth_type == "RESOURCE_PRINCIPAL":
                client_cfg = AgentSpecOciClientConfigWithResourcePrincipal(
                    name="oci_client", service_endpoint=service_endpoint
                )
            elif auth_type == "API_KEY":
                client_cfg = AgentSpecOciClientConfigWithApiKey(
                    name="oci_client",
                    service_endpoint=service_endpoint,
                    auth_profile=model.auth_profile,
                    auth_file_location=model.auth_file_location,
                )
            elif auth_type == "SECURITY_TOKEN":
                client_cfg = AgentSpecOciClientConfigWithSecurityToken(
                    name="oci_client",
                    service_endpoint=service_endpoint,
                    auth_profile=model.auth_profile,
                    auth_file_location=model.auth_file_location,
                )
            else:
                raise ValueError(f"Unsupported OCI auth_type: {auth_type}")

            return AgentSpecOciGenAiConfig(
                name="oci",
                model_id=model.model_id,
                compartment_id=model.compartment_id,
                client_config=client_cfg,
                provider=AgentSpecModelProvider(model.provider.upper()) if model.provider else None,
                api_type=AgentSpecOciAPIType.OCI,
            )
        if isinstance(model, langchain_ollama.ChatOllama):
            return AgentSpecOllamaConfig(
                name=model.model,
                url=model.base_url or "",
                model_id=model.model,
            )
        if isinstance(model, langchain_openai.ChatOpenAI):
            api_type = (
                AgentSpecOpenAIAPIType.RESPONSES
                if model.use_responses_api
                else AgentSpecOpenAIAPIType.CHAT_COMPLETIONS
            )
            if (model.openai_api_base or "").startswith("https://api.openai.com"):
                return AgentSpecOpenAiConfig(
                    name=model.model_name, model_id=model.model_name, api_type=api_type
                )
            else:
                return AgentSpecOpenAiCompatibleConfig(
                    name=model.model_name,
                    url=model.openai_api_base or "",
                    model_id=model.model_name,
                    api_type=api_type,
                )
        raise ValueError(f"The LLM instance provided is of an unsupported type `{type(model)}`.")

    def _langgraph_agent_convert_to_agentspec(
        self,
        langgraph_component: LangGraphComponent,
        referenced_objects: Dict[str, AgentSpecComponent],
    ) -> AgentSpecAgent:
        if isinstance(langgraph_component, CompiledStateGraph):
            agent_name = langgraph_component.get_name()
        else:
            agent_name = "LangGraph Agent"
        if isinstance(langgraph_component, CompiledStateGraph):
            langgraph_component = langgraph_component.builder
        model_node = langgraph_component.nodes["model"]
        basechatmodel = self._extract_basechatmodel_from_model_node(model_node)
        if "tools" in langgraph_component.nodes:
            tool_node = langgraph_component.nodes["tools"]
            tools = self._extract_tools_from_react_agent(tool_node)
        else:
            tools = []
        return AgentSpecAgent(
            name=agent_name,
            llm_config=self._basechatmodel_convert_to_agentspec(basechatmodel),
            system_prompt=self._extract_prompt_from_model_node(model_node),
            tools=tools,
        )

    def _extract_tools_from_react_agent(
        self, langgraph_component: StateNodeSpec[Any, Any]
    ) -> List[AgentSpecTool]:
        tools = []
        if hasattr(langgraph_component, "runnable") and hasattr(
            langgraph_component.runnable, "tools_by_name"
        ):
            for tool_name, tool in langgraph_component.runnable.tools_by_name.items():
                tools.append(self._langgraph_any_tool_to_agentspec_tool(tool))
        return tools

    def _langgraph_any_tool_to_agentspec_tool(self, tool: StructuredTool) -> AgentSpecTool:
        agentspec_server_tool = self._langgraph_server_tool_to_agentspec_tool(tool)
        # Safely get the attribute and narrow its type (for mypy)
        coroutine = getattr(tool, "coroutine", None)
        if not isinstance(coroutine, FunctionType):
            return agentspec_server_tool
        if not coroutine.__closure__:
            return agentspec_server_tool
        closures_by_name = {
            name: cell.cell_contents
            for name, cell in zip(coroutine.__code__.co_freevars, coroutine.__closure__)
        }
        connection_dict = closures_by_name.get("connection")
        if not isinstance(connection_dict, dict) or "transport" not in connection_dict:
            return agentspec_server_tool
        # Cast to the expected TypedDict union for type checking
        client_transport = self._langgraph_mcp_connection_to_agentspec_client_transport(
            cast(
                Union["StdioConnection", "SSEConnection", "StreamableHttpConnection"],
                connection_dict,
            )
        )
        return AgentSpecMCPTool(
            name=agentspec_server_tool.name,
            description=agentspec_server_tool.description,
            inputs=agentspec_server_tool.inputs,
            client_transport=client_transport,
        )

    def _langgraph_mcp_connection_to_agentspec_client_transport(
        self,
        conn: "Union[StdioConnection, SSEConnection, StreamableHttpConnection]",
    ) -> ClientTransport:
        """
        Convert a LangGraph MCP connection dict into a ClientTransport.

        Expected conn shapes:
        - stdio:
            {
                "transport": "stdio",
                "command": "...",
                "args": [...],
                "env": {...},
                "cwd": "...",
                "session_kwargs": {
                    "read_timeout_seconds": datetime.timedelta(...) | int | float
                }
            }
        - sse:
            {
                "transport": "sse",
                "url": "...",
                "headers": {...},
                "httpx_client_factory": _HttpxClientFactory(...)
            }
        - streamable_http:
            {
                "transport": "streamable_http",
                "url": "...",
                "headers": {...},
                "httpx_client_factory": _HttpxClientFactory(...)
            }
        """

        if conn.get("httpx_client_factory"):
            raise NotImplementedError(
                "Conversion from langchain MCP connections with arbitrary httpx client factory objects is not yet implemented"
            )

        session_params = self._build_session_parameters(conn)

        # Below, we use `[]` for mandatory keys and `.get` for NotRequired keys, where c is a TypedDict

        if conn["transport"] == "stdio":
            cwd_str = str(conn.get("cwd"))
            return StdioTransport(
                name="agentspec_stdio_transport",
                command=conn["command"],
                args=conn["args"],
                env=conn.get("env"),
                cwd=cwd_str,
                session_parameters=session_params,
            )

        if conn["transport"] == "sse":
            return SSETransport(
                name="agentspec_sse_transport",
                url=conn["url"],
                headers=conn.get("headers"),
                session_parameters=session_params,
            )

        if conn["transport"] == "streamable_http":
            return StreamableHTTPTransport(
                name="agentspec_streamablehttp_transport",
                url=conn["url"],
                headers=conn.get("headers"),
                session_parameters=session_params,
            )

        raise ValueError(f'Unsupported transport: {conn["transport"]}')

    @staticmethod
    def _build_session_parameters(conn: Mapping[str, Any]) -> SessionParameters:
        session_kwargs = conn.get("session_kwargs", {}) or {}
        raw = session_kwargs.get("read_timeout_seconds")

        if isinstance(raw, datetime.timedelta):
            rts = raw.total_seconds()
        elif isinstance(raw, (int, float)):
            rts = float(raw)
        else:
            rts = None

        return SessionParameters() if rts is None else SessionParameters(read_timeout_seconds=rts)

    def _get_obj_reference(self, obj: Any) -> str:
        return f"{obj.__class__.__name__.lower()}/{id(obj)}"
