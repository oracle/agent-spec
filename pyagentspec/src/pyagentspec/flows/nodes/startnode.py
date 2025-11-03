# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines start nodes, which mark the first step of a flow."""

from typing import List

from typing_extensions import Self

from pyagentspec.flows.node import Node
from pyagentspec.property import Property
from pyagentspec.validation_helpers import model_validator_with_error_accumulation


class StartNode(Node):
    """Start nodes denote the start of the execution of a flow.

    - **Inputs**
        The list of inputs that should be the inputs of the flow. If both input and output
        properties are specified they must be an exact match

        If None is given, ``pyagentspec`` copies the outputs provided, if any. Otherwise, no input is exposed.
    - **Outputs**
        The list of outputs of the step. If both input and output properties are specified they
        must be an exact match

        If None is given, ``pyagentspec`` copies the inputs provided, if any. Otherwise, no output is exposed.
    - **Branches**
        One, the default next.

    Examples
    --------
    >>> from pyagentspec.property import Property
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
    >>> user_question_property = Property(
    ...     json_schema=dict(
    ...         title="user_question",
    ...         description="The user question.",
    ...         type="string",
    ...     )
    ... )
    >>> answer_property = Property(json_schema=dict(title="answer", type="string"))
    >>> start_node = StartNode(name="start", inputs=[user_question_property])
    >>> end_node = EndNode(name="end", outputs=[answer_property])
    >>> llm_node = LlmNode(
    ...     name="llm node",
    ...     prompt_template="Answer the user question: {{user_question}}",
    ...     llm_config=llm_config,
    ... )
    >>> flow = Flow(
    ...     name="flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, llm_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(name="start_to_llm", from_node=start_node, to_node=llm_node),
    ...         ControlFlowEdge(name="llm_to_end", from_node=llm_node, to_node=end_node),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="query_edge",
    ...             source_node=start_node,
    ...             source_output="user_question",
    ...             destination_node=llm_node,
    ...             destination_input="user_question",
    ...         ),
    ...         DataFlowEdge(
    ...             name="answer_edge",
    ...             source_node=llm_node,
    ...             source_output="generated_text",
    ...             destination_node=end_node,
    ...             destination_input="answer"
    ...         ),
    ...     ],
    ... )

    """

    @model_validator_with_error_accumulation
    def _validate_inputs_and_outputs_are_equal(self) -> Self:
        """Perform additional validation and set automatically the values of some fields."""
        if self.inputs and self.outputs and self.inputs != self.outputs:
            raise ValueError(
                "If both inputs and outputs are specified for a StartNode, they must be equal."
            )
        return self

    def _get_inferred_inputs(self) -> List[Property]:
        return self.inputs or self.outputs or []

    def _get_inferred_outputs(self) -> List[Property]:
        return self.outputs or self.inputs or []
