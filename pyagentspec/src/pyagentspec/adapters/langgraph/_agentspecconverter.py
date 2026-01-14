# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import datetime
from types import CellType, FunctionType
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from pyagentspec import Property
from pyagentspec.adapters.langgraph._agentspec_converter_flow import (
    _langgraph_graph_convert_to_agentspec,
)
from pyagentspec.adapters.langgraph._types import (
    BaseChatModel,
    CompiledStateGraph,
    LangGraphComponent,
    RunnableBinding,
    StateNodeSpec,
    StructuredTool,
    langchain_ollama,
    langchain_openai,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms import OllamaConfig as AgentSpecOllamaConfig
from pyagentspec.llms import OpenAiCompatibleConfig as AgentSpecOpenAiCompatibleConfig
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
    from langchain_mcp_adapters.sessions import (  # type: ignore
        SSEConnection,
        StdioConnection,
        StreamableHttpConnection,
    )


class LangGraphToAgentSpecConverter:
    def convert(
        self,
        langgraph_component: LangGraphComponent,
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
        langgraph_component: LangGraphComponent,
        referenced_objects: Dict[str, AgentSpecComponent],
    ) -> AgentSpecComponent:
        agentspec_component: Optional[AgentSpecComponent] = None
        if self._is_react_agent(langgraph_component):
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
        # Creating an agent with the `create_react_agent` creates a node with the key "agent"
        node = langgraph_component.nodes.get("agent")
        return node is not None and hasattr(node.runnable, "get_graph")

    def _extract_llm_model_from_runnables_closures(
        self, agent_node: StateNodeSpec[Any]
    ) -> BaseChatModel:
        nodes = cast(Any, agent_node.runnable).get_graph().nodes

        # The graph contains three nodes:
        # - call_model_input node
        # - the call_model Runnable node
        # - a call_model_output node
        # We can get the data that we want from the call_model Runnable node
        call_model_node = next(node for node in nodes.values() if node.name == "call_model")

        # Get the Runnable from the node
        runnable: Any = call_model_node.data

        # Extract variables that have been closed over in the `create_react_agent` function execution
        # Because the data related to the model's configuration has been wrapped in a runnable,
        # and isn't stored in a class's attributes for example
        closure: tuple[CellType, ...] = runnable.func.__closure__

        # Extract the instance of RunnableBinding which contains relevant information for the react agent
        model = next(cl.cell_contents.last for cl in closure if hasattr(cl.cell_contents, "last"))

        if isinstance(model, RunnableBinding):
            model = model.bound
        if not isinstance(model, BaseChatModel):
            raise ValueError(
                f"Expect to find a BaseChatModel in the agent_node, but found: {type(model)}"
            )
        return model

    def _extract_prompt_from_react_agent_node(
        self, langgraph_agent_node: StateNodeSpec[Any]
    ) -> str:
        # The agent_node's runnable corresponds to the `call_model` function, that contains the prompt somewhere
        call_model_function = langgraph_agent_node.runnable.func  # type: ignore
        # We get the cell contents of the last element of the `call_model` function closure,
        # which should contain the sequence of actions performed by the runnable (it's a runnable sequence)
        call_model_runnable_sequence = call_model_function.__closure__[-1].cell_contents
        # The first element of the function related to this runnable sequence is a Prompt (a runnable as well)
        # Getting the first element of its function closure will take us to the SystemMessage
        if call_model_runnable_sequence.first.func.__closure__ is None:
            # No system prompt was provided, we return empty string
            return ""
        system_message = call_model_runnable_sequence.first.func.__closure__[0].cell_contents
        # This system message contains the prompt we need
        return str(system_message.content)

    def _langgraph_server_tool_to_agentspec_tool(self, tool: StructuredTool) -> AgentSpecTool:
        return ServerTool(
            name=tool.name,
            description=tool.description,
            inputs=[
                Property(json_schema=property_json_schema, title=property_title)
                for property_title, property_json_schema in tool.args.items()
            ],
        )

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
        agent_node = langgraph_component.nodes["agent"]
        model_instance = self._extract_llm_model_from_runnables_closures(agent_node)
        if "tools" in langgraph_component.nodes:
            tool_node = langgraph_component.nodes["tools"]
            tools = self._extract_tools_from_react_agent(tool_node)
        else:
            tools = []
        return AgentSpecAgent(
            name=agent_name,
            llm_config=self._build_agentspec_llm_from_langgraph_model(model_instance),
            system_prompt=self._extract_prompt_from_react_agent_node(agent_node),
            tools=tools,
        )

    def _build_agentspec_llm_from_langgraph_model(self, model: BaseChatModel) -> AgentSpecLlmConfig:
        try:
            from langchain_oci import ChatOCIGenAI as _ChatOCIGenAI  # type: ignore
        except ImportError:
            _ChatOCIGenAI = None

        # Detect OCI first to handle subclasses of ChatOpenAI used in tests
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

            provider_raw = getattr(model, "provider", None)
            provider = None
            if isinstance(provider_raw, str):
                norm = provider_raw.strip().upper()
                for m in AgentSpecModelProvider:
                    if norm == m.name:
                        provider = m
                        break
                if provider is None:
                    raise NotImplementedError(
                        f"Unsupported OCI provider '{provider_raw}'. Please add a mapping to AgentSpecModelProvider."
                    )

            return AgentSpecOciGenAiConfig(
                name="oci",
                model_id=model.model_id,
                compartment_id=model.compartment_id,
                client_config=client_cfg,
                provider=provider,
                api_type=AgentSpecOciAPIType.OCI,
            )

        if isinstance(model, langchain_openai.ChatOpenAI):
            api_type: AgentSpecOpenAIAPIType
            if getattr(model, "use_responses_api", False):
                api_type = AgentSpecOpenAIAPIType.RESPONSES
            else:
                api_type = AgentSpecOpenAIAPIType.CHAT_COMPLETIONS
            return AgentSpecOpenAiCompatibleConfig(
                name=getattr(model, "model_name", "openai"),
                url=getattr(model, "openai_api_base", "") or "",
                model_id=getattr(model, "model_name", ""),
                api_type=api_type,
            )

        if isinstance(model, langchain_ollama.ChatOllama):
            return AgentSpecOllamaConfig(
                name=getattr(model, "model", "ollama"),
                url=getattr(model, "base_url", "") or "",
                model_id=getattr(model, "model", ""),
            )

        raise ValueError(f"Unsupported LLM instance type: {type(model)}")

    def _extract_tools_from_react_agent(
        self, langgraph_component: StateNodeSpec[Any, None]
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
        client_transport = self._langgraph_mcp_connection_to_agentspec_client_transport(
            connection_dict
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
        from langchain_mcp_adapters.sessions import (
            SSEConnection,
            StdioConnection,
            StreamableHttpConnection,
        )

        if conn.get("httpx_client_factory"):
            raise NotImplementedError(
                "Conversion from langchain MCP connections with arbitrary httpx client factory objects is not yet implemented"
            )

        session_params = self._build_session_parameters(conn)
        transport = conn["transport"]

        # Below, we use `[]` for mandatory keys and `.get` for NotRequired keys, where c is a TypedDict

        if transport == "stdio":
            c = cast(StdioConnection, conn)
            return StdioTransport(
                name="agentspec_stdio_transport",
                command=c["command"],
                args=c["args"],
                env=c.get("env"),
                cwd=c.get("cwd"),
                session_parameters=session_params,
            )

        if transport == "sse":
            c = cast(SSEConnection, conn)
            return SSETransport(
                name="agentspec_sse_transport",
                url=c["url"],
                headers=c.get("headers"),
                session_parameters=session_params,
            )

        if transport == "streamable_http":
            c = cast(StreamableHttpConnection, conn)
            return StreamableHTTPTransport(
                name="agentspec_streamablehttp_transport",
                url=c["url"],
                headers=c.get("headers"),
                session_parameters=session_params,
            )

        raise ValueError(f"Unsupported transport: {transport}")

    @staticmethod
    def _build_session_parameters(conn: Dict[str, Any]) -> SessionParameters:
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
