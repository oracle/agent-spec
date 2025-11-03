# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors

# .. generation_config:
from pyagentspec.llms import LlmGenerationConfig

generation_config = LlmGenerationConfig(max_tokens=512, temperature=1.0, top_p=1.0)
# .. end-generation_config

# .. vllm_config:
from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
    default_generation_parameters=generation_config,
)
# .. end-vllm_config

# .. agent:
from pyagentspec import Agent

agent = Agent(
    name="my_first_agent",
    llm_config=llm_config,
    system_prompt="You are a helpful assistant.",
)
# .. end-agent


# .. flow:
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import LlmNode, StartNode, EndNode
from pyagentspec.property import StringProperty

start_node = StartNode(name="start", inputs=[StringProperty(title="user_question")])
end_node = EndNode(name="end", outputs=[StringProperty(title="llm_output")])
llm_node = LlmNode(
    name="llm_node",
    prompt_template="{{user_question}}",
    llm_config=llm_config,
    outputs=[StringProperty(title="llm_output")]
)
flow = Flow(
    name="flow",
    start_node=start_node,
    nodes=[start_node, end_node, llm_node],
    control_flow_connections=[
        ControlFlowEdge(name="cfe1", from_node=start_node, to_node=llm_node),
        ControlFlowEdge(name="cfe2", from_node=llm_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="dfe1",
            source_node=start_node,
            source_output="user_question",
            destination_node=llm_node,
            destination_input="user_question"
        ),
        DataFlowEdge(
            name="dfe2",
            source_node=llm_node,
            source_output="llm_output",
            destination_node=end_node,
            destination_input="llm_output"
        ),
    ],
)
# .. end-flow

# .. recap:
from pyagentspec.llms import LlmGenerationConfig, VllmConfig

generation_config = LlmGenerationConfig(max_tokens=512, temperature=1.0, top_p=1.0)

llm_config = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
    default_generation_parameters=generation_config,
)

from pyagentspec import Agent

agent = Agent(
    name="my_first_agent",
    llm_config=llm_config,
    system_prompt="You are a helpful assistant.",
)

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import LlmNode, StartNode, EndNode
from pyagentspec.property import StringProperty

start_node = StartNode(name="start", inputs=[StringProperty(title="user_question")])
end_node = EndNode(name="end", outputs=[StringProperty(title="llm_output")])
llm_node = LlmNode(
    name="llm_node",
    prompt_template="{{user_question}}",
    llm_config=llm_config,
    outputs=[StringProperty(title="llm_output")]
)
flow = Flow(
    name="flow",
    start_node=start_node,
    nodes=[start_node, end_node, llm_node],
    control_flow_connections=[
        ControlFlowEdge(name="cfe1", from_node=start_node, to_node=llm_node),
        ControlFlowEdge(name="cfe2", from_node=llm_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="dfe1",
            source_node=start_node,
            source_output="user_question",
            destination_node=llm_node,
            destination_input="user_question"
        ),
        DataFlowEdge(
            name="dfe2",
            source_node=llm_node,
            source_output="llm_output",
            destination_node=end_node,
            destination_input="llm_output"
        ),
    ],
)
# .. end-recap
