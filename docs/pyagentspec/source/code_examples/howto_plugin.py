# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors

from pyagentspec.llms.vllmconfig import VllmConfig
llm_config = VllmConfig(
    name="Vllm model",
    url="vllm_url",
    model_id="model_id",
)

# .. start-customcomponents:
from typing import ClassVar, List

from pyagentspec.flows.node import Node
from pyagentspec.property import Property, StringProperty

class PluginRegexNode(Node):
    """Node to extract information from a raw text using a regular expression (regex)."""

    regex_pattern: str
    """Specify the regex pattern for searching in the input text."""

    DEFAULT_INPUT_KEY: ClassVar[str] = "text"
    """Input key for the name to transition to next."""

    DEFAULT_OUTPUT_KEY: ClassVar[str] = "output"
    """Input key for the name to transition to next."""

    def _get_inferred_inputs(self) -> List[Property]:
        input_title = self.inputs[0].title if self.inputs else self.DEFAULT_INPUT_KEY
        return [StringProperty(title=input_title)]

    def _get_inferred_outputs(self) -> List[Property]:
        output_title = self.outputs[0].title if self.outputs else self.DEFAULT_OUTPUT_KEY
        return [StringProperty(title=output_title)]
# .. end-customcomponents
# .. start-create-assistant:
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.property import StringProperty

llmoutput_property = StringProperty(title="llm_output", default="ERROR")
parsedoutput_property = StringProperty(title="output", default="<result>ERROR</result>")
start_node = StartNode(id="start", name="start", inputs=[])
llm_node = LlmNode(
    id="llm",
    name="llm",
    llm_config=llm_config,
    prompt_template=(
        "What is the result of 100+(454-3). Think step by step and then give "
        "your answer between <result>...</result> delimiters"
    ),
    outputs=[llmoutput_property],
)
regex_node = PluginRegexNode(
    id="regex",
    name="regex",
    regex_pattern=r"<result>(.*)</result>",
    outputs=[parsedoutput_property],
)
end_node = EndNode(id="end", name="end", outputs=[parsedoutput_property])

assistant = Flow(
    id="regex_flow",
    name="regex_flow",
    start_node=start_node,
    nodes=[start_node, llm_node, regex_node, end_node],
    control_flow_connections=[
        ControlFlowEdge(id="start_llm", name="start->llm", from_node=start_node, to_node=llm_node),
        ControlFlowEdge(id="llm_regex", name="llm->regex", from_node=llm_node, to_node=regex_node),
        ControlFlowEdge(id="regex_end", name="regex->end", from_node=regex_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="edge",
            source_node=llm_node,
            source_output="llm_output",
            destination_node=regex_node,
            destination_input="text"
        ),
        DataFlowEdge(
            name="edge",
            source_node=regex_node,
            source_output="output",
            destination_node=end_node,
            destination_input="output"
        ),
    ]
)
# .. end-create-assistant
# .. start-create-plugins:
from pyagentspec.serialization.pydanticdeserializationplugin import (
    PydanticComponentDeserializationPlugin,
)
from pyagentspec.serialization.pydanticserializationplugin import PydanticComponentSerializationPlugin

example_serialization_plugin = PydanticComponentSerializationPlugin(
    component_types_and_models={
        PluginRegexNode.__name__: PluginRegexNode,
    }
)

example_deserialization_plugin = PydanticComponentDeserializationPlugin(
    component_types_and_models={
        PluginRegexNode.__name__: PluginRegexNode,
    }
)
# .. end-create-plugins
"""
# .. start-export-config:
from pyagentspec.serialization import AgentSpecSerializer
serialized_assistant = AgentSpecSerializer(plugins=[example_serialization_plugin]).to_json(assistant)

with open("assistant_config.json", "w") as f:
    f.write(serialized_assistant)

# .. end-export-config
# .. start-load-config:
from wayflowcore.flow import Flow as RuntimeFlow
from wayflowcore.agentspec import AgentSpecLoader

with open("assistant_config.json") as f:
    agentspec_export = f.read()

# agentspec_loader = AgentSpecLoader(plugins=[example_deserialization_plugin])
assistant: RuntimeFlow = agentspec_loader.load_yaml(agentspec_export)
# .. end-load-config
# .. start-execute-assistant:
from wayflowcore.executors.executionstatus import FinishedStatus
inputs = {}
conversation = assistant.start_conversation(inputs)

status = conversation.execute()
if isinstance(status, FinishedStatus):
    outputs = status.output_values
    print(f"Assistant outputs: {outputs['output']}")
else:
    print(f"ERROR: Expected 'FinishedStatus', got {status.__class__.__name__}")

# Assistant outputs: 551
# .. end-execute-assistant
"""
