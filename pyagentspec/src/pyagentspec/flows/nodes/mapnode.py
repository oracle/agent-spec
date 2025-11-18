# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from pyagentspec.component import SerializeAsEnum
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.property import Property

if TYPE_CHECKING:
    from pyagentspec.flows.nodes.parallelmapnode import ParallelMapNode


class ReductionMethod(Enum):
    """Enumerator for the types of reduction available in the MapNode."""

    APPEND = "append"
    """Append all the elements to a list"""
    SUM = "sum"
    """Sum all the elements"""
    AVERAGE = "average"
    """Compute the average of all the elements"""
    MAX = "max"
    """Get the element with the highest value"""
    MIN = "min"
    """Get the element with the lowest value"""


class MapNode(Node):
    """The map node executes a subflow on each element of a given input as part of a flow.

    - **Inputs**
        Inferred from the inner structure. It's the sets of inputs
        required by the StartNode of the inner flow.
        The names of the inputs will be the ones of the inner flow,
        complemented with the ``iterated_`` prefix. Their type is
        ``Union[inner_type, List[inner_type]]``, where ``inner_type``
        is the type of the respective input in the inner flow.

        If None is given, ``pyagentspec`` infers input properties directly from the inner flow,
        specifying title and type according to the rules defined above.

    - **Outputs**
        Inferred from the inner structure. It's the union of the
        sets of outputs exposed by the EndNodes of the inner flow,
        combined with the reducer method of each output.
        The names of the outputs will be the ones of the inner flow,
        complemented with the ``collected_`` prefix. Their type depends
        on the ``reduce`` method specified for that output:

        - ``List`` of the respective output type in case of ``append``
        - same type of the respective output type in case of ``sum``, ``avg``

        If None is given, ``pyagentspec`` infers outputs by exposing
        an output property for each entry in the ``reducers`` dictionary, specifying title
        and type according to the rules defined above.

    - **Branches**
        One, the default next.

    Examples
    --------
    In this example we will create a flow that returns
    an L2-normalized version of a given list of numbers.

    >>> from pyagentspec.property import Property
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.nodes import EndNode, StartNode, MapNode, ToolNode
    >>> from pyagentspec.tools import ServerTool

    First, we define a MapNode that returns the square of all the elements in a list.
    It will be used to compute the L2-norm.

    >>> x_property = Property(json_schema={"title": "x", "type": "number"})
    >>> x_square_property = Property(
    ...     json_schema={"title": "x_square", "type": "number"}
    ... )
    >>> square_tool = ServerTool(
    ...     name="compute_square_tool",
    ...     description="Computes the square of a number",
    ...     inputs=[x_property],
    ...     outputs=[x_square_property],
    ... )
    >>> list_of_x_property = Property(
    ...     json_schema={"title": "x_list", "type": "array", "items": {"type": "number"}}
    ... )
    >>> start_node = StartNode(name="start", inputs=[x_property])
    >>> end_node = EndNode(name="end", outputs=[x_square_property])
    >>> square_tool_node = ToolNode(name="square tool node", tool=square_tool)
    >>> square_number_flow = Flow(
    ...     name="Square number flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, square_tool_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(
    ...             name="start_to_tool", from_node=start_node, to_node=square_tool_node
    ...         ),
    ...         ControlFlowEdge(
    ...             name="tool_to_end", from_node=square_tool_node, to_node=end_node
    ...         ),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="x_edge",
    ...             source_node=start_node,
    ...             source_output="x",
    ...             destination_node=square_tool_node,
    ...             destination_input="x",
    ...         ),
    ...         DataFlowEdge(
    ...             name="x_square_edge",
    ...             source_node=square_tool_node,
    ...             source_output="x_square",
    ...             destination_node=end_node,
    ...             destination_input="x_square",
    ...         ),
    ...     ],
    ... )
    >>> list_of_x_square_property = Property(
    ...     json_schema={"title": "x_square_list", "type": "array", "items": {"type": "number"}}
    ... )
    >>> square_numbers_map_node = MapNode(
    ...     name="square number map node",
    ...     subflow=square_number_flow,
    ... )

    Now we define the MapNode responsible for normalizing the given list of input numbers.
    The denominator is the same for all of the numbers,
    we are going to map only the numerators (i.e., the input numbers).

    >>> numerator_property = Property(
    ...     json_schema={"title": "numerator", "type": "number"}
    ... )
    >>> denominator_property = Property(
    ...     json_schema={"title": "denominator", "type": "number"}
    ... )
    >>> result_property = Property(
    ...     json_schema={"title": "result", "type": "number"}
    ... )
    >>> division_tool = ServerTool(
    ...     name="division_tool",
    ...     description="Computes the ratio between two numbers",
    ...     inputs=[numerator_property, denominator_property],
    ...     outputs=[result_property],
    ... )
    >>> start_node = StartNode(name="start", inputs=[numerator_property, denominator_property])
    >>> end_node = EndNode(name="end", outputs=[result_property])
    >>> divide_node = ToolNode(name="divide node", tool=division_tool)
    >>> normalize_flow = Flow(
    ...     name="Normalize flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, divide_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(name="start_to_tool", from_node=start_node, to_node=divide_node),
    ...         ControlFlowEdge(name="tool_to_end", from_node=divide_node, to_node=end_node),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="numerator_edge",
    ...             source_node=start_node,
    ...             source_output="numerator",
    ...             destination_node=divide_node,
    ...             destination_input="numerator",
    ...         ),
    ...         DataFlowEdge(
    ...             name="denominator_edge",
    ...             source_node=start_node,
    ...             source_output="denominator",
    ...             destination_node=divide_node,
    ...             destination_input="denominator",
    ...         ),
    ...         DataFlowEdge(
    ...             name="result_edge",
    ...             source_node=divide_node,
    ...             source_output="result",
    ...             destination_node=end_node,
    ...             destination_input="result",
    ...         ),
    ...     ],
    ... )

    Finally, we define the overall flow:

    - The list of inputs is squared
    - The squared list is summed and root squared
    - The list of inputs is normalized based on the outcomes of the previous 2 steps

    >>> squared_sum_property = Property(
    ...     json_schema={"title": "squared_sum", "type": "number"}
    ... )
    >>> normalized_list_of_x_property = Property(
    ...     json_schema={
    ...         "title": "x_list_normalized",
    ...         "type": "array",
    ...         "items": {"type": "number"},
    ...     }
    ... )
    >>> normalize_map_node = MapNode(
    ...     name="normalize map node",
    ...     subflow=normalize_flow,
    ... )
    >>> squared_sum_tool = ServerTool(
    ...     name="squared_sum_tool",
    ...     description="Computes the squared sum of a list of numbers",
    ...     inputs=[list_of_x_property],
    ...     outputs=[squared_sum_property],
    ... )
    >>> start_node = StartNode(name="start", inputs=[list_of_x_property])
    >>> end_node = EndNode(name="end", outputs=[normalized_list_of_x_property])
    >>> squared_sum_tool_node = ToolNode(name="squared sum tool node", tool=squared_sum_tool)
    >>> flow = Flow(
    ...     name="L2 normalize flow",
    ...     start_node=start_node,
    ...     nodes=[
    ...         start_node,
    ...         square_numbers_map_node,
    ...         squared_sum_tool_node,
    ...         normalize_map_node,
    ...         end_node,
    ...     ],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(
    ...             name="start_to_square_numbers",
    ...             from_node=start_node,
    ...             to_node=square_numbers_map_node
    ...         ),
    ...         ControlFlowEdge(
    ...             name="square_numbers_to_squared_sum_tool",
    ...             from_node=square_numbers_map_node,
    ...             to_node=squared_sum_tool_node
    ...         ),
    ...         ControlFlowEdge(
    ...             name="squared_sum_tool_to_normalize",
    ...             from_node=squared_sum_tool_node,
    ...             to_node=normalize_map_node
    ...         ),
    ...         ControlFlowEdge(
    ...             name="normalize_to_end",
    ...             from_node=normalize_map_node,
    ...             to_node=end_node
    ...         ),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="list_of_x_edge",
    ...             source_node=start_node,
    ...             source_output="x_list",
    ...             destination_node=square_numbers_map_node,
    ...             destination_input="iterated_x",
    ...         ),
    ...         DataFlowEdge(
    ...             name="x_square_list_edge",
    ...             source_node=square_numbers_map_node,
    ...             source_output="collected_x_square",
    ...             destination_node=squared_sum_tool_node,
    ...             destination_input="x_list",
    ...         ),
    ...         DataFlowEdge(
    ...             name="numerator_edge",
    ...             source_node=start_node,
    ...             source_output="x_list",
    ...             destination_node=normalize_map_node,
    ...             destination_input="iterated_numerator",
    ...         ),
    ...         DataFlowEdge(
    ...             name="denominator_edge",
    ...             source_node=squared_sum_tool_node,
    ...             source_output="squared_sum",
    ...             destination_node=normalize_map_node,
    ...             destination_input="iterated_denominator",
    ...         ),
    ...         DataFlowEdge(
    ...             name="x_list_normalized_edge",
    ...             source_node=normalize_map_node,
    ...             source_output="collected_result",
    ...             destination_node=end_node,
    ...             destination_input="x_list_normalized",
    ...         ),
    ...     ],
    ... )

    """

    subflow: Flow
    """The flow that should be applied to all the input values"""
    reducers: Optional[Dict[str, SerializeAsEnum[ReductionMethod]]] = None
    """The way the outputs of the different executions (map) should be collected together (reduce).
       It's a dictionary mapping the name of an output to the respective reduction method
       (e.g., append, sum, avg, ..., allowed methods depend on the type of the output)"""

    def model_post_init(self, __context: Any) -> None:
        """Override of the method used by Component as post-init."""
        if self.reducers is None:
            self.reducers = self._get_default_reducers()
        super().model_post_init(__context)

    def _get_default_reducers(self) -> Dict[str, ReductionMethod]:
        return _get_default_reducers(self)

    def _get_inferred_inputs(self) -> List[Property]:
        return _get_inferred_inputs(self)

    def _get_inferred_outputs(self) -> List[Property]:
        return _get_inferred_outputs(self)


def _get_default_reducers(
    map_node: Union["MapNode", "ParallelMapNode"],
) -> Dict[str, ReductionMethod]:
    default_reducers = (
        {
            output.json_schema["title"]: ReductionMethod.APPEND
            for output in map_node.subflow.outputs or []
        }
        if hasattr(map_node, "subflow")
        else {}
    )
    return default_reducers


def _get_inferred_inputs(map_node: Union["MapNode", "ParallelMapNode"]) -> List[Property]:
    if not hasattr(map_node, "subflow"):
        return []
    return [
        Property(
            json_schema={
                "title": f"iterated_{subflow_input_property.json_schema['title']}",
                "anyOf": [
                    subflow_input_property.json_schema,
                    {"type": "array", "items": subflow_input_property.json_schema},
                ],
            }
        )
        for subflow_input_property in map_node.subflow.inputs or []
    ]


def _get_inferred_outputs(map_node: Union["MapNode", "ParallelMapNode"]) -> List[Property]:
    if not hasattr(map_node, "subflow"):
        return []
    outputs = []
    for output in map_node.subflow.outputs or []:
        if map_node.reducers is not None and output.title in map_node.reducers:
            if map_node.reducers[output.title] == ReductionMethod.APPEND:
                json_schema = {
                    "title": f"collected_{output.title}",
                    "type": "array",
                    "items": output.json_schema,
                }
            else:
                json_schema = {
                    **output.json_schema,
                    "title": f"collected_{output.title}",
                }
            outputs.append(Property(json_schema=json_schema))
    return outputs
