# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from pyagentspec.adapters._utils import create_pydantic_model_from_properties, render_template
from pyagentspec.adapters.crewai._types import (
    CrewAIFlow,
    CrewAILlm,
    CrewAITool,
    ExecuteOutput,
    FlowState,
    NodeInput,
    NodeOutput,
)
from pyagentspec.flows.edges import DataFlowEdge
from pyagentspec.flows.node import Node as AgentSpecNode
from pyagentspec.flows.nodes import EndNode as AgentSpecEndNode
from pyagentspec.flows.nodes import InputMessageNode as AgentSpecInputMessageNode
from pyagentspec.flows.nodes import LlmNode as AgentSpecLlmNode
from pyagentspec.flows.nodes import OutputMessageNode as AgentSpecOutputMessageNode
from pyagentspec.flows.nodes import StartNode as AgentSpecStartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import _empty_default as pyagentspec_empty_default


class NodeExecutor(ABC):
    def __init__(self, node: AgentSpecNode) -> None:
        self.node = node
        self.edges: List[DataFlowEdge] = []

    def attach_edge(self, edge: DataFlowEdge) -> None:
        self.edges.append(edge)

    @abstractmethod
    def _execute(self, inputs: NodeInput) -> ExecuteOutput:
        """
        Returns the output of executing node with the given inputs.
        """

    def get_node_wrapper(self) -> Callable[..., NodeOutput]:
        """
        Prepares a callable that will be decorated and part of the CrewAI Flow class.
        This wraps around the node's _execute method and handles all inputs and outputs
        using the state variable of the CrewAI Flow.
        """

        def node_wrapper(self_flow: CrewAIFlow[FlowState], *args: Any, **kwargs: Any) -> NodeOutput:
            inputs = self._get_inputs(self_flow.state)
            execute_outputs = self._execute(inputs)
            node_outputs = self._update_status(self_flow.state, execute_outputs)

            return node_outputs

        return node_wrapper

    def _get_inputs(self, state: FlowState) -> NodeInput:
        input_properties = self.node.inputs or []
        input_values = {}

        for edge in self.edges:
            if edge.destination_node.id == self.node.id:
                property_name = edge.destination_input
                property_name_global = self._globalize_property_name(property_name)
                input_values[property_name] = state[property_name_global]

        return self._cast_values_and_add_defaults(input_values, input_properties)

    def _update_status(self, state: FlowState, outputs: ExecuteOutput) -> NodeOutput:
        output_properties = self.node.outputs or []
        output_values = self._cast_values_and_add_defaults(outputs, output_properties)

        for edge in self.edges:
            if edge.source_node.id == self.node.id:
                property_value = output_values[edge.source_output]

                output_property_name_global = self._globalize_property_name(edge.source_output)
                state[output_property_name_global] = property_value

                next_input_property_name_global = self._globalize_property_name(
                    edge.destination_input, edge.destination_node.id
                )
                state[next_input_property_name_global] = property_value

        return {
            property.title: output_values[property.title]
            for property in output_properties
            if property.title in output_values
        }

    def _globalize_property_name(self, property_name: str, node_id: Optional[str] = None) -> str:
        return f"{node_id or self.node.id}::{property_name}"

    def _cast_values_and_add_defaults(
        self,
        values_dict: Dict[str, Any],
        properties: List[AgentSpecProperty],
    ) -> Dict[str, Any]:
        results_dict: Dict[str, Any] = {}
        for property_ in properties:
            key = property_.title
            if key in values_dict:
                value = values_dict.get(key)
                if property_.type == "string" and not isinstance(value, str):
                    value = json.dumps(value)
                elif property_.type == "boolean" and isinstance(value, (int, float)):
                    value = bool(value)
                elif property_.type == "integer" and isinstance(value, (float, bool)):
                    value = int(value)
                elif property_.type == "number" and isinstance(value, (int, bool)):
                    value = float(value)
                results_dict[key] = value
            elif property_.default is not pyagentspec_empty_default:
                results_dict[key] = property_.default
            else:
                raise ValueError(
                    f"Expected node `{self.node.name}` to have a value "
                    f"for property `{property_.title}`, but none was found."
                )
        return results_dict


class StartNodeExecutor(NodeExecutor):
    node: AgentSpecStartNode

    def _get_inputs(self, state: FlowState) -> NodeInput:
        input_properties = self.node.inputs or []
        input_values = {}

        for property in input_properties:
            if property.title in state:
                input_values[property.title] = state[property.title]

        return self._cast_values_and_add_defaults(input_values, input_properties)

    def _execute(self, inputs: NodeInput) -> ExecuteOutput:
        return inputs


class EndNodeExecutor(NodeExecutor):
    node: AgentSpecEndNode

    def _update_status(self, state: FlowState, outputs: ExecuteOutput) -> NodeOutput:
        output_properties = self.node.outputs or []
        output_values = {}

        for property in output_properties:
            if property.title in outputs:
                output_values[property.title] = outputs[property.title]

        output_values = self._cast_values_and_add_defaults(output_values, output_properties)

        for property_name, property_value in output_values.items():
            state[self._globalize_property_name(property_name)] = property_value

        return output_values

    def _execute(self, inputs: NodeInput) -> ExecuteOutput:
        return inputs


class ToolNodeExecutor(NodeExecutor):
    node: AgentSpecToolNode

    def __init__(self, node: AgentSpecToolNode, tool: CrewAITool) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecToolNode):
            raise TypeError("ToolNodeExecutor can only be initialized with ToolNode")
        self.tool = tool

    def _execute(self, inputs: NodeInput) -> ExecuteOutput:
        tool_output = self.tool.run(**inputs)

        if isinstance(tool_output, dict):
            return tool_output

        output_name = self.node.outputs[0].title if self.node.outputs else "tool_output"
        return {output_name: tool_output}


class LlmNodeExecutor(NodeExecutor):
    node: AgentSpecLlmNode

    def __init__(self, node: AgentSpecLlmNode, llm: CrewAILlm) -> None:
        super().__init__(node)

        self.llm: CrewAILlm = llm

        node_outputs = self.node.outputs or []
        requires_structured_generation = not (
            len(node_outputs) == 1 and node_outputs[0].type == "string"
        )
        if requires_structured_generation:
            self.llm.response_format = create_pydantic_model_from_properties(
                self.node.name.title() + "ResponseFormat", node_outputs
            )

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        prompt_template = self.node.prompt_template
        rendered_prompt = render_template(prompt_template, inputs)

        generated_message = self.llm.call(rendered_prompt)

        if self.llm.response_format is not None:
            if not isinstance(generated_message, BaseModel):
                raise TypeError(
                    f"Expected LLM response format to be BaseModel, got {type(generated_message)!r}"
                )

            return generated_message.dict()
        else:
            node_outputs = self.node.outputs or []
            output_name = node_outputs[0].title if node_outputs else "generated_text"
            return {output_name: generated_message}


class InputMessageNodeExecutor(NodeExecutor):
    node: AgentSpecInputMessageNode

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        from crewai.events.event_listener import event_listener
        from crewai.utilities.printer import Printer

        printer = Printer()
        event_listener.formatter.pause_live_updates()

        try:
            printer.print(content=f"\nPlease provide your input message:", color="bold_yellow")
            response = input().strip()
            output_name = (
                self.node.outputs[0].title
                if self.node.outputs
                else AgentSpecInputMessageNode.DEFAULT_OUTPUT
            )
            return {output_name: response}
        finally:
            event_listener.formatter.resume_live_updates()


class OutputMessageNodeExecutor(NodeExecutor):
    node: AgentSpecOutputMessageNode

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        from crewai.events.event_listener import event_listener
        from crewai.utilities.printer import Printer

        printer = Printer()
        event_listener.formatter.pause_live_updates()

        try:
            message = render_template(self.node.message, inputs)
            printer.print(content=f"\n{message}\n", color="bold_yellow")
            return {}
        finally:
            event_listener.formatter.resume_live_updates()
