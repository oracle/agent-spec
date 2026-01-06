# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx

from pyagentspec.adapters._utils import render_nested_object_template, render_template
from pyagentspec.adapters.langgraph._types import (
    BaseChatModel,
    BaseMessage,
    BaseTool,
    Checkpointer,
    CompiledStateGraph,
    ExecuteOutput,
    FlowStateSchema,
    LangGraphTool,
    Messages,
    NodeExecutionDetails,
    NodeOutputsType,
    RunnableConfig,
    interrupt,
    langgraph_graph,
)
from pyagentspec.adapters.langgraph.mcp_utils import _run_async_in_sync_simple
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.flows.edges import DataFlowEdge
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import AgentNode as AgentSpecAgentNode
from pyagentspec.flows.nodes import ApiNode as AgentSpecApiNode
from pyagentspec.flows.nodes import BranchingNode as AgentSpecBranchingNode
from pyagentspec.flows.nodes import EndNode as AgentSpecEndNode
from pyagentspec.flows.nodes import FlowNode as AgentSpecFlowNode
from pyagentspec.flows.nodes import InputMessageNode as AgentSpecInputMessageNode
from pyagentspec.flows.nodes import LlmNode as AgentSpecLlmNode
from pyagentspec.flows.nodes import MapNode as AgentSpecMapNode
from pyagentspec.flows.nodes import OutputMessageNode as AgentSpecOutputMessageNode
from pyagentspec.flows.nodes import StartNode as AgentSpecStartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import _empty_default as pyagentspec_empty_default

MessageLike = Union[BaseMessage, List[str], Tuple[str, str], str, Dict[str, Any]]


class NodeExecutor(ABC):
    def __init__(self, node: Node) -> None:
        self.node = node
        self.edges: List[DataFlowEdge] = []

    def __call__(self, state: FlowStateSchema) -> Any:
        inputs = self._get_inputs(state)
        outputs, execution_details = self._execute(inputs, state.get("messages", []))
        return self._update_status(outputs, execution_details, state)

    def attach_edge(self, edge: DataFlowEdge) -> None:
        self.edges.append(edge)

    @abstractmethod
    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        """Returns the output of executing node with the given inputs.
        The output will be transformed into a dictionary based on the FlowStateSchema.
        """
        # TODO: for all nodes implementing the _execute method, if the node returns a value,
        # we wrap it in a dictionary with the key being the title of the output descriptor, the value being... the value
        # Otherwise if we have multiple properties in the output descriptors, we should verify that the output is a dictionary and that it contains all the keys required for it to be considered a valid output

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
                elif property_.type == "integer" and isinstance(value, str):
                    # Try converting numeric strings to integers; if it fails, leave as-is
                    try:
                        value = int(value.strip())
                    except ValueError as e:
                        if not str(e).startswith("could not convert string to int:"):
                            raise e
                elif property_.type == "number" and isinstance(value, (int, bool)):
                    value = float(value)
                elif property_.type == "number" and isinstance(value, str):
                    # Try converting numeric strings to floats; if it fails, leave as-is
                    try:
                        value = float(value.strip())
                    except ValueError as e:
                        if not str(e).startswith("could not convert string to float:"):
                            raise e
                results_dict[key] = value
            elif property_.default is not pyagentspec_empty_default:
                results_dict[key] = property_.default
            else:
                raise ValueError(
                    f"Expected node `{self.node.name}` to have a value "
                    f"for property `{property_.title}`, but none was found."
                )
        return results_dict

    def _get_inputs(self, state: FlowStateSchema) -> Dict[str, Any]:
        """Retrieve the inputs for this node, adding default values when missing, and casting to right type."""
        inputs = self.node.inputs or []
        # We retrieve the inputs related to this node
        io_inputs = {
            input_name: value
            for node_id, node_inputs in state["inputs"].items()
            if node_id == self.node.id
            for input_name, value in node_inputs.items()
            # We select only the entries that are generated for specific steps
            # i.e., the key is a tuple (node_name, node_input)
        }
        return self._cast_values_and_add_defaults(io_inputs, inputs)

    def _update_status(
        self,
        outputs: NodeOutputsType,
        execution_details: NodeExecutionDetails,
        previous_state: FlowStateSchema,
    ) -> FlowStateSchema:
        """Updates the status of the flow with the given information"""
        outputs = self._cast_values_and_add_defaults(outputs, self.node.outputs or [])
        next_node_inputs = previous_state.get("inputs", {})

        for edge in self.edges:
            if edge.destination_node.id not in next_node_inputs:
                next_node_inputs[edge.destination_node.id] = {}
            next_node_inputs[edge.destination_node.id][edge.destination_input] = outputs[
                edge.source_output
            ]

        if "branch" not in execution_details:
            execution_details["branch"] = Node.DEFAULT_NEXT_BRANCH

        if "generated_messages" not in execution_details:
            execution_details["generated_messages"] = []

        if "should_finish" not in execution_details:
            execution_details["should_finish"] = False

        return {
            "inputs": next_node_inputs,
            "outputs": outputs,
            "messages": langgraph_graph.add_messages(
                previous_state.get("messages", []),
                execution_details["generated_messages"],
            ),
            "node_execution_details": execution_details,
        }


class StartNodeExecutor(NodeExecutor):
    node: AgentSpecStartNode

    def _get_inputs(self, state: FlowStateSchema) -> Dict[str, Any]:
        """
        Retrieve the inputs for this node, adding default values when missing, and casting to right type.

        For the StartNode this works in a slightly different way, because inputs do not have the node id
        in their name, as when flows are first invoked they just have the input name as key.
        """
        inputs = self.node.inputs or []

        state_inputs = state.get("inputs", {})
        # The start node takes the key entries that have no node name (i.e., they are not a tuple)
        io_inputs = {
            node_input: value
            for node_input, value in state_inputs.items()
            if isinstance(node_input, str)
        }

        # We remove the inputs we have extracted to avoid polluting the state inputs
        for node_input in io_inputs:
            state_inputs.pop(node_input)

        return self._cast_values_and_add_defaults(io_inputs, inputs)

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        return inputs, NodeExecutionDetails()


class EndNodeExecutor(NodeExecutor):
    node: AgentSpecEndNode

    def __init__(self, node: AgentSpecEndNode) -> None:
        super().__init__(node)
        self.flow_outputs: List[AgentSpecProperty] = []

    def set_flow_outputs(self, flow_outputs: List[AgentSpecProperty]) -> None:
        self.flow_outputs = flow_outputs

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        return inputs, NodeExecutionDetails(branch=self.node.branch_name, should_finish=True)

    def _update_status(
        self,
        outputs: NodeOutputsType,
        execution_details: NodeExecutionDetails,
        previous_state: FlowStateSchema,
    ) -> FlowStateSchema:
        """Updates the status of the flow with the given information"""
        new_state = super()._update_status(
            outputs=outputs,
            execution_details=execution_details,
            previous_state=previous_state,
        )
        outputs = new_state["outputs"]
        new_state["outputs"] = {
            property_.title: outputs.get(property_.title, property_.default)
            for property_ in (self.flow_outputs or [])
        }
        for property_name, property_value in outputs.items():
            if property_value is pyagentspec_empty_default:
                raise ValueError(
                    f"EndNode `{self.node.name}` exited without any value generated for property `{property_name}`"
                )
        return new_state


class BranchingNodeExecutor(NodeExecutor):
    node: AgentSpecBranchingNode

    def __init__(self, node: AgentSpecBranchingNode) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecBranchingNode):
            raise TypeError("BranchingNodeExecutor can only be initialized with BranchingNode")
        if not self.node.inputs:
            raise ValueError("BranchingNode requires at least one input")

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        if not isinstance(self.node, AgentSpecBranchingNode):
            raise TypeError("BranchingNodeExecutor can only be executed with BranchingNode")
        branching_node = self.node
        node_inputs = branching_node.inputs or []
        input_branch_prop_title = node_inputs[0].title
        input_branch_name = inputs.get(
            input_branch_prop_title, AgentSpecBranchingNode.DEFAULT_BRANCH
        )
        selected_branch = branching_node.mapping.get(
            input_branch_name, AgentSpecBranchingNode.DEFAULT_BRANCH
        )
        return {}, NodeExecutionDetails(branch=selected_branch)


class ToolNodeExecutor(NodeExecutor):
    node: AgentSpecToolNode

    def __init__(self, node: AgentSpecToolNode, tool: LangGraphTool) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecToolNode):
            raise TypeError("ToolNodeExecutor can only be initialized with ToolNode")
        self.tool_callable = tool

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        # LangGraphTool = Union[BaseTool, Callable[..., Any]]
        tool = self.tool_callable

        if isinstance(tool, BaseTool):
            if getattr(tool, "coroutine", None) is None:
                tool_output = tool.invoke(inputs)
            else:
                # this is an async tool (most likely MCP tool), we need to await it but this _execute method needs to be sync
                async def arun():  # type: ignore
                    return await tool.ainvoke(inputs)

                tool_output = _run_async_in_sync_simple(arun, method_name="arun")
        else:
            # Plain callable: we call it like a function
            tool_output = tool(**inputs)

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
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
    ) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecAgentNode):
            raise TypeError("AgentNodeExecutor can only be initialized with AgentNode")
        self.tool_registry = tool_registry
        self.checkpointer = checkpointer
        self.converted_components = converted_components
        self.config = config
        self._agents_cache: Dict[str, CompiledStateGraph[Any, Any]] = {}

    def _create_react_agent_with_given_input_values(
        self, inputs: Dict[str, Any]
    ) -> CompiledStateGraph[Any, Any]:
        from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

        if not isinstance(self.node.agent, AgentSpecAgent):
            raise TypeError("AgentNodeExecutor can only be used with AgentSpecAgent agents")

        agentspec_component = self.node.agent
        system_prompt = render_template(agentspec_component.system_prompt, inputs)
        if system_prompt not in self._agents_cache:
            self._agents_cache[
                system_prompt
            ] = AgentSpecToLangGraphConverter()._create_react_agent_with_given_info(
                name=agentspec_component.name,
                system_prompt=system_prompt,
                llm_config=agentspec_component.llm_config,
                tools=agentspec_component.tools,
                toolboxes=agentspec_component.toolboxes,
                inputs=agentspec_component.inputs or [],
                outputs=agentspec_component.outputs or [],
                tool_registry=self.tool_registry,
                converted_components=self.converted_components,
                checkpointer=self.checkpointer,
                config=self.config,
            )
        return self._agents_cache[system_prompt]

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        agent = self._create_react_agent_with_given_input_values(inputs)
        inputs |= {
            "remaining_steps": 20,  # Get the right number of steps left
            "messages": messages,
            "structured_response": {},
        }
        result = agent.invoke(inputs, self.config)
        if not self.node.outputs:
            generated_message = result["messages"][-1]
            generated_messages: List[MessageLike] = [
                {"role": "assistant", "content": generated_message.content}
            ]
            return {}, NodeExecutionDetails(generated_messages=generated_messages)

        return dict(result.get("structured_response", {})), NodeExecutionDetails()


class InputMessageNodeExecutor(NodeExecutor):
    node: AgentSpecInputMessageNode

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        response = interrupt("")
        output_name = (
            self.node.outputs[0].title
            if self.node.outputs
            else AgentSpecInputMessageNode.DEFAULT_OUTPUT
        )
        generated_messages: List[MessageLike] = [{"role": "user", "content": response}]
        return {output_name: response}, NodeExecutionDetails(generated_messages=generated_messages)


class OutputMessageNodeExecutor(NodeExecutor):
    node: AgentSpecOutputMessageNode

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        message = render_template(self.node.message, inputs)
        generated_messages: List[MessageLike] = [{"role": "assistant", "content": message}]
        return {}, NodeExecutionDetails(generated_messages=generated_messages)


class LlmNodeExecutor(NodeExecutor):
    node: AgentSpecLlmNode

    def __init__(self, node: AgentSpecLlmNode, llm: BaseChatModel) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecLlmNode):
            raise TypeError("LlmNodeExecutor can only be initialized with LlmNode")
        outputs = self.node.outputs
        if outputs is not None and len(outputs) == 1 and outputs[0].type == "string":
            self.requires_structured_generation = False
        else:
            self.requires_structured_generation = True
        if not isinstance(llm, BaseChatModel):
            raise TypeError("Llm can only be initialized with a BaseChatModel")

        self.llm: BaseChatModel = llm

        node_outputs = self.node.outputs or []
        self.requires_structured_generation = not (
            len(node_outputs) == 1 and node_outputs[0].type == "string"
        )

        self.structured_llm: Any = None

        if self.requires_structured_generation:
            json_schema = {
                # Title is required by langgraph
                "title": "structured_output",
                "type": "object",
                "properties": {output.title: output.json_schema for output in node_outputs},
            }
            self.structured_llm = self.llm.with_structured_output(json_schema)

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        node_outputs = self.node.outputs or []
        prompt_template = self.node.prompt_template
        rendered_prompt = render_template(prompt_template, inputs)
        invoke_inputs = [{"role": "user", "content": rendered_prompt}]

        if self.requires_structured_generation:
            if self.structured_llm is None:
                raise RuntimeError("Structured LLM was not initialized")

            generated_raw = self.structured_llm.invoke(invoke_inputs)

            if not isinstance(generated_raw, dict):
                raise TypeError(
                    f"Expected structured LLM to return a dict, got {type(generated_raw)!r}"
                )

            generated_output: Dict[str, Any] = generated_raw
            # LangGraph sometimes flattens a 1-property nested object; rebuild if needed
            if len(node_outputs) == 1 and node_outputs[0].title != list(generated_output.keys())[0]:
                generated_output = {node_outputs[0].title: generated_output}
        else:
            generated_message = self.llm.invoke(invoke_inputs)
            output_name = node_outputs[0].title if node_outputs else "generated_text"
            if not hasattr(generated_message, "content"):
                raise ValueError(
                    "generated_message should not be a dict when not doing structured generation"
                )
            generated_output = {output_name: generated_message.content}
        return generated_output, NodeExecutionDetails()


class ApiNodeExecutor(NodeExecutor):
    node: AgentSpecApiNode

    def __init__(self, node: AgentSpecApiNode) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecApiNode):
            raise TypeError("ApiNodeExecutor can only be initialized with ApiNode")

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        api_node = self.node
        if not isinstance(api_node, AgentSpecApiNode):
            raise TypeError("ApiNodeExecutor can only execute ApiNode")
        api_node_data = render_nested_object_template(api_node.data, inputs)
        api_node_headers = {
            render_template(k, inputs): render_nested_object_template(v, inputs)
            for k, v in api_node.headers.items()
        }
        api_node_query_params = {
            render_template(k, inputs): render_nested_object_template(v, inputs)
            for k, v in api_node.query_params.items()
        }
        api_node_url = render_template(api_node.url, inputs)

        data = None
        json_data = None
        content = None
        if isinstance(api_node_data, dict):
            data = api_node_data
        elif isinstance(api_node_data, (str, bytes)):
            content = api_node_data
        else:
            json_data = api_node_data

        response = httpx.request(
            method=api_node.http_method,
            url=api_node_url,
            params=api_node_query_params,
            json=json_data,
            content=content,
            data=data,
            headers=api_node_headers,
        )
        return response.json(), NodeExecutionDetails()


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

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        flow_output = self.subflow.invoke({"messages": messages, "inputs": inputs}, self.config)
        return flow_output["outputs"], NodeExecutionDetails(
            branch=flow_output["node_execution_details"]["branch"]
        )


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
        if not self.node.inputs:
            raise ValueError("MapNode has no inputs")
        self.subflow = subflow
        self.config = config
        self.inputs_to_iterate: List[str] = []

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        # TODO: handle different reducers

        outputs: Dict[str, List[Any]] = {output.title: [] for output in self.node.outputs or []}

        if not self.inputs_to_iterate:
            raise ValueError("MapNode has no inputs to iterate")

        num_inputs_to_iterate = None
        for input_name in self.inputs_to_iterate:
            if num_inputs_to_iterate is None:
                num_inputs_to_iterate = len(inputs[input_name])
            elif len(inputs[input_name]) != num_inputs_to_iterate:
                raise ValueError(
                    f"Found inputs to iterate with different sizes ({inputs[input_name]} and {num_inputs_to_iterate})"
                )
        if num_inputs_to_iterate is None:
            raise ValueError("MapNode inputs_to_iterate did not match any provided inputs")

        for i in range(num_inputs_to_iterate):
            # Need to initialize a new dictionary of inputs at every iteration as it will be modified by the subflow
            subflow_inputs = {
                input_.title.replace("iterated_", ""): (
                    inputs[input_.title][i]
                    if input_.title in self.inputs_to_iterate
                    else inputs[input_.title]
                )
                for input_ in (self.node.inputs or [])
            }
            subflow_outputs = self.subflow.invoke({"inputs": subflow_inputs, "messages": messages})
            for output_name, output_value in subflow_outputs["outputs"].items():
                collected_output_name = "collected_" + output_name
                # Not all outputs might be exposed, we filter those that are required by node's outputs
                if collected_output_name in outputs:
                    outputs[collected_output_name].append(output_value)

        return outputs, NodeExecutionDetails()

    def set_inputs_to_iterate(self, inputs_to_iterate: list[str]) -> None:
        self.inputs_to_iterate = inputs_to_iterate
