# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from dataclasses import is_dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Type, cast

from pydantic import BaseModel, TypeAdapter, create_model

from pyagentspec import Property
from pyagentspec.adapters.langgraph._types import (
    BranchSpec,
    CompiledStateGraph,
    LangGraphComponent,
    StateGraph,
    StateNodeSpec,
    langgraph_graph,
)
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.node import Node as AgentSpecNode
from pyagentspec.flows.nodes import BranchingNode, EndNode, FlowNode, StartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
from pyagentspec.property import StringProperty, UnionProperty
from pyagentspec.tools.servertool import ServerTool as AgentSpecServerTool

if TYPE_CHECKING:
    from pyagentspec.adapters.langgraph._agentspecconverter import LangGraphToAgentSpecConverter

END = langgraph_graph.END
START = langgraph_graph.START


def _validate_conditional_edges_support(graph: LangGraphComponent) -> None:
    if isinstance(graph, CompiledStateGraph):
        graph = graph.builder
    for branch_specs in graph.branches.values():
        if len(branch_specs) > 1:
            raise ValueError(
                "Conversion of multiple conditional edges with the same source node is not yet supported"
            )


def _langgraph_graph_convert_to_agentspec(
    converter: "LangGraphToAgentSpecConverter",
    graph: LangGraphComponent,
    referenced_objects: Dict[str, AgentSpecComponent],
) -> AgentSpecFlow:
    _validate_conditional_edges_support(graph)
    nodes: List[AgentSpecNode] = []
    flow_name = graph.name if isinstance(graph, CompiledStateGraph) else "LangGraph Flow"
    if isinstance(graph, CompiledStateGraph):
        graph = graph.builder
    for node_name, node in graph.nodes.items():
        if node_name in (START, END):
            continue
        if isinstance(node.runnable, (StateGraph, CompiledStateGraph)):
            subgraph_node = cast(AgentSpecFlow, converter.convert(node.runnable, {}))
            flow_node = FlowNode(
                name=node_name,
                subflow=subgraph_node,
            )
            referenced_objects[node_name] = flow_node
            nodes.append(flow_node)
        else:
            nodes.append(
                _langgraph_node_convert_to_agentspec(graph, node_name, node, referenced_objects)
            )

    start_node, end_node = _get_start_end_nodes(graph, referenced_objects)
    nodes.append(start_node)
    nodes.append(end_node)

    control_flow_edges: List[ControlFlowEdge] = []
    data_flow_edges: List[DataFlowEdge] = []
    for edge in graph.edges:
        control_flow_edges.append(
            _langgraph_edges_convert_to_agentspec_ctrl_flow(edge, referenced_objects)
        )
        data_flow_edges.append(
            _langgraph_edges_convert_to_agentspec_data_flow(graph, edge, referenced_objects)
        )

    for branch in graph.branches.items():
        source_node, branch_specs = branch
        additional_nodes, additional_ctrl_flows, additional_data_flows = (
            _langgraph_branch_convert_to_agentspec(
                source_node, branch_specs, graph, referenced_objects
            )
        )
        nodes.extend(additional_nodes)
        control_flow_edges.extend(additional_ctrl_flows)
        data_flow_edges.extend(additional_data_flows)

    # Add missing edges towards END nodes for nodes with no outgoing edges
    for agentspec_node in nodes:
        if agentspec_node.name == START or agentspec_node.name == END:
            continue
        if not any(
            ctrl_flow.from_node.name == agentspec_node.name for ctrl_flow in control_flow_edges
        ):
            edge = agentspec_node.name, END
            control_flow_edges.append(
                _langgraph_edges_convert_to_agentspec_ctrl_flow(edge, referenced_objects)
            )
            data_flow_edges.append(
                _langgraph_edges_convert_to_agentspec_data_flow(graph, edge, referenced_objects)
            )

    return AgentSpecFlow(
        name=flow_name,
        start_node=start_node,
        nodes=nodes,
        control_flow_connections=control_flow_edges,
        data_flow_connections=data_flow_edges,
    )


def _langgraph_branch_convert_to_agentspec(
    source_node: str,
    branch_specs: Dict[str, BranchSpec],
    graph: StateGraph[Any, Any, Any, Any],
    referenced_objects: Dict[str, AgentSpecComponent],
) -> Tuple[List[AgentSpecNode], List[ControlFlowEdge], List[DataFlowEdge]]:
    additional_nodes: List[AgentSpecNode] = []
    additional_ctrl_flows: List[ControlFlowEdge] = []
    additional_data_flows: List[DataFlowEdge] = []

    for conditional_node_name, branch_spec in branch_specs.items():
        mapping: Dict[str, str]
        if branch_spec.ends is None:
            raise TypeError(
                f"""Mapping for {conditional_node_name} not found.
            Make sure to add proper return type hints to the branching function."""
            )
        mapping = {str(k): v for k, v in branch_spec.ends.items()}

        # Create the conditional node to compute which branch to go to
        conditional_node_input = _resolve_output_properties(graph, [source_node])
        conditional_node = AgentSpecToolNode(
            name=conditional_node_name,
            tool=AgentSpecServerTool(
                name=f"{conditional_node_name}_tool",
                inputs=[conditional_node_input],
                outputs=[StringProperty(title=BranchingNode.DEFAULT_INPUT)],
            ),
        )
        additional_nodes.append(conditional_node)
        referenced_objects[conditional_node_name] = conditional_node

        # The source node goes to the conditional node to compute which
        # branch to go to
        source_node_to_conditional_node_ctrl_flow = ControlFlowEdge(
            name=f"{source_node}_to_{conditional_node_name}",
            from_node=cast(AgentSpecNode, referenced_objects[source_node]),
            to_node=conditional_node,
        )
        additional_ctrl_flows.append(source_node_to_conditional_node_ctrl_flow)
        source_node_to_conditional_node_data_flow = DataFlowEdge(
            name=f"{source_node}_to_{conditional_node_name}_data_edge",
            source_node=cast(AgentSpecNode, referenced_objects[source_node]),
            source_output=conditional_node_input.title,
            destination_node=conditional_node,
            destination_input=conditional_node_input.title,
        )
        additional_data_flows.append(source_node_to_conditional_node_data_flow)

        # Create the branching node for the current conditional edge
        branching_node_name = f"{conditional_node_name}_branching_node"
        branching_node = BranchingNode(
            name=branching_node_name,
            mapping=mapping,
        )
        additional_nodes.append(branching_node)
        referenced_objects[branching_node_name] = branching_node

        # Create ControlFlowEdge to go from the conditional node to the branching node
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

        # For each different target node, we create a control flow edge
        # that goes from the branching node to the target node if `from_branch == branch_name`
        for branch_name, target_node_name in mapping.items():
            additional_ctrl_flows.append(
                ControlFlowEdge(
                    name=f"{branching_node_name}_to_{target_node_name}",
                    from_node=branching_node,
                    to_node=cast(AgentSpecNode, referenced_objects[target_node_name]),
                    from_branch=branch_name,
                )
            )
            additional_data_flows.append(
                DataFlowEdge(
                    name=f"data_{source_node}_to_{target_node_name}",
                    source_node=cast(AgentSpecNode, referenced_objects[source_node]),
                    source_output=_resolve_output_properties(graph, [target_node_name]).title,
                    destination_node=cast(AgentSpecNode, referenced_objects[target_node_name]),
                    destination_input=_resolve_output_properties(graph, [target_node_name]).title,
                ),
            )

        # We create an edge for the default case, that goes straight to the end node
        # This should "in practice" never be reached
        name = f"{branching_node_name}_to_{END}"
        if not any(flow.name == name for flow in additional_ctrl_flows):
            additional_ctrl_flows.append(
                ControlFlowEdge(
                    name=name,
                    from_node=branching_node,
                    to_node=cast(AgentSpecNode, referenced_objects[END]),
                    from_branch=BranchingNode.DEFAULT_BRANCH,
                )
            )

    return (additional_nodes, additional_ctrl_flows, additional_data_flows)


def _get_start_end_nodes(
    graph: StateGraph[Any, Any, Any],
    referenced_objects: Dict[str, AgentSpecComponent],
) -> Tuple[AgentSpecNode, AgentSpecNode]:
    if START not in referenced_objects:
        if START not in graph.nodes:
            referenced_objects[START] = StartNode(
                name=START,
                inputs=[_get_property_from_schema(graph.input_schema)],
                outputs=[_get_property_from_schema(graph.input_schema)],
            )
        else:
            referenced_objects[START] = _langgraph_node_convert_to_agentspec(
                graph,
                START,
                graph.nodes[START],
                referenced_objects,
            )

    if END not in referenced_objects:
        if END not in graph.nodes:
            referenced_objects[END] = EndNode(
                name=END,
                inputs=[_get_property_from_schema(graph.output_schema)],
                outputs=[_get_property_from_schema(graph.output_schema)],
            )
        else:
            referenced_objects[END] = _langgraph_node_convert_to_agentspec(
                graph,
                END,
                graph.nodes[END],
                referenced_objects,
            )

    return (
        cast(AgentSpecNode, referenced_objects[START]),
        cast(AgentSpecNode, referenced_objects[END]),
    )


def _get_property_from_schema(schema: Type[Any]) -> Property:
    if issubclass(schema, BaseModel):
        json_schema = schema.model_json_schema()
    elif is_dataclass(schema):
        json_schema = TypeAdapter(schema).json_schema()
    else:
        try:
            input_model = create_model(schema.__name__, **schema.__annotations__)
            json_schema = input_model.model_json_schema()
        except Exception:
            return Property(json_schema={}, title="state")  # "Any" property

    properties = json_schema["properties"]

    # Pydantic keeps changing the title of the fields to PascalCase
    # We overwrite the title with the proper field name
    for field in schema.__annotations__:
        if field in properties:
            properties[field]["title"] = field

    input_property = Property(json_schema=json_schema, title="state")
    return input_property


def _resolve_output_properties(
    graph: StateGraph[Any, Any, Any],
    target_nodes: List[str],
) -> Property:
    match target_nodes:
        case []:
            # This case handles nodes that don't have an explicit outgoing edge
            # They are then routed to the end node automatically
            # And thus the property is the output schema of the entire graph
            return _get_property_from_schema(graph.output_schema)
        case [node_name]:
            # This case is used to get the output property for going from a node to a target node
            if node_name == START:
                return _get_property_from_schema(graph.input_schema)
            if node_name == END:
                return _get_property_from_schema(graph.output_schema)
            return _get_property_from_schema(graph.nodes[node_name].input_schema)
        case nodes:
            # This case is used to get a union property of all the target nodes
            properties: List[Property] = []
            for node_name in nodes:
                properties.append(_resolve_output_properties(graph, [node_name]))
            union_property = UnionProperty(any_of=properties)
            return union_property


def _langgraph_node_convert_to_agentspec(
    graph: StateGraph[Any, Any, Any],
    node_name: str,
    node: "StateNodeSpec[Any]",
    referenced_objects: Dict[str, AgentSpecComponent],
) -> AgentSpecNode:
    if node_name in referenced_objects:
        converted_node = referenced_objects[node_name]
        if not isinstance(converted_node, AgentSpecNode):
            raise TypeError(
                f"expected node {converted_node} to be of type {AgentSpecNode}, got: {converted_node.__class__}"
            )
        return converted_node

    input_property = _get_property_from_schema(node.input_schema)

    target_nodes: List[str] = []
    for from_, to in graph.edges:
        if from_ != to and from_ == node_name:
            target_nodes.append(to)
    output_property = _resolve_output_properties(graph, target_nodes)

    tool = AgentSpecServerTool(
        name=node_name + "_tool",
        inputs=[input_property],
        outputs=[output_property],
    )
    referenced_objects[node_name] = AgentSpecToolNode(
        name=node_name,
        tool=tool,
        inputs=[input_property],
        outputs=[output_property],
    )
    return cast(AgentSpecNode, referenced_objects[node_name])


def _langgraph_edges_convert_to_agentspec_ctrl_flow(
    edge: Tuple[str, str],
    referenced_objects: Dict[str, AgentSpecComponent],
) -> ControlFlowEdge:
    from_, to = edge
    name = f"{from_}_to_{to}"

    return ControlFlowEdge(
        name=name,
        from_node=cast(AgentSpecNode, referenced_objects[from_]),
        to_node=cast(AgentSpecNode, referenced_objects[to]),
    )


def _langgraph_edges_convert_to_agentspec_data_flow(
    graph: StateGraph[Any, Any, Any],
    edge: Tuple[str, str],
    referenced_objects: Dict[str, AgentSpecComponent],
) -> DataFlowEdge:
    from_, to = edge
    name = f"{from_}_to_{to}_data_edge"

    if from_ == START:
        internal_state_property = _get_property_from_schema(graph.input_schema)
    else:
        internal_state_property = _get_property_from_schema(graph.state_schema)

    destination_input_property = _resolve_output_properties(graph, [to])

    source_node = cast(AgentSpecNode, referenced_objects[from_])
    destination_node = cast(AgentSpecNode, referenced_objects[to])

    data_flow_edge = DataFlowEdge(
        name=name,
        source_node=source_node,
        destination_node=destination_node,
        source_output=internal_state_property.title,
        destination_input=destination_input_property.title,
    )
    return data_flow_edge
