# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import ast
import dis
import inspect
import textwrap
from dataclasses import is_dataclass
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Collection,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    cast,
    get_type_hints,
)

from pydantic import BaseModel, TypeAdapter, create_model

from pyagentspec import Property
from pyagentspec.adapters.langgraph._types import (
    BaseChatModel,
    BranchSpec,
    CompiledStateGraph,
    LangGraphComponent,
    StateGraph,
    StateNodeSpec,
    langgraph_graph,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.node import Node as AgentSpecNode
from pyagentspec.flows.nodes import AgentNode as AgentSpecAgentNode
from pyagentspec.flows.nodes import BranchingNode, EndNode, FlowNode
from pyagentspec.flows.nodes import LlmNode as AgentSpecLlmNode
from pyagentspec.flows.nodes import StartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.property import StringProperty, UnionProperty
from pyagentspec.templating import get_placeholders_from_json_object
from pyagentspec.tools.servertool import ServerTool as AgentSpecServerTool

if TYPE_CHECKING:
    from pyagentspec.adapters.langgraph._agentspecconverter import LangGraphToAgentSpecConverter

END = langgraph_graph.END
START = langgraph_graph.START
GRAPH_STATE_PROPERTY_TITLE = "state"
OPAQUE_INPUT_PROPERTY_TITLE = "input"
OPAQUE_OUTPUT_PROPERTY_TITLE = "output"


class _FieldWiringFallbackRequired(ValueError):
    """Raised when a LangGraph flow is valid but not exactly representable with field wiring."""


class _OpaquePortProperty(Property):
    """Private marker for adapter-generated opaque ports."""


class _OpaqueUnionProperty(UnionProperty):
    """Private marker for opaque union ports."""


def _validate_conditional_edges_support(graph: StateGraph[Any, Any, Any]) -> None:
    for branch_specs in graph.branches.values():
        if len(branch_specs) > 1:
            raise ValueError(
                "Conversion of multiple conditional edges with the same source node "
                "is not yet supported"
            )


def _langgraph_graph_convert_to_agentspec(
    converter: "LangGraphToAgentSpecConverter",
    graph: LangGraphComponent,
    referenced_objects: Dict[str, AgentSpecComponent],
) -> AgentSpecFlow:
    """Convert a LangGraph state graph into an Agent Spec flow.

    The exporter first tries field wiring. If any required adjacent data edge cannot be
    represented exactly in Agent Spec, the whole flow falls back to opaque `state` wiring so the
    exported graph stays structurally valid and internally consistent.
    """
    flow_name, normalized_graph = _prepare_langgraph_graph_for_export(graph)
    # Build field-wired nodes/edges in an isolated reference map first so a later fallback does
    # not leave partially converted field-wired objects mixed into the opaque `state` export.
    field_wiring_referenced_objects = dict(referenced_objects)
    try:
        converted_flow = _FieldWiringFlowExporter(
            converter,
            normalized_graph,
            flow_name,
            field_wiring_referenced_objects,
        ).build()
    except _FieldWiringFallbackRequired:
        return _StateWiringFlowExporter(
            converter,
            normalized_graph,
            flow_name,
            referenced_objects,
        ).build()

    referenced_objects.update(field_wiring_referenced_objects)
    return converted_flow


def _prepare_langgraph_graph_for_export(
    graph: LangGraphComponent,
) -> Tuple[str, StateGraph[Any, Any, Any]]:
    """Normalize and validate one LangGraph graph before export."""
    flow_name = graph.name if isinstance(graph, CompiledStateGraph) else "LangGraph Flow"
    normalized_graph = graph.builder if isinstance(graph, CompiledStateGraph) else graph
    _validate_conditional_edges_support(normalized_graph)
    return flow_name, normalized_graph


class _BaseLangGraphFlowExporter:
    """Shared flow assembly for the field-wiring and state-wiring export strategies."""

    def __init__(
        self,
        converter: "LangGraphToAgentSpecConverter",
        graph: StateGraph[Any, Any, Any],
        flow_name: str,
        referenced_objects: Dict[str, AgentSpecComponent],
    ) -> None:
        self._converter = converter
        self._graph = graph
        self._flow_name = flow_name
        self._referenced_objects = referenced_objects

    def build(self) -> AgentSpecFlow:
        nodes: List[AgentSpecNode] = []
        for node_name, node in self._graph.nodes.items():
            if node_name in (START, END):
                continue
            nodes.append(self._convert_node(node_name, node))

        start_node, end_node = self._build_start_end_nodes()
        nodes.append(start_node)
        nodes.append(end_node)

        control_flow_edges: List[ControlFlowEdge] = []
        data_flow_edges: List[DataFlowEdge] = []
        for edge in self._graph.edges:
            from_, to = edge
            control_flow_edges.append(
                _langgraph_edge_convert_to_agentspec_ctrl_flow(edge, self._referenced_objects)
            )
            data_flow_edges.extend(
                _build_data_flow_edges_for_node_pair(
                    source_node=cast(AgentSpecNode, self._referenced_objects[from_]),
                    destination_node=cast(AgentSpecNode, self._referenced_objects[to]),
                    edge_name_prefix=f"{from_}_to_{to}",
                )
            )

        for source_node_name, branch_specs in self._graph.branches.items():
            for conditional_node_name, branch in branch_specs.items():
                additional_nodes, additional_ctrl_flows, additional_data_flows = (
                    self._build_conditional_branch(
                        source_node_name,
                        conditional_node_name,
                        branch,
                    )
                )
                nodes.extend(additional_nodes)
                control_flow_edges.extend(additional_ctrl_flows)
                data_flow_edges.extend(additional_data_flows)

        # Add missing edges towards END nodes for nodes with no outgoing edges.
        for agentspec_node in nodes:
            if agentspec_node.name == START or agentspec_node.name == END:
                continue
            if not any(
                ctrl_flow.from_node.name == agentspec_node.name for ctrl_flow in control_flow_edges
            ):
                edge = agentspec_node.name, END
                from_, to = edge
                control_flow_edges.append(
                    _langgraph_edge_convert_to_agentspec_ctrl_flow(
                        edge,
                        self._referenced_objects,
                    )
                )
                data_flow_edges.extend(
                    _build_data_flow_edges_for_node_pair(
                        source_node=cast(AgentSpecNode, self._referenced_objects[from_]),
                        destination_node=cast(AgentSpecNode, self._referenced_objects[to]),
                        edge_name_prefix=f"{from_}_to_{to}",
                    )
                )

        self._validate_data_flow_edges(nodes, data_flow_edges)

        return AgentSpecFlow(
            name=self._flow_name,
            start_node=start_node,
            nodes=nodes,
            control_flow_connections=control_flow_edges,
            data_flow_connections=data_flow_edges,
        )

    def _convert_node(
        self,
        node_name: str,
        node: "StateNodeSpec[Any]",
    ) -> AgentSpecNode:
        """Convert one LangGraph node under the current private export strategy."""
        converted_node = self._referenced_objects.get(node_name)
        if converted_node is not None:
            if not isinstance(converted_node, AgentSpecNode):
                raise TypeError(
                    f"expected node {converted_node} to be of type {AgentSpecNode}, "
                    f"got: {converted_node.__class__}"
                )
            return converted_node

        converted_node = self._build_node(node_name, node)
        self._referenced_objects[node_name] = converted_node
        return converted_node

    def _build_node(
        self,
        node_name: str,
        node: "StateNodeSpec[Any]",
    ) -> AgentSpecNode:
        """Dispatch one LangGraph node to the corresponding Agent Spec node kind."""
        if self._is_graph_backed_node(node):
            return self._build_flow_node(node_name, node)
        return self._build_tool_node(node_name, node)

    def _is_graph_backed_node(self, node: "StateNodeSpec[Any]") -> bool:
        """Return whether the LangGraph node wraps another graph-backed component."""
        return isinstance(node.runnable, (StateGraph, CompiledStateGraph))

    def _build_start_end_nodes(self) -> Tuple[AgentSpecNode, AgentSpecNode]:
        """Return the exported START and END nodes under the current export strategy."""
        return (
            self._get_or_build_start_end_node(
                START,
                self._graph.input_schema,
                StartNode,
            ),
            self._get_or_build_start_end_node(
                END,
                self._graph.output_schema,
                EndNode,
            ),
        )

    def _get_or_build_start_end_node(
        self,
        start_end_node_name: str,
        public_schema: Any,
        start_end_node_class: Type[Any],
    ) -> AgentSpecNode:
        """Return the exported START/END node, building it on first use."""
        converted_node = self._referenced_objects.get(start_end_node_name)
        if converted_node is not None:
            if not isinstance(converted_node, AgentSpecNode):
                raise TypeError(
                    f"expected node {converted_node} to be of type {AgentSpecNode}, "
                    f"got: {converted_node.__class__}"
                )
            return converted_node
        if start_end_node_name in self._graph.nodes:
            return self._convert_node(
                start_end_node_name,
                self._graph.nodes[start_end_node_name],
            )

        start_end_node_properties = self._get_start_end_node_properties(
            start_end_node_name,
            public_schema,
        )
        start_end_node = cast(
            AgentSpecNode,
            start_end_node_class(
                name=start_end_node_name,
                inputs=start_end_node_properties,
                outputs=list(start_end_node_properties),
            ),
        )
        self._referenced_objects[start_end_node_name] = start_end_node
        return start_end_node

    def _build_conditional_branch(
        self,
        source_node_name: str,
        conditional_node_name: str,
        branch: BranchSpec,
    ) -> Tuple[List[AgentSpecNode], List[ControlFlowEdge], List[DataFlowEdge]]:
        """Build the Agent Spec helper nodes and edges for one LangGraph conditional branch."""
        additional_nodes: List[AgentSpecNode] = []
        additional_ctrl_flows: List[ControlFlowEdge] = []
        additional_data_flows: List[DataFlowEdge] = []

        if branch.ends is None:
            raise TypeError(f"""Mapping for {conditional_node_name} not found.
                Make sure to add proper return type hints to the branching function.""")

        mapping = {
            str(route_token): target_node_name
            for route_token, target_node_name in branch.ends.items()
        }
        source_node = cast(AgentSpecNode, self._referenced_objects[source_node_name])
        conditional_node_name = _dedupe_name(
            conditional_node_name,
            self._referenced_objects.keys(),
        )

        conditional_node = AgentSpecToolNode(
            name=conditional_node_name,
            tool=AgentSpecServerTool(
                name=f"{conditional_node_name}_tool",
                inputs=self._resolve_conditional_node_inputs(source_node_name, branch),
                outputs=[StringProperty(title=BranchingNode.DEFAULT_INPUT)],
            ),
        )
        additional_nodes.append(conditional_node)
        self._referenced_objects[conditional_node_name] = conditional_node

        additional_ctrl_flows.append(
            ControlFlowEdge(
                name=f"{source_node_name}_to_{conditional_node_name}",
                from_node=source_node,
                to_node=conditional_node,
            )
        )
        additional_data_flows.extend(
            _build_data_flow_edges_for_node_pair(
                source_node=source_node,
                destination_node=conditional_node,
                edge_name_prefix=f"{source_node_name}_to_{conditional_node_name}",
            )
        )

        branching_node_name = _dedupe_name(
            f"{conditional_node_name}_branching_node",
            self._referenced_objects.keys(),
        )
        branching_node = BranchingNode(
            name=branching_node_name,
            mapping=mapping,
        )
        additional_nodes.append(branching_node)
        self._referenced_objects[branching_node_name] = branching_node

        additional_ctrl_flows.append(
            ControlFlowEdge(
                name=f"{conditional_node_name}_to_{branching_node_name}",
                from_node=conditional_node,
                to_node=branching_node,
            )
        )
        additional_data_flows.append(
            DataFlowEdge(
                name=f"{conditional_node_name}_to_{branching_node_name}_data_edge",
                source_node=conditional_node,
                source_output=BranchingNode.DEFAULT_INPUT,
                destination_node=branching_node,
                destination_input=BranchingNode.DEFAULT_INPUT,
            )
        )

        # BranchingNode selects the mapping value as the outgoing Agent Spec branch name, so we
        # materialize one explicit edge per distinct target node, not per route token.
        for target_node_name in dict.fromkeys(mapping.values()):
            additional_ctrl_flows.append(
                ControlFlowEdge(
                    name=f"{branching_node_name}_branch_{target_node_name}",
                    from_node=branching_node,
                    to_node=cast(AgentSpecNode, self._referenced_objects[target_node_name]),
                    from_branch=target_node_name,
                )
            )
            additional_data_flows.extend(
                _build_data_flow_edges_for_node_pair(
                    source_node=source_node,
                    destination_node=cast(
                        AgentSpecNode,
                        self._referenced_objects[target_node_name],
                    ),
                    edge_name_prefix=f"data_{source_node_name}_to_{target_node_name}",
                ),
            )

        # Always keep an explicit default edge to END, even if another mapped branch also targets
        # END, because the default branch is a distinct Agent Spec branch.
        additional_ctrl_flows.append(
            ControlFlowEdge(
                name=f"{branching_node_name}_default_to_{END}",
                from_node=branching_node,
                to_node=cast(AgentSpecNode, self._referenced_objects[END]),
                from_branch=BranchingNode.DEFAULT_BRANCH,
            )
        )

        return (additional_nodes, additional_ctrl_flows, additional_data_flows)

    def _validate_data_flow_edges(
        self,
        nodes: List[AgentSpecNode],
        data_flow_edges: List[DataFlowEdge],
    ) -> None:
        """Allow concrete strategies to validate assembled data edges."""

    def _build_flow_node(
        self,
        node_name: str,
        node: "StateNodeSpec[Any]",
    ) -> FlowNode:
        """Convert a graph-backed LangGraph node that exports as an Agent Spec FlowNode."""
        raise NotImplementedError

    def _build_tool_node(
        self,
        node_name: str,
        node: "StateNodeSpec[Any]",
    ) -> AgentSpecNode:
        """Convert a LangGraph leaf runnable that should export as an Agent Spec ToolNode."""
        raise NotImplementedError

    def _get_start_end_node_properties(
        self,
        start_end_node_name: str,
        public_schema: Any,
    ) -> List[Property]:
        """Return the START/END node properties for the current export strategy."""
        raise NotImplementedError

    def _resolve_conditional_node_inputs(
        self,
        source_node_name: str,
        branch: BranchSpec,
    ) -> List[Property]:
        """Return the synthetic route-node inputs for the current export strategy."""
        raise NotImplementedError


class _StateWiringFlowExporter(_BaseLangGraphFlowExporter):
    """Exporter that uses a single opaque `state` interface throughout the flow."""

    def _build_flow_node(
        self,
        node_name: str,
        node: "StateNodeSpec[Any]",
    ) -> FlowNode:
        subgraph_runnable = cast(LangGraphComponent, node.runnable)
        subgraph_flow_name, normalized_subgraph = _prepare_langgraph_graph_for_export(
            subgraph_runnable
        )
        subflow = _StateWiringFlowExporter(
            self._converter,
            normalized_subgraph,
            subgraph_flow_name,
            {},
        ).build()
        return FlowNode(
            name=node_name,
            subflow=subflow,
            inputs=[self._build_state_wired_input_property(node.input_schema)],
            outputs=[self._build_state_wired_output_property(node_name)],
        )

    def _build_tool_node(
        self,
        node_name: str,
        node: "StateNodeSpec[Any]",
    ) -> AgentSpecNode:
        input_property = self._build_state_wired_input_property(node.input_schema)
        output_property = self._build_state_wired_output_property(node_name)
        return AgentSpecToolNode(
            name=node_name,
            tool=AgentSpecServerTool(
                name=node_name + "_tool",
                inputs=[input_property],
                outputs=[output_property],
            ),
            inputs=[input_property],
            outputs=[output_property],
        )

    def _get_start_end_node_properties(
        self,
        start_end_node_name: str,
        public_schema: Any,
    ) -> List[Property]:
        schema = public_schema if public_schema is not None else self._graph.state_schema
        return [
            _build_opaque_property_from_schema(
                schema,
                title=GRAPH_STATE_PROPERTY_TITLE,
            )
        ]

    def _resolve_conditional_node_inputs(
        self,
        source_node_name: str,
        branch: BranchSpec,
    ) -> List[Property]:
        schema = getattr(branch, "input_schema", None)
        if schema is None:
            if source_node_name in self._graph.nodes:
                schema = self._graph.nodes[source_node_name].input_schema
            else:
                schema = self._graph.input_schema or self._graph.state_schema
        return [
            _build_opaque_property_from_schema(
                schema,
                title=GRAPH_STATE_PROPERTY_TITLE,
            )
        ]

    def _build_state_wired_input_property(self, schema: Any) -> Property:
        return _build_opaque_property_from_schema(
            schema if schema is not None else self._graph.state_schema,
            title=GRAPH_STATE_PROPERTY_TITLE,
        )

    def _build_state_wired_output_property(self, node_name: str) -> Property:
        target_node_names = [
            to_node_name
            for from_node_name, to_node_name in self._graph.edges
            if from_node_name != to_node_name and from_node_name == node_name
        ]
        if target_node_names in ([], [END]):
            return _build_opaque_property_from_schema(
                self._graph.output_schema or self._graph.state_schema,
                title=GRAPH_STATE_PROPERTY_TITLE,
            )
        if len(target_node_names) == 1:
            target_node_name = target_node_names[0]
            target_schema = (
                self._graph.output_schema
                if target_node_name == END
                else self._graph.nodes[target_node_name].input_schema
            )
            return _build_opaque_property_from_schema(
                target_schema or self._graph.state_schema,
                title=GRAPH_STATE_PROPERTY_TITLE,
            )

        target_properties: List[Property] = []
        for target_node_name in target_node_names:
            target_schema = (
                self._graph.output_schema
                if target_node_name == END
                else self._graph.nodes[target_node_name].input_schema
            )
            target_properties.append(
                _build_opaque_property_from_schema(
                    target_schema or self._graph.state_schema,
                    title=GRAPH_STATE_PROPERTY_TITLE,
                )
            )
        return _build_opaque_union_property(
            target_properties,
            title=GRAPH_STATE_PROPERTY_TITLE,
        )


class _FieldWiringFlowExporter(_BaseLangGraphFlowExporter):
    """Exporter that preserves direct field wiring only for directly representable flows."""

    def _build_node(
        self,
        node_name: str,
        node: "StateNodeSpec[Any]",
    ) -> AgentSpecNode:
        """Dispatch field-wired nodes directly by exported Agent Spec node kind."""
        if self._is_graph_backed_node(node):
            return self._build_flow_node(node_name, node)

        declared_input_properties, declared_output_properties = (
            _get_langgraph_node_declared_properties(
                self._graph,
                node,
            )
        )
        llm_node_export_target = _get_partial_bound_llm_and_prompt_from_node(node)
        if llm_node_export_target is not None:
            bound_llm, bound_prompt = llm_node_export_target
            # Keep Python `str.format(...)` prompts as ToolNodes so export never changes prompt
            # rendering semantics by silently translating `{field}` into Agent Spec placeholders.
            if not self._converter._contains_python_format_fields(bound_prompt):
                try:
                    return self._build_llm_node(
                        node_name,
                        bound_llm,
                        bound_prompt,
                        declared_input_properties,
                        declared_output_properties,
                    )
                except ValueError:
                    # Keep export best-effort: if promotion to a richer LlmNode shape cannot
                    # preserve the wrapper contract exactly, degrade to a plain ToolNode instead
                    # of failing the whole flow conversion.
                    pass
        # A leaf callable can still export as AgentNode when it is a `partial(...)` with one
        # bound react agent and the underlying callable visibly invokes that parameter.
        agent_node_export_target = _get_partial_bound_react_agent_invoke_target_from_node(
            self._converter,
            node,
        )
        if agent_node_export_target is not None:
            wrapped_agent_prompt = self._converter._extract_prompt_from_react_agent(
                agent_node_export_target
            )
            if not self._converter._contains_python_format_fields(wrapped_agent_prompt):
                try:
                    return self._build_agent_node(
                        node_name,
                        agent_node_export_target,
                        declared_input_properties,
                        declared_output_properties,
                    )
                except ValueError:
                    # Keep export best-effort: if AgentNode promotion would require a stricter
                    # interface than the wrapper actually exposes, fall back to ToolNode export.
                    pass
        return self._build_tool_node(
            node_name,
            node,
            declared_input_properties=declared_input_properties,
            declared_output_properties=declared_output_properties,
        )

    def _build_flow_node(
        self,
        node_name: str,
        node: "StateNodeSpec[Any]",
    ) -> FlowNode:
        subgraph_runnable = cast(LangGraphComponent, node.runnable)
        subflow = _langgraph_graph_convert_to_agentspec(
            self._converter,
            subgraph_runnable,
            {},
        )
        return FlowNode(name=node_name, subflow=subflow)

    def _build_tool_node(
        self,
        node_name: str,
        node: "StateNodeSpec[Any]",
        declared_input_properties: Optional[List[Property]] = None,
        declared_output_properties: Optional[List[Property]] = None,
    ) -> AgentSpecNode:
        if declared_input_properties is None and declared_output_properties is None:
            declared_input_properties, declared_output_properties = (
                _get_langgraph_node_declared_properties(
                    self._graph,
                    node,
                )
            )

        input_properties = declared_input_properties or [
            _build_opaque_property_from_schema(
                node.input_schema,
                title=OPAQUE_INPUT_PROPERTY_TITLE,
            )
        ]

        output_properties = declared_output_properties
        if output_properties is None:
            target_nodes = [
                to for from_, to in self._graph.edges if from_ != to and from_ == node_name
            ]
            # When a leaf node does not declare outputs, export the state shape expected by its
            # downstream consumers. This is an adapter approximation: Agent Spec needs an explicit
            # output port, while LangGraph lets the node return a patch that is interpreted in the
            # context of the next node(s).
            if target_nodes in ([], [END]):
                # No explicit outgoing edge means LangGraph implicitly routes this node to END.
                # An explicit edge to END has the same exported output shape.
                output_properties = [
                    _build_opaque_property_from_schema(
                        self._graph.output_schema,
                        title=OPAQUE_OUTPUT_PROPERTY_TITLE,
                    )
                ]
            elif len(target_nodes) == 1:
                target_node_name = target_nodes[0]
                # With one downstream node, export the state shape that node reads.
                output_properties = [
                    _build_opaque_property_from_schema(
                        self._graph.nodes[target_node_name].input_schema,
                        title=OPAQUE_OUTPUT_PROPERTY_TITLE,
                    )
                ]
            else:
                # With multiple downstream nodes, export a union of the state shapes each
                # possible target expects to read.
                target_properties: List[Property] = []
                for target_node_name in target_nodes:
                    if target_node_name == END:
                        target_properties.append(
                            _build_opaque_property_from_schema(
                                self._graph.output_schema,
                                title=OPAQUE_OUTPUT_PROPERTY_TITLE,
                            )
                        )
                    else:
                        target_properties.append(
                            _build_opaque_property_from_schema(
                                self._graph.nodes[target_node_name].input_schema,
                                title=OPAQUE_OUTPUT_PROPERTY_TITLE,
                            )
                        )
                output_properties = [
                    _build_opaque_union_property(
                        target_properties,
                        title=OPAQUE_OUTPUT_PROPERTY_TITLE,
                    )
                ]

        return AgentSpecToolNode(
            name=node_name,
            tool=AgentSpecServerTool(
                name=node_name + "_tool",
                inputs=input_properties,
                outputs=output_properties,
            ),
            inputs=input_properties,
            outputs=output_properties,
        )

    def _build_agent_node(
        self,
        node_name: str,
        wrapped_react_agent: LangGraphComponent,
        declared_input_properties: Optional[List[Property]],
        declared_output_properties: Optional[List[Property]],
    ) -> AgentSpecAgentNode:
        if not declared_input_properties:
            raise ValueError(
                f"Unable to export `{node_name}` as an AgentNode because wrapped LangGraph "
                "agents require named input fields. Define `input_schema=` on the node or "
                "annotate the callable's `state` parameter with a TypedDict, dataclass, or "
                "Pydantic model that has named fields."
            )
        if not declared_output_properties:
            raise ValueError(
                f"Unable to export `{node_name}` as an AgentNode because wrapped LangGraph "
                "agents require named output fields. Add a return annotation or output schema "
                "using a TypedDict, dataclass, or Pydantic model with named fields."
            )

        wrapped_agentspec_agent = self._converter._langgraph_agent_convert_to_agentspec(
            wrapped_react_agent,
            self._referenced_objects,
        )
        # AgentNode inputs are the wrapped agent's detected Agent Spec prompt variables, so
        # require the wrapper node's declared input fields to match that double-curly placeholder
        # contract exactly. Single-curly `{...}` text is ignored here because it is not part of
        # the exported Agent Spec input interface.
        wrapped_agent_prompt_inputs = set(
            get_placeholders_from_json_object(wrapped_agentspec_agent.system_prompt)
        )
        node_input_titles = {property_.title for property_ in declared_input_properties}
        if wrapped_agent_prompt_inputs != node_input_titles:
            raise ValueError(
                f"Unable to export `{node_name}` as an AgentNode because the wrapper node "
                f"inputs {sorted(node_input_titles)} do not match the wrapped agent prompt "
                f"placeholders {sorted(wrapped_agent_prompt_inputs)}."
            )

        return AgentSpecAgentNode(
            name=node_name,
            agent=AgentSpecAgent(
                name=wrapped_agentspec_agent.name,
                description=wrapped_agentspec_agent.description,
                metadata=dict(wrapped_agentspec_agent.metadata or {}),
                llm_config=wrapped_agentspec_agent.llm_config,
                system_prompt=wrapped_agentspec_agent.system_prompt,
                tools=list(wrapped_agentspec_agent.tools),
                toolboxes=list(wrapped_agentspec_agent.toolboxes),
                human_in_the_loop=wrapped_agentspec_agent.human_in_the_loop,
                transforms=list(wrapped_agentspec_agent.transforms),
                inputs=declared_input_properties,
                outputs=declared_output_properties,
            ),
        )

    def _build_llm_node(
        self,
        node_name: str,
        bound_llm: BaseChatModel,
        bound_prompt: str,
        declared_input_properties: Optional[List[Property]],
        declared_output_properties: Optional[List[Property]],
    ) -> AgentSpecLlmNode:
        prompt_template, prompt_variables = self._converter._normalize_prompt_template_string(
            bound_prompt
        )
        input_properties_by_title = {
            property_.title: property_ for property_ in declared_input_properties or []
        }
        node_input_titles = set(input_properties_by_title)
        # LlmNode inputs are defined by detected Agent Spec `{{variable}}` placeholders. If the
        # LangGraph node already declares a named input schema, require it to match that contract
        # exactly so we do not silently drop wrapper inputs or invent a narrower Agent Spec
        # interface. Single-curly `{...}` text is preserved as-is and does not participate in the
        # exported input signature.
        if declared_input_properties is not None and node_input_titles != set(prompt_variables):
            raise ValueError(
                f"Unable to export `{node_name}` as an LlmNode because the wrapper node "
                f"inputs {sorted(node_input_titles)} do not match the wrapped LLM prompt "
                f"placeholders {sorted(prompt_variables)}."
            )

        input_properties: List[Property]
        if declared_input_properties is None:
            input_properties = [StringProperty(title=variable) for variable in prompt_variables]
        else:
            input_properties = [
                input_properties_by_title[variable] for variable in prompt_variables
            ]

        return AgentSpecLlmNode(
            name=node_name,
            llm_config=cast(
                "AgentSpecLlmConfig",
                self._converter.convert(bound_llm, self._referenced_objects),
            ),
            prompt_template=prompt_template,
            inputs=input_properties,
            outputs=declared_output_properties,
        )

    def _get_start_end_node_properties(
        self,
        start_end_node_name: str,
        public_schema: Any,
    ) -> List[Property]:
        opaque_boundary_title = (
            OPAQUE_INPUT_PROPERTY_TITLE
            if start_end_node_name == START
            else OPAQUE_OUTPUT_PROPERTY_TITLE
        )
        # Only expose named-field boundary ports when the public boundary schema is
        # narrower than the internal graph state. Otherwise we keep one opaque boundary port.
        if public_schema is self._graph.state_schema:
            return [
                _build_opaque_property_from_schema(
                    public_schema,
                    title=GRAPH_STATE_PROPERTY_TITLE,
                )
            ]
        return _get_named_field_properties_from_schema(public_schema) or [
            _build_opaque_property_from_schema(
                public_schema,
                title=opaque_boundary_title,
            )
        ]

    def _resolve_conditional_node_inputs(
        self,
        source_node_name: str,
        branch: BranchSpec,
    ) -> List[Property]:
        if named_field_properties := _get_named_field_properties_from_schema(branch.input_schema):
            return named_field_properties
        if source_node_name in self._graph.nodes:
            return [
                _build_opaque_property_from_schema(
                    self._graph.nodes[source_node_name].input_schema,
                    title=OPAQUE_INPUT_PROPERTY_TITLE,
                )
            ]
        return [
            _build_opaque_property_from_schema(
                self._graph.state_schema,
                title=OPAQUE_INPUT_PROPERTY_TITLE,
            )
        ]

    def _validate_data_flow_edges(
        self,
        nodes: List[AgentSpecNode],
        data_flow_edges: List[DataFlowEdge],
    ) -> None:
        """Require every named input in field-wiring mode to be satisfied locally."""
        for destination_node in nodes:
            if destination_node.name == START:
                continue

            required_input_titles = [
                property_.title
                for property_ in destination_node.inputs or []
                if not _is_opaque_property(property_)
                and property_.default is Property.empty_default
            ]
            if not required_input_titles:
                continue

            provided_input_titles = {
                edge.destination_input
                for edge in data_flow_edges
                if edge.destination_node.name == destination_node.name
            }
            missing_input_titles = [
                title for title in required_input_titles if title not in provided_input_titles
            ]
            if missing_input_titles:
                raise _FieldWiringFallbackRequired(
                    f"Unable to represent data flow into `{destination_node.name}` for fields: "
                    f"{', '.join(missing_input_titles)}."
                )


def _dedupe_name(
    name_candidate: str,
    referenced_object_names: Collection[str],
) -> str:
    """Return a unique component name by appending a numeric suffix when needed."""
    if name_candidate not in referenced_object_names:
        return name_candidate

    name_suffix = 1
    deduped_name = f"{name_candidate}_{name_suffix}"
    while deduped_name in referenced_object_names:
        name_suffix += 1
        deduped_name = f"{name_candidate}_{name_suffix}"
    return deduped_name


def _build_json_schema_from_schema_type(schema: Type[Any]) -> Optional[Dict[str, Any]]:
    """Build a raw JSON schema dictionary from a Python schema type."""
    if issubclass(schema, BaseModel):
        return schema.model_json_schema()
    if is_dataclass(schema):
        return TypeAdapter(schema).json_schema()
    try:
        return cast(
            Dict[str, Any],
            create_model(schema.__name__, **schema.__annotations__).model_json_schema(),
        )
    except Exception:
        return None


def _rename_top_level_property_titles(
    json_schema: Dict[str, Any],
    field_names: Collection[str],
) -> Dict[str, Any]:
    """Rewrite top-level property titles to their field names."""
    properties = json_schema.get("properties")
    if not isinstance(properties, dict):
        return json_schema

    normalized_properties = dict(properties)
    updated = False
    for field_name in field_names:
        field_schema = properties.get(field_name)
        if isinstance(field_schema, dict) and field_schema.get("title") != field_name:
            normalized_properties[field_name] = {**field_schema, "title": field_name}
            updated = True

    if not updated:
        return json_schema
    return {**json_schema, "properties": normalized_properties}


def _build_opaque_property_from_schema(
    schema: Type[Any],
    title: str,
) -> Property:
    """Build one opaque property from a schema type."""
    json_schema = _build_json_schema_from_schema_type(schema)
    if json_schema is None:
        # Some class-like schemas expose annotations that we cannot turn into a valid Pydantic
        # model/json schema. In that case we still export the port as one opaque property rather
        # than failing the whole graph conversion.
        return _OpaquePortProperty(json_schema={}, title=title)

    # Agent Spec validates nested schema titles too. Pydantic generates display titles such
    # as "Weather Data", which makes the opaque property invalid, so rewrite the
    # top-level field titles back to their schema field names before constructing `Property`.
    return _OpaquePortProperty(
        json_schema=_rename_top_level_property_titles(
            json_schema,
            getattr(schema, "__annotations__", {}),
        ),
        title=title,
    )


def _build_opaque_union_property(
    properties: List[Property],
    title: str,
) -> Property:
    """Build one opaque union port from multiple opaque fallback shapes."""
    return _OpaqueUnionProperty(
        any_of=properties,
        title=title,
    )


def _is_opaque_property(property_: Property) -> bool:
    """Return whether a property is one of the adapter's opaque fallback ports."""
    return isinstance(property_, (_OpaquePortProperty, _OpaqueUnionProperty))


def _get_langgraph_runnable_callable(runnable: Any) -> Any:
    """Return the callable stored on a LangGraph runnable, preferring sync then async wrappers."""
    if callable(getattr(runnable, "func", None)):
        return runnable.func
    if callable(getattr(runnable, "afunc", None)):
        return runnable.afunc
    return runnable


def _get_named_field_properties_from_schema(schema: Any) -> Optional[List[Property]]:
    """Return one property per schema field when the schema exposes named fields."""
    # Convert a structured schema into one Agent Spec property per field so later conversion
    # steps can wire nodes by field name instead of falling back to a single opaque port. If the
    # schema does not expose named fields, return None and let callers use opaque state-level
    # wiring instead.
    annotations = getattr(schema, "__annotations__", None)
    if not annotations:
        return None

    json_schema = _build_json_schema_from_schema_type(cast(Type[Any], schema))
    if json_schema is None:
        return None
    properties = json_schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return None

    result: List[Property] = []
    for field_name in list(annotations) + [name for name in properties if name not in annotations]:
        # Rebuild the field properties from the JSON schema so titles stay aligned with the
        # original field names rather than Pydantic-generated display names.
        field_schema = properties.get(field_name)
        if not isinstance(field_schema, dict):
            continue
        result.append(Property(title=field_name, json_schema={**field_schema, "title": field_name}))
    return result or None


def _get_langgraph_node_declared_properties(
    graph: StateGraph[Any, Any, Any],
    node: "StateNodeSpec[Any]",
) -> Tuple[Optional[List[Property]], Optional[List[Property]]]:
    """Infer the declared named-field inputs and outputs for a LangGraph node."""
    # Infer the named-field inputs and outputs a LangGraph node declares so leaf nodes can
    # expose concrete ports like "user_query" or "answer" instead of only the whole graph state.
    runnable = getattr(node, "runnable", None)
    unwrapped_callable = _get_langgraph_runnable_callable(runnable)
    bound_positional_arguments = 0
    bound_keyword_arguments: set[str] = set()
    # LangGraph may store node callables in wrappers or `functools.partial(...)`.
    # We currently unwrap those layers only to recover annotations when an explicit
    # named-field input schema is not already available on the node itself.
    while isinstance(unwrapped_callable, partial):
        bound_positional_arguments += len(unwrapped_callable.args)
        bound_keyword_arguments.update((unwrapped_callable.keywords or {}).keys())
        unwrapped_callable = unwrapped_callable.func

    type_hints: Dict[str, Any] = {}
    if callable(unwrapped_callable):
        try:
            type_hints = get_type_hints(unwrapped_callable)
        except Exception:
            raw_annotations = getattr(unwrapped_callable, "__annotations__", {}) or {}
            if isinstance(raw_annotations, dict):
                type_hints = raw_annotations

    input_properties: Optional[List[Property]] = None
    if node.input_schema is not graph.state_schema:
        # Prefer the explicit node input schema when LangGraph narrowed it below the graph state.
        input_properties = _get_named_field_properties_from_schema(node.input_schema)

    if input_properties is None and callable(unwrapped_callable):
        # Otherwise fall back to the first positional parameter annotation on the callable.
        try:
            signature = inspect.signature(unwrapped_callable)
        except (TypeError, ValueError):
            pass
        else:
            positional_parameter_index = 0
            for parameter in signature.parameters.values():
                if parameter.name in bound_keyword_arguments:
                    continue
                if parameter.kind not in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ):
                    continue
                if positional_parameter_index < bound_positional_arguments:
                    positional_parameter_index += 1
                    continue
                annotation = type_hints.get(parameter.name, parameter.annotation)
                if annotation is not inspect.Signature.empty:
                    input_properties = _get_named_field_properties_from_schema(annotation)
                break

    # Outputs come from the declared return type first, then from runnable.output_schema when
    # LangGraph wrapped the callable and kept the schema there instead.
    output_properties = _get_named_field_properties_from_schema(type_hints.get("return"))
    if output_properties is None:
        output_properties = _get_named_field_properties_from_schema(
            getattr(runnable, "output_schema", None)
        )

    return input_properties, output_properties


def _get_partial_bound_llm_and_prompt_from_node(
    node: "StateNodeSpec[Any]",
) -> Optional[Tuple[BaseChatModel, str]]:
    """Return the bound LLM and prompt string when a node is authored as a prompt+model partial."""
    partial_bound_arguments = _get_partial_bound_arguments_from_node(node)
    if partial_bound_arguments is None:
        return None

    unwrapped_callable, bound_arguments = partial_bound_arguments

    bound_llms = [
        (argument_name, argument_value)
        for argument_name, argument_value in bound_arguments.arguments.items()
        if isinstance(argument_value, BaseChatModel)
    ]
    if len(bound_llms) != 1:
        return None
    llm_parameter_name, bound_llm = bound_llms[0]
    if not _callable_has_invoke_call_on_parameter(unwrapped_callable, llm_parameter_name):
        return None

    bound_prompt_arguments = [
        argument_value
        for argument_name, argument_value in bound_arguments.arguments.items()
        if isinstance(argument_value, str)
        # Treat only explicitly named prompt/template strings as prompt candidates so unrelated
        # bound strings do not cause a generic partial wrapper to be promoted to LlmNode.
        and any(token in argument_name.lower() for token in ("prompt", "template"))
    ]
    if len(bound_prompt_arguments) != 1:
        return None

    return bound_llm, bound_prompt_arguments[0]


def _get_partial_bound_react_agent_invoke_target_from_node(
    converter: "LangGraphToAgentSpecConverter",
    node: "StateNodeSpec[Any]",
) -> Optional[LangGraphComponent]:
    """Return the partial-bound react agent when the callable directly invokes it."""
    partial_bound_arguments = _get_partial_bound_arguments_from_node(node)
    if partial_bound_arguments is None:
        return None

    unwrapped_callable, bound_arguments = partial_bound_arguments
    react_agent_bound_arguments = [
        (argument_name, argument_value)
        for argument_name, argument_value in bound_arguments.arguments.items()
        if isinstance(argument_value, (StateGraph, CompiledStateGraph))
        and converter._is_react_agent(argument_value)
    ]
    # We only promote the wrapper when exactly one bound argument is a react agent and the
    # callable visibly invokes that same parameter.
    if len(react_agent_bound_arguments) != 1:
        return None

    agent_parameter_name, agent_node_export_target = react_agent_bound_arguments[0]
    if not _callable_has_invoke_call_on_parameter(unwrapped_callable, agent_parameter_name):
        return None

    return agent_node_export_target


def _get_partial_bound_arguments_from_node(
    node: "StateNodeSpec[Any]",
) -> Optional[Tuple[Any, inspect.BoundArguments]]:
    """Return the unwrapped callable and final bound arguments for a partial-authored node."""
    runnable = getattr(node, "runnable", None)
    wrapped_callable = _get_langgraph_runnable_callable(runnable)
    if not isinstance(wrapped_callable, partial):
        return None

    partial_layers: List[Any] = []
    unwrapped_callable: Any = wrapped_callable
    # Flatten nested partials so we can recover the original function signature and the final
    # set of bound arguments LangGraph will call it with.
    while isinstance(unwrapped_callable, partial):
        partial_layers.append(unwrapped_callable)
        unwrapped_callable = unwrapped_callable.func

    if not callable(unwrapped_callable):
        return None

    bound_arguments_positional: List[Any] = []
    bound_arguments_keyword: Dict[str, Any] = {}
    for partial_layer in reversed(partial_layers):
        bound_arguments_positional.extend(partial_layer.args)
        bound_arguments_keyword.update(partial_layer.keywords or {})

    try:
        # `bind_partial()` mirrors how nested `partial(...)` objects accumulate arguments without
        # requiring the wrapper to have already bound every remaining parameter on the callable.
        bound_arguments = inspect.signature(unwrapped_callable).bind_partial(
            *bound_arguments_positional,
            **bound_arguments_keyword,
        )
    except (TypeError, ValueError):
        return None

    return unwrapped_callable, bound_arguments


def _callable_has_invoke_call_on_parameter(callable_obj: Any, parameter_name: str) -> bool:
    """Return whether the callable source contains `<parameter>.invoke(...)` or `.ainvoke(...)`."""
    try:
        callable_source = inspect.getsource(callable_obj)
    except (OSError, TypeError):
        callable_source = None

    if callable_source is not None:
        try:
            parsed_source = ast.parse(textwrap.dedent(callable_source))
        except SyntaxError:
            pass
        else:
            # Prefer source inspection because it keeps the heuristic straightforward and works
            # across normal `def`/`async def` wrappers.
            for ast_node in ast.walk(parsed_source):
                if not isinstance(ast_node, ast.Call):
                    continue
                called_function = ast_node.func
                if not isinstance(called_function, ast.Attribute):
                    continue
                if called_function.attr not in {"invoke", "ainvoke"}:
                    continue
                if (
                    isinstance(called_function.value, ast.Name)
                    and called_function.value.id == parameter_name
                ):
                    return True

    try:
        instructions = list(dis.get_instructions(callable_obj))
    except TypeError:
        return False

    # Some callables do not have retrievable source (for example interactive definitions), so
    # fall back to bytecode and look for `<parameter>.<invoke-like-attr>` loads there.
    for current_instruction, next_instruction in zip(instructions, instructions[1:]):
        if not current_instruction.opname.startswith("LOAD_FAST"):
            continue
        if current_instruction.argval != parameter_name:
            continue
        if next_instruction.opname not in {"LOAD_ATTR", "LOAD_METHOD"}:
            continue
        if next_instruction.argval in {"invoke", "ainvoke"}:
            return True

    return False


def _langgraph_edge_convert_to_agentspec_ctrl_flow(
    edge: Tuple[str, str],
    referenced_objects: Dict[str, AgentSpecComponent],
) -> ControlFlowEdge:
    """Convert a LangGraph control edge into an Agent Spec control edge."""
    from_, to = edge

    return ControlFlowEdge(
        name=f"{from_}_to_{to}",
        from_node=cast(AgentSpecNode, referenced_objects[from_]),
        to_node=cast(AgentSpecNode, referenced_objects[to]),
    )


def _build_data_flow_edges_for_node_pair(
    source_node: AgentSpecNode,
    destination_node: AgentSpecNode,
    edge_name_prefix: str,
) -> List[DataFlowEdge]:
    """Build all Agent Spec data edges for one converted source/destination node pair."""
    # Prefer explicit field-to-field data edges when both nodes expose named ports.
    destination_input_titles = {property_.title for property_ in destination_node.inputs or []}
    shared_titles = [
        property_.title
        for property_ in source_node.outputs or []
        if property_.title in destination_input_titles
    ]
    if shared_titles:
        return [
            DataFlowEdge(
                name=f"{edge_name_prefix}_{title}_data_edge",
                source_node=source_node,
                destination_node=destination_node,
                source_output=title,
                destination_input=title,
            )
            for title in shared_titles
        ]

    source_outputs = source_node.outputs or []
    destination_inputs = destination_node.inputs or []

    # Some nodes legitimately do not consume any data from their predecessor (for example,
    # static-prompt LlmNodes). In that case we keep only the control-flow edge.
    if len(destination_inputs) == 0 or len(source_outputs) == 0:
        return []

    # Fall back to one opaque-port edge when both nodes only expose a single opaque port.
    if (
        len(source_outputs) == 1
        and len(destination_inputs) == 1
        and _is_opaque_property(source_outputs[0])
        and _is_opaque_property(destination_inputs[0])
    ):
        return [
            DataFlowEdge(
                name=f"{edge_name_prefix}_data_edge",
                source_node=source_node,
                destination_node=destination_node,
                source_output=source_outputs[0].title,
                destination_input=destination_inputs[0].title,
            )
        ]

    raise _FieldWiringFallbackRequired(
        f"Unable to represent data flow between `{source_node.name}` and "
        f"`{destination_node.name}` without mixing opaque-port wiring and named field wiring."
    )
