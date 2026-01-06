# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import ClassVar, List, Optional

from typing_extensions import Self

from pyagentspec.flows.node import Node
from pyagentspec.property import Property, StringProperty
from pyagentspec.templating import get_placeholder_properties_from_json_object
from pyagentspec.validation_helpers import model_validator_with_error_accumulation


class InputMessageNode(Node):
    """
    This node interrupts the execution of the flow in order to wait for a user input, and restarts after receiving it.
    An agent message, if given, is appended to the conversation before waiting for input.
    User input is appended to the conversation as a user message, and it is returned as a string property from the node.

    - **Inputs**
        One per variable in the message
    - **Outputs**
        One string property that represents the content of the input user message.

        If None is given, ``pyagentspec`` infers a string property named ``user_input``.
    - **Branches**
        One, the default next.

    Examples
    --------
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.nodes import StartNode, EndNode, InputMessageNode, OutputMessageNode, LlmNode
    >>> from pyagentspec.property import StringProperty
    >>> start_node = StartNode(name="start")
    >>> prompt_node = OutputMessageNode(name="ask_input", message="What is the paragraph you want to rephrase?")
    >>> input_node = InputMessageNode(name="user_input", outputs=[StringProperty(title="user_input")])
    >>> llm_node = LlmNode(
    ...     name="rephrase",
    ...     llm_config=llm_config,
    ...     prompt_template="Rephrase {{user_input}}",
    ...     outputs=[StringProperty(title="rephrased_user_input")],
    ... )
    >>> output_node = OutputMessageNode(name="ask_input", message="{{rephrased_user_input}}")
    >>> end_node = EndNode(name="end")
    >>> flow = Flow(
    ...     name="rephrase_paragraph_flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, prompt_node, input_node, llm_node, output_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(name="ce1", from_node=start_node, to_node=prompt_node),
    ...         ControlFlowEdge(name="ce2", from_node=prompt_node, to_node=input_node),
    ...         ControlFlowEdge(name="ce3", from_node=input_node, to_node=llm_node),
    ...         ControlFlowEdge(name="ce4", from_node=llm_node, to_node=output_node),
    ...         ControlFlowEdge(name="ce5", from_node=output_node, to_node=end_node),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="de1",
    ...             source_node=input_node,
    ...             source_output="user_input",
    ...             destination_node=llm_node,
    ...             destination_input="user_input",
    ...         ),
    ...         DataFlowEdge(
    ...             name="de2",
    ...             source_node=llm_node,
    ...             source_output="rephrased_user_input",
    ...             destination_node=output_node,
    ...             destination_input="rephrased_user_input",
    ...         ),
    ...     ]
    ... )

    """

    message: Optional[str] = None
    """The agent message to append to the conversation before waiting for user input"""

    DEFAULT_OUTPUT: ClassVar[str] = "user_input"

    def _get_inferred_inputs(self) -> List[Property]:
        message = getattr(self, "message", None)
        if message is None:
            return []
        return get_placeholder_properties_from_json_object(message)

    def _get_inferred_outputs(self) -> List[Property]:
        output_title = self.outputs[0].title if self.outputs else self.DEFAULT_OUTPUT
        return [StringProperty(title=output_title, description="Input provided by the user")]

    @model_validator_with_error_accumulation
    def _validate_outputs_have_right_format(self) -> Self:
        """Perform additional validation and set automatically the values of some fields."""
        outputs = getattr(self, "outputs", [])
        if len(outputs) != 1:
            raise ValueError(f"Expected a single output, given {len(outputs)} instead.")
        if outputs[0].type != "string":
            raise ValueError(
                f"Expected an output of type string, given `{outputs[0].type}` instead."
            )
        return self
