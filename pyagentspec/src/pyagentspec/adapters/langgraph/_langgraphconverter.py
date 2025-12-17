# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, create_model

from pyagentspec import Component as AgentSpecComponent
from pyagentspec.adapters._utils import render_template
from pyagentspec.adapters.langgraph._node_execution import NodeExecutor
from pyagentspec.adapters.langgraph._types import (
    BaseCallbackHandler,
    BaseChatModel,
    Checkpointer,
    CompiledStateGraph,
    ControlFlow,
    FlowInputSchema,
    FlowOutputSchema,
    FlowStateSchema,
    LangGraphTool,
    RunnableConfig,
    StateGraph,
    StructuredTool,
    SystemMessage,
    interrupt,
    langgraph_graph,
    langgraph_prebuilt,
)
from pyagentspec.adapters.langgraph.tracing import AgentSpecCallbackHandler
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.node import Node as AgentSpecNode
from pyagentspec.flows.nodes import AgentNode as AgentSpecAgentNode
from pyagentspec.flows.nodes import ApiNode as AgentSpecApiNode
from pyagentspec.flows.nodes import BranchingNode as AgentSpecBranchingNode
from pyagentspec.flows.nodes import EndNode as AgentSpecEndNode
from pyagentspec.flows.nodes import FlowNode as AgentSpecFlowNode
from pyagentspec.flows.nodes import InputMessageNode as AgentSpecInputMessageNode
from pyagentspec.flows.nodes import LlmNode as AgentSpecLlmNode
from pyagentspec.flows.nodes import MapNode as AgentSpecMapNode
from pyagentspec.flows.nodes import OutputMessageNode as AgentSpecOutputMessageNode
from pyagentspec.flows.nodes import StartNode as AgentSpecStartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
from pyagentspec.llms.llmconfig import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.ollamaconfig import OllamaConfig
from pyagentspec.llms.openaicompatibleconfig import OpenAIAPIType, OpenAiCompatibleConfig
from pyagentspec.llms.openaiconfig import OpenAiConfig
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import DictProperty as AgentSpecDictProperty
from pyagentspec.property import IntegerProperty as AgentSpecIntegerProperty
from pyagentspec.property import ListProperty as AgentSpecListProperty
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import _empty_default as _agentspec_empty_default
from pyagentspec.property import json_schemas_have_same_type
from pyagentspec.tools import ClientTool as AgentSpecClientTool
from pyagentspec.tools import RemoteTool as AgentSpecRemoteTool
from pyagentspec.tools import ServerTool as AgentSpecServerTool
from pyagentspec.tools import Tool as AgentSpecTool


class SchemaRegistry:
    def __init__(self) -> None:
        self.models: Dict[str, type[BaseModel]] = {}


def _build_type_from_schema(
    name: str,
    schema: Dict[str, Any],
    registry: SchemaRegistry,
) -> Any:
    # Enum -> Literal[…]
    if "enum" in schema and isinstance(schema["enum"], list):
        values = schema["enum"]
        # Literal supports a tuple of literal values as a single subscription argument
        return Literal[tuple(values)]

    # anyOf / oneOf -> Union[…]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            variants = [
                _build_type_from_schema(f"{name}Alt{i}", s, registry)
                for i, s in enumerate(schema[key])
            ]
            return Union[tuple(variants)]

    t = schema.get("type")

    # list of types -> Union[…]
    if isinstance(t, list):
        variants = [
            _build_type_from_schema(f"{name}Alt{i}", {"type": subtype}, registry)
            for i, subtype in enumerate(t)
        ]
        return Union[tuple(variants)]

    # arrays
    if t == "array":
        items_schema = schema.get("items", {"type": "any"})
        item_type = _build_type_from_schema(f"{name}Item", items_schema, registry)
        return List[item_type]  # type: ignore
    # objects
    if t == "object" or ("properties" in schema or "required" in schema):
        # Create or reuse a Pydantic model for this object schema
        model_name = schema.get("title") or name
        unique_name = model_name
        suffix = 1
        while unique_name in registry.models:
            suffix += 1
            unique_name = f"{model_name}_{suffix}"

        props = schema.get("properties", {}) or {}
        required = set(schema.get("required", []))

        fields: Dict[str, Tuple[Any, Any]] = {}
        for prop_name, prop_schema in props.items():
            prop_type = _build_type_from_schema(f"{unique_name}_{prop_name}", prop_schema, registry)
            desc = prop_schema.get("description")
            default_field = (
                Field(..., description=desc)
                if prop_name in required
                else Field(None, description=desc)
            )
            fields[prop_name] = (prop_type, default_field)

        # Enforce additionalProperties: False (extra=forbid)
        extra_forbid = schema.get("additionalProperties") is False
        model_kwargs: Dict[str, Any] = {}
        if extra_forbid:
            # Pydantic v2: pass a ConfigDict/dict into __config__
            model_kwargs["__config__"] = ConfigDict(extra="forbid")

        model_cls = create_model(unique_name, **fields, **model_kwargs)  # type: ignore
        registry.models[unique_name] = model_cls
        return model_cls

    # primitives / fallback
    mapping = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "null": type(None),
        "any": Any,
        None: Any,
        "": Any,
    }
    return mapping.get(t, Any)


def _create_pydantic_model_from_properties(
    model_name: str, properties: List[AgentSpecProperty]
) -> type[BaseModel]:
    registry = SchemaRegistry()
    fields: Dict[str, Tuple[Any, Any]] = {}

    for property_ in properties:
        # Build the annotation from the json_schema (handles enum/array/object/etc.)
        annotation = _build_type_from_schema(property_.title, property_.json_schema, registry)

        field_params: Dict[str, Any] = {}
        if property_.description:
            field_params["description"] = property_.description

        if property_.default is not _agentspec_empty_default:
            default_field = Field(property_.default, **field_params)
        else:
            default_field = Field(..., **field_params)

        fields[property_.title] = (annotation, default_field)

    return create_model(model_name, **fields)  # type: ignore


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
        if config is None:
            if checkpointer is not None:
                config = RunnableConfig({"configurable": {"thread_id": str(uuid4())}})
            else:
                config = RunnableConfig({})
        if agentspec_component.id not in converted_components:
            converted_components[agentspec_component.id] = self._convert(
                agentspec_component, tool_registry, converted_components, checkpointer, config
            )
        return converted_components[agentspec_component.id]

    def _convert(
        self,
        agentspec_component: AgentSpecComponent,
        tool_registry: Dict[str, LangGraphTool],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> Any:
        if isinstance(agentspec_component, AgentSpecAgent):
            callback = AgentSpecCallbackHandler(
                llm_config=agentspec_component.llm_config,
                tools=agentspec_component.tools,
            )
            config_with_callbacks = _add_callback_to_runnable_config(callback, config)
            return self._agent_convert_to_langgraph(
                agentspec_component,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config_with_callbacks,
            )
        elif isinstance(agentspec_component, AgentSpecLlmConfig):
            return self._llm_convert_to_langgraph(agentspec_component, config=config)
        elif isinstance(agentspec_component, AgentSpecServerTool):
            return self._server_tool_convert_to_langgraph(
                agentspec_component, tool_registry, config=config
            )
        elif isinstance(agentspec_component, AgentSpecClientTool):
            if checkpointer is None:
                raise ValueError(
                    "A Checkpointer must be provided when the Agent Spec configuration contains client tools"
                )
            return self._client_tool_convert_to_langgraph(agentspec_component)
        elif isinstance(agentspec_component, AgentSpecRemoteTool):
            return self._remote_tool_convert_to_langgraph(agentspec_component, config=config)
        elif isinstance(agentspec_component, AgentSpecFlow):
            return self._flow_convert_to_langgraph(
                agentspec_component,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
        elif isinstance(agentspec_component, AgentSpecNode):
            return self._node_convert_to_langgraph(
                agentspec_component,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
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

            branch_name = control_flow_edge.from_branch or AgentSpecNode.DEFAULT_NEXT_BRANCH
            control_flow[source_node_id][branch_name] = control_flow_edge.to_node.id

        return control_flow

    def _add_conditional_edges_to_graph(
        self,
        control_flow: "ControlFlow",
        graph_builder: StateGraph["FlowStateSchema", None, "FlowInputSchema", "FlowOutputSchema"],
    ) -> None:
        for source_node_id, control_flow_mapping in control_flow.items():
            get_branch = lambda state: state["node_execution_details"].get(
                "branch", AgentSpecNode.DEFAULT_NEXT_BRANCH
            )
            graph_builder.add_conditional_edges(source_node_id, get_branch, control_flow_mapping)

    def _flow_convert_to_langgraph(
        self,
        flow: AgentSpecFlow,
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> CompiledStateGraph[Any, Any, Any]:

        graph_builder = StateGraph(
            FlowStateSchema, input_schema=FlowInputSchema, output_schema=FlowOutputSchema
        )
        graph_builder.add_edge(langgraph_graph.START, flow.start_node.id)

        node_executors = {
            node.id: self.convert(
                node,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
            for node in flow.nodes
        }

        def _find_property(properties: List[AgentSpecProperty], name: str) -> AgentSpecProperty:
            return next((property_ for property_ in properties if property_.title == name))

        # We tell the MapNodes which inputs they should iterate over
        # Based on the type of the outputs they are connected to
        for agentspec_node in flow.nodes:
            if isinstance(agentspec_node, AgentSpecMapNode):
                inputs_to_iterate = []
                for data_flow_edge in flow.data_flow_connections or []:
                    if data_flow_edge.destination_node is agentspec_node:
                        source_property = _find_property(
                            data_flow_edge.source_node.outputs or [],
                            data_flow_edge.source_output,
                        )
                        inner_flow_input_property = _find_property(
                            agentspec_node.subflow.inputs or [],
                            data_flow_edge.destination_input.replace("iterated_", "", 1),
                        )
                        if json_schemas_have_same_type(
                            source_property.json_schema,
                            AgentSpecListProperty(item_type=inner_flow_input_property).json_schema,
                        ):
                            inputs_to_iterate.append(data_flow_edge.destination_input)
                node_executors[agentspec_node.id].set_inputs_to_iterate(inputs_to_iterate)
            elif isinstance(agentspec_node, AgentSpecEndNode):
                node_executors[agentspec_node.id].set_flow_outputs(flow.outputs)

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
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> "NodeExecutor":
        if isinstance(node, AgentSpecStartNode):
            return self._start_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecEndNode):
            return self._end_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecToolNode):
            return self._tool_node_convert_to_langgraph(
                node,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
        elif isinstance(node, AgentSpecLlmNode):
            return self._llm_node_convert_to_langgraph(
                node,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
        elif isinstance(node, AgentSpecAgentNode):
            return self._agent_node_convert_to_langgraph(
                node,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
        elif isinstance(node, AgentSpecBranchingNode):
            return self._branching_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecApiNode):
            return self._api_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecFlowNode):
            return self._flow_node_convert_to_langgraph(
                node,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
        elif isinstance(node, AgentSpecInputMessageNode):
            return self._input_message_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecOutputMessageNode):
            return self._output_message_node_convert_to_langgraph(node)
        elif isinstance(node, AgentSpecMapNode):
            return self._map_node_convert_to_langgraph(
                node,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
        else:
            raise NotImplementedError(
                f"The AgentSpec component of type {type(node)} is not yet supported for conversion"
            )

    def _input_message_node_convert_to_langgraph(
        self,
        node: AgentSpecInputMessageNode,
    ) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import InputMessageNodeExecutor

        return InputMessageNodeExecutor(node)

    def _output_message_node_convert_to_langgraph(
        self,
        node: AgentSpecOutputMessageNode,
    ) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import OutputMessageNodeExecutor

        return OutputMessageNodeExecutor(node)

    def _map_node_convert_to_langgraph(
        self,
        map_node: AgentSpecMapNode,
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
        from pyagentspec.adapters.langgraph._node_execution import MapNodeExecutor

        subflow = AgentSpecToLangGraphConverter().convert(
            map_node.subflow,
            tool_registry=tool_registry,
            converted_components=converted_components,
            checkpointer=checkpointer,
            config=config,
        )
        if not isinstance(subflow, CompiledStateGraph):
            raise TypeError("MapNodeExecutor can only be initialized with MapNode")

        return MapNodeExecutor(map_node, subflow, config)

    def _flow_node_convert_to_langgraph(
        self,
        flow_node: AgentSpecFlowNode,
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
        from pyagentspec.adapters.langgraph._node_execution import FlowNodeExecutor

        subflow = AgentSpecToLangGraphConverter().convert(
            flow_node.subflow,
            tool_registry=tool_registry,
            converted_components=converted_components,
            checkpointer=checkpointer,
            config=config,
        )
        if not isinstance(subflow, CompiledStateGraph):
            raise TypeError("FlowNodeExecutor can only initialize FlowNode")

        return FlowNodeExecutor(
            flow_node,
            subflow,
            config,
        )

    def _api_node_convert_to_langgraph(self, api_node: AgentSpecApiNode) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import ApiNodeExecutor

        return ApiNodeExecutor(api_node)

    def _branching_node_convert_to_langgraph(
        self, branching_node: AgentSpecBranchingNode
    ) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import BranchingNodeExecutor

        return BranchingNodeExecutor(branching_node)

    def _agent_node_convert_to_langgraph(
        self,
        agent_node: AgentSpecAgentNode,
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import AgentNodeExecutor

        return AgentNodeExecutor(
            agent_node,
            tool_registry=tool_registry,
            converted_components=converted_components,
            checkpointer=checkpointer,
            config=config,
        )

    def _llm_node_convert_to_langgraph(
        self,
        llm_node: AgentSpecLlmNode,
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import LlmNodeExecutor

        llm: BaseChatModel = self.convert(
            llm_node.llm_config,
            tool_registry=tool_registry,
            converted_components=converted_components,
            checkpointer=checkpointer,
            config=config,
        )
        return LlmNodeExecutor(llm_node, llm)

    def _tool_node_convert_to_langgraph(
        self,
        tool_node: AgentSpecToolNode,
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import ToolNodeExecutor

        tool = self.convert(
            tool_node.tool,
            tool_registry=tool_registry,
            converted_components=converted_components,
            checkpointer=checkpointer,
            config=config,
        )

        return ToolNodeExecutor(tool_node, tool)

    def _end_node_convert_to_langgraph(self, end_node: AgentSpecEndNode) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import EndNodeExecutor

        return EndNodeExecutor(end_node)

    def _start_node_convert_to_langgraph(self, start_node: AgentSpecStartNode) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import StartNodeExecutor

        return StartNodeExecutor(start_node)

    def _remote_tool_convert_to_langgraph(
        self,
        remote_tool: AgentSpecRemoteTool,
        config: RunnableConfig,
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
                json=remote_tool_data,
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
            callbacks=config.get("callbacks"),
        )
        return structured_tool

    def _server_tool_convert_to_langgraph(
        self,
        agentspec_server_tool: AgentSpecServerTool,
        tool_registry: Dict[str, LangGraphTool],
        config: RunnableConfig,
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
                callbacks=config.get("callbacks"),
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

    def _create_react_agent_with_given_info(
        self,
        name: str,
        system_prompt: str,
        llm_config: AgentSpecLlmConfig,
        tools: List[AgentSpecTool],
        inputs: List[AgentSpecProperty],
        outputs: List[AgentSpecProperty],
        tool_registry: Dict[str, LangGraphTool],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> CompiledStateGraph[Any, Any, Any]:
        model = self.convert(
            llm_config,
            tool_registry=tool_registry,
            converted_components=converted_components,
            checkpointer=checkpointer,
            config=config,
        )
        langgraph_tools = [
            self.convert(
                t,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
            for t in tools
        ]
        prompt = SystemMessage(system_prompt)
        output_model: Optional[type[BaseModel]] = None
        input_model: Optional[type[BaseModel]] = None

        if inputs:
            input_model = _create_pydantic_model_from_properties(
                "AgentInputModel",
                inputs
                + [
                    # Properties required by langgraph
                    AgentSpecIntegerProperty(title="remaining_steps"),
                    AgentSpecListProperty(title="messages", item_type=AgentSpecProperty()),
                ]
                + (
                    [
                        AgentSpecDictProperty(
                            title="structured_response", value_type=AgentSpecProperty()
                        )
                    ]
                    if outputs
                    else []
                ),
            )

        if outputs:
            output_model = _create_pydantic_model_from_properties("AgentOutputModel", outputs)

        return langgraph_prebuilt.create_react_agent(
            name=name,
            model=model,
            tools=langgraph_tools,
            prompt=prompt,
            checkpointer=checkpointer,
            response_format=output_model,
            state_schema=input_model,
        )

    def _agent_convert_to_langgraph(
        self,
        agentspec_component: AgentSpecAgent,
        tool_registry: Dict[str, LangGraphTool],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> CompiledStateGraph[Any, Any, Any]:
        return self._create_react_agent_with_given_info(
            name=agentspec_component.name,
            system_prompt=agentspec_component.system_prompt,
            llm_config=agentspec_component.llm_config,
            tools=agentspec_component.tools,
            inputs=agentspec_component.inputs or [],
            outputs=agentspec_component.outputs or [],
            tool_registry=tool_registry,
            converted_components=converted_components,
            checkpointer=checkpointer,
            config=config,
        )

    def _llm_convert_to_langgraph(
        self, llm_config: AgentSpecLlmConfig, config: RunnableConfig
    ) -> BaseChatModel:
        """Create the LLM model object for the chosen llm configuration."""
        generation_config: Dict[str, Any] = {}
        generation_parameters = llm_config.default_generation_parameters

        if generation_parameters is not None:
            generation_config["temperature"] = generation_parameters.temperature
            generation_config["max_completion_tokens"] = generation_parameters.max_tokens
            generation_config["top_p"] = generation_parameters.top_p

        use_responses_api = False
        if isinstance(llm_config, (OpenAiCompatibleConfig, OpenAiConfig)):
            use_responses_api = llm_config.api_type == OpenAIAPIType.RESPONSES

        if isinstance(llm_config, VllmConfig):
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=llm_config.model_id,
                api_key=SecretStr("EMPTY"),
                base_url=_prepare_openai_compatible_url(llm_config.url),
                use_responses_api=use_responses_api,
                callbacks=config.get("callbacks"),
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
                callbacks=config.get("callbacks"),
                **generation_config,
            )
        elif isinstance(llm_config, OpenAiConfig):
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=llm_config.model_id,
                use_responses_api=use_responses_api,
                callbacks=config.get("callbacks"),
                **generation_config,
            )
        elif isinstance(llm_config, OpenAiCompatibleConfig):
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=llm_config.model_id,
                base_url=_prepare_openai_compatible_url(llm_config.url),
                use_responses_api=use_responses_api,
                callbacks=config.get("callbacks"),
                **generation_config,
            )
        else:
            raise NotImplementedError(
                f"Llm model of type {llm_config.__class__.__name__} is not yet supported."
            )


def _prepare_openai_compatible_url(url: str) -> str:
    """
    Correctly formats a URL for an OpenAI-compatible server.

    This function is robust and handles multiple formats:
    - Ensures a scheme (http, https) is present, defaulting to 'http'.
    - Replaces any existing path with exactly '/v1'.

    Examples:
        - "localhost:8000"          -> "http://localhost:8000/v1"
        - "127.0.0.1:5000"          -> "http://127.0.0.1:5000/v1"
        - "https://api.example.com"   -> "https://api.example.com/v1"
        - "http://my-host/api/v2"   -> "http://my-host/v1"
    """
    from urllib.parse import urlparse, urlunparse

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    parsed_url = urlparse(url)
    # parsed_url is a namedtuple object, and it has the _replace method
    # this is actually a public facing method, check python documentation of namedtuple
    v1_url_parts = parsed_url._replace(path="/v1", params="", query="", fragment="")
    final_url = urlunparse(v1_url_parts)

    return str(final_url)


def _add_callback_to_runnable_config(
    callback: BaseCallbackHandler, config: RunnableConfig
) -> RunnableConfig:
    callbacks = [callback]
    existing_callbacks = config.get("callbacks")
    if not existing_callbacks:
        existing_callbacks = []
    if isinstance(existing_callbacks, list):
        existing_callbacks = existing_callbacks + callbacks
    config_with_callbacks = RunnableConfig({**config, "callbacks": existing_callbacks})
    return config_with_callbacks
