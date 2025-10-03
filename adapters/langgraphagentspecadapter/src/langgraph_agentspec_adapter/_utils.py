# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Hashable, List, Tuple, TypedDict, Union

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph, RunnableConfig
from pydantic import SerializeAsAny
from typing_extensions import TypeAlias

from pyagentspec.flows.edges import DataFlowEdge
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import AgentNode as AgentSpecAgentNode
from pyagentspec.flows.nodes import ApiNode as AgentSpecApiNode
from pyagentspec.flows.nodes import BranchingNode as AgentSpecBranchingNode
from pyagentspec.flows.nodes import EndNode as AgentSpecEndNode
from pyagentspec.flows.nodes import FlowNode as AgentSpecFlowNode
from pyagentspec.flows.nodes import LlmNode as AgentSpecLlmNode
from pyagentspec.flows.nodes import MapNode as AgentSpecMapNode
from pyagentspec.flows.nodes import StartNode as AgentSpecStartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
from pyagentspec.templating import TEMPLATE_PLACEHOLDER_REGEXP
from pyagentspec.tools import Tool

LangGraphTool: TypeAlias = Union[BaseTool, Callable[..., Any]]
LangGraphComponent = Union[StateGraph[Any, Any, Any], CompiledStateGraph[Any, Any, Any]]


@dataclass
class LangGraphLlmConfig:
    model_type: str
    model_name: str
    base_url: str
    tools: List[SerializeAsAny[Tool]]


class NodeExecutionDetails(TypedDict, total=False):
    should_finish: bool
    branch: str


NodeOutputsType: TypeAlias = Dict[str, Any]
ExecuteOutput: TypeAlias = Tuple[NodeOutputsType, NodeExecutionDetails]
NextNodeInputs: TypeAlias = Dict[str, Any]


class FlowStateSchema(TypedDict):
    inputs: NextNodeInputs
    outputs: NodeOutputsType
    node_execution_details: NodeExecutionDetails


SourceNodeId: TypeAlias = str
BranchName: TypeAlias = Hashable
TargetNodeId: TypeAlias = str
ControlFlow: TypeAlias = Dict[SourceNodeId, Dict[BranchName, TargetNodeId]]


def render_template(template: str, inputs: Dict[str, Any]) -> str:
    """Render a prompt template using inputs."""
    return _recursive_template_splitting_rendering(
        template, [(input_title, input_value) for input_title, input_value in inputs.items()]
    )


def _recursive_template_splitting_rendering(template: str, inputs: List[Tuple[str, Any]]) -> str:
    """Recursively split and join the templates using the list of inputs."""
    if len(inputs) == 0:
        return template
    input_title, input_value = inputs[-1]
    splitting_regexp = TEMPLATE_PLACEHOLDER_REGEXP.replace(r"(\w+)", input_title)
    split_templates = re.split(splitting_regexp, template)
    rendered_split_templates = [
        _recursive_template_splitting_rendering(t, inputs[:-1]) for t in split_templates
    ]
    rendered_template = str(input_value).join(rendered_split_templates)
    return rendered_template


class NodeExecutor(ABC):
    def __init__(self, node: Node) -> None:
        self.node = node
        self.edges: List[DataFlowEdge] = []

    def __call__(self, state: FlowStateSchema) -> Any:
        inputs = self._get_inputs(state)
        outputs, execution_details = self._execute(inputs)
        return self._format_output(outputs, execution_details, state)

    def attach_edge(self, edge: DataFlowEdge) -> None:
        self.edges.append(edge)

    @abstractmethod
    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        """Returns the output of executing node with the given inputs.
        The output will be transformed into a dictionary based on the FlowStateSchema.
        """
        # TODO: for all nodes implementing the _execute method, if the node returns a value,
        # we wrap it in a dictionary with the key being the title of the output descriptor, the value being... the value
        # Otherwise if we have multiple properties in the output descriptors, we should verify that the output is a dictionary and that it contains all the keys required for it to be considered a valid output

    def _get_inputs(self, state: FlowStateSchema) -> Dict[str, Any]:
        inputs = self.node.inputs or []
        default_inputs = {
            input_property.title: input_property.default
            for input_property in inputs
            if "default" in input_property.json_schema
        }
        io_inputs = state["inputs"]

        # TODO: Proper DataFlowEdge flow, runners of LangGraph graphs shouldn't be imposed to know about component ids
        # NOTE: could implement special case _get_inputs and _format_output for Start and End Nodes
        return default_inputs | io_inputs

    def _format_output(
        self,
        outputs: NodeOutputsType,
        execution_details: NodeExecutionDetails,
        previous_state: FlowStateSchema,
    ) -> FlowStateSchema:
        next_node_inputs = previous_state["inputs"] or {}
        for edge in self.edges:
            next_node_inputs[edge.destination_input] = outputs[edge.source_output]

        return {
            "inputs": next_node_inputs,
            "outputs": outputs,
            "node_execution_details": execution_details,
        }


class StartNodeExecutor(NodeExecutor):
    node: AgentSpecStartNode

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        node_inputs = self.node.inputs or []
        outputs = {
            input_property.title: inputs.get(input_property.title, input_property.default)
            for input_property in node_inputs
        }
        return outputs, NodeExecutionDetails()


class EndNodeExecutor(NodeExecutor):
    node: AgentSpecEndNode

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        node_inputs = self.node.inputs or []
        outputs = {
            input_property.title: inputs.get(input_property.title, input_property.default)
            for input_property in node_inputs
        }
        return outputs, NodeExecutionDetails()


class BranchingNodeExecutor(NodeExecutor):
    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        if not isinstance(self.node, AgentSpecBranchingNode):
            raise TypeError("BranchingNodeExecutor can only execute BranchingNode")
        if self.node.inputs:
            input_branch_prop_title = self.node.inputs[0].title
            input_branch_name = str(
                inputs.get(input_branch_prop_title, AgentSpecBranchingNode.DEFAULT_BRANCH)
            )
            selected_branch = self.node.mapping.get(
                input_branch_name, AgentSpecBranchingNode.DEFAULT_BRANCH
            )
            return {}, NodeExecutionDetails(branch=selected_branch)
        return {}, NodeExecutionDetails(branch=AgentSpecBranchingNode.DEFAULT_BRANCH)


class ToolNodeExecutor(NodeExecutor):
    node: AgentSpecToolNode

    def __init__(self, node: AgentSpecToolNode, tool: LangGraphTool) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecToolNode):
            raise TypeError("ToolNodeExecutor can only be initialized with ToolNode")
        self.tool_callable = tool

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        tool_output = self.tool_callable(**inputs)

        if isinstance(tool_output, dict):
            # useful for multiple outputs, avoid nesting dictionaries
            return tool_output, NodeExecutionDetails()

        output_name = self.node.outputs[0].title if self.node.outputs else "tool_output"
        return {output_name: tool_output}, NodeExecutionDetails()


class AgentNodeExecutor(NodeExecutor):
    node: AgentSpecAgentNode

    def __init__(
        self,
        node: AgentSpecAgentNode,
        agent: CompiledStateGraph[Any, Any],
        config: RunnableConfig,
    ) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecAgentNode):
            raise TypeError("AgentNode can only be initialized with AgentNode")
        self.agent = agent
        self.config = config

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        # If the agent has placeholders, it currently doesn't get dynamically replaced with the
        # given inputs
        generated_message = self.agent.invoke(inputs, self.config)
        if isinstance(generated_message, str):
            output_name = self.node.outputs[0].title if self.node.outputs else "generated_text"
            return {output_name: generated_message}, NodeExecutionDetails()

        return dict(generated_message), NodeExecutionDetails()


class LlmNodeExecutor(NodeExecutor):
    node: AgentSpecLlmNode

    def __init__(self, node: AgentSpecLlmNode, llm: BaseChatModel) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecLlmNode):
            raise TypeError("LlmNodeExecutor can only be initialized with LlmNode")
        if not isinstance(self.llm, BaseChatModel):
            raise TypeError("Llm can only be initialized with a BaseChatModel")
        self.llm = llm

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        prompt_template = self.node.prompt_template
        rendered_prompt = render_template(prompt_template, inputs)
        generated_message = self.llm.invoke([{"role": "user", "content": rendered_prompt}])
        generated_text = generated_message.content
        output_name = self.node.outputs[0].title if self.node.outputs else "generated_text"
        return {output_name: generated_text}, NodeExecutionDetails()


class ApiNodeExecutor(NodeExecutor):
    node: AgentSpecApiNode

    def __init__(self, node: AgentSpecApiNode) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecApiNode):
            raise TypeError("ApiNode can only be initialized with ApiNode")

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        api_node = self.node
        if not isinstance(api_node, AgentSpecApiNode):
            raise TypeError("ApiNode can only execute ApiNode")
        remote_tool_data = {k: render_template(v, inputs) for k, v in api_node.data.items()}
        remote_tool_headers = {k: render_template(v, inputs) for k, v in api_node.headers.items()}
        remote_tool_query_params = {
            k: render_template(v, inputs) for k, v in api_node.query_params.items()
        }
        remote_tool_url = render_template(api_node.url, inputs)
        response = httpx.request(
            method=api_node.http_method,
            url=remote_tool_url,
            params=remote_tool_query_params,
            data=remote_tool_data,
            headers=remote_tool_headers,
        )
        output = {
            "data": response.json(),
            "status_code": response.status_code,
        }
        output_name = self.node.outputs[0].title if self.node.outputs else "api_output"
        return {output_name: output}, NodeExecutionDetails()


class FlowNodeExecutor(NodeExecutor):
    node: AgentSpecFlowNode

    def __init__(
        self,
        node: AgentSpecFlowNode,
        subflow: CompiledStateGraph[Any, Any],
        config: RunnableConfig,
    ) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecFlowNode):
            raise TypeError("FlowNodeExecutor can only initialize FlowNode")
        self.subflow = subflow
        self.config = config

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        output_name = self.node.outputs[0].title if self.node.outputs else "flow_output"
        flow_output = self.subflow.invoke(inputs, self.config)
        return {output_name: flow_output}, NodeExecutionDetails()


class MapNodeExecutor(NodeExecutor):
    node: AgentSpecMapNode

    def __init__(
        self,
        node: AgentSpecMapNode,
        subflow: CompiledStateGraph[Any, Any],
        config: RunnableConfig,
    ) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecMapNode):
            raise TypeError("MapNodeExecutor can only be initialized with MapNode")
        self.subflow = subflow
        self.config = config

    def _execute(self, inputs: Dict[str, Any]) -> ExecuteOutput:
        # TODO: handle different reducers, handle multiple inputs and outputs
        map_node = self.node
        if not isinstance(map_node, AgentSpecMapNode):
            raise TypeError("MapNodeExecutor can only execute MapNodes")

        output_name = self.node.outputs[0].title if self.node.outputs else "collected_outputs"

        if not self.node.inputs:
            raise ValueError("MapNode has no inputs")

        input_name = self.node.inputs[0].title
        single_input_name = input_name[len("iterated_") :]
        single_output_name = output_name[len("collected_") :]
        outputs = []

        for inp in inputs[input_name]:
            out = self.subflow.invoke({"inputs": {single_input_name: inp}})
            outputs.append(out)

        collected_add_output = None
        for output in outputs:
            if collected_add_output is None:
                collected_add_output = output["outputs"][single_output_name]
            else:
                collected_add_output += output["outputs"][single_output_name]

        return {output_name: collected_add_output}, NodeExecutionDetails()
