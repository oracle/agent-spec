# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# mypy: ignore-errors

# .. start-import:
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import (
    BooleanProperty,
    DictProperty,
    FloatProperty,
    ListProperty,
    StringProperty,
    UnionProperty,
)

# .. end-import


# .. start-code:
input_1 = FloatProperty(title="Input_1", default=0.2)
input_2 = DictProperty(
    title="Input_2",
    value_type=StringProperty(),
    default={},
)
input_3 = UnionProperty(title="Input_3", any_of=[StringProperty(), FloatProperty()])

output_1 = ListProperty(
    title="Output_1",
    item_type=ListProperty(
        item_type=StringProperty(),
    ),
)
output_2 = BooleanProperty(title="Output_2", default=True)
output_3 = FloatProperty(title="Output_3", default=1.2)

# VLLMConfig is a subclass of Component, we will define it more in detail later
# This Component does not have input/output schemas, the default should be an empty list
vllm = VllmConfig(
    id="99asbdiugjk4b5",
    name="LLama 3.1 8b",
    description="llama 3.1 config",
    model_id="llama3.1-8b-instruct",
    url="url.to.my.llm.com/hostedllm:12345",
)

# Node is a subclass of Component, we will define it more in detail later
node_1 = StartNode(id="lniwuebjsdvkc", name="Node 1", inputs=[input_1])
node_2 = LlmNode(
    id="nxbcwoiauhbjv",
    name="Node 2",
    llm_config=vllm,
    prompt_template="This is the prompt! {{ Input_2 }} {{ Input_3 }}",
    inputs=[input_2, input_3],
    outputs=[output_2],
)
node_3 = EndNode(id="724893yhrj", name="Node 3", outputs=[output_2, output_3])

# Control flow edges
control_edge_1 = ControlFlowEdge(
    id="nh32tewsaicjkl", name="ctrl_edge_1", from_node=node_1, to_node=node_2
)
control_edge_2 = ControlFlowEdge(
    id="28yu3egh", name="ctrl_edge_2", from_node=node_2, to_node=node_3
)

# Data flow edges
data_edge_1 = DataFlowEdge(
    id="buhdgsbjmn",
    name="data_edge_1",
    source_node=node_1,
    source_output="Input_1",
    destination_node=node_2,
    destination_input="Input_3",
)
data_edge_2 = DataFlowEdge(
    id="67uyh5423hje",
    name="data_edge_2",
    source_node=node_2,
    source_output="Output_2",
    destination_node=node_3,
    destination_input="Output_2",
)
data_edge_3 = DataFlowEdge(
    id="722njqbakhcsa",
    name="data_edge_3",
    source_node=node_1,
    source_output="Input_1",
    destination_node=node_3,
    destination_input="Output_3",
)

# Flow is a subclass of Component, we will define it more in detail later
flow = Flow(
    id="mmnhagawse",
    name="Example test flow",
    start_node=node_1,
    nodes=[node_1, node_2, node_3],
    control_flow_connections=[control_edge_1, control_edge_2],
    data_flow_connections=[data_edge_1, data_edge_2, data_edge_3],
    inputs=[input_1],
    outputs=[output_2, output_3],
)
# .. end-code
