# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines end nodes, which mark the last node of a flow."""

from typing import List

from typing_extensions import Self

from pyagentspec.flows.node import Node
from pyagentspec.property import Property
from pyagentspec.validation_helpers import model_validator_with_error_accumulation


class EndNode(Node):
    """
    End nodes denote the end of the execution of a flow.

    There might be several end nodes in a flow, in which case the executor of the flow
    should be able to track which one was reached and pass that back to the caller.

    - **Inputs**
        The list of inputs of the step. If both input and output properties are specified they
        must be an exact match

        If None is given, ``pyagentspec`` copies the outputs provided, if any. Otherwise, no input is exposed.
    - **Outputs**
        The list of outputs that should be exposed by the flow. If both input and output properties
        are specified they must be an exact match

        If None is given, ``pyagentspec`` copies the inputs provided, if any. Otherwise, no output is exposed.
    - **Branches**
        None.

    Examples
    --------
    >>> from pyagentspec.agent import Agent
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.nodes import AgentNode, BranchingNode, StartNode, EndNode
    >>> from pyagentspec.property import Property
    >>> languages_to_branch_name = {
    ...     "english": "ENGLISH",
    ...     "spanish": "SPANISH",
    ...     "italian": "ITALIAN",
    ... }
    >>> language_property = Property(
    ...     json_schema={"title": "language", "type": "string"}
    ... )
    >>> agent = Agent(
    ...     name="Language detector agent",
    ...     llm_config=llm_config,
    ...     system_prompt=(
    ...         "Your task is to understand the language spoken by the user."
    ...         "Please output only the language in lowercase and submit."
    ...     ),
    ...     outputs=[language_property],
    ... )
    >>> start_node = StartNode(name="start")
    >>> english_end_node = EndNode(
    ...     name="english end", branch_name=languages_to_branch_name["english"]
    ... )
    >>> spanish_end_node = EndNode(
    ...     name="spanish end", branch_name=languages_to_branch_name["spanish"]
    ... )
    >>> italian_end_node = EndNode(
    ...     name="italian end", branch_name=languages_to_branch_name["italian"]
    ... )
    >>> unknown_end_node = EndNode(name="unknown language end", branch_name="unknown")
    >>> branching_node = BranchingNode(
    ...     name="language check",
    ...     mapping=languages_to_branch_name,
    ...     inputs=[language_property]
    ... )
    >>> agent_node = AgentNode(
    ...     name="User input agent node",
    ...     agent=agent,
    ... )
    >>> assistant = Flow(
    ...     name="Check access flow",
    ...     start_node=start_node,
    ...     nodes=[
    ...         start_node,
    ...         agent_node,
    ...         branching_node,
    ...         english_end_node,
    ...         spanish_end_node,
    ...         italian_end_node,
    ...         unknown_end_node,
    ...     ],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(
    ...             name="start_to_agent", from_node=start_node, to_node=agent_node
    ...         ),
    ...         ControlFlowEdge(
    ...             name="agent_to_branching", from_node=agent_node, to_node=branching_node
    ...         ),
    ...         ControlFlowEdge(
    ...             name="branching_to_english_end",
    ...             from_node=branching_node,
    ...             from_branch=languages_to_branch_name["english"],
    ...             to_node=english_end_node,
    ...         ),
    ...         ControlFlowEdge(
    ...             name="branching_to_spanish_end",
    ...             from_node=branching_node,
    ...             from_branch=languages_to_branch_name["spanish"],
    ...             to_node=spanish_end_node,
    ...         ),
    ...         ControlFlowEdge(
    ...             name="branching_to_italian_end",
    ...             from_node=branching_node,
    ...             from_branch=languages_to_branch_name["italian"],
    ...             to_node=italian_end_node,
    ...         ),
    ...         ControlFlowEdge(
    ...             name="branching_to_unknown_end",
    ...             from_node=branching_node,
    ...             from_branch=BranchingNode.DEFAULT_BRANCH,
    ...             to_node=unknown_end_node,
    ...         ),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="language_edge",
    ...             source_node=agent_node,
    ...             source_output="language",
    ...             destination_node=branching_node,
    ...             destination_input="language",
    ...         ),
    ...     ],
    ... )

    """

    branch_name: str = Node.DEFAULT_NEXT_BRANCH
    """The name of the branch that corresponds to the branch that gets closed by this node,
       which will be exposed by the Flow"""

    @model_validator_with_error_accumulation
    def _validate_inputs_and_outputs_are_equal(self) -> Self:
        """Perform additional validation and set automatically the values of some fields."""
        if self.inputs and self.outputs and self.inputs != self.outputs:
            raise ValueError(
                "If both inputs and outputs are specified for an EndNode, they must be equal."
            )
        return self

    def _get_inferred_branches(self) -> List[str]:
        return []  # By definition an EndStep has no outgoing branch

    def _get_inferred_inputs(self) -> List[Property]:
        return self.inputs or self.outputs or []

    def _get_inferred_outputs(self) -> List[Property]:
        return self.outputs or self.inputs or []
