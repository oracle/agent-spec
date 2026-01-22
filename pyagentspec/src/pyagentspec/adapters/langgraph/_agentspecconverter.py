# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import datetime
from types import FunctionType, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
    cast,
    get_args,
    get_origin,
)

from typing_extensions import Literal

from pyagentspec import Property
from pyagentspec.adapters.langgraph._agentspec_converter_flow import (
    _langgraph_graph_convert_to_agentspec,
)
from pyagentspec.adapters.langgraph._types import (
    BaseChatModel,
    CompiledStateGraph,
    LangGraphComponent,
    LangGraphLlmConfig,
    StateNodeSpec,
    StructuredTool,
    SystemMessage,
    langchain_ollama,
    langchain_openai,
    langgraph_graph,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.agenticcomponent import AgenticComponent as AgentSpecAgenticComponent
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
from pyagentspec.swarm import HandoffMode as AgentSpecHandoffMode
from pyagentspec.swarm import Swarm as AgentSpecSwarm
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
        if self._is_swarm(langgraph_component):
            agentspec_component = self._langgraph_swarm_convert_to_agentspec(
                langgraph_component, referenced_objects
            )
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

    def _is_swarm(self, langgraph_component: LangGraphComponent) -> bool:
        builder = (
            langgraph_component.builder
            if isinstance(langgraph_component, CompiledStateGraph)
            else langgraph_component
        )

        branches = getattr(builder, "branches", None)
        state_schema = getattr(builder, "state_schema", None)

        if not branches or not state_schema:
            return False

        annotations = getattr(state_schema, "__annotations__", {}) or {}
        if "active_agent" not in annotations:
            return False

        start_branches = branches.get(langgraph_graph.START, {})
        if not isinstance(start_branches, dict):
            return False

        for branch_spec in start_branches.values():
            path = getattr(branch_spec, "path", None)
            func = getattr(path, "func", None)
            if getattr(func, "__name__", "") == "route_to_active_agent":
                return True

        return False

    def _extract_llm_config_from_runnables_closures(
        self, model_node: StateNodeSpec[Any, Any]
    ) -> LangGraphLlmConfig:
        # Extract variables that have been closed over in the `create_agent` function execution
        # Because the data related to the model's configuration has been wrapped in a runnable,
        # and isn't stored in a class's attributes for example
        # Extract the instance of RunnableBinding which contains relevant information for the react agent
        runnable = getattr(model_node, "runnable", None)
        func = getattr(runnable, "func", None)
        if not isinstance(func, FunctionType) or func.__closure__ is None:
            raise ValueError("Unsupported runnable shape when extracting LLM config")

        model = next(
            cl.cell_contents
            for cl in func.__closure__
            if isinstance(cl.cell_contents, BaseChatModel)
        )

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
        self, langgraph_model_node: StateNodeSpec[Any, Any]
    ) -> str:
        # The agent_node's runnable corresponds to the `call_model` function, that contains the prompt somewhere
        runnable = getattr(langgraph_model_node, "runnable", None)
        call_model_function = getattr(runnable, "func", None)
        if (
            not isinstance(call_model_function, FunctionType)
            or call_model_function.__closure__ is None
        ):
            return ""
        # We get the cell contents of the last element of the `call_model` function closure,
        # which should contain the sequence of actions performed by the runnable (it's a runnable sequence)
        try:
            system_message = next(
                cl.cell_contents
                for cl in call_model_function.__closure__
                if isinstance(cl.cell_contents, SystemMessage)
            )
            # This system message contains the prompt we need
            return str(system_message.content)
        except StopIteration:
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
        model_node = langgraph_component.nodes["model"]
        llm_config = self._extract_llm_config_from_runnables_closures(model_node)
        if "tools" in langgraph_component.nodes:
            tool_node = langgraph_component.nodes["tools"]
            tools = self._extract_tools_from_react_agent(tool_node)
        else:
            tools = []
        return AgentSpecAgent(
            name=agent_name,
            llm_config=self._build_agentspec_llm_from_config(llm_config),
            system_prompt=self._extract_prompt_from_react_agent_node(model_node),
            tools=tools,
        )

    def _langgraph_swarm_convert_to_agentspec(
        self,
        langgraph_component: LangGraphComponent,
        referenced_objects: Dict[str, AgentSpecComponent],
    ) -> AgentSpecSwarm:
        if isinstance(langgraph_component, CompiledStateGraph):
            compiled_swarm = langgraph_component
            graph = langgraph_component.get_graph()
        else:
            compiled_swarm = langgraph_component.compile()
            graph = compiled_swarm.get_graph()

        if "__start__" not in graph.nodes:
            raise ValueError("LangGraph swarm graph does not contain a start node")

        start_node = graph.nodes["__start__"].data
        swarm_state_schema = compiled_swarm.builder.state_schema

        active_agent_annotation = getattr(swarm_state_schema, "__annotations__", {}).get(
            "active_agent"
        )
        if active_agent_annotation is None:
            raise ValueError("Unable to detect active agent annotation in LangGraph swarm state")

        agent_names = self._extract_agent_names_from_annotation(active_agent_annotation)

        if not agent_names:
            raise ValueError("No agent names detected in LangGraph swarm")

        agents: Dict[str, AgentSpecAgenticComponent] = {}
        for agent_name in agent_names:
            node = graph.nodes.get(agent_name)
            if node is None:
                raise ValueError(f"Agent '{agent_name}' not found in LangGraph swarm graph")

            agent_graph = getattr(node, "data", None)
            if not isinstance(agent_graph, CompiledStateGraph):
                raise ValueError(f"Swarm node '{agent_name}' is not a CompiledStateGraph")

            agents[agent_name] = self.convert(agent_graph, referenced_objects)  # type: ignore

        relationships: List[Tuple[AgentSpecAgenticComponent, AgentSpecAgenticComponent]] = []
        for agent_name in agent_names:
            destinations = self._extract_handoff_destinations(graph, agent_name)
            for destination in destinations:
                if destination not in agents:
                    continue
                relationships.append((agents[agent_name], agents[destination]))

        first_agent_name = getattr(start_node, "destinations", [None])[0]
        if first_agent_name is None and agent_names:
            first_agent_name = agent_names[0]

        if first_agent_name is None:
            raise ValueError("Unable to determine first agent for LangGraph swarm")

        return AgentSpecSwarm(
            name=(
                compiled_swarm.get_name()
                if isinstance(langgraph_component, CompiledStateGraph)
                else "LangGraph Swarm"
            ),
            first_agent=agents[first_agent_name],
            relationships=relationships,
            handoff=AgentSpecHandoffMode.OPTIONAL,
        )

    def _extract_agent_names_from_annotation(self, annotation: Any) -> List[str]:
        origin = get_origin(annotation)

        if origin in {Union, UnionType}:
            names: List[str] = []
            for arg in get_args(annotation):
                if arg is type(None):
                    continue
                names.extend(self._extract_agent_names_from_annotation(arg))
            return names

        if origin is Literal:
            names = []
            for arg in get_args(annotation):
                if arg is type(None):
                    continue
                if not isinstance(arg, str):
                    raise ValueError(
                        "Unsupported Literal value for swarm conversion. Expected string agent name."
                    )
                names.append(arg)
            return names

        if isinstance(annotation, str):
            return [annotation]

        if isinstance(annotation, type) and issubclass(annotation, str):
            raise ValueError("Unsupported active agent annotation for swarm conversion: plain str")

        raise ValueError("Unsupported active agent annotation for swarm conversion")

    def _extract_handoff_destinations(self, graph: Any, agent_name: str) -> List[str]:
        edges = getattr(graph, "edges", [])
        destinations: List[str] = []
        for edge in edges:
            if getattr(edge, "source", None) == agent_name:
                target = getattr(edge, "target", None)
                if target is not None and not str(target).startswith("__"):
                    destinations.append(target)
        return destinations

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
