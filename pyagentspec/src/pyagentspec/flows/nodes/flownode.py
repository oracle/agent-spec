# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import List

from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.property import Property


class FlowNode(Node):
    """The flow node executes a subflow as part of a flow.

    - **Inputs**
        Inferred from the inner structure. It's the sets of inputs
        required by the StartNode of the inner flow.
    - **Outputs**
        Inferred from the inner structure. It's the union of the
        sets of outputs exposed by the EndNodes of the inner flow.
    - **Branches**
        Inferred from the inner flow, one per each different value of the attribute
        ``branch_name`` of the nodes of type EndNode in the inner flow.

    Example
    -------
    The ``FlowNode`` is particularly suitable when subflows can be reused inside a project.
    Let's see an example with a flow that estimates numerical value
    using the "wisdowm of the crowd" effect:

    >>> from pyagentspec.property import Property
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.flows.nodes import MapNode, LlmNode, ToolNode, StartNode, EndNode
    >>> from pyagentspec.tools import ServerTool
    >>> duplication_tool = ServerTool(
    ...     name="duplication_tool",
    ...     description="",
    ...     inputs=[
    ...         Property(
    ...             json_schema={"title": "element", "description": "", "type": "string"}
    ...         ),
    ...         Property(
    ...             json_schema={"title": "n", "description": "", "type": "integer"}
    ...         ),
    ...     ],
    ...     outputs=[
    ...         Property(
    ...             json_schema={
    ...                 "title": "flow_iterable_queries",
    ...                 "type": "array",
    ...                 "items": {"type": "string"}
    ...             },
    ...         )
    ...     ],
    ... )
    >>> reduce_tool = ServerTool(
    ...     name="reduce_tool",
    ...     description="",
    ...     inputs=[
    ...         Property(
    ...             json_schema={"title": "elements", "type": "array", "items": {"type": "string"}}
    ...         ),
    ...     ],
    ...     outputs=[Property(json_schema={"title": "flow_processed_query", "type": "string"})],
    ... )
    >>> # Defining a simple prompt
    >>> REASONING_PROMPT_TEMPLATE = '''Provide your best numerical estimate for: {{user_input}}
    ... Your answer should be a single number.
    ... Do not include any units, reasoning, or extra text.'''
    >>> # Defining the subflow for the map step
    >>> user_input_property = Property(
    ...     json_schema={"title": "user_input", "type": "string"}
    ... )
    >>> flow_processed_query_property = Property(
    ...     json_schema={"title": "flow_processed_query", "type": "string"}
    ... )
    >>> start_node = StartNode(name="start", inputs=[user_input_property])
    >>> end_node = EndNode(name="end", outputs=[flow_processed_query_property])
    >>> llm_node = LlmNode(
    ...     name="reasoning llm node",
    ...     llm_config=llm_config,
    ...     prompt_template=REASONING_PROMPT_TEMPLATE,
    ...     inputs=[user_input_property],
    ...     outputs=[flow_processed_query_property],
    ... )
    >>> inner_map_flow = Flow(
    ...     name="Map flow",
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
    ...             source_output="user_input",
    ...             destination_node=llm_node,
    ...             destination_input="user_input",
    ...         ),
    ...         DataFlowEdge(
    ...             name="search_results_edge",
    ...             source_node=llm_node,
    ...             source_output="flow_processed_query",
    ...             destination_node=end_node,
    ...             destination_input="flow_processed_query"
    ...         ),
    ...     ],
    ... )
    >>> user_query_property = Property(
    ...     json_schema={"title": "user_query", "type": "string"}
    ... )
    >>> n_repeat_property = Property(
    ...     json_schema={"title": "n_repeat", "type": "integer"}
    ... )
    >>> flow_iterable_queries_property = Property(
    ...     json_schema={
    ...         "title": "iterated_user_input",
    ...         "type": "array",
    ...         "items": {"type": "string"},
    ...     }
    ... )
    >>> flow_processed_queries_property = Property(
    ...     json_schema={
    ...         "title": "collected_flow_processed_query",
    ...         "type": "array",
    ...         "items": {"type": "string"},
    ...     }
    ... )
    >>> start_node = StartNode(name="start", inputs=[user_query_property, n_repeat_property])
    >>> end_node = EndNode(name="end", outputs=[flow_processed_query_property])
    >>> duplication_node = ToolNode(
    ...     name="duplication_tool node",
    ...     tool=duplication_tool,
    ... )
    >>> reduce_node = ToolNode(
    ...     name="reduce_tool node",
    ...     tool=reduce_tool,
    ... )
    >>> map_node = MapNode(
    ...     name="map node",
    ...     subflow=inner_map_flow,
    ...     inputs=[flow_iterable_queries_property],
    ...     outputs=[flow_processed_queries_property],
    ... )
    >>> mapreduce_flow = Flow(
    ...     name="Map-reduce flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, duplication_node, map_node, reduce_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(
    ...             name="start_to_duplication", from_node=start_node, to_node=duplication_node
    ...         ),
    ...         ControlFlowEdge(
    ...             name="duplication_to_map", from_node=duplication_node, to_node=map_node
    ...         ),
    ...         ControlFlowEdge(name="map_to_reduce", from_node=map_node, to_node=reduce_node),
    ...         ControlFlowEdge(name="reduce_to_end", from_node=reduce_node, to_node=end_node),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="query_edge",
    ...             source_node=start_node,
    ...             source_output="user_query",
    ...             destination_node=duplication_node,
    ...             destination_input="element",
    ...         ),
    ...         DataFlowEdge(
    ...             name="n_repeat_edge",
    ...             source_node=start_node,
    ...             source_output="n_repeat",
    ...             destination_node=duplication_node,
    ...             destination_input="n",
    ...         ),
    ...         DataFlowEdge(
    ...             name="flow_iterables_edge",
    ...             source_node=duplication_node,
    ...             source_output="flow_iterable_queries",
    ...             destination_node=map_node,
    ...             destination_input="iterated_user_input",
    ...         ),
    ...         DataFlowEdge(
    ...             name="flow_processed_queries_edge",
    ...             source_node=map_node,
    ...             source_output="collected_flow_processed_query",
    ...             destination_node=reduce_node,
    ...             destination_input="elements",
    ...         ),
    ...         DataFlowEdge(
    ...             name="flow_processed_query_edge",
    ...             source_node=reduce_node,
    ...             source_output="flow_processed_query",
    ...             destination_node=end_node,
    ...             destination_input="flow_processed_query",
    ...         ),
    ...     ],
    ... )

    Once the subflow is created we can simply integrate it with the ``FlowNode``:

    >>> from pyagentspec.flows.nodes import FlowNode, AgentNode
    >>> from pyagentspec.agent import Agent
    >>> start_node = StartNode(name="start")
    >>> end_node = EndNode(name="end", outputs=[flow_processed_query_property])
    >>> flow_node = FlowNode(name="flow node", subflow=mapreduce_flow)
    >>> agent = Agent(
    ...     name="User interaction agent",
    ...     llm_config=llm_config,
    ...     system_prompt=(
    ...         "Your task is to gather from the user the query and the number of times "
    ...         "it should be asked to an LLM. Once you have this information, submit and exit."
    ...     ),
    ...     outputs=[user_query_property, n_repeat_property],
    ... )
    >>> agent_node = AgentNode(name="flow node", agent=agent)
    >>> flow = Flow(
    ...     name="Map flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, agent_node, flow_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(name="start_to_agent", from_node=start_node, to_node=agent_node),
    ...         ControlFlowEdge(name="agent_to_flow", from_node=agent_node, to_node=flow_node),
    ...         ControlFlowEdge(name="flow_to_end", from_node=flow_node, to_node=end_node),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="query_edge",
    ...             source_node=agent_node,
    ...             source_output="user_query",
    ...             destination_node=flow_node,
    ...             destination_input="user_query",
    ...         ),
    ...         DataFlowEdge(
    ...             name="n_rep_edge",
    ...             source_node=agent_node,
    ...             source_output="n_repeat",
    ...             destination_node=flow_node,
    ...             destination_input="n_repeat"
    ...         ),
    ...         DataFlowEdge(
    ...             name="n_rep_edge",
    ...             source_node=flow_node,
    ...             source_output="flow_processed_query",
    ...             destination_node=end_node,
    ...             destination_input="flow_processed_query"
    ...         ),
    ...     ],
    ... )

    """

    subflow: Flow
    """The flow that should be executed"""

    def _get_inferred_branches(self) -> List[str]:
        if hasattr(self, "subflow"):
            end_nodes = sorted(
                list({node.branch_name for node in self.subflow.nodes if isinstance(node, EndNode)})
            )
            return end_nodes if end_nodes else super()._get_inferred_branches()
        return []

    def _get_inferred_inputs(self) -> List[Property]:
        return (self.subflow.inputs or []) if hasattr(self, "subflow") else []

    def _get_inferred_outputs(self) -> List[Property]:
        return (self.subflow.outputs or []) if hasattr(self, "subflow") else []
