# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import Dict, List, Optional

from pydantic import SerializeAsAny
from typing_extensions import Self

from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.node import Node
from pyagentspec.property import Property, properties_have_same_type
from pyagentspec.validation_helpers import model_validator_with_error_accumulation


class Flow(AgenticComponent):
    """
    A flow is a component to model sequences of operations to do in a precised order.

    The operations and sequence is defined by the nodes and transitions associated to the flow.
    Steps can be deterministic, or for some use LLMs.

    Example
    -------
    >>> from pyagentspec.property import Property
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.flows.nodes import LlmNode, StartNode, EndNode
    >>> prompt_property = Property(
    ...     json_schema={"title": "prompt", "type": "string"}
    ... )
    >>> llm_output_property = Property(
    ...     json_schema={"title": "llm_output", "type": "string"}
    ... )
    >>> start_node = StartNode(name="start", inputs=[prompt_property])
    >>> end_node = EndNode(name="end", outputs=[llm_output_property])
    >>> llm_node = LlmNode(
    ...     name="simple llm node",
    ...     llm_config=llm_config,
    ...     prompt_template="{{prompt}}",
    ...     inputs=[prompt_property],
    ...     outputs=[llm_output_property],
    ... )
    >>> flow = Flow(
    ...     name="Simple prompting flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, llm_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(name="start_to_llm", from_node=start_node, to_node=llm_node),
    ...         ControlFlowEdge(name="llm_to_end", from_node=llm_node, to_node=end_node),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="prompt_edge",
    ...             source_node=start_node,
    ...             source_output="prompt",
    ...             destination_node=llm_node,
    ...             destination_input="prompt",
    ...         ),
    ...         DataFlowEdge(
    ...             name="llm_output_edge",
    ...             source_node=llm_node,
    ...             source_output="llm_output",
    ...             destination_node=end_node,
    ...             destination_input="llm_output"
    ...         ),
    ...     ],
    ... )

    """

    start_node: SerializeAsAny[Node]
    """The starting node of this flow. It must be also part of the nodes list"""
    nodes: List[SerializeAsAny[Node]]
    """The list of nodes that compose this Flow"""
    control_flow_connections: List[ControlFlowEdge]
    """The list of edges that define the control flow of this Flow"""
    data_flow_connections: Optional[List[DataFlowEdge]] = None
    """The list of edges that define the data flow of this Flow"""

    def _get_end_nodes(self) -> List[Node]:
        # Import here to avoid circular dependencies
        from pyagentspec.flows.nodes.endnode import EndNode

        return [
            end_node for end_node in getattr(self, "nodes", []) if isinstance(end_node, EndNode)
        ]

    def _get_inferred_inputs(self) -> List[Property]:
        return (self.start_node.inputs or []) if hasattr(self, "start_node") else []

    def _get_inferred_outputs(self) -> List[Property]:
        # If outputs are provided, we don't try to infer them
        if self.outputs is not None:
            return self.outputs
        end_nodes = self._get_end_nodes()
        # Outputs are inferred from all the end nodes in the flow
        end_node_outputs = [
            end_node_output
            for end_node in end_nodes
            for end_node_output in (end_node.outputs or [])
        ]
        # The inferred outputs are those that appear in all the end nodes
        flow_outputs_by_name = {}
        for end_node_output in end_node_outputs:
            output_name = end_node_output.json_schema["title"]
            if output_name not in flow_outputs_by_name:
                if all(
                    any(
                        output.json_schema["title"] == output_name
                        for output in (end_node.outputs or [])
                    )
                    for end_node in end_nodes
                ):
                    flow_outputs_by_name[output_name] = end_node_output
        return list(flow_outputs_by_name.values())

    @model_validator_with_error_accumulation
    def _validate_flow_uses_start_node_correctly(self) -> Self:
        from pyagentspec.flows.nodes import StartNode

        # There is exactly one StartNode in the Flow
        start_nodes = [node for node in self.nodes if isinstance(node, StartNode)]
        if len(start_nodes) != 1:
            raise ValueError(
                "A Flow should be composed of exactly one StartNode, "
                f"contains {len(start_nodes)}.\nPlease check for missing "
                "or duplicated nodes."
            )

        # and this StartNode is the `start_node` node
        flow_start_node = start_nodes[0]
        if self.start_node is not flow_start_node:
            raise ValueError(
                "The ``start_node`` node is not matching the start node from the "
                f"list of nodes in the flow ``nodes`` (start node was '{self.start_node.name}', "
                f"found '{flow_start_node.name}' in ``nodes``."
            )

        # Finally, the start_node must have exactly one outgoing control flow edge
        start_node_outgoing_transitions_names = [
            edge.name for edge in self.control_flow_connections if edge.from_node is self.start_node
        ]
        if len(start_node_outgoing_transitions_names) != 1:
            raise ValueError(
                "The ``start_node`` should have exactly one outgoing control flow edge, "
                f"found {len(start_node_outgoing_transitions_names)}. Please check the list of "
                "control flow edges."
            )
        return self

    @model_validator_with_error_accumulation
    def _validate_start_node_has_no_incoming_control_flow_edge(self) -> Self:
        from pyagentspec.flows.nodes import StartNode

        control_flow_to_start_nodes_names = [
            edge.name
            for edge in self.control_flow_connections
            if isinstance(edge.to_node, StartNode)
        ]
        if len(control_flow_to_start_nodes_names) > 0:
            raise ValueError(
                "Transitions to StartNode is not accepted. Please check the "
                f"following control flow edges: \n{control_flow_to_start_nodes_names}"
            )
        return self

    @model_validator_with_error_accumulation
    def _validate_flow_has_at_least_one_end_node(self) -> Self:
        from pyagentspec.flows.nodes import EndNode

        next_flow_end_node = next((node for node in self.nodes if isinstance(node, EndNode)), None)
        if next_flow_end_node is None:
            raise ValueError(
                "A Flow should be composed of at least one EndNode but "
                "didn't find any in ``nodes``. Please make sure to add "
                "EndNode(s) to the flow."
            )
        return self

    @model_validator_with_error_accumulation
    def _validate_each_end_node_has_at_least_one_incoming_control_flow_edge(self) -> Self:
        for node in self._get_end_nodes():
            end_node_incoming_control_flow_edges = [
                edge for edge in self.control_flow_connections if edge.to_node is node
            ]
            if len(end_node_incoming_control_flow_edges) == 0:
                raise ValueError(
                    "Found an end node without any incoming control flow edge, "
                    f"which is not permitted (node is '{node.name}'). Please check the "
                    "control flow edges."
                )
        return self

    @model_validator_with_error_accumulation
    def _validate_each_end_node_has_no_outgoing_control_flow_edges(self) -> Self:
        from pyagentspec.flows.nodes import EndNode

        control_flow_from_end_nodes_names = [
            edge.name
            for edge in self.control_flow_connections
            if isinstance(edge.from_node, EndNode)
        ]
        if len(control_flow_from_end_nodes_names) > 0:
            raise ValueError(
                "Transitions from EndNode is not accepted. Please check the "
                f"following control flow connections: \n{control_flow_from_end_nodes_names}"
            )

        return self

    @model_validator_with_error_accumulation
    def _validate_control_edges_use_existing_nodes(self) -> Self:
        node_ids = {node.id for node in getattr(self, "nodes", [])}
        for control_edge in getattr(self, "control_flow_connections", []) or []:
            if control_edge.from_node.id not in node_ids:
                raise ValueError(
                    f"A control flow edge was defined, but the flow does not contain"
                    f" the source node '{control_edge.from_node.name}'"
                )
            if control_edge.to_node.id not in node_ids:
                raise ValueError(
                    f"A control flow edge was defined, but the flow does not contain"
                    f" the destination node '{control_edge.to_node.name}'"
                )
        return self

    @model_validator_with_error_accumulation
    def _validate_data_edges_use_existing_nodes(self) -> Self:
        node_ids = {node.id for node in getattr(self, "nodes", [])}
        for data_edge in getattr(self, "data_flow_connections", []) or []:
            if data_edge.source_node.id not in node_ids:
                raise ValueError(
                    f"A data flow edge was defined, but the flow does not contain the"
                    f" source node '{data_edge.source_node.name}'"
                )
            if data_edge.destination_node.id not in node_ids:
                raise ValueError(
                    f"A data flow edge was defined, but the flow does not contain the"
                    f" destination node '{data_edge.destination_node.name}'"
                )
        return self

    @model_validator_with_error_accumulation
    def _validate_endnode_outputs_with_same_name_have_consistent_types(self) -> Self:
        end_node_outputs = [
            end_node_output
            for end_node in self._get_end_nodes()
            for end_node_output in (end_node.outputs or [])
        ]
        flow_outputs_by_name: Dict[str, Property] = {}
        for end_node_output in end_node_outputs:
            output_name = end_node_output.json_schema["title"]
            if output_name in flow_outputs_by_name:
                if not properties_have_same_type(
                    end_node_output, flow_outputs_by_name[output_name]
                ):
                    raise ValueError(
                        f"Two EndNode outputs have the same name `{output_name}`, but different types"
                    )
            else:
                flow_outputs_by_name[output_name] = end_node_output
        return self

    @model_validator_with_error_accumulation
    def _validate_flow_outputs_appear_in_all_endnodes_or_have_default(self) -> Self:
        for flow_output in getattr(self, "outputs", []):
            output_name = flow_output.json_schema["title"]
            if "default" not in flow_output.json_schema:
                if output_not_in_all_end_nodes := not all(
                    any(
                        output.json_schema["title"] == output_name
                        and properties_have_same_type(output, flow_output)
                        for output in (end_node.outputs or [])
                    )
                    for end_node in self._get_end_nodes()
                ):
                    raise ValueError(
                        f"Flow output named `{output_name}` does not have a default value "
                        f"and it does not appear in every EndNode with the expected type"
                    )
        return self
