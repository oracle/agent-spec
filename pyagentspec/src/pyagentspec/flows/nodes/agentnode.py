# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import List

from pydantic import SerializeAsAny

from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.flows.node import Node
from pyagentspec.property import Property


class AgentNode(Node):
    """
    The agent execution node is a node that will execute an agent as part of a flow.

    If branches are configured, the agent will be prompted to select a branch before the agent node
    completes to transition to another node of the Flow.

    - **Inputs**
        Inferred from the definition of the agent to execute.
    - **Outputs**
        Inferred from the definition of the agent to execute.
    - **Branches**
        One, the default next.

    Examples
    --------
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.agent import Agent
    >>> from pyagentspec.property import Property
    >>> from pyagentspec.flows.nodes import AgentNode, StartNode, EndNode
    >>> from pyagentspec.tools import ServerTool
    >>> query_property = Property(json_schema={"title": "query", "type": "string"})
    >>> search_results_property = Property(
    ...     json_schema={"title": "search_results", "type": "array", "items": {"type": "string"}}
    ... )
    >>> search_tool = ServerTool(
    ...     name="search_tool",
    ...     description=(
    ...        "This tool runs a web search with the given query "
    ...        "and returns the most relevant results"
    ...     ),
    ...     inputs=[query_property],
    ...     outputs=[search_results_property],
    ... )
    >>> agent = Agent(
    ...     name="Search agent",
    ...     llm_config=llm_config,
    ...     system_prompt=(
    ...         "Your task is to gather the required information for the user: {{query}}"
    ...     ),
    ...     tools=[search_tool],
    ...     outputs=[search_results_property],
    ... )
    >>> start_node = StartNode(name="start", inputs=[query_property])
    >>> end_node = EndNode(name="end", outputs=[search_results_property])
    >>> agent_node = AgentNode(
    ...     name="Search agent node",
    ...     agent=agent,
    ... )
    >>> flow = Flow(
    ...     name="Search agent flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, agent_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(name="start_to_agent", from_node=start_node, to_node=agent_node),
    ...         ControlFlowEdge(name="agent_to_end", from_node=agent_node, to_node=end_node),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="query_edge",
    ...             source_node=start_node,
    ...             source_output="query",
    ...             destination_node=agent_node,
    ...             destination_input="query",
    ...         ),
    ...         DataFlowEdge(
    ...             name="search_results_edge",
    ...             source_node=agent_node,
    ...             source_output="search_results",
    ...             destination_node=end_node,
    ...             destination_input="search_results"
    ...         ),
    ...     ],
    ... )

    """

    agent: SerializeAsAny[AgenticComponent]
    """The agentic component that will be called as part of the execution of this node"""

    def _get_inferred_branches(self) -> List[str]:
        return self.branches if self.branches else super()._get_inferred_branches()

    def _get_inferred_inputs(self) -> List[Property]:
        return (self.agent.inputs or []) if hasattr(self, "agent") else []

    def _get_inferred_outputs(self) -> List[Property]:
        return (self.agent.outputs or []) if hasattr(self, "agent") else []
