# Copyright © 2025 Oracle and/or its affiliates.
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
    CompiledStateGraph,
    LangGraphComponent,
    LangGraphLlmConfig,
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
from pyagentspec.llms import VllmConfig as AgentSpecVllmConfig
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

    def _extract_llm_config_from_runnables_closures(
        self, agent_node: StateNodeSpec[Any]
    ) -> LangGraphLlmConfig:
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
        if isinstance(model, langchain_openai.ChatOpenAI):
            model_type = "openaicompatible"
            model_name = model.model_name
            base_url = model.openai_api_base
            api_type: AgentSpecOpenAIAPIType
            if model.use_responses_api:
                api_type = AgentSpecOpenAIAPIType.RESPONSES
            else:
                api_type = AgentSpecOpenAIAPIType.CHAT_COMPLETIONS

            return LangGraphLlmConfig(
                model_type=model_type,
                model_name=model_name,
                base_url=base_url or "",
                api_type=api_type,
            )

        elif isinstance(model, langchain_ollama.ChatOllama):
            model_type = "ollama"
            model_name = model.model
            base_url = model.base_url

            return LangGraphLlmConfig(
                model_type=model_type,
                model_name=model_name,
                base_url=base_url or "",
            )

        else:
            raise ValueError(
                f"The LLM instance provided is of an unsupported type `{type(model)}`."
            )

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

    def _build_agentspec_llm_from_config(
        self, langgraph_llm_config: LangGraphLlmConfig
    ) -> AgentSpecLlmConfig:
        if langgraph_llm_config.model_type == "ollama":
            return AgentSpecOllamaConfig(
                name=langgraph_llm_config.model_name,
                url=langgraph_llm_config.base_url,
                model_id=langgraph_llm_config.model_name,
            )
        elif langgraph_llm_config.model_type == "vllm":
            return AgentSpecVllmConfig(
                name=langgraph_llm_config.model_name,
                url=langgraph_llm_config.base_url,
                model_id=langgraph_llm_config.model_name,
                api_type=langgraph_llm_config.api_type,
            )
        elif langgraph_llm_config.model_type == "openaicompatible":
            return AgentSpecOpenAiCompatibleConfig(
                name=langgraph_llm_config.model_name,
                url=langgraph_llm_config.base_url,
                model_id=langgraph_llm_config.model_name,
                api_type=langgraph_llm_config.api_type,
            )
        raise ValueError(
            f"The LLM instance provided is of an unsupported type `{langgraph_llm_config.model_type}`."
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
        llm_config = self._extract_llm_config_from_runnables_closures(agent_node)
        if "tools" in langgraph_component.nodes:
            tool_node = langgraph_component.nodes["tools"]
            tools = self._extract_tools_from_react_agent(tool_node)
        else:
            tools = []
        return AgentSpecAgent(
            name=agent_name,
            llm_config=self._build_agentspec_llm_from_config(llm_config),
            system_prompt=self._extract_prompt_from_react_agent_node(agent_node),
            tools=tools,
        )

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
