# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors
# docs-title: Agent Spec Code Example - How to Catch Exceptions in Flows

# .. start-##_Define_flaky_tool
from pyagentspec.property import BooleanProperty, StringProperty
from pyagentspec.tools import ServerTool

# Example tool that may raise at runtime (implementation depends on the executor)
raise_error = BooleanProperty(title="raise_error")
tool_output = StringProperty(title="tool_output", default="")
flaky_tool = ServerTool(
    name="flaky_tool",
    description="A tool that may raise an exception depending on inputs",
    inputs=[raise_error],
    outputs=[tool_output],
)
# .. end-##_Define_flaky_tool

# .. start-##_Define_subflow
from pyagentspec.flows.nodes import EndNode, StartNode, ToolNode
from pyagentspec.flows.flowbuilder import FlowBuilder

flaky_tool_node = ToolNode(name="flaky_tool_node", tool=flaky_tool)
subflow = FlowBuilder.build_linear_flow([flaky_tool_node])
# .. end-##_Define_subflow

# .. start-##_Wrap_with_CatchExceptionNode
from pyagentspec.flows.nodes import CatchExceptionNode

catch_node = CatchExceptionNode(name="catch_node", subflow=subflow)
# .. end-##_Wrap_with_CatchExceptionNode

# .. start-##_Build_Exception_Handling_Flow
from pyagentspec.flows.nodes import OutputMessageNode

outer_start = StartNode(name="start", inputs=[raise_error])
output_message_on_failure = OutputMessageNode(
    name="output_message_on_failure",
    message="Encountered failure while running subflow: {{exception_info}}"
)
success_end = EndNode(name="success_end", outputs=[tool_output])
failure_end = EndNode(name="failure_end", outputs=[tool_output])

flow =(
    FlowBuilder()
    .add_node(outer_start)
    .add_node(catch_node)
    .add_node(output_message_on_failure)
    .add_node(success_end)
    .add_node(failure_end)

    .add_edge(outer_start, catch_node, edge_name="start_to_catch")
    .add_edge(catch_node, success_end, edge_name="catch_to_success")
    .add_edge(catch_node, output_message_on_failure, CatchExceptionNode.CAUGHT_EXCEPTION_BRANCH, "caught_to_message")
    .add_edge(output_message_on_failure, failure_end, edge_name="message_to_failure_end")

    .add_data_edge(outer_start, catch_node, raise_error.title)
    .add_data_edge(catch_node, success_end, tool_output.title)
    .add_data_edge(
        catch_node, output_message_on_failure,
        (CatchExceptionNode.DEFAULT_EXCEPTION_INFO_VALUE, "exception_info")
    )
    .build()
)
# .. end-##_Build_Exception_Handling_Flow

# .. start-##_Export_config_to_Agent_Spec
from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(flow)
# .. end-##_Export_config_to_Agent_Spec
