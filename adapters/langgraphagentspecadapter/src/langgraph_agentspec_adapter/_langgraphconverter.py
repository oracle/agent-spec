# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Any, Dict, List, Optional, cast
from uuid import uuid4

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph, RunnableConfig  # type: ignore[attr-defined]
from langgraph.prebuilt import create_react_agent
from langgraph.types import Checkpointer, interrupt
from pyagentspec import Component as AgentSpecComponent
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.node import Node as AgentSpecNode
from pyagentspec.flows.nodes import AgentNode as AgentSpecAgentNode
from pyagentspec.flows.nodes import ApiNode as AgentSpecApiNode
from pyagentspec.flows.nodes import BranchingNode as AgentSpecBranchingNode
from pyagentspec.flows.nodes import EndNode as AgentSpecEndNode
from pyagentspec.flows.nodes import FlowNode as AgentSpecFlowNode
from pyagentspec.flows.nodes import LlmNode as AgentSpecLlmNode
from pyagentspec.flows.nodes import MapNode as AgentSpecMapNode
from pyagentspec.flows.nodes import StartNode as AgentSpecStartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
from pyagentspec.llms.llmconfig import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.ollamaconfig import OllamaConfig
from pyagentspec.llms.openaiconfig import OpenAiConfig
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.tools import ClientTool as AgentSpecClientTool
from pyagentspec.tools import RemoteTool as AgentSpecRemoteTool
from pyagentspec.tools import ServerTool as AgentSpecServerTool
from pydantic import BaseModel, Field, SecretStr, create_model

from langgraph_agentspec_adapter._utils import (
    ControlFlow,
    FlowStateSchema,
    LangGraphComponent,
    LangGraphTool,
    NodeExecutor,
    render_template,
)


def _create_pydantic_model_from_properties(
    model_name: str, properties: List[AgentSpecProperty]
) -> type[BaseModel]:
    # Create a pydantic model whose attributes are the given properties
    fields: Dict[str, Any] = {}
    for property_ in properties:
        param_name = property_.title
        default = property_.default
        annotation = _json_schema_type_to_python_annotation(property_.json_schema)
        fields[param_name] = (annotation, Field(default=default))
    return cast(type[BaseModel], create_model(model_name, **fields))


def _json_schema_type_to_python_annotation(json_schema: Dict[str, Any]) -> str:
    if "anyOf" in json_schema:
        possible_types = set(
            _json_schema_type_to_python_annotation(inner_json_schema_type)
            for inner_json_schema_type in json_schema["anyOf"]
        )
        return f"Union[{','.join(possible_types)}]"
    if isinstance(json_schema["type"], list):
        possible_types = set(
            _json_schema_type_to_python_annotation(inner_json_schema_type)
            for inner_json_schema_type in json_schema["type"]
        )
        return f"Union[{','.join(possible_types)}]"

    if json_schema["type"] == "array":
        return f"List[{_json_schema_type_to_python_annotation(json_schema['items'])}]"
    mapping = {
        "string": "str",
        "number": "float",
        "integer": "int",
        "boolean": "bool",
        "null": "None",
        "object": "Dict[str, Any]",
    }

    return mapping.get(json_schema["type"], "Any")


class AgentSpecToLangGraphConverter:
    def convert(
        self,
        agentspec_component: AgentSpecComponent,
        tool_registry: Dict[str, LangGraphTool],
        converted_components: Optional[Dict[str, Any]] = None,
        checkpointer: Optional[Checkpointer] = None,
        config: Optional[RunnableConfig] = None,
    ) -> Any:
        """Convert the given PyAgentSpec component object into the corresponding LangGraph component"""
        if converted_components is None:
            converted_components = {}
        if checkpointer is None:
            checkpointer = InMemorySaver()
        if config is None:
            config = RunnableConfig({"configurable": {"thread_id": str(uuid4())}})
        if agentspec_component.id not in converted_components:
            converted_components[agentspec_component.id] = self._convert(
                agentspec_component,
                tool_registry,
                converted_components,
                checkpointer,
                config,
            )
        return converted_components[agentspec_component.id]

    def _convert(
        self,
        agentspec_component: AgentSpecComponent,
        tool_registry: Dict[str, LangGraphTool],
        converted_components: Dict[str, Any],
        checkpointer: Checkpointer,
        config: RunnableConfig,
    ) -> Any:
        if isinstance(agentspec_component, AgentSpecAgent):
            return self._agent_convert_to_langgraph(
                agentspec_component, tool_registry, converted_components, checkpointer
            )
        elif isinstance(agentspec_component, AgentSpecLlmConfig):
            return self._llm_convert_to_langgraph(agentspec_component)
        elif isinstance(agentspec_component, AgentSpecServerTool):
            return self._server_tool_convert_to_langgraph(agentspec_component, tool_registry)
        elif isinstance(agentspec_component, AgentSpecClientTool):
            return self._client_tool_convert_to_langgraph(agentspec_component)
        elif isinstance(agentspec_component, AgentSpecRemoteTool):
            return self._remote_tool_convert_to_langgraph(agentspec_component)
        elif isinstance(agentspec_component, AgentSpecFlow):
            return self._flow_convert_to_langgraph(
                agentspec_component,
                tool_registry,
                converted_components,
                checkpointer,
            )
        elif isinstance(agentspec_component, AgentSpecNode):
            return self._node_convert_to_langgraph(
                agentspec_component,
                tool_registry,
                checkpointer,
                config,
            )
        elif isinstance(agentspec_component, AgentSpecComponent):
            raise NotImplementedError(
                f"The Agent Spec type '{agentspec_component.__class__.__name__}' is not yet supported for conversion."
            )
        else:
            raise TypeError(
                f"Expected object of type 'pyagentspec.component.Component',"
                f" but got {type(agentspec_component)} instead"
            )

    def _create_control_flow(
        self, control_flow_connections: List[ControlFlowEdge]
    ) -> "ControlFlow":
        control_flow: "ControlFlow" = {}
        for control_flow_edge in control_flow_connections:
            source_node_id = control_flow_edge.from_node.id
            if source_node_id not in control_flow:
                control_flow[source_node_id] = {}

            branch_name = control_flow_edge.from_branch or AgentSpecBranchingNode.DEFAULT_BRANCH
            control_flow[source_node_id][branch_name] = control_flow_edge.to_node.id

        return control_flow

    def _add_conditional_edges_to_graph(
        self,
        control_flow: "ControlFlow",
        graph_builder: StateGraph["FlowStateSchema"],
    ) -> None:
        for source_node_id, control_flow_mapping in control_flow.items():
            get_branch = lambda state: state["node_execution_details"].get(
                "branch", AgentSpecBranchingNode.DEFAULT_BRANCH
            )
            graph_builder.add_conditional_edges(source_node_id, get_branch, control_flow_mapping)

    def _flow_convert_to_langgraph(
        self,
        flow: AgentSpecFlow,
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Checkpointer,
    ) -> "LangGraphComponent":
        from langgraph_agentspec_adapter._utils import FlowStateSchema

        graph_builder = StateGraph(FlowStateSchema)
        graph_builder.add_edge(START, flow.start_node.id)

        node_executors = {
            node.id: self.convert(node, tool_registry, converted_components) for node in flow.nodes
        }

        for node_id, node_executor in node_executors.items():
            graph_builder.add_node(node_id, node_executor)

            for data_flow_edge in flow.data_flow_connections or []:
                node_executors[data_flow_edge.source_node.id].attach_edge(data_flow_edge)

        control_flow: "ControlFlow" = self._create_control_flow(flow.control_flow_connections)
        self._add_conditional_edges_to_graph(control_flow, graph_builder)
        return graph_builder.compile(checkpointer=checkpointer)

    def _node_convert_to_langgraph(
        self,
        node: AgentSpecNode,
        tool_registry: Dict[str, "LangGraphTool"],
        checkpointer: Checkpointer,
        config: RunnableConfig,
    ) -> "NodeExecutor":
        if isinstance(node, AgentSpecStartNode):
            return self._start_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecEndNode):
            return self._end_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecToolNode):
            return self._tool_node_convert_to_langgraph(node, tool_registry)
        elif isinstance(node, AgentSpecLlmNode):
            return self._llm_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecAgentNode):
            return self._agent_node_convert_to_langgraph(node, tool_registry, checkpointer, config)
        elif isinstance(node, AgentSpecBranchingNode):
            return self._branching_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecApiNode):
            return self._api_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecFlowNode):
            return self._flow_node_convert_to_langgraph(node, tool_registry, checkpointer, config)
        elif isinstance(node, AgentSpecMapNode):
            return self._map_node_convert_to_langgraph(
                node,
                tool_registry,
                checkpointer,
                config,
            )
        else:
            raise NotImplementedError(
                f"The AgentSpec component of type {type(node)} is not yet supported for conversion"
            )

    def _map_node_convert_to_langgraph(
        self,
        map_node: AgentSpecMapNode,
        tool_registry: Dict[str, "LangGraphTool"],
        checkpointer: Checkpointer,
        config: RunnableConfig,
    ) -> "NodeExecutor":
        from langgraph_agentspec_adapter._langgraphconverter import AgentSpecToLangGraphConverter
        from langgraph_agentspec_adapter._utils import MapNodeExecutor

        subflow = AgentSpecToLangGraphConverter().convert(
            map_node.subflow, tool_registry, checkpointer=checkpointer
        )
        if not isinstance(subflow, CompiledStateGraph):
            raise TypeError("MapNodeExecutor can only be initialized with MapNode")

        return MapNodeExecutor(map_node, subflow, config)

    def _flow_node_convert_to_langgraph(
        self,
        flow_node: AgentSpecFlowNode,
        tool_registry: Dict[str, "LangGraphTool"],
        checkpointer: Checkpointer,
        config: RunnableConfig,
    ) -> "NodeExecutor":
        from langgraph_agentspec_adapter._langgraphconverter import AgentSpecToLangGraphConverter
        from langgraph_agentspec_adapter._utils import FlowNodeExecutor

        subflow = AgentSpecToLangGraphConverter().convert(
            flow_node.subflow, tool_registry, checkpointer=checkpointer
        )
        if not isinstance(subflow, CompiledStateGraph):
            raise TypeError("FlowNodeExecutor can only initialize FlowNode")

        return FlowNodeExecutor(
            flow_node,
            subflow,
            config,
        )

    def _api_node_convert_to_langgraph(self, api_node: AgentSpecApiNode) -> "NodeExecutor":
        from langgraph_agentspec_adapter._utils import ApiNodeExecutor

        return ApiNodeExecutor(api_node)

    def _branching_node_convert_to_langgraph(
        self, branching_node: AgentSpecBranchingNode
    ) -> "NodeExecutor":
        from langgraph_agentspec_adapter._utils import BranchingNodeExecutor

        return BranchingNodeExecutor(branching_node)

    def _agent_node_convert_to_langgraph(
        self,
        agent_node: AgentSpecAgentNode,
        tool_registry: Dict[str, "LangGraphTool"],
        checkpointer: Checkpointer,
        config: RunnableConfig,
    ) -> "NodeExecutor":
        from langgraph_agentspec_adapter._utils import AgentNodeExecutor

        agent = AgentSpecToLangGraphConverter().convert(
            agent_node, tool_registry, checkpointer=checkpointer
        )
        if not isinstance(agent, CompiledStateGraph):
            raise TypeError("AgentNodeExecutor can only execute AgentNode")
        return AgentNodeExecutor(agent_node, agent, config)

    def _llm_node_convert_to_langgraph(self, llm_node: AgentSpecLlmNode) -> "NodeExecutor":
        from langgraph_agentspec_adapter._utils import LlmNodeExecutor

        llm: BaseChatModel = AgentSpecToLangGraphConverter().convert(llm_node.llm_config, {})
        return LlmNodeExecutor(llm_node, llm)

    def _tool_node_convert_to_langgraph(
        self, tool_node: AgentSpecToolNode, tool_registry: Dict[str, "LangGraphTool"]
    ) -> "NodeExecutor":
        from langgraph_agentspec_adapter._utils import ToolNodeExecutor

        try:
            tool = tool_registry[tool_node.tool.name]
        except KeyError:
            raise RuntimeError(f"Tool {tool_node.tool.id} was not found in the tool registry.")

        return ToolNodeExecutor(tool_node, tool)

    def _end_node_convert_to_langgraph(self, end_node: AgentSpecEndNode) -> "NodeExecutor":
        from langgraph_agentspec_adapter._utils import EndNodeExecutor

        return EndNodeExecutor(end_node)

    def _start_node_convert_to_langgraph(self, start_node: AgentSpecStartNode) -> "NodeExecutor":
        from langgraph_agentspec_adapter._utils import StartNodeExecutor

        return StartNodeExecutor(start_node)

    def _remote_tool_convert_to_langgraph(
        self,
        remote_tool: AgentSpecRemoteTool,
    ) -> LangGraphTool:
        def _remote_tool(**kwargs: Any) -> Any:
            remote_tool_data = {k: render_template(v, kwargs) for k, v in remote_tool.data.items()}
            remote_tool_headers = {
                k: render_template(v, kwargs) for k, v in remote_tool.headers.items()
            }
            remote_tool_query_params = {
                k: render_template(v, kwargs) for k, v in remote_tool.query_params.items()
            }
            remote_tool_url = render_template(remote_tool.url, kwargs)
            response = httpx.request(
                method=remote_tool.http_method,
                url=remote_tool_url,
                params=remote_tool_query_params,
                data=remote_tool_data,
                headers=remote_tool_headers,
            )
            return response.json()

        # Use a Pydantic model for args_schema
        args_model = _create_pydantic_model_from_properties(
            f"{remote_tool.name}Args",
            remote_tool.inputs or [],
        )

        structured_tool = StructuredTool(
            name=remote_tool.name,
            description=remote_tool.description or "",
            args_schema=args_model,
            func=_remote_tool,
        )
        return structured_tool

    def _server_tool_convert_to_langgraph(
        self,
        agentspec_server_tool: AgentSpecServerTool,
        tool_registry: Dict[str, LangGraphTool],
    ) -> LangGraphTool:
        # Ensure the tool exists in the registry
        if agentspec_server_tool.name not in tool_registry:
            raise ValueError(
                f"The Agent Spec representation includes a tool '{agentspec_server_tool.name}' "
                f"but this tool does not appear in the tool registry"
            )

        tool_obj = tool_registry[agentspec_server_tool.name]

        # If it’s already a LangChain tool (StructuredTool or compatible), return as-is
        if isinstance(tool_obj, StructuredTool):
            return tool_obj

        # If it's a plain callable, wrap it with a Pydantic args schema
        if callable(tool_obj):
            # Use a Pydantic model (not a dict) for args_schema
            args_model = _create_pydantic_model_from_properties(
                f"{agentspec_server_tool.name}Args",
                agentspec_server_tool.inputs or [],
            )
            description = agentspec_server_tool.description or ""
            wrapped = StructuredTool(
                name=agentspec_server_tool.name,
                description=description,
                args_schema=args_model,  # model class, not a dict
                func=tool_obj,
            )
            return wrapped

        # Otherwise unsupported tool type
        raise TypeError(
            f"Unsupported tool type for '{agentspec_server_tool.name}': {type(tool_obj)}. "
            "Expected a callable or a StructuredTool."
        )

    def _client_tool_convert_to_langgraph(
        self, agentspec_client_tool: AgentSpecClientTool
    ) -> LangGraphTool:
        def client_tool(*args: Any, **kwargs: Any) -> Any:
            tool_request = {
                "type": "client_tool_request",
                "name": agentspec_client_tool.name,
                "description": agentspec_client_tool.description,
                "inputs": {
                    "args": args,
                    "kwargs": kwargs,
                },
            }
            response = interrupt(tool_request)
            return response

        # Use a Pydantic model for args_schema
        args_model = _create_pydantic_model_from_properties(
            f"{agentspec_client_tool.name}Args",
            agentspec_client_tool.inputs or [],
        )

        structured_tool = StructuredTool(
            name=agentspec_client_tool.name,
            description=agentspec_client_tool.description or "",
            args_schema=args_model,
            func=client_tool,
        )
        return structured_tool

    def _agent_convert_to_langgraph(
        self,
        agentspec_component: AgentSpecAgent,
        tool_registry: Dict[str, LangGraphTool],
        converted_components: Dict[str, Any],
        checkpointer: Checkpointer,
    ) -> CompiledStateGraph[Any, Any, Any]:
        if agentspec_component.llm_config is None:
            raise ValueError(
                f"LangGraph create_react_agent requires an LLM configuration, was ``None``"
            )
        model = self.convert(agentspec_component.llm_config, tool_registry, converted_components)
        tools = [
            self.convert(t, tool_registry, converted_components) for t in agentspec_component.tools
        ]
        prompt = SystemMessage(agentspec_component.system_prompt)
        output_model: Optional[type[BaseModel]] = None
        input_model: Optional[type[BaseModel]] = None

        if agentspec_component.inputs:
            input_model = _create_pydantic_model_from_properties(
                "AgentInputModel", agentspec_component.inputs
            )
        if agentspec_component.outputs:
            output_model = _create_pydantic_model_from_properties(
                "AgentOutputModel", agentspec_component.outputs
            )

        agent = create_react_agent(
            name=agentspec_component.name,
            model=model,
            tools=tools,
            prompt=prompt,
            checkpointer=checkpointer,
            response_format=output_model,
            state_schema=input_model,
        )
        return agent

    def _llm_convert_to_langgraph(self, llm_config: AgentSpecLlmConfig) -> BaseChatModel:
        """Create the LLM model object for the chosen llm configuration."""
        generation_config: Dict[str, Any] = {}
        generation_parameters = llm_config.default_generation_parameters

        if generation_parameters is not None:
            generation_config["temperature"] = generation_parameters.temperature
            generation_config["max_completion_tokens"] = generation_parameters.max_tokens
            generation_config["top_p"] = generation_parameters.top_p

        if isinstance(llm_config, VllmConfig):
            from urllib.parse import urljoin

            from langchain_openai import ChatOpenAI

            base_url = llm_config.url
            if not base_url.startswith("http://"):
                base_url = f"http://{base_url}"
            if "/v1" not in base_url:
                base_url = urljoin(base_url + "/", "v1")
            return ChatOpenAI(
                model=llm_config.model_id,
                name=llm_config.model_id,
                api_key=SecretStr("EMPTY"),
                base_url=base_url,
                **generation_config,
            )
        elif isinstance(llm_config, OllamaConfig):
            from langchain_ollama import ChatOllama

            generation_config = {
                "temperature": generation_config.get("temperature"),
                "num_predict": generation_config.get("max_completion_tokens"),
                "top_p": generation_config.get("top_p"),
            }
            return ChatOllama(
                base_url=llm_config.url,
                model=llm_config.model_id,
                **generation_config,
            )
        elif isinstance(llm_config, OpenAiConfig):
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=llm_config.model_id,
                **generation_config,
            )
        else:
            raise NotImplementedError(
                f"Llm model of type {llm_config.__class__.__name__} is not yet supported."
            )
