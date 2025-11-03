# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors
# docs-title: Code Example - How to Do Map and Reduce Operations in Flows

# .. start-##_Define_the_LLM
from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
)
# .. end-##_Define_the_LLM

# .. start-##_Create_the_Flow_for_the_MapNode
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import StringProperty
from pyagentspec.flows.nodes import LlmNode, StartNode, EndNode

start_node = StartNode(name="start_node", inputs=[StringProperty(title="article")])
end_node = EndNode(name="end_node", outputs=[StringProperty(title="summary")])
summarize_node = LlmNode(
    name="summarize_node",
    llm_config=llm_config,
    prompt_template="""Summarize this article in 10 words:
 {{article}}""",
    outputs=[StringProperty(title="summary")],
)
summarize_flow = Flow(
    name="mapnode_subflow",
    start_node=start_node,
    nodes=[start_node, end_node, summarize_node],
    control_flow_connections=[
        ControlFlowEdge(name="cfe1", from_node=start_node, to_node=summarize_node),
        ControlFlowEdge(name="cfe2", from_node=summarize_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="dfe1",
            source_node=start_node,
            source_output="article",
            destination_node=summarize_node,
            destination_input="article",
        ),
        DataFlowEdge(
            name="dfe2",
            source_node=summarize_node,
            source_output="summary",
            destination_node=end_node,
            destination_input="summary",
        ),
    ],
)
# .. end-##_Create_the_Flow_for_the_MapNode
# .. start-##_Create_the_MapNode
from pyagentspec.property import ListProperty, StringProperty
from pyagentspec.flows.nodes import MapNode

map_node = MapNode(
    name="map_node",
    subflow=summarize_flow,
    inputs=[ListProperty(title="iterated_article", item_type=StringProperty(title="article"))],
    outputs=[ListProperty(title="collected_summary", item_type=StringProperty(title="summary"))],
)
# .. end-##_Create_the_MapNode

# .. start-##_Create_the_final_Flow
start_node = StartNode(
    name="start_node",
    inputs=[ListProperty(title="articles", item_type=StringProperty(title="article"))],
)
end_node = EndNode(
    name="end_node",
    outputs=[ListProperty(title="summaries", item_type=StringProperty(title="summary"))],
)
flow = Flow(
    name="flow",
    start_node=start_node,
    nodes=[start_node, end_node, map_node],
    control_flow_connections=[
        ControlFlowEdge(name="cfe1", from_node=start_node, to_node=map_node),
        ControlFlowEdge(name="cfe2", from_node=map_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="dfe1",
            source_node=start_node,
            source_output="articles",
            destination_node=map_node,
            destination_input="iterated_article",
        ),
        DataFlowEdge(
            name="dfe2",
            source_node=map_node,
            source_output="collected_summary",
            destination_node=end_node,
            destination_input="summaries",
        ),
    ],
)
# .. end-##_Create_the_final_Flow

# .. start-export-config-to-agentspec
from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(flow)
# .. end-export-config-to-agentspec

# .. start-full-code
from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
)

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import StringProperty
from pyagentspec.flows.nodes import LlmNode, StartNode, EndNode

start_node = StartNode(name="start_node", inputs=[StringProperty(title="article")])
end_node = EndNode(name="end_node", outputs=[StringProperty(title="summary")])
summarize_node = LlmNode(
    name="summarize_node",
    llm_config=llm_config,
    prompt_template="""Summarize this article in 10 words:
 {{article}}""",
    outputs=[StringProperty(title="summary")],
)
summarize_flow = Flow(
    name="mapnode_subflow",
    start_node=start_node,
    nodes=[start_node, end_node, summarize_node],
    control_flow_connections=[
        ControlFlowEdge(name="cfe1", from_node=start_node, to_node=summarize_node),
        ControlFlowEdge(name="cfe2", from_node=summarize_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="dfe1",
            source_node=start_node,
            source_output="article",
            destination_node=summarize_node,
            destination_input="article",
        ),
        DataFlowEdge(
            name="dfe2",
            source_node=summarize_node,
            source_output="summary",
            destination_node=end_node,
            destination_input="summary",
        ),
    ],
)

from pyagentspec.property import ListProperty, StringProperty
from pyagentspec.flows.nodes import MapNode

map_node = MapNode(
    name="map_node",
    subflow=summarize_flow,
    inputs=[ListProperty(title="iterated_article", item_type=StringProperty(title="article"))],
    outputs=[ListProperty(title="collected_summary", item_type=StringProperty(title="summary"))],
)

start_node = StartNode(
    name="start_node",
    inputs=[ListProperty(title="articles", item_type=StringProperty(title="article"))],
)
end_node = EndNode(
    name="end_node",
    outputs=[ListProperty(title="summaries", item_type=StringProperty(title="summary"))],
)
flow = Flow(
    name="flow",
    start_node=start_node,
    nodes=[start_node, end_node, map_node],
    control_flow_connections=[
        ControlFlowEdge(name="cfe1", from_node=start_node, to_node=map_node),
        ControlFlowEdge(name="cfe2", from_node=map_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="dfe1",
            source_node=start_node,
            source_output="articles",
            destination_node=map_node,
            destination_input="iterated_article",
        ),
        DataFlowEdge(
            name="dfe2",
            source_node=map_node,
            source_output="collected_summary",
            destination_node=end_node,
            destination_input="summaries",
        ),
    ],
)

from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(flow)
# .. end-full-code
