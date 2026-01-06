# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors
# docs-title: Code Example - How to Build Flows with the Flow Builder

# .. start-##_Build_a_linear_flow
from pyagentspec.flows.flowbuilder import FlowBuilder
from pyagentspec.flows.nodes import LlmNode
from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    name="Llama 3.1 8B instruct",
    url="your_url",
    model_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
)

greet = LlmNode(name="greet", llm_config=llm_config, prompt_template="Say hello")
reply = LlmNode(name="reply", llm_config=llm_config, prompt_template="Say world")

linear_flow = FlowBuilder.build_linear_flow([greet, reply])
# .. end-##_Build_a_linear_flow


# .. start-##_Build_a_flow_with_a_conditional
decider = LlmNode(
    name="decider",
    llm_config=llm_config,
    prompt_template="Return success or fail",
)
on_success = LlmNode(name="on_success", llm_config=llm_config, prompt_template="OK")
on_fail = LlmNode(name="on_fail", llm_config=llm_config, prompt_template="KO")

flow_with_branch = (
    FlowBuilder()
    .add_sequence([decider])
    .add_node(on_success)
    .add_node(on_fail)
    .add_conditional(
        source_node=decider,
        source_value=LlmNode.DEFAULT_OUTPUT,
        destination_map={"success": on_success, "fail": on_fail},
        default_destination=on_fail,
    )
    .set_entry_point(decider)
    .set_finish_points([on_success, on_fail])
    .build()
)
# .. end-##_Build_a_flow_with_a_conditional

# .. start-##_Build_a_flow_with_manual_connections
producer = LlmNode(name="producer", llm_config=llm_config, prompt_template="Say Hello")
consumer1 = LlmNode(name="consumer1", llm_config=llm_config, prompt_template="{{generated_text}}")
consumer2 = LlmNode(name="consumer2", llm_config=llm_config, prompt_template="{{also_value}}")

flow_with_connections = (
    FlowBuilder()
    .add_node(producer)
    .add_node(consumer1)
    .add_node(consumer2)
    .add_edge(producer, consumer1)
    .add_edge(producer, consumer2)
    # Using the default output name for LlmNode.DEFAULT_OUTPUT
    .add_data_edge(producer, consumer1, LlmNode.DEFAULT_OUTPUT)
    .add_data_edge(producer, consumer2, (LlmNode.DEFAULT_OUTPUT, "also_value"))
    .set_entry_point(producer)
    .set_finish_points([consumer1, consumer2])
    .build()
)
# .. end-##_Build_a_flow_with_manual_connections

# .. start-##_Export_to_IR
from pyagentspec.serialization import AgentSpecSerializer

serialized_linear = AgentSpecSerializer().to_json(linear_flow)
serialized_branch = AgentSpecSerializer().to_json(flow_with_branch)
# .. end-##_Export_to_IR


# .. start-full-code
from pyagentspec.flows.flowbuilder import FlowBuilder
from pyagentspec.flows.nodes import LlmNode
from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    name="Llama 3.1 8B instruct",
    url="http://localhost:8000",
    model_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
)

greet = LlmNode(name="greet", llm_config=llm_config, prompt_template="Say hello")
reply = LlmNode(name="reply", llm_config=llm_config, prompt_template="Say world")
linear_flow = FlowBuilder.build_linear_flow([greet, reply])

decider = LlmNode(
    name="decider",
    llm_config=llm_config,
    prompt_template="Return success or fail",
)
on_success = LlmNode(name="on_success", llm_config=llm_config, prompt_template="OK")
on_fail = LlmNode(name="on_fail", llm_config=llm_config, prompt_template="KO")
flow_with_branch = (
    FlowBuilder()
    .add_sequence([decider])
    .add_node(on_success)
    .add_node(on_fail)
    .add_conditional(
        source_node=decider,
        source_value=LlmNode.DEFAULT_OUTPUT,
        destination_map={"success": on_success, "fail": on_fail},
        default_destination=on_fail,
    )
    .set_entry_point(decider)
    .set_finish_points([on_success, on_fail])
    .build()
)

from pyagentspec.serialization import AgentSpecSerializer
serialized_linear = AgentSpecSerializer().to_json(linear_flow)
serialized_branch = AgentSpecSerializer().to_json(flow_with_branch)
# .. end-full-code
