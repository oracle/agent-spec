# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import logging
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    TypeGuard,
    Union,
    cast,
)
from uuid import uuid4

from pydantic import BaseModel, SecretStr
from typing_extensions import NotRequired, Required

from pyagentspec import Component as AgentSpecComponent
from pyagentspec.adapters._tools_common import _create_remote_tool_func
from pyagentspec.adapters._utils import (
    SchemaRegistry,
    _build_type_from_schema,
    create_pydantic_model_from_properties,
)
from pyagentspec.adapters.langgraph._node_execution import (
    NodeExecutor,
    extract_outputs_from_invoke_result,
)
from pyagentspec.adapters.langgraph._types import (
    AgentState,
    BaseCallbackHandler,
    BaseChatModel,
    BaseTool,
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
    interrupt,
    langchain_agents,
    langgraph_graph,
)
from pyagentspec.adapters.langgraph.mcp_utils import _HttpxClientFactory, run_async_in_sync
from pyagentspec.adapters.langgraph.tracing import (
    AgentSpecLlmCallbackHandler,
    AgentSpecToolCallbackHandler,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.flows.edges import ControlFlowEdge as AgentSpecControlFlowEdge
from pyagentspec.flows.edges import DataFlowEdge as AgentSpecDataFlowEdge
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.node import Node as AgentSpecNode
from pyagentspec.flows.nodes import AgentNode as AgentSpecAgentNode
from pyagentspec.flows.nodes import ApiNode as AgentSpecApiNode
from pyagentspec.flows.nodes import BranchingNode as AgentSpecBranchingNode
from pyagentspec.flows.nodes import CatchExceptionNode as AgentSpecCatchExceptionNode
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
from pyagentspec.mcp.clienttransport import ClientTransport as AgentSpecClientTransport
from pyagentspec.mcp.clienttransport import SSEmTLSTransport as AgentSpecSSEmTLSTransport
from pyagentspec.mcp.clienttransport import SSETransport as AgentSpecSSETransport
from pyagentspec.mcp.clienttransport import StdioTransport as AgentSpecStdioTransport
from pyagentspec.mcp.clienttransport import (
    StreamableHTTPmTLSTransport as AgentSpecStreamableHTTPmTLSTransport,
)
from pyagentspec.mcp.clienttransport import (
    StreamableHTTPTransport as AgentSpecStreamableHTTPTransport,
)
from pyagentspec.mcp.tools import MCPTool as AgentSpecMCPTool
from pyagentspec.mcp.tools import MCPToolBox as AgentSpecMCPToolBox
from pyagentspec.mcp.tools import MCPToolSpec as AgentSpecMCPToolSpec
from pyagentspec.property import ListProperty as AgentSpecListProperty
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import StringProperty as AgentSpecStringProperty
from pyagentspec.property import _empty_default as _agentspec_empty_default
from pyagentspec.property import json_schemas_have_same_type
from pyagentspec.tools import ClientTool as AgentSpecClientTool
from pyagentspec.tools import RemoteTool as AgentSpecRemoteTool
from pyagentspec.tools import ServerTool as AgentSpecServerTool
from pyagentspec.tools import Tool as AgentSpecTool
from pyagentspec.tools import ToolBox as AgentSpecToolBox
from pyagentspec.tracing.events import AgentExecutionEnd as AgentSpecAgentExecutionEnd
from pyagentspec.tracing.events import AgentExecutionStart as AgentSpecAgentExecutionStart
from pyagentspec.tracing.events import FlowExecutionEnd as AgentSpecFlowExecutionEnd
from pyagentspec.tracing.events import FlowExecutionStart as AgentSpecFlowExecutionStart
from pyagentspec.tracing.spans import AgentExecutionSpan as AgentSpecAgentExecutionSpan
from pyagentspec.tracing.spans import FlowExecutionSpan as AgentSpecFlowExecutionSpan

if TYPE_CHECKING:
    from langchain_mcp_adapters.sessions import (
        SSEConnection,
        StdioConnection,
        StreamableHttpConnection,
    )


def _mcp_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("langchain_mcp_adapters") is not None


def _ensure_mcp_dependency_installed() -> None:
    if not _mcp_available():
        raise RuntimeError(
            "langchain-mcp-adapters is required to preload MCP tools. "
            "Install it (e.g., pip install langchain-mcp-adapters) or remove MCP tools from the spec."
        )


def _create_agent_state_typed_dict(
    model_name: str,
    inputs: List[AgentSpecProperty],
) -> "type[AgentState[BaseModel]]":
    """Create a TypedDict subclass of LangChain's AgentState with custom inputs.

    We extend the default AgentState (which already includes `messages` and
    optional `structured_response`) by adding our input properties and a
    required `remaining_steps` field. Required/optional inputs are expressed
    using PEP 655 `Required`/`NotRequired`.
    """
    import types

    registry = SchemaRegistry()

    annotations: Dict[str, Any] = {
        "remaining_steps": Required[int],
    }

    for property_ in inputs:
        annotation = _build_type_from_schema(property_.title, property_.json_schema, registry)
        if property_.default is not _agentspec_empty_default:
            annotations[property_.title] = NotRequired[annotation]
        else:
            annotations[property_.title] = Required[annotation]

    def _exec_body(ns: Dict[str, Any]) -> None:
        ns["__annotations__"] = annotations

    # total=False => unspecified fields are optional unless wrapped with Required
    return types.new_class(
        model_name,
        (AgentState[BaseModel],),
        {"total": False},
        _exec_body,
    )


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
            return self._agent_convert_to_langgraph(
                agentspec_component,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
        elif isinstance(agentspec_component, AgentSpecLlmConfig):
            return self._llm_convert_to_langgraph(agentspec_component, config=config)
        elif isinstance(agentspec_component, AgentSpecClientTransport):
            return self._client_transport_convert_to_langgraph(agentspec_component)
        elif isinstance(agentspec_component, AgentSpecMCPTool):
            _ensure_mcp_dependency_installed()
            _ensure_checkpointer_and_valid_tool_config(agentspec_component, checkpointer)
            return self._mcp_tool_convert_to_langgraph(
                agentspec_component,
                tool_registry=tool_registry,
                converted_components=converted_components,
            )
        elif isinstance(agentspec_component, AgentSpecMCPToolBox):
            _ensure_mcp_dependency_installed()
            return self._mcp_toolbox_convert_to_langgraph(
                agentspec_component,
                tool_registry=tool_registry,
                converted_components=converted_components,
            )
        elif isinstance(agentspec_component, AgentSpecServerTool):
            _ensure_checkpointer_and_valid_tool_config(agentspec_component, checkpointer)
            return self._server_tool_convert_to_langgraph(
                agentspec_component, tool_registry, config=config
            )
        elif isinstance(agentspec_component, AgentSpecClientTool):
            _ensure_checkpointer_and_valid_tool_config(agentspec_component, checkpointer)
            return self._client_tool_convert_to_langgraph(agentspec_component)
        elif isinstance(agentspec_component, AgentSpecRemoteTool):
            _ensure_checkpointer_and_valid_tool_config(agentspec_component, checkpointer)
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
        self, control_flow_connections: List[AgentSpecControlFlowEdge]
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

        from pyagentspec.adapters.langgraph._types import RunnableLambda

        for node_id, node_executor in node_executors.items():
            # Provide both sync and async entrypoints natively. LangGraph will use
            # the appropriate one based on invoke/stream vs ainvoke/astream.
            runnable = RunnableLambda(
                func=lambda state, _exec=node_executor: _exec(state),  # type: ignore
                afunc=lambda state, _exec=node_executor: _exec.__acall__(state),
                name=node_id,
            )
            graph_builder.add_node(node_id, runnable)

        data_flow_connections: List[AgentSpecDataFlowEdge] = []
        if flow.data_flow_connections is None:
            # We manually create data flow connections if they are not given in the flow
            # This is the conversion recommended in the Agent Spec language specification
            for source_node in flow.nodes:
                for destination_node in flow.nodes:
                    for source_output in source_node.outputs or []:
                        for destination_input in destination_node.inputs or []:
                            if source_output.title == destination_input.title:
                                data_flow_connections.append(
                                    AgentSpecDataFlowEdge(
                                        name=f"{source_node.name}-{destination_node.name}-{source_output.title}",
                                        source_node=source_node,
                                        source_output=source_output.title,
                                        destination_node=destination_node,
                                        destination_input=destination_input.title,
                                    )
                                )
        else:
            data_flow_connections = flow.data_flow_connections

        for data_flow_edge in data_flow_connections:
            node_executors[data_flow_edge.source_node.id].attach_edge(data_flow_edge)

        control_flow: "ControlFlow" = self._create_control_flow(flow.control_flow_connections)
        self._add_conditional_edges_to_graph(control_flow, graph_builder)
        compiled_graph = graph_builder.compile(checkpointer=checkpointer)

        # Warn users on Python < 3.11 about async interrupts potentially failing.
        # We warn during graph loading/compilation time to avoid runtime surprises.
        if sys.version_info < (3, 11):
            uses_interrupt = False
            try:
                # Any InputMessageNode implies interrupt; client tools may interrupt too.
                uses_interrupt = any(
                    isinstance(n, AgentSpecInputMessageNode) or isinstance(n, AgentSpecToolNode)
                    for n in flow.nodes
                )
            except Exception:
                uses_interrupt = False
            if uses_interrupt or checkpointer is not None:
                logger = logging.getLogger("pyagentspec.adapters.langgraph")
                logger.warning(
                    "Async interrupts on Python < 3.11 may raise 'Called get_config outside of a runnable context'. "
                    "Prefer invoke/stream or upgrade to Python 3.11+ for ainvoke/astream."
                )

        # To enable flow execution traces monkey patch all the functions that invoke the compiled graph

        original_stream = compiled_graph.stream

        def patch_with_flow_execution_span(*args: Any, **kwargs: Any) -> Generator[Any, Any, None]:
            span_name = f"FlowExecution[{flow.name}]"
            inputs = kwargs.get("input", {})
            if not isinstance(inputs, dict):
                inputs = {}
            with AgentSpecFlowExecutionSpan(name=span_name, flow=flow) as span:
                span.add_event(AgentSpecFlowExecutionStart(flow=flow, inputs=inputs))
                original_result: dict[str, Any] | Any = {}
                result: dict[str, Any]
                # This is going to patch stream and astream, that return iterators and yield chunks
                for chunk in original_stream(*args, **kwargs):
                    yield chunk
                    if isinstance(chunk, tuple):
                        original_result = chunk[1]
                if not isinstance(original_result, dict):
                    result = {}
                else:
                    result = original_result
                span.add_event(
                    AgentSpecFlowExecutionEnd(
                        flow=flow,
                        outputs=result.get("outputs", {}),
                        branch_selected=result.get("node_execution_details", {}).get("branch", ""),
                    )
                )

        original_astream = compiled_graph.astream

        async def patch_async_with_flow_execution_span(
            *args: Any, **kwargs: Any
        ) -> AsyncGenerator[Any, Any]:
            span_name = f"FlowExecution[{flow.name}]"
            inputs = kwargs.get("input", {})
            if not isinstance(inputs, dict):
                inputs = {}
            span = AgentSpecFlowExecutionSpan(name=span_name, flow=flow)
            try:
                await span.start_async()
            except NotImplementedError:
                span.start()
            try:
                try:
                    await span.add_event_async(
                        AgentSpecFlowExecutionStart(flow=flow, inputs=inputs)
                    )
                except NotImplementedError:
                    span.add_event(AgentSpecFlowExecutionStart(flow=flow, inputs=inputs))
                original_result: dict[str, Any] | Any = {}
                result: dict[str, Any]
                # This is going to patch stream and astream, that return iterators and yield chunks
                async for chunk in original_astream(*args, **kwargs):
                    yield chunk
                    if isinstance(chunk, tuple):
                        original_result = chunk[1]
                if not isinstance(original_result, dict):
                    result = {}
                else:
                    result = original_result
                span_end_event = AgentSpecFlowExecutionEnd(
                    flow=flow,
                    outputs=result.get("outputs", {}),
                    branch_selected=result.get("node_execution_details", {}).get("branch", ""),
                )
                try:
                    await span.add_event_async(span_end_event)
                except NotImplementedError:
                    span.add_event(span_end_event)
            finally:
                try:
                    await span.end_async()
                except NotImplementedError:
                    span.end()

        # Monkey patch invocation functions to inject tracing
        # No need to patch `(a)invoke` as the internally use `(a)stream`
        compiled_graph.stream = patch_with_flow_execution_span  # type: ignore
        compiled_graph.astream = patch_async_with_flow_execution_span  # type: ignore
        return compiled_graph

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
        elif isinstance(node, AgentSpecCatchExceptionNode):
            return self._catch_exception_node_convert_to_langgraph(
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
        from pyagentspec.adapters.langgraph._node_execution import MapNodeExecutor

        subflow = self.convert(
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
        from pyagentspec.adapters.langgraph._node_execution import FlowNodeExecutor

        subflow = self.convert(
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

    def _catch_exception_node_convert_to_langgraph(
        self,
        catch_node: AgentSpecCatchExceptionNode,
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> "NodeExecutor":
        from pyagentspec.adapters.langgraph._node_execution import CatchExceptionNodeExecutor

        subflow = self.convert(
            catch_node.subflow,
            tool_registry=tool_registry,
            converted_components=converted_components,
            checkpointer=checkpointer,
            config=config,
        )
        if not isinstance(subflow, CompiledStateGraph):
            raise TypeError(
                "Internal error: CatchExceptionNodeExecutor expects `subflow` "
                f"to be a CompiledStateGraph, was {type(subflow)}"
            )

        return CatchExceptionNodeExecutor(
            catch_node,
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
        tool_name = remote_tool.name
        tool_description = remote_tool.description or ""
        _remote_tool = _confirm_then(
            func=_create_remote_tool_func(remote_tool),
            tool_name=tool_name,
            requires_confirmation=remote_tool.requires_confirmation,
        )

        # Use a Pydantic model for args_schema
        args_model = create_pydantic_model_from_properties(
            f"{tool_name}Args",
            remote_tool.inputs or [],
        )

        structured_tool = StructuredTool(
            name=tool_name,
            description=tool_description,
            args_schema=args_model,
            func=_remote_tool,
            callbacks=[
                AgentSpecToolCallbackHandler(tool=remote_tool),
            ],
        )
        return structured_tool

    def _server_tool_convert_to_langgraph(
        self,
        agentspec_server_tool: AgentSpecServerTool,
        tool_registry: Dict[str, LangGraphTool],
        config: RunnableConfig,
    ) -> LangGraphTool:
        def _is_structured_tool(x: Any) -> TypeGuard[StructuredTool]:
            return isinstance(x, StructuredTool)

        if agentspec_server_tool.name not in tool_registry:
            raise ValueError(
                f"The Agent Spec representation includes a tool '{agentspec_server_tool.name}' "
                f"but this tool does not appear in the tool registry"
            )

        tool_obj = tool_registry[agentspec_server_tool.name]
        tool_name = agentspec_server_tool.name
        tool_description = agentspec_server_tool.description or ""
        requires_confirmation = agentspec_server_tool.requires_confirmation
        if _is_structured_tool(tool_obj):
            if tool_obj.func is None:
                raise TypeError(
                    f"Unsupported tool type for '{tool_name}': StructuredTool has no func."
                )
            if tool_obj.args_schema is None:
                raise TypeError(
                    f"Unsupported tool type for '{tool_name}': StructuredTool has no args_schema."
                )

            wrapped_tool_func = _confirm_then(
                func=tool_obj.func,
                tool_name=tool_name,
                requires_confirmation=requires_confirmation,
            )
            return StructuredTool(
                name=tool_obj.name,
                description=tool_obj.description,
                args_schema=tool_obj.args_schema,
                func=wrapped_tool_func,
                callbacks=[
                    AgentSpecToolCallbackHandler(tool=agentspec_server_tool),
                ],
            )

        if not callable(tool_obj):
            raise TypeError(
                f"Unsupported tool type for '{tool_name}': {type(tool_obj)}. Expected callable or StructuredTool."
            )

        wrapped_tool_func = _confirm_then(
            func=tool_obj,
            tool_name=tool_name,
            requires_confirmation=requires_confirmation,
        )

        args_model = create_pydantic_model_from_properties(
            f"{tool_name}Args",
            agentspec_server_tool.inputs or [],
        )
        return StructuredTool(
            name=tool_name,
            description=tool_description,
            args_schema=args_model,
            func=wrapped_tool_func,
            callbacks=[
                AgentSpecToolCallbackHandler(tool=agentspec_server_tool),
            ],
        )

    def _client_tool_convert_to_langgraph(
        self, agentspec_client_tool: AgentSpecClientTool
    ) -> LangGraphTool:
        # Warn at load time for Python < 3.11 since client tools use interrupt under the hood.
        if sys.version_info < (3, 11):
            logging.getLogger("pyagentspec.adapters.langgraph").warning(
                "Async interrupts on Python < 3.11 may raise 'Called get_config outside of a runnable context'. "
                "Prefer invoke/stream or upgrade to Python 3.11+ for ainvoke/astream."
            )

        tool_name = agentspec_client_tool.name
        tool_description = agentspec_client_tool.description or ""
        requires_confirmation = agentspec_client_tool.requires_confirmation

        def client_tool(*args: Any, **kwargs: Any) -> Any:
            if requires_confirmation:
                if args:
                    raise ValueError("Args are not supported, please only use kwargs")
                confirmed, reason = _confirm_tool_use(tool_name, **kwargs)

                if not confirmed:
                    return f"Tool '{tool_name}' was denied execution by the user. Reason: {reason}"

            tool_request = {
                "type": "client_tool_request",
                "name": tool_name,
                "description": tool_description,
                "inputs": {
                    "args": args,
                    "kwargs": kwargs,
                },
            }
            response = interrupt(tool_request)
            return response

        # Use a Pydantic model for args_schema
        args_model = create_pydantic_model_from_properties(
            f"{tool_name}Args",
            agentspec_client_tool.inputs or [],
        )

        structured_tool = StructuredTool(
            name=tool_name,
            description=tool_description,
            args_schema=args_model,
            func=client_tool,
            # We do not add the tool execution callback here as it's not expected for client tools
        )
        return structured_tool

    def _mcp_tool_convert_to_langgraph(
        self,
        agentspec_mcp_tool: AgentSpecMCPTool,
        tool_registry: Dict[str, LangGraphTool],
        converted_components: Dict[str, Any],
    ) -> BaseTool:
        connection = self.convert(
            agentspec_mcp_tool.client_transport,
            tool_registry=tool_registry,
            converted_components=converted_components,
        )
        exposed_tools = self._get_or_create_langgraph_mcp_tools(
            client_transport=agentspec_mcp_tool.client_transport,
            langgraph_connection=connection,
            connection_key=agentspec_mcp_tool.client_transport.id,
            tool_registry=tool_registry,
        )
        return exposed_tools[agentspec_mcp_tool.name]

    def _mcp_toolbox_convert_to_langgraph(
        self,
        agentspec_mcp_toolbox: AgentSpecMCPToolBox,
        tool_registry: Dict[str, LangGraphTool],
        converted_components: Dict[str, Any],
    ) -> List[BaseTool]:
        connection = self.convert(
            agentspec_mcp_toolbox.client_transport,
            tool_registry=tool_registry,
            converted_components=converted_components,
        )
        remote_tools = self._get_or_create_langgraph_mcp_tools(
            client_transport=agentspec_mcp_toolbox.client_transport,
            langgraph_connection=connection,
            connection_key=agentspec_mcp_toolbox.client_transport.id,
            tool_registry=tool_registry,
        )
        # Below is logic to filter tools based on the tool_filter attribute of the toolbox
        # Normalize filter to {name: ToolSpec|None} (where None is when the filter is a string)
        filter_map = {
            (filter if isinstance(filter, str) else filter.name): (
                None if isinstance(filter, str) else filter
            )
            for filter in (agentspec_mcp_toolbox.tool_filter or [])
        }
        # If no filter provided, return all tools
        if not filter_map:
            filtered_tools = list(remote_tools.values())
        else:
            # Find missing by name first
            missing = sorted(name for name in filter_map if name not in remote_tools)
            if missing:
                raise ValueError("Missing tools: " + ", ".join(missing))
            # Validate specs (when provided) and collect tools
            for name, spec in filter_map.items():
                tool = remote_tools[name]
                if spec is not None and not _are_mcp_tool_spec_and_langchain_schemas_equal(
                    spec, tool
                ):
                    raise ValueError(
                        "Input descriptors mismatch for tool '%s'.\nLocal: %s\nRemote: %s"
                        % (spec.name, spec, getattr(tool, "args_schema", None))
                    )
            filtered_tools = [remote_tools[name] for name in filter_map]
        return filtered_tools

    def _create_react_agent_with_given_info(
        self,
        *,
        name: str,
        system_prompt: str,
        agent: AgentSpecAgent,
        llm_config: AgentSpecLlmConfig,
        tools: List[AgentSpecTool],
        toolboxes: List[AgentSpecToolBox],
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
        ] + [
            t
            for tb in toolboxes
            for t in self.convert(
                tb,
                tool_registry=tool_registry,
                converted_components=converted_components,
                checkpointer=checkpointer,
                config=config,
            )
        ]
        output_model: Optional[type[BaseModel]] = None
        state_schema: Optional[Any] = None

        # Build response (output) model (used for response_format)
        if outputs:
            output_model = create_pydantic_model_from_properties("AgentOutputModel", outputs)

        if inputs:
            state_schema = _create_agent_state_typed_dict(
                "AgentState",
                inputs=inputs,
            )

        compiled_graph = langchain_agents.create_agent(
            name=name,
            model=model,
            tools=langgraph_tools,
            system_prompt=system_prompt,
            checkpointer=checkpointer,
            response_format=output_model,
            state_schema=state_schema,
        )

        # To enable flow execution traces monkey patch all the functions that invoke the compiled graph

        original_stream = compiled_graph.stream

        def patch_with_agent_execution_span(*args: Any, **kwargs: Any) -> Generator[Any, Any, Any]:
            span_name = f"AgentExecution[{agent.name}]"
            inputs = kwargs.get("input", {})
            if not isinstance(inputs, dict):
                inputs = {}
            with AgentSpecAgentExecutionSpan(name=span_name, agent=agent) as span:
                span.add_event(AgentSpecAgentExecutionStart(agent=agent, inputs=inputs))
                original_result: dict[str, Any] | Any = {}
                result: dict[str, Any]
                # This is going to patch stream and astream, that return iterators and yield chunks
                for chunk in original_stream(*args, **kwargs):
                    yield chunk
                    if isinstance(chunk, tuple):
                        original_result = chunk[1]
                if not isinstance(original_result, dict):
                    result = {}
                else:
                    result = original_result
                outputs = extract_outputs_from_invoke_result(result, agent.outputs or [])
                span.add_event(AgentSpecAgentExecutionEnd(agent=agent, outputs=outputs))

        original_astream = compiled_graph.astream

        async def patch_async_with_agent_execution_span(
            *args: Any, **kwargs: Any
        ) -> AsyncGenerator[Any, Any]:
            span_name = f"AgentExecution[{agent.name}]"
            inputs = kwargs.get("input", {})
            if not isinstance(inputs, dict):
                inputs = {}
            span = AgentSpecAgentExecutionSpan(name=span_name, agent=agent)
            try:
                await span.start_async()
            except NotImplementedError:
                span.start()
            try:
                try:
                    await span.add_event_async(
                        AgentSpecAgentExecutionStart(agent=agent, inputs=inputs)
                    )
                except NotImplementedError:
                    span.add_event(AgentSpecAgentExecutionStart(agent=agent, inputs=inputs))
                original_result: dict[str, Any] | Any = {}
                result: dict[str, Any]
                # This is going to patch stream and astream, that return iterators and yield chunks
                async for chunk in original_astream(*args, **kwargs):
                    yield chunk
                    if isinstance(chunk, tuple):
                        original_result = chunk[1]
                if not isinstance(original_result, dict):
                    result = {}
                else:
                    result = original_result

                outputs = extract_outputs_from_invoke_result(result, agent.outputs or [])
                try:
                    await span.add_event_async(
                        AgentSpecAgentExecutionEnd(agent=agent, outputs=outputs)
                    )
                except NotImplementedError:
                    span.add_event(AgentSpecAgentExecutionEnd(agent=agent, outputs=outputs))
            finally:
                try:
                    await span.end_async()
                except NotImplementedError:
                    span.end()

        # Monkey patch invocation functions to inject tracing
        # No need to patch `(a)invoke` as the internally use `(a)stream`
        compiled_graph.stream = patch_with_agent_execution_span  # type: ignore
        compiled_graph.astream = patch_async_with_agent_execution_span  # type: ignore
        return compiled_graph

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
            agent=agentspec_component,
            llm_config=agentspec_component.llm_config,
            tools=agentspec_component.tools,
            toolboxes=agentspec_component.toolboxes,
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

        callbacks: List[BaseCallbackHandler] = [
            AgentSpecLlmCallbackHandler(llm_config=llm_config),
        ]

        if isinstance(llm_config, VllmConfig):
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=llm_config.model_id,
                api_key=SecretStr("EMPTY"),
                base_url=_prepare_openai_compatible_url(llm_config.url),
                use_responses_api=use_responses_api,
                callbacks=callbacks,
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
                callbacks=callbacks,
                **generation_config,
            )
        elif isinstance(llm_config, OpenAiConfig):
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=llm_config.model_id,
                use_responses_api=use_responses_api,
                callbacks=callbacks,
                **generation_config,
            )
        elif isinstance(llm_config, OpenAiCompatibleConfig):
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=llm_config.model_id,
                base_url=_prepare_openai_compatible_url(llm_config.url),
                use_responses_api=use_responses_api,
                callbacks=callbacks,
                **generation_config,
            )
        else:
            raise NotImplementedError(
                f"Llm model of type {llm_config.__class__.__name__} is not yet supported."
            )

    def _client_transport_convert_to_langgraph(
        self, agentspec_component: AgentSpecClientTransport
    ) -> "Union[StdioConnection, SSEConnection, StreamableHttpConnection]":
        import datetime

        from langchain_mcp_adapters.sessions import (
            SSEConnection,
            StdioConnection,
            StreamableHttpConnection,
        )

        sesh = agentspec_component.session_parameters.model_dump()
        sesh["read_timeout_seconds"] = datetime.timedelta(seconds=sesh["read_timeout_seconds"])
        if isinstance(agentspec_component, AgentSpecStdioTransport):
            return StdioConnection(
                transport="stdio",
                command=agentspec_component.command,
                args=agentspec_component.args,
                env=agentspec_component.env,
                cwd=agentspec_component.cwd,
                session_kwargs=sesh,
            )
        if isinstance(agentspec_component, AgentSpecSSEmTLSTransport):
            return SSEConnection(
                transport="sse",
                url=agentspec_component.url,
                headers=agentspec_component.headers,
                httpx_client_factory=_HttpxClientFactory(
                    key_file=agentspec_component.key_file,
                    cert_file=agentspec_component.cert_file,
                    ssl_ca_cert=agentspec_component.ca_file,
                ),
            )
        if isinstance(agentspec_component, AgentSpecSSETransport):
            return SSEConnection(
                transport="sse",
                url=agentspec_component.url,
                headers=agentspec_component.headers,
                httpx_client_factory=_HttpxClientFactory(verify=False),
            )
        if isinstance(agentspec_component, AgentSpecStreamableHTTPmTLSTransport):
            return StreamableHttpConnection(
                transport="streamable_http",
                url=agentspec_component.url,
                headers=agentspec_component.headers,
                httpx_client_factory=_HttpxClientFactory(
                    key_file=agentspec_component.key_file,
                    cert_file=agentspec_component.cert_file,
                    ssl_ca_cert=agentspec_component.ca_file,
                ),
            )
        if isinstance(agentspec_component, AgentSpecStreamableHTTPTransport):
            return StreamableHttpConnection(
                transport="streamable_http",
                url=agentspec_component.url,
                headers=agentspec_component.headers,
                httpx_client_factory=_HttpxClientFactory(verify=False),
            )
        raise ValueError(
            f"Agent Spec ClientTransport '{agentspec_component.__class__.__name__}' is not supported yet."
        )

    def _get_or_create_langgraph_mcp_tools(
        self,
        client_transport: AgentSpecClientTransport,
        langgraph_connection: "Union[StdioConnection, SSEConnection, StreamableHttpConnection]",
        connection_key: str,
        tool_registry: Dict[str, LangGraphTool],
    ) -> Dict[str, BaseTool]:
        """
        Synchronously load MCP tools and cache them into tool_registry keyed by:
        f"{agentspec_client_transport.id}::{tool_name}"

        Caching behavior:
        - If any tools are already present in the registry for this connection, returns those
        without reloading.
        - Otherwise, loads tools and inserts them atomically into the registry.
        """
        from langchain_mcp_adapters.tools import load_mcp_tools

        conn_prefix = f"{connection_key}::"
        existing = _get_session_tools_from_tool_registry(tool_registry, conn_prefix)
        if existing:
            return existing

        async def load_all_mcp_tools() -> List[BaseTool]:
            # Note: langchain supports session-specific MCP tools but we don't support that
            return await load_mcp_tools(session=None, connection=langgraph_connection)

        tools = run_async_in_sync(load_all_mcp_tools, method_name="load_mcp_tools")
        # We add callbacks to the tool for proper tracing
        for tool in tools:
            # Since we might not have the tool definition (e.g., in toolboxes)
            # we create the tool on-the-fly
            agentspec_tool = AgentSpecMCPTool(
                name=tool.name,
                description=tool.description,
                client_transport=client_transport,
                inputs=[
                    AgentSpecProperty(title=arg_name, json_schema=arg_json_schema)
                    for arg_name, arg_json_schema in tool.args.items()
                ],
                outputs=[AgentSpecStringProperty(title="tool_output")],
            )
            if not tool.callbacks:
                tool.callbacks = []
            if isinstance(tool.callbacks, BaseCallbackHandler):
                tool.callbacks = [tool.callbacks]
            tool.callbacks.append(AgentSpecToolCallbackHandler(tool=agentspec_tool))  # type: ignore

        _add_session_tools_to_registry(tool_registry, tools, conn_prefix)

        return _get_session_tools_from_tool_registry(tool_registry, conn_prefix)


def _get_session_tools_from_tool_registry(
    tool_registry: Dict[str, LangGraphTool], conn_prefix: str
) -> Dict[str, BaseTool]:
    return {
        key.replace(conn_prefix, ""): cast(BaseTool, tool)
        for key, tool in tool_registry.items()
        if key.startswith(conn_prefix)
    }


def _add_session_tools_to_registry(
    tool_registry: Dict[str, LangGraphTool], tools: List[BaseTool], conn_prefix: str
) -> None:
    # Prepare a staged mapping so we can insert all-or-nothing
    staged: Dict[str, BaseTool] = {}
    for tool in tools:
        # Derive a name: prefer .name, fallback to __name__ for callables
        tool_name = getattr(tool, "name", None)
        if not tool_name and callable(tool):
            tool_name = getattr(tool, "__name__", None)
        if not tool_name:
            raise ValueError("Loaded a tool without a name attribute or __name__.")

        key = f"{conn_prefix}{tool_name}"
        # Do not overwrite an existing entry if present
        if key not in tool_registry:
            staged[key] = tool
        else:
            raise ValueError(
                "Trying to add the same tool twice; this might happen "
                "when the tool is declared as both a standalone MCPTool and part of a MCPToolBox"
            )

    # Commit staged entries
    tool_registry.update(staged)


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


def _are_mcp_tool_spec_and_langchain_schemas_equal(
    mcp_spec: AgentSpecMCPToolSpec, langchain_schema: BaseTool
) -> bool:
    if not isinstance(langchain_schema.args_schema, dict):
        raise ValueError(
            f"Expected Langchain StructuredTool.args_schema to be a dict but got {type(langchain_schema.args_schema)}"
        )
    agentspec_json_schemas = {
        inp.json_schema["title"]: _normalize_title(inp.json_schema)
        for inp in (mcp_spec.inputs or [])
    }
    langchain_json_schemas = {
        k: _normalize_title(v) for k, v in langchain_schema.args_schema["properties"].items()
    }
    return json_schemas_have_same_type(agentspec_json_schemas, langchain_json_schemas)


def _normalize_title(d: Dict[str, Any]) -> Dict[str, Any]:
    """If `title`, then lowercase."""
    out = dict(d)  # shallow copy
    if isinstance(out.get("title"), str):
        out["title"] = out["title"].lower()
    return out


def _confirm_tool_use(tool_name: str, **tool_arguments: Any) -> Tuple[bool, str]:
    # aligned with https://docs.langchain.com/oss/python/langchain/human-in-the-loop#responding-to-interrupts
    ALLOWED_DECISIONS = ["approve", "reject"]
    confirmation_payload = {
        "action_requests": [
            {
                "name": tool_name,
                "arguments": tool_arguments,
                "description": f"Tool execution pending approval\n\nTool: {tool_name}\nArgs: {tool_arguments}",
            }
        ],
        "review_configs": [
            {
                "action_name": tool_name,
                "allowed_decisions": ALLOWED_DECISIONS,
                "description": (
                    'Please resume with {"decisions": [{"type": "approve"}]}  # or "reject" '
                    'with an optional "reason" for rejected tool calls.'
                ),
            }
        ],
    }
    response = interrupt(confirmation_payload)
    if not isinstance(response, dict) or "decisions" not in response:
        raise ValueError(
            f"Tool confirmation result for tool {tool_name} is not valid, should be a "
            f"dict with a 'decisions' key, was {response!r} of type {type(response)}."
        )
    decision_list = response["decisions"]
    if len(decision_list) != 1:
        raise ValueError(
            f"Tool confirmation result for tool {tool_name} is not valid, decisions "
            f"should be of length 1, was of length {len(decision_list)}"
        )
    decision = decision_list[0]
    if "type" not in decision or not decision["type"] in ALLOWED_DECISIONS:
        raise ValueError(
            f"Tool confirmation result for tool {tool_name} is not valid, "
            f"decision should be in {ALLOWED_DECISIONS}, was {decision}."
        )

    return (decision["type"] == "approve"), decision.get("reason", "No reason was provided.")


def _confirm_then(
    func: Callable[..., Any],
    tool_name: str,
    requires_confirmation: bool,
) -> Callable[..., Any]:
    """Wrap a callable so that it first interrupts for confirmation (if required)."""
    if not requires_confirmation:
        return func

    def _wrapped(**kwargs: Any) -> Any:
        confirmed, reason = _confirm_tool_use(tool_name, **kwargs)

        if not confirmed:
            return f"Tool '{tool_name}' was denied execution by the user. Reason: {reason}"

        return func(**kwargs)

    return _wrapped


def _ensure_checkpointer_and_valid_tool_config(
    agentspec_tool: AgentSpecTool, checkpointer: Optional[Checkpointer]
) -> None:
    tool_name = agentspec_tool.name
    if agentspec_tool.requires_confirmation and checkpointer is None:
        raise ValueError(
            f"A Checkpointer is required for tool '{tool_name}' because requires_confirmation=True"
        )
    elif isinstance(agentspec_tool, AgentSpecClientTool) and checkpointer is None:
        raise ValueError(f"A Checkpointer is required when using ClientTool '{tool_name}'.")

    tool_output = agentspec_tool.outputs or []
    if agentspec_tool.requires_confirmation and (
        len(tool_output) != 1 or "type" in tool_output[0].json_schema
    ):
        # TODO: refine to only raise output property does not support string
        raise ValueError(
            f"Invalid output schema for tool '{tool_name}' requiring tool confirmation: "
            f"json schema should be left unspecified when using tool confirmation, was {tool_output}. "
            f'Please use outputs=[Property(title="{tool_name}", json_schema={{}})]'
        )
