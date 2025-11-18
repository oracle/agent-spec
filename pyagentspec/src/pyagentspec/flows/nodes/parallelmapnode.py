# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.component import SerializeAsEnum
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes.mapnode import (
    ReductionMethod,
    _get_default_reducers,
    _get_inferred_inputs,
    _get_inferred_outputs,
)
from pyagentspec.property import Property
from pyagentspec.versioning import AgentSpecVersionEnum


class ParallelMapNode(Node):
    """The parallel map node executes a subflow on each element of a given input in a parallel manner.

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
    In this example we create a flow that generates a summary of the given articles that talk about LLMs.

    >>> from pyagentspec.property import BooleanProperty, StringProperty, ListProperty
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.nodes import EndNode, StartNode, ParallelMapNode, LlmNode, BranchingNode
    >>> from pyagentspec.flows.node import Node

    First we define the flow that determines if an article talks about LLMs or not:

    - if it does, we return it, so that we will use it for our summary
    - if it does not, we don't return its text

    >>> def create_data_flow_edge(source_node: Node, destination_node: Node, property_name: str) -> DataFlowEdge:
    ...     return DataFlowEdge(
    ...         name=f"{source_node.name}_{destination_node.name}_{property_name}_edge",
    ...         source_node=source_node,
    ...         source_output=property_name,
    ...         destination_node=destination_node,
    ...         destination_input=property_name,
    ...     )
    >>>
    >>> article_property = StringProperty(title="article")
    >>> is_llm_article_property = StringProperty(title="is_article")
    >>> llm_node = LlmNode(
    ...     name="check_if_article_talks_about_llms_node",
    ...     prompt_template="Look at this article: {{article}}. Does it talk about LLMs? Answer `yes` or `no`.",
    ...     llm_config=llm_config,
    ...     inputs=[article_property],
    ...     outputs=[is_llm_article_property],
    ... )
    >>>
    >>> branching_node = BranchingNode(
    ...     name="decide_if_we_should_return_the_article",
    ...     mapping={"yes": "yes"},
    ...     inputs=[is_llm_article_property],
    ... )
    >>>
    >>> start_node = StartNode(name="start", inputs=[article_property])
    >>> end_node_with_output = EndNode(name="end_with_output", outputs=[article_property])
    >>> end_node_without_output = EndNode(name="end_without_output", outputs=[])
    >>>
    >>> check_if_article_is_about_llm_flow = Flow(
    ...     name="is_article_about_llm_flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, llm_node, end_node_with_output, end_node_without_output, branching_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(name="start_to_llm", from_node=start_node, to_node=llm_node),
    ...         ControlFlowEdge(name="llm_to_branching", from_node=llm_node, to_node=branching_node),
    ...         ControlFlowEdge(name="branching_to_end_with", from_node=branching_node, to_node=end_node_with_output),
    ...         ControlFlowEdge(name="branching_to_end_without", from_node=branching_node, to_node=end_node_without_output),
    ...     ],
    ...     data_flow_connections=[
    ...         create_data_flow_edge(start_node, llm_node, article_property.title),
    ...         create_data_flow_edge(llm_node, branching_node, is_llm_article_property.title),
    ...         create_data_flow_edge(start_node, end_node_with_output, article_property.title),
    ...     ],
    ...     outputs=[StringProperty(title=article_property.title, default="")],
    ... )

    We put this flow into a ``ParallelMapNode``, so that we can perform the check
    in parallel on multiple articles at the same time.

    >>> list_of_articles_property = ListProperty(title="iterated_article", item_type=article_property)
    >>> list_of_articles_about_llm_property = ListProperty(title="collected_article", item_type=article_property)
    >>> parallel_article_check_node = ParallelMapNode(
    ...     name="parallel_check_if_articles_talk_about_llms_node",
    ...     subflow=check_if_article_is_about_llm_flow,
    ...     inputs=[list_of_articles_property],
    ...     outputs=[list_of_articles_about_llm_property],
    ... )

    Finally, we create the flow that takes the list of articles as input, filters them through the
    ``ParallelMapNode`` we have just created, and we generate the summary with the remaining articles.

    >>> summary_property = StringProperty(title="summary")
    >>> summary_llm_node = LlmNode(
    ...     name="generate_summary_of_llm_articles_node",
    ...     prompt_template="Summarize the following articles that talk about LLMs: {{collected_article}}",
    ...     llm_config=llm_config,
    ...     inputs=[list_of_articles_about_llm_property],
    ...     outputs=[summary_property],
    ... )
    >>> start_node = StartNode(name="start", inputs=[list_of_articles_property])
    >>> end_node = EndNode(name="end", outputs=[summary_property])
    >>> generate_summary_of_llm_articles_flow = Flow(
    ...     name="Generate summary of articles about LLMs flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, parallel_article_check_node, summary_llm_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(name="start_to_parallelmap", from_node=start_node, to_node=parallel_article_check_node),
    ...         ControlFlowEdge(name="parallelmap_to_llm", from_node=parallel_article_check_node, to_node=summary_llm_node),
    ...         ControlFlowEdge(name="llm_to_end", from_node=summary_llm_node, to_node=end_node),
    ...     ],
    ...     data_flow_connections=[
    ...         create_data_flow_edge(start_node, parallel_article_check_node, list_of_articles_property.title),
    ...         create_data_flow_edge(parallel_article_check_node, summary_llm_node, list_of_articles_about_llm_property.title),
    ...         create_data_flow_edge(summary_llm_node, end_node, summary_property.title),
    ...     ],
    ... )

    """

    subflow: Flow
    """The flow that should be applied to all the input values"""
    reducers: Optional[Dict[str, SerializeAsEnum[ReductionMethod]]] = None
    """The way the outputs of the different executions (map) should be collected together (reduce).
       It's a dictionary mapping the name of an output to the respective reduction method
       (e.g., append, sum, avg, ..., allowed methods depend on the type of the output)"""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )

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
