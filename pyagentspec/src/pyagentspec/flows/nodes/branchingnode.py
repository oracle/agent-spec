# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import ClassVar, Dict, List

from pyagentspec.flows.node import Node
from pyagentspec.property import Property, StringProperty


class BranchingNode(Node):
    """
    Select the next node to transition to based on a mapping.

    The input is used as key for the mapping. If the input does not correspond to any of the keys
    of the mapping the branch 'default' will be selected. This node is intended to be a part of a
    Flow.

    - **Inputs**
        The input value that should be used as key for the mapping.

        If None is given, ``pyagentspec`` infers a string property named ``branching_mapping_key``.
    - **Outputs**
        None.
    - **Branches**
        One for each value in the mapping, plus a branch called ``default``,
        which is the branch taken by the flow when mapping fails
        (i.e., the input does not match any key in the mapping).

    Examples
    --------
    >>> from pyagentspec.agent import Agent
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.nodes import AgentNode, BranchingNode, StartNode, EndNode
    >>> from pyagentspec.property import Property
    >>> CORRECT_PASSWORD_BRANCH = "PASSWORD_OK"
    >>> password_property = Property(
    ...     json_schema={"title": "password", "type": "string"}
    ... )
    >>> agent = Agent(
    ...     name="User input agent",
    ...     llm_config=llm_config,
    ...     system_prompt=(
    ...         "Your task is to ask the password to the user. "
    ...         "Once you get it, submit it and end."
    ...     ),
    ...     outputs=[password_property],
    ... )
    >>> start_node = StartNode(name="start")
    >>> access_granted_end_node = EndNode(
    ...     name="access granted end", branch_name="ACCESS_GRANTED"
    ... )
    >>> access_denied_end_node = EndNode(
    ...     name="access denied end", branch_name="ACCESS_DENIED"
    ... )
    >>> branching_node = BranchingNode(
    ...     name="password check",
    ...     mapping={"123456": CORRECT_PASSWORD_BRANCH},
    ...     inputs=[password_property]
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
    ...         access_granted_end_node,
    ...         access_denied_end_node
    ...     ],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(
    ...             name="start_to_agent",
    ...             from_node=start_node,
    ...             to_node=agent_node
    ...         ),
    ...         ControlFlowEdge(
    ...             name="agent_to_branching",
    ...             from_node=agent_node,
    ...             to_node=branching_node
    ...         ),
    ...         ControlFlowEdge(
    ...             name="branching_to_access_granted",
    ...             from_node=branching_node,
    ...             from_branch=CORRECT_PASSWORD_BRANCH,
    ...             to_node=access_granted_end_node,
    ...         ),
    ...         ControlFlowEdge(
    ...             name="branching_to_access_denied",
    ...             from_node=branching_node,
    ...             from_branch=BranchingNode.DEFAULT_BRANCH,
    ...             to_node=access_denied_end_node,
    ...         ),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="password_edge",
    ...             source_node=agent_node,
    ...             source_output="password",
    ...             destination_node=branching_node,
    ...             destination_input="password",
    ...         ),
    ...     ],
    ... )

    """

    DEFAULT_BRANCH: ClassVar[str] = "default"
    """Name of the default branch used when mapping fails"""

    DEFAULT_INPUT: ClassVar[str] = "branching_mapping_key"
    """Input key for the name to transition to next."""

    mapping: Dict[str, str]
    """The mapping between the value of the input and the name of the outgoing branch
       that will be taken when that input value is given"""

    def _get_inferred_branches(self) -> List[str]:
        return list({BranchingNode.DEFAULT_BRANCH, *getattr(self, "mapping", {}).values()})

    def _get_inferred_inputs(self) -> List[Property]:
        input_title = self.inputs[0].title if self.inputs else BranchingNode.DEFAULT_INPUT
        return [
            StringProperty(
                title=input_title,
                description="Next branch name in the flow",
            )
        ]

    def _get_inferred_outputs(self) -> List[Property]:
        return []
