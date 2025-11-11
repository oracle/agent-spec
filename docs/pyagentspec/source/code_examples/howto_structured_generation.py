# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors


from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    name="llm",
    model_id="model_id",
    url="url",
)

# .. start-article
article = """Sea turtles are ancient reptiles that have been around for over 100 million years. 
             They play crucial roles in marine ecosystems, such as maintaining healthy seagrass beds and coral reefs. 
             Unfortunately, they are under threat due to poaching, habitat loss, and pollution. 
             Conservation efforts worldwide aim to protect nesting sites and reduce bycatch in fishing gear."""
# .. end-article

# .. start-flow1
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import StringProperty

# Inputs and outputs
input_1 = StringProperty(title="article")
output_1 = StringProperty(title="summary")

# Nodes
start_node = StartNode(name="start_node", inputs=[input_1])
summarize_node = LlmNode(
    name="summarize_node",
    prompt_template="""Summarize this article in 10 words:\n {{article}}""",
    llm_config=llm_config,
    outputs=[output_1]
)
end_node = EndNode(name="end_node", outputs=[output_1])

# Control flow edges
control_edge_1 = ControlFlowEdge(
    name="control_edge_1", from_node=start_node, to_node=summarize_node
)
control_edge_2 = ControlFlowEdge(
    name="control_edge_2", from_node=summarize_node, to_node=end_node
)

# Data flow edges
data_edge_1 = DataFlowEdge(
    name="data_edge_1",
    source_node=start_node,
    source_output="article",
    destination_node=summarize_node,
    destination_input="article",
)
data_edge_2 = DataFlowEdge(
    name="data_edge_2",
    source_node=summarize_node,
    source_output="summary",
    destination_node=end_node,
    destination_input="summary",
)

# Flow
flow = Flow(
    name="Ten words summary",
    start_node=start_node,
    nodes=[start_node, summarize_node, end_node],
    control_flow_connections=[control_edge_1, control_edge_2],
    data_flow_connections=[data_edge_1, data_edge_2],
    inputs=[input_1],
    outputs=[output_1],
)
# .. end-flow1

# .. start-serialization1
from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(flow)
# .. end-serialization1

# .. start-structured11
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import ListProperty, StringProperty

input_1 = StringProperty(title="article")

# Desired outputs
animal_output = StringProperty(
    title="animal_name",
    description="name of the animal",
)

danger_level_output = StringProperty(
    title="danger_level",
    description='level of danger of the animal. Can be "HIGH", "MEDIUM" or "LOW"',
)

threats_output = ListProperty(
    title="threats",
    description="list of threats for the animal",
    item_type=StringProperty(title="threat"),
)

# Nodes
start_node = StartNode(name="start_node", inputs=[input_1])
summarize_node = LlmNode(
    name="summarize_node",
    prompt_template="""Extract from the following article the name of the animal, its danger level and the threats it's subject to. The article:\n\n {{article}}""",
    llm_config=llm_config,
    outputs=[animal_output, danger_level_output, threats_output]
)
end_node = EndNode(name="end_node", outputs=[animal_output, danger_level_output, threats_output])
# .. end-structured11

# .. start-structured12
# Control flow edges
control_edge_1 = ControlFlowEdge(
    name="control_edge_1", from_node=start_node, to_node=summarize_node
)
control_edge_2 = ControlFlowEdge(
    name="control_edge_2", from_node=summarize_node, to_node=end_node
)

# Data flow edges
data_edge_1 = DataFlowEdge(
    name="data_edge_1",
    source_node=start_node,
    source_output="article",
    destination_node=summarize_node,
    destination_input="article",
)
data_edge_2 = DataFlowEdge(
    name="data_edge_2",
    source_node=summarize_node,
    source_output="animal_name",
    destination_node=end_node,
    destination_input="animal_name",
)
data_edge_3 = DataFlowEdge(
    name="data_edge_3",
    source_node=summarize_node,
    source_output="danger_level",
    destination_node=end_node,
    destination_input="danger_level",
)
data_edge_4 = DataFlowEdge(
    name="data_edge_4",
    source_node=summarize_node,
    source_output="threats",
    destination_node=end_node,
    destination_input="threats",
)

# Flow
flow = Flow(
    name="Animal and its danger level and exposed threats",
    start_node=start_node,
    nodes=[start_node, summarize_node, end_node],
    control_flow_connections=[control_edge_1, control_edge_2],
    data_flow_connections=[data_edge_1, data_edge_2, data_edge_3, data_edge_4],
    inputs=[input_1],
    outputs=[animal_output, danger_level_output, threats_output],
)

from pyagentspec.serialization import AgentSpecSerializer
serialized_flow = AgentSpecSerializer().to_json(flow)
# .. end-structured12

# .. start-structured21
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import StringProperty, Property

input_1 = StringProperty(title="article")

# Output schema
animal_json_schema = {
    "title": "animal_object",
    "description": "information about the animal",
    "type": "object",
    "properties": {
        "animal_name": {
            "type": "string",
            "description": "name of the animal",
            "default": "",
        },
        "danger_level": {
            "type": "string",
            "description": 'level of danger of the animal. Can be "HIGH", "MEDIUM" or "LOW"',
            "default": "",
        },
        "threats": {
            "type": "array",
            "description": "list of threats for the animal",
            "items": {"type": "string"},
            "default": [],
        },
    },
}
animal_object = Property(json_schema=animal_json_schema)

# Nodes
start_node = StartNode(name="start_node", inputs=[input_1])
summarize_node = LlmNode(
    name="summarize_node",
    prompt_template="""Extract from the following article the name of the animal, its danger level and the threats it's subject to. The article:\n\n {{article}}""",
    llm_config=llm_config,
    outputs=[animal_object]
)
end_node = EndNode(name="end_node", outputs=[animal_object])
# .. end-structured21

# .. start-structured22
# Control Flow edges
control_edge_1 = ControlFlowEdge(
    name="control_edge_1", from_node=start_node, to_node=summarize_node
)
control_edge_2 = ControlFlowEdge(
    name="control_edge_2", from_node=summarize_node, to_node=end_node
)

# Data flow edges
data_edge_1 = DataFlowEdge(
    name="data_edge_1",
    source_node=start_node,
    source_output="article",
    destination_node=summarize_node,
    destination_input="article",
)
data_edge_2 = DataFlowEdge(
    name="data_edge_2",
    source_node=summarize_node,
    source_output="animal_object",
    destination_node=end_node,
    destination_input="animal_object",
)

# Flow
flow = Flow(
    name="Animal and its danger level and exposed threats",
    start_node=start_node,
    nodes=[start_node, summarize_node, end_node],
    control_flow_connections=[control_edge_1, control_edge_2],
    data_flow_connections=[data_edge_1, data_edge_2],
    inputs=[input_1],
    outputs=[animal_object],
)

from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(flow)
# .. end-structured22

# .. start-structured31
from pyagentspec.agent import Agent
from pyagentspec.flows.nodes import EndNode, AgentNode, StartNode
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import ListProperty, StringProperty

input_1 = StringProperty(title="article")

# Desired outputs
animal_output = StringProperty(
    title="animal_name",
    description="name of the animal",
)

danger_level_output = StringProperty(
    title="danger_level",
    description='level of danger of the animal. Can be "HIGH", "MEDIUM" or "LOW"',
)

threats_output = ListProperty(
    title="threats",
    description="list of threats for the animal",
    item_type=StringProperty(title="threat"),
)

# Nodes
start_node = StartNode(name="start_node", inputs=[input_1])
agent = Agent(
    name="Summarizing agent",
    llm_config=llm_config,
    system_prompt="""Extract from the following article the name of the animal, its danger level and the threats it's subject to. The article:\n\n {{article}}""",
    human_in_the_loop=False,
    outputs=[animal_output, danger_level_output, threats_output]
)
summarize_node = AgentNode(
    name="summarize_node",
    agent=agent,
    outputs=[animal_output, danger_level_output, threats_output]
)
end_node = EndNode(name="end_node", outputs=[animal_output, danger_level_output, threats_output])
# .. end-structured31

# .. start-structured32
# Control flow edges
control_edge_1 = ControlFlowEdge(
    name="control_edge_1", from_node=start_node, to_node=summarize_node
)
control_edge_2 = ControlFlowEdge(
    name="control_edge_2", from_node=summarize_node, to_node=end_node
)

# Data flow edges
data_edge_1 = DataFlowEdge(
    name="data_edge_1",
    source_node=start_node,
    source_output="article",
    destination_node=summarize_node,
    destination_input="article",
)
data_edge_2 = DataFlowEdge(
    name="data_edge_2",
    source_node=summarize_node,
    source_output="animal_name",
    destination_node=end_node,
    destination_input="animal_name",
)
data_edge_3 = DataFlowEdge(
    name="data_edge_3",
    source_node=summarize_node,
    source_output="danger_level",
    destination_node=end_node,
    destination_input="danger_level",
)
data_edge_4 = DataFlowEdge(
    name="data_edge_4",
    source_node=summarize_node,
    source_output="threats",
    destination_node=end_node,
    destination_input="threats",
)

# Flow
flow = Flow(
    name="Animal and its danger level and exposed threats",
    start_node=start_node,
    nodes=[start_node, summarize_node, end_node],
    control_flow_connections=[control_edge_1, control_edge_2],
    data_flow_connections=[data_edge_1, data_edge_2, data_edge_3, data_edge_4],
    inputs=[input_1],
    outputs=[animal_output, danger_level_output, threats_output],
)

from pyagentspec.serialization import AgentSpecSerializer
serialized_flow = AgentSpecSerializer().to_json(flow)
# .. end-structured32

# .. start-complete
from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    name="llm",
    model_id="model_id",
    url="url",
)

article = """Sea turtles are ancient reptiles that have been around for over 100 million years. 
             They play crucial roles in marine ecosystems, such as maintaining healthy seagrass beds and coral reefs. 
             Unfortunately, they are under threat due to poaching, habitat loss, and pollution. 
             Conservation efforts worldwide aim to protect nesting sites and reduce bycatch in fishing gear."""

# EXAMPLE - Summary of article
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import StringProperty

# Inputs and outputs
input_1 = StringProperty(title="article")
output_1 = StringProperty(title="summary")

# Nodes
start_node = StartNode(name="start_node", inputs=[input_1])
summarize_node = LlmNode(
    name="summarize_node",
    prompt_template="""Summarize this article in 10 words:\n {{article}}""",
    llm_config=llm_config,
    outputs=[output_1]
)
end_node = EndNode(name="end_node", outputs=[output_1])

# Control flow edges
control_edge_1 = ControlFlowEdge(
    name="control_edge_1", from_node=start_node, to_node=summarize_node
)
control_edge_2 = ControlFlowEdge(
    name="control_edge_2", from_node=summarize_node, to_node=end_node
)

# Data flow edges
data_edge_1 = DataFlowEdge(
    name="data_edge_1",
    source_node=start_node,
    source_output="article",
    destination_node=summarize_node,
    destination_input="article",
)
data_edge_2 = DataFlowEdge(
    name="data_edge_2",
    source_node=summarize_node,
    source_output="summary",
    destination_node=end_node,
    destination_input="summary",
)

# Flow
flow = Flow(
    name="Ten words summary",
    start_node=start_node,
    nodes=[start_node, summarize_node, end_node],
    control_flow_connections=[control_edge_1, control_edge_2],
    data_flow_connections=[data_edge_1, data_edge_2],
    inputs=[input_1],
    outputs=[output_1],
)

from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(flow)

# EXAMPLE - With 3 outputs
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import ListProperty, StringProperty

input_1 = StringProperty(title="article")

# Desired outputs
animal_output = StringProperty(
    title="animal_name",
    description="name of the animal",
)

danger_level_output = StringProperty(
    title="danger_level",
    description='level of danger of the animal. Can be "HIGH", "MEDIUM" or "LOW"',
)

threats_output = ListProperty(
    title="threats",
    description="list of threats for the animal",
    item_type=StringProperty(title="threat"),
)

# Nodes
start_node = StartNode(name="start_node", inputs=[input_1])
summarize_node = LlmNode(
    name="summarize_node",
    prompt_template="""Extract from the following article the name of the animal, its danger level and the threats it's subject to. The article:\n\n {{article}}""",
    llm_config=llm_config,
    outputs=[animal_output, danger_level_output, threats_output]
)
end_node = EndNode(name="end_node", outputs=[animal_output, danger_level_output, threats_output])

# Control flow edges
control_edge_1 = ControlFlowEdge(
    name="control_edge_1", from_node=start_node, to_node=summarize_node
)
control_edge_2 = ControlFlowEdge(
    name="control_edge_2", from_node=summarize_node, to_node=end_node
)

# Data flow edges
data_edge_1 = DataFlowEdge(
    name="data_edge_1",
    source_node=start_node,
    source_output="article",
    destination_node=summarize_node,
    destination_input="article",
)
data_edge_2 = DataFlowEdge(
    name="data_edge_2",
    source_node=summarize_node,
    source_output="animal_name",
    destination_node=end_node,
    destination_input="animal_name",
)
data_edge_3 = DataFlowEdge(
    name="data_edge_3",
    source_node=summarize_node,
    source_output="danger_level",
    destination_node=end_node,
    destination_input="danger_level",
)
data_edge_4 = DataFlowEdge(
    name="data_edge_4",
    source_node=summarize_node,
    source_output="threats",
    destination_node=end_node,
    destination_input="threats",
)

# Flow
flow = Flow(
    name="Animal and its danger level and exposed threats",
    start_node=start_node,
    nodes=[start_node, summarize_node, end_node],
    control_flow_connections=[control_edge_1, control_edge_2],
    data_flow_connections=[data_edge_1, data_edge_2, data_edge_3, data_edge_4],
    inputs=[input_1],
    outputs=[animal_output, danger_level_output, threats_output],
)

from pyagentspec.serialization import AgentSpecSerializer
serialized_flow = AgentSpecSerializer().to_json(flow)

# EXAMPLE - Complex JSON
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import StringProperty, Property

input_1 = StringProperty(title="article")

# Output schema
animal_json_schema = {
    "title": "animal_object",
    "description": "information about the animal",
    "type": "object",
    "properties": {
        "animal_name": {
            "type": "string",
            "description": "name of the animal",
            "default": "",
        },
        "danger_level": {
            "type": "string",
            "description": 'level of danger of the animal. Can be "HIGH", "MEDIUM" or "LOW"',
            "default": "",
        },
        "threats": {
            "type": "array",
            "description": "list of threats for the animal",
            "items": {"type": "string"},
            "default": [],
        },
    },
}
animal_object = Property(json_schema=animal_json_schema)

# Nodes
start_node = StartNode(name="start_node", inputs=[input_1])
summarize_node = LlmNode(
    name="summarize_node",
    prompt_template="""Extract from the following article the name of the animal, its danger level and the threats it's subject to. The article:\n\n {{article}}""",
    llm_config=llm_config,
    outputs=[animal_object]
)
end_node = EndNode(name="end_node", outputs=[animal_object])

# Control Flow edges
control_edge_1 = ControlFlowEdge(
    name="control_edge_1", from_node=start_node, to_node=summarize_node
)
control_edge_2 = ControlFlowEdge(
    name="control_edge_2", from_node=summarize_node, to_node=end_node
)

# Data flow edges
data_edge_1 = DataFlowEdge(
    name="data_edge_1",
    source_node=start_node,
    source_output="article",
    destination_node=summarize_node,
    destination_input="article",
)
data_edge_2 = DataFlowEdge(
    name="data_edge_2",
    source_node=summarize_node,
    source_output="animal_object",
    destination_node=end_node,
    destination_input="animal_object",
)

# Flow
flow = Flow(
    name="Animal and its danger level and exposed threats",
    start_node=start_node,
    nodes=[start_node, summarize_node, end_node],
    control_flow_connections=[control_edge_1, control_edge_2],
    data_flow_connections=[data_edge_1, data_edge_2],
    inputs=[input_1],
    outputs=[animal_object],
)

from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(flow)

# EXAMPLE - With Agents
from pyagentspec.agent import Agent
from pyagentspec.flows.nodes import EndNode, AgentNode, StartNode
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.property import ListProperty, StringProperty

input_1 = StringProperty(title="article")

# Desired outputs
animal_output = StringProperty(
    title="animal_name",
    description="name of the animal",
)

danger_level_output = StringProperty(
    title="danger_level",
    description='level of danger of the animal. Can be "HIGH", "MEDIUM" or "LOW"',
)

threats_output = ListProperty(
    title="threats",
    description="list of threats for the animal",
    item_type=StringProperty(title="threat"),
)

# Nodes
start_node = StartNode(name="start_node", inputs=[input_1])
agent = Agent(
    name="Summarizing agent",
    llm_config=llm_config,
    system_prompt="""Extract from the following article the name of the animal, its danger level and the threats it's subject to. The article:\n\n {{article}}""",
    human_in_the_loop=False,
    outputs=[animal_output, danger_level_output, threats_output]
)
summarize_node = AgentNode(
    name="summarize_node",
    agent=agent,
    outputs=[animal_output, danger_level_output, threats_output]
)
end_node = EndNode(name="end_node", outputs=[animal_output, danger_level_output, threats_output])

# Control flow edges
control_edge_1 = ControlFlowEdge(
    name="control_edge_1", from_node=start_node, to_node=summarize_node
)
control_edge_2 = ControlFlowEdge(
    name="control_edge_2", from_node=summarize_node, to_node=end_node
)

# Data flow edges
data_edge_1 = DataFlowEdge(
    name="data_edge_1",
    source_node=start_node,
    source_output="article",
    destination_node=summarize_node,
    destination_input="article",
)
data_edge_2 = DataFlowEdge(
    name="data_edge_2",
    source_node=summarize_node,
    source_output="animal_name",
    destination_node=end_node,
    destination_input="animal_name",
)
data_edge_3 = DataFlowEdge(
    name="data_edge_3",
    source_node=summarize_node,
    source_output="danger_level",
    destination_node=end_node,
    destination_input="danger_level",
)
data_edge_4 = DataFlowEdge(
    name="data_edge_4",
    source_node=summarize_node,
    source_output="threats",
    destination_node=end_node,
    destination_input="threats",
)

# Flow
flow = Flow(
    name="Animal and its danger level and exposed threats",
    start_node=start_node,
    nodes=[start_node, summarize_node, end_node],
    control_flow_connections=[control_edge_1, control_edge_2],
    data_flow_connections=[data_edge_1, data_edge_2, data_edge_3, data_edge_4],
    inputs=[input_1],
    outputs=[animal_output, danger_level_output, threats_output],
)

from pyagentspec.serialization import AgentSpecSerializer
serialized_flow = AgentSpecSerializer().to_json(flow)
# .. end-complete
