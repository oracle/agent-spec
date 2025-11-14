# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors
# docs-title: Agent Spec Code Example - How to Run Multiple Flows in Parallel

# .. start-##_Define_the_tools
from pyagentspec.property import DictProperty, ListProperty, StringProperty
from pyagentspec.tools import ServerTool

username_property = StringProperty(title="username")
user_info_property = DictProperty(title="user_info", value_type=StringProperty())
get_user_information_tool = ServerTool(
    name="get_user_information",
    description="Retrieve information about a user",
    inputs=[username_property],
    outputs=[user_info_property],
)

current_time_property = StringProperty(title="current_time")
get_current_time_tool = ServerTool(
    name="get_current_time",
    description="Return current time",
    inputs=[],
    outputs=[current_time_property],
)

user_purchases_property = ListProperty(title="user_purchases", item_type=DictProperty(value_type=StringProperty()))
get_user_last_purchases_tool = ServerTool(
    name="get_user_last_purchases",
    description="Retrieve the list of purchases made by a user",
    inputs=[username_property],
    outputs=[user_purchases_property],
)

items_on_sale_property = ListProperty(title="items_on_sale", item_type=DictProperty(value_type=StringProperty()))
get_items_on_sale_tool = ServerTool(
    name="get_items_on_sale",
    description="Retrieve the list of items currently on sale",
    inputs=[],
    outputs=[items_on_sale_property],
)
# .. end-##_Define_the_tools
# .. start-##_Create_the_flows_to_be_run_in_parallel
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import ParallelFlowNode, ToolNode, StartNode, EndNode

def create_one_node_flow(node: Node) -> Flow:
    """Create a flow that wraps the given node, having the same inputs and outputs"""
    flow_name = node.name + "_flow"
    start_node = StartNode(name=flow_name + "_start", inputs=node.inputs)
    end_node = EndNode(name=flow_name + "_end", outputs=node.outputs)
    return Flow(
        name=flow_name,
        start_node=start_node,
        nodes=[start_node, end_node, node],
        control_flow_connections=[
            ControlFlowEdge(name="c1", from_node=start_node, to_node=node),
            ControlFlowEdge(name="c2", from_node=node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name=f"din_{input_property.title}",
                source_node=start_node, source_output=input_property.title,
                destination_node=node, destination_input=input_property.title,
            )
            for input_property in node.inputs
        ] + [
            DataFlowEdge(
                name=f"dout_{output_property.title}",
                source_node=node, source_output=output_property.title,
                destination_node=end_node, destination_input=output_property.title,
            )
            for output_property in node.outputs
        ]
    )

get_current_time_flow = create_one_node_flow(
    ToolNode(name="get_current_time_step", tool=get_current_time_tool)
)
get_user_information_flow = create_one_node_flow(
    ToolNode(name="get_user_information_step", tool=get_user_information_tool)
)
get_user_last_purchases_flow = create_one_node_flow(
    ToolNode(name="get_user_last_purchases_step", tool=get_user_last_purchases_tool)
)
get_items_on_sale_flow = create_one_node_flow(
    ToolNode(name="get_items_on_sale_steo", tool=get_items_on_sale_tool)
)

parallel_flow_node = ParallelFlowNode(
    name="parallel_flow_node",
    subflows=[
        get_current_time_flow,
        get_user_information_flow,
        get_user_last_purchases_flow,
        get_items_on_sale_flow,
    ],
)
# .. end-##_Create_the_flows_to_be_run_in_parallel
# .. start-##_Generate_the_marketing_message
from pyagentspec.llms import VllmConfig
from pyagentspec.flows.nodes import OutputMessageNode, LlmNode

llm_config = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
)

prompt = """# Instructions

You are a marketing expert. You have to write a welcome message for a user.

The message must contain:
- A first sentence of greetings, including user's name, and personalized in case it's user's birthday
- A proposal containing something to buy

The purchase proposal must be:
- aligned with user's purchase history
- part of the list of items on sale

# User information

{{user_info}}

Note that the current time to check the birthday is: {{current_time}}

The list of items purchased by the user is:
{{user_purchases}}

# Items on sale

{{items_on_sale}}

Please write the welcome message for the user.
Do not give me the instructions to do it, I want only the final message to send.
"""

prepare_marketing_message_node = LlmNode(
    name="prepare_marketing_message_node", prompt_template=prompt, llm_config=llm_config
)
output_message_node = OutputMessageNode(name="output_message_node", message="{{output}}")
# .. end-##_Generate_the_marketing_message
# .. start-##_Create_and_test_the_final_flow
from pyagentspec.flows.flow import Flow

start_node = StartNode(name="start_node", inputs=[username_property])
end_node = EndNode(name="end_node")
flow = Flow(
    name="marketing_message_flow",
    start_node=start_node,
    nodes=[parallel_flow_node, prepare_marketing_message_node, output_message_node, start_node, end_node],
    control_flow_connections=[
        ControlFlowEdge(name="cfe1", from_node=start_node, to_node=parallel_flow_node),
        ControlFlowEdge(name="cfe2", from_node=parallel_flow_node, to_node=prepare_marketing_message_node),
        ControlFlowEdge(name="cfe3", from_node=prepare_marketing_message_node, to_node=output_message_node),
        ControlFlowEdge(name="cfe4", from_node=output_message_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="dfe_username",
            source_node=start_node, source_output="username",
            destination_node=parallel_flow_node, destination_input="username",
        )
    ] + [
        DataFlowEdge(
            name="dfe_" + property_.title,
            source_node=parallel_flow_node, source_output=property_.title,
            destination_node=prepare_marketing_message_node, destination_input=property_.title,
        )
        for property_ in [current_time_property, user_info_property, user_purchases_property, items_on_sale_property]
    ]
)
# .. end-##_Create_and_test_the_final_flow
# .. start-##_Export_config_to_Agent_Spec
from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(flow)
# .. end-##_Export_config_to_Agent_Spec
# .. start-##_Load_Agent_Spec_config
from pyagentspec.serialization import AgentSpecDeserializer

flow = AgentSpecDeserializer().from_json(serialized_flow)
# .. end-##_Load_Agent_Spec_config


# .. start-##_Full_code
from pyagentspec.property import DictProperty, ListProperty, StringProperty
from pyagentspec.tools import ServerTool

username_property = StringProperty(title="username")
user_info_property = DictProperty(title="user_info", value_type=StringProperty())
get_user_information_tool = ServerTool(
    name="get_user_information",
    description="Retrieve information about a user",
    inputs=[username_property],
    outputs=[user_info_property],
)

current_time_property = StringProperty(title="current_time")
get_current_time_tool = ServerTool(
    name="get_current_time",
    description="Return current time",
    inputs=[],
    outputs=[current_time_property],
)

user_purchases_property = ListProperty(title="user_purchases", item_type=DictProperty(value_type=StringProperty()))
get_user_last_purchases_tool = ServerTool(
    name="get_user_last_purchases",
    description="Retrieve the list of purchases made by a user",
    inputs=[username_property],
    outputs=[user_purchases_property],
)

items_on_sale_property = ListProperty(title="items_on_sale", item_type=DictProperty(value_type=StringProperty()))
get_items_on_sale_tool = ServerTool(
    name="get_items_on_sale",
    description="Retrieve the list of items currently on sale",
    inputs=[],
    outputs=[items_on_sale_property],
)


from pyagentspec.flows.flow import Flow
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import ParallelFlowNode, ToolNode, StartNode, EndNode

def create_one_node_flow(node: Node) -> Flow:
    """Create a flow that wraps the given node, having the same inputs and outputs"""
    flow_name = node.name + "_flow"
    start_node = StartNode(name=flow_name + "_start", inputs=node.inputs)
    end_node = EndNode(name=flow_name + "_start", outputs=node.outputs)
    return Flow(
        name=flow_name,
        start_node=start_node,
        nodes=[start_node, end_node, node],
        control_flow_connections=[
            ControlFlowEdge(name="c1", from_node=start_node, to_node=node),
            ControlFlowEdge(name="c2", from_node=node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name=f"din_{input_property.title}",
                source_node=start_node, source_output=input_property.title,
                destination_node=node, destination_input=input_property.title,
            )
            for input_property in node.inputs
        ] + [
            DataFlowEdge(
                name=f"dout_{output_property.title}",
                source_node=node, source_output=output_property.title,
                destination_node=end_node, destination_input=output_property.title,
            )
            for output_property in node.outputs
        ]
    )

get_current_time_flow = create_one_node_flow(
    ToolNode(name="get_current_time_step", tool=get_current_time_tool)
)
get_user_information_flow = create_one_node_flow(
    ToolNode(name="get_user_information_step", tool=get_user_information_tool)
)
get_user_last_purchases_flow = create_one_node_flow(
    ToolNode(name="get_user_last_purchases_step", tool=get_user_last_purchases_tool)
)
get_items_on_sale_flow = create_one_node_flow(
    ToolNode(name="get_items_on_sale_steo", tool=get_items_on_sale_tool)
)

parallel_flow_node = ParallelFlowNode(
    name="parallel_flow_node",
    subflows=[
        get_current_time_flow,
        get_user_information_flow,
        get_user_last_purchases_flow,
        get_items_on_sale_flow,
    ],
)


from pyagentspec.llms import VllmConfig
from pyagentspec.flows.nodes import OutputMessageNode, LlmNode

llm_config = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
)

prompt = """# Instructions

You are a marketing expert. You have to write a welcome message for a user.

The message must contain:
- A first sentence of greetings, including user's name, and personalized in case it's user's birthday
- A proposal containing something to buy

The purchase proposal must be:
- aligned with user's purchase history
- part of the list of items on sale

# User information

{{user_info}}

Note that the current time to check the birthday is: {{current_time}}

The list of items purchased by the user is:
{{user_purchases}}

# Items on sale

{{items_on_sale}}

Please write the welcome message for the user.
Do not give me the instructions to do it, I want only the final message to send.
"""

prepare_marketing_message_node = LlmNode(
    name="prepare_marketing_message_node", prompt_template=prompt, llm_config=llm_config
)
output_message_node = OutputMessageNode(name="output_message_node", message="{{output}}")


from pyagentspec.flows.flow import Flow

start_node = StartNode(name="start_node", inputs=[username_property])
end_node = EndNode(name="end_node")
flow = Flow(
    name="marketing_message_flow",
    start_node=start_node,
    nodes=[parallel_flow_node, prepare_marketing_message_node, output_message_node, start_node, end_node],
    control_flow_connections=[
        ControlFlowEdge(name="cfe1", from_node=start_node, to_node=parallel_flow_node),
        ControlFlowEdge(name="cfe2", from_node=parallel_flow_node, to_node=prepare_marketing_message_node),
        ControlFlowEdge(name="cfe3", from_node=prepare_marketing_message_node, to_node=output_message_node),
        ControlFlowEdge(name="cfe4", from_node=output_message_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="dfe_username",
            source_node=start_node, source_output="username",
            destination_node=parallel_flow_node, destination_input="username",
        )
    ] + [
        DataFlowEdge(
            name="dfe_" + property_.title,
            source_node=parallel_flow_node, source_output=property_.title,
            destination_node=prepare_marketing_message_node, destination_input=property_.title,
        )
        for property_ in [current_time_property, user_info_property, user_purchases_property, items_on_sale_property]
    ]
)

from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(flow)
# .. end-##_Full_code
