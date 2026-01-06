# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import List

from pyagentspec.flows.node import Node
from pyagentspec.property import Property
from pyagentspec.templating import get_placeholder_properties_from_json_object


class OutputMessageNode(Node):
    """
    This node appends an agent message to the ongoing flow conversation.

    - **Inputs**
        One per variable in the message.
    - **Outputs**
        No outputs.
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

    message: str
    """Content of the agent message to append. Allows placeholders, which can define inputs."""

    def _get_inferred_inputs(self) -> List[Property]:
        return get_placeholder_properties_from_json_object(getattr(self, "message", ""))

    def _get_inferred_outputs(self) -> List[Property]:
        return []
