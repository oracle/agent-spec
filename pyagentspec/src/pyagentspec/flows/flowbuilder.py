# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the flow builder for Agent Spec Flows."""

from typing import Literal, cast, overload

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import BranchingNode, EndNode, StartNode
from pyagentspec.property import Property
from pyagentspec.serialization import AgentSpecSerializer

DEFAULT_FLOW_NAME = "Flow"


class FlowBuilder:
    """A builder for constructing Agent Spec Flows."""

    start_node: Node

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.control_flow_connections: list[ControlFlowEdge] = []
        self.data_flow_connections: list[DataFlowEdge] = []
        self._conditional_edge_counter = 1
        self._end_node_counter = 1

    def add_node(self, node: Node) -> "FlowBuilder":
        """
        Add a new node to the Flow.

        Parameters
        ----------
        node:
            Node to add to the Flow.
        """
        name = node.name
        if name in self.nodes:
            raise ValueError(f"Node with name '{name}' already exists")
        self.nodes[name] = node
        return self

    def add_edge(
        self,
        source_node: list[Node | str] | Node | str,
        dest_node: Node | str,
        from_branch: list[str | None] | str | None = None,
        edge_name: str | None = None,
    ) -> "FlowBuilder":
        """
        Add a control flow edge to the Flow.

        Parameters
        ----------
        source_node:
            Single node/name (creates 1 edge) or list of nodes/names (creates N edges)
            which constitute the start of the control flow edge(s).
        dest_node:
            Node/name that constitutes the end of the control flow edge(s).
        from_branch:
            Optional source branch name(s) to use in the control flow edge(s).
            When a list, must be of the same length as the list of source_node.
        edge_name:
            Name for the edge. Defaults to f"control_edge_{source_node.name}_{dest_node.name}_{from_branch}".
        """
        start_node_list: list[Node | str]
        from_branch_list: list[str | None]
        if isinstance(source_node, list):
            start_node_list = source_node
            from_branch_list = (
                from_branch
                if isinstance(from_branch, list)
                else [from_branch] * len(start_node_list)
            )
        else:
            if isinstance(from_branch, list):
                raise ValueError(
                    "A list was given for `from_branch` but `source_node` is not a list of nodes. "
                    "Make sure that the types are matching"
                )
            start_node_list = [source_node]
            from_branch_list = [from_branch]

        if len(start_node_list) != len(from_branch_list):
            raise ValueError("source_node and from_branch must have the same length")

        destination_node = self._get_node(dest_node, prefix_err_msg="End node")

        for start_key_, from_branch_ in zip(start_node_list, from_branch_list):
            source_node_ = self._get_node(start_key_, prefix_err_msg="Start node")
            self.control_flow_connections.append(
                ControlFlowEdge(
                    name=edge_name
                    or f"control_edge_{source_node_.name}_{destination_node.name}_{from_branch_}",
                    from_node=source_node_,
                    from_branch=from_branch_,
                    to_node=destination_node,
                )
            )
        return self

    def add_data_edge(
        self,
        source_node: Node | str,
        dest_node: Node | str,
        data_name: str | tuple[str, str],
        edge_name: str | None = None,
    ) -> "FlowBuilder":
        """
        Add a data flow edge to the Flow.

        Parameters
        ----------
        source_node:
            Node/name which constitute the start/source of the data flow edge.
        dest_node:
            Node/name that constitutes the end/destination of the data flow edge.
        data_name:
            Name of the data property to propagate between the two nodes, either
            str when the name is shared, or tuple (source_output, destination_input)
            when the names are different.
        edge_name:
            Name for the edge. Defaults to "data_flow_edge"
        """

        source_node_ = self._get_node(source_node, prefix_err_msg="Source node")
        dest_node_ = self._get_node(dest_node, prefix_err_msg="Destination node")

        # Validate data_name
        if isinstance(data_name, tuple):
            if len(data_name) != 2 or not all(isinstance(x, str) for x in data_name):
                raise ValueError("data_name tuple must be (str, str)")
            source_output, dest_input = data_name
        elif isinstance(data_name, str):
            source_output, dest_input = data_name, data_name
        else:
            raise ValueError("data_name must be str or tuple[str, str]")

        self.data_flow_connections.append(
            DataFlowEdge(
                name=edge_name or "data_flow_edge",
                source_node=source_node_,
                source_output=source_output,
                destination_node=dest_node_,
                destination_input=dest_input,
            )
        )
        return self

    def add_sequence(self, nodes: list[Node]) -> "FlowBuilder":
        """
        Add a sequence of nodes to the Flow.

        Parameters
        ----------
        nodes:
            List of nodes to add to the Flow.
        """
        # Add all nodes first (allows mixing with other builder calls)
        for node_ in nodes:
            self.add_node(node_)

        # Then wire control flow edges between consecutive nodes
        if len(nodes) > 1:
            for left, right in zip(nodes[:-1], nodes[1:]):
                self.add_edge(left, right)

        return self

    def add_conditional(
        self,
        source_node: Node | str,
        source_value: str | tuple[Node | str, str],
        destination_map: dict[str, Node | str],
        default_destination: Node | str,
        branching_node_name: str | None = None,
    ) -> "FlowBuilder":
        """
        Add a condition/branching to the Flow.

        Parameters
        ----------
        source_node:
            Node/name from which to start the branching from.
        source_value:
            Which value to use to perform the branching condition. If str, uses the `source_node`.
            If `tuple[Node | str, str]`, uses the specified node and output name.
        destination_map:
            Dictionary which specifies which node to transition to for given values.
        default_destination:
            Node/name where to transition to if no matching value/transition is found
            in the `destination_map`.
        branching_node_name:
            Optional name for the branching node. Uses automatically generated auto-incrementing
            names if not providing.

        Example
        -------
        >>> from pyagentspec.flows.flowbuilder import FlowBuilder
        >>> from pyagentspec.flows.nodes import LlmNode
        >>>
        >>> flow = (
        ...     FlowBuilder()
        ...     .add_node(LlmNode(name="source_node", llm_config=llm_config, prompt_template="Generate 'fail' or 'success'"))
        ...     .add_node(LlmNode(name="fail_node", llm_config=llm_config, prompt_template="Print 'FAIL'"))
        ...     .add_node(LlmNode(name="success_node", llm_config=llm_config, prompt_template="Print 'SUCESS'"))
        ...     .add_conditional("source_node", LlmNode.DEFAULT_OUTPUT, {"success": "success_node", "fail": "fail_node"}, default_destination="fail_node")
        ...     .set_entry_point("source_node")
        ...     .set_finish_points(["fail_node", "success_node"])
        ...     .build()
        ... )

        """
        data_edge_name = f"DataEdgeForConditional_{self._conditional_edge_counter}"

        if branching_node_name:
            conditional_node_name = branching_node_name
        else:
            conditional_node_name = f"ConditionalNode_{self._conditional_edge_counter}"
            self._conditional_edge_counter += 1

        destination_map_str = {
            k: (n.name if isinstance(n, Node) else n) for k, n in destination_map.items()
        }
        self.add_node(
            BranchingNode(
                name=conditional_node_name,
                mapping=destination_map_str,
            )
        )

        # Prevent user from colliding with default branch name
        if BranchingNode.DEFAULT_BRANCH in destination_map_str.values():
            raise ValueError(
                f"destination_map cannot contain reserved branch label '{BranchingNode.DEFAULT_BRANCH}'. "
                "Please use `default_destination` instead."
            )

        # adding control flow edges
        self.add_edge(source_node, conditional_node_name)
        for destination_node_name in destination_map_str.values():
            self.add_edge(conditional_node_name, destination_node_name, destination_node_name)

        self.add_edge(conditional_node_name, default_destination, BranchingNode.DEFAULT_BRANCH)

        # adding data flow edge for the input
        if source_value:
            source_node_ = source_node if not isinstance(source_value, tuple) else source_value[0]
            source_value_ = source_value if not isinstance(source_value, tuple) else source_value[1]
            self.add_data_edge(
                source_node_,
                conditional_node_name,
                (source_value_, BranchingNode.DEFAULT_INPUT),
                data_edge_name,
            )
        return self

    def set_entry_point(
        self, node: Node | str, inputs: list[Property] | None = None
    ) -> "FlowBuilder":
        """
        Sets the first node to execute in the Flow.

        Parameters
        ----------
        node:
            Node/name that will first be run in the Flow.
        inputs:
            Optional list of inputs for the flow. If `None`, auto-detects as the list of
            inputs that are not generated at some point in the execution of the flow.
        """
        if getattr(self, "start_node", None) is not None:
            raise ValueError("Entry point already set; set_entry_point cannot be called twice")

        start_node_name = "StartNode"
        start_node = StartNode(name=start_node_name, inputs=inputs)
        self.start_node = start_node
        self.add_node(start_node)
        self.add_edge(start_node_name, node)
        return self

    def set_finish_points(
        self,
        node: list[Node | str] | Node | str,
        outputs: list[list[Property] | None] | list[Property] | None = None,
    ) -> "FlowBuilder":
        """
        Specifies the potential points of completion of the Flow.

        Parameters
        ----------
        node:
            Node/name or list of nodes/names which are terminal nodes in the Flow.
        outputs:
            Optional list of outputs for the flow branches corresponding to each
            of the specified terminal nodes. Must be of the same length as `node`.
            If `None`, auto-detects as the intersection of all the outputs generated by
            any node in any execution branch of the flow.
        """
        source_node_list = node if isinstance(node, list) else [node]
        outputs_list: list[list[Property] | None]
        if outputs is None:
            outputs_list = [None] * len(source_node_list)
        elif isinstance(outputs, list) and isinstance(outputs[0], Property):
            # Is supposed to be a flat list of properties
            for idx, p in enumerate(outputs):
                if not isinstance(p, Property):
                    raise ValueError(f"outputs[{idx}] must be a Property, is {p!r}")
            outputs_list = cast(list[list[Property] | None], [outputs])
        else:
            # Is supposed to be a nested list of properties
            outputs_list = cast(list[list[Property] | None], outputs)
            for idx, property_list in enumerate(outputs_list):
                if not (
                    isinstance(property_list, list)
                    and all(isinstance(p, Property) for p in property_list)
                ):
                    raise ValueError(
                        f"outputs[{idx}] must be a list of Property, is {property_list!r}"
                    )

        if len(source_node_list) != len(outputs_list):
            raise ValueError("Number of finish sources and outputs must match")

        for source_key, outputs_ in zip(source_node_list, outputs_list):
            end_node_name = f"EndNode_{self._end_node_counter}"
            self._end_node_counter += 1
            self.add_node(EndNode(name=end_node_name, outputs=outputs_))
            self.add_edge(source_key, end_node_name)
        return self

    def build(self, name: str = DEFAULT_FLOW_NAME) -> Flow:
        """
        Build the Flow.

        Will raise errors if encountering any while building the Flow.
        """
        # Determine start node: prefer explicitly set via set_entry_point,
        # otherwise accept a single StartNode added manually.
        if hasattr(self, "start_node"):
            start_node_obj = self.start_node
        else:
            start_nodes = [n for n in self.nodes.values() if isinstance(n, StartNode)]
            if len(start_nodes) == 1:
                start_node_obj = start_nodes[0]
            elif len(start_nodes) > 1:
                raise ValueError("There cannot be more than one start node in a Flow")
            else:
                raise ValueError("Missing start node, make sure to call `set_finish_points`")

        # Ensure there is at least one finish node (EndNode) in the flow
        if not any(isinstance(n, EndNode) for n in self.nodes.values()):
            raise ValueError("Missing finish node")
        return Flow(
            name=name,
            start_node=start_node_obj,
            nodes=list(self.nodes.values()),
            control_flow_connections=self.control_flow_connections,
            data_flow_connections=self.data_flow_connections,
        )

    def build_spec(
        self, name: str = DEFAULT_FLOW_NAME, serialize_as: Literal["JSON", "YAML"] = "JSON"
    ) -> str:
        """
        Build the Flow and return its Agent Spec JSON/YAML configuration.

        Will raise errors if encountering any while building the Flow.
        """
        flow = self.build(name)
        if serialize_as == "JSON":
            return AgentSpecSerializer().to_json(flow)
        elif serialize_as == "YAML":
            return AgentSpecSerializer().to_yaml(flow)
        else:
            raise ValueError(f"Incorrect serialization format {serialize_as}")

    @overload
    @classmethod
    def build_linear_flow(
        cls,
        nodes: list[Node],
        name: str = DEFAULT_FLOW_NAME,
        serialize_as: Literal[None] = None,
        data_flow_edges: (
            list[
                tuple[Node | str, Node | str, str]
                | tuple[Node | str, Node | str, str, str]
                | DataFlowEdge
            ]
            | None
        ) = None,
        inputs: list[Property] | None = None,
        outputs: list[list[Property] | None] | list[Property] | None = None,
    ) -> Flow: ...

    @overload
    @classmethod
    def build_linear_flow(
        cls,
        nodes: list[Node],
        name: str = DEFAULT_FLOW_NAME,
        serialize_as: Literal["JSON", "YAML"] = "JSON",
        data_flow_edges: (
            list[
                tuple[Node | str, Node | str, str]
                | tuple[Node | str, Node | str, str, str]
                | DataFlowEdge
            ]
            | None
        ) = None,
        inputs: list[Property] | None = None,
        outputs: list[list[Property] | None] | list[Property] | None = None,
    ) -> str: ...

    @classmethod
    def build_linear_flow(
        cls,
        nodes: list[Node],
        name: str = DEFAULT_FLOW_NAME,
        serialize_as: Literal["JSON", "YAML"] | None = None,
        data_flow_edges: (
            list[
                tuple[Node | str, Node | str, str]
                | tuple[Node | str, Node | str, str, str]
                | DataFlowEdge
            ]
            | None
        ) = None,
        inputs: list[Property] | None = None,
        outputs: list[list[Property] | None] | list[Property] | None = None,
    ) -> Flow | str:
        """
        Build a linear flow from a list of nodes.

        Parameters
        ----------
        nodes:
            List of nodes to use to create the linear/sequential Flow.
        serialize_as:
            Format for the returned object. If `None`, returns a pyagentspec `Flow`.
            Otherwise, returns its Agent Spec configuration as JSON/YAML.
        data_flow_edges:
            Optional list of data flow edges. Either a `DataFlowEdge` object
            or a (src_node, dst_node, var_name) tuple when the variable name is
            shared, or (src_node, dst_node, src_in, dst_out) otherwise.
        inputs:
            Optional list of inputs for the flow. If `None`, auto-detects as the list of
            inputs that are not generated at some point in the execution of the flow.
        outputs:
            Optional list of outputs for the flow branches corresponding to each
            of the specified terminal nodes. Must be of the same length as `node`.
            If `None`, auto-detects as the intersection of all the outputs generated by
            any node in any execution branch of the flow.
        """
        if isinstance(nodes[0], StartNode):
            raise ValueError("It is not necessary to add a StartNode to the list of nodes")
        if isinstance(nodes[-1], EndNode):
            raise ValueError("It is not necessary to add an EndNode to the list of nodes")

        flow_builder = cls().add_sequence(nodes)

        if data_flow_edges:
            for edge_info in data_flow_edges:
                if isinstance(edge_info, tuple) and len(edge_info) == 3:
                    src_node, dst_node, data_name = edge_info
                    flow_builder.add_data_edge(src_node, dst_node, data_name)
                elif isinstance(edge_info, tuple) and len(edge_info) == 4:
                    src_node, dst_node, src_in, dst_out = edge_info
                    flow_builder.add_data_edge(src_node, dst_node, (src_in, dst_out))
                elif isinstance(edge_info, DataFlowEdge):
                    flow_builder.add_data_edge(
                        edge_info.source_node,
                        edge_info.destination_node,
                        (edge_info.source_output, edge_info.destination_input),
                    )

        flow_builder.set_entry_point(nodes[0], inputs=inputs).set_finish_points(
            nodes[-1], outputs=outputs
        )

        if serialize_as:
            return flow_builder.build_spec(name=name, serialize_as=serialize_as)
        else:
            return flow_builder.build(name=name)

    def _get_node(self, node_or_name: Node | str, prefix_err_msg: str = "Node with name") -> Node:
        node_name = node_or_name.name if isinstance(node_or_name, Node) else node_or_name

        if node_name not in self.nodes:
            raise ValueError(f"{prefix_err_msg} '{node_name}' not found")

        return self.nodes[node_name]

    def _get_node_name(
        self, node_or_name: Node | str, prefix_err_msg: str = "Node with name"
    ) -> str:
        if isinstance(node_or_name, str):
            return node_or_name

        return self._get_node(node_or_name, prefix_err_msg).name
