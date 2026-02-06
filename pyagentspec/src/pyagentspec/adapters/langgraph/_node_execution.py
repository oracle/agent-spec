# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
import logging
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import anyio
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
    langchain_core_messages_content,
    langgraph_graph,
)
from pyagentspec.adapters.langgraph.mcp_utils import _run_async_in_sync_simple
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.flows.edges import DataFlowEdge
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import AgentNode as AgentSpecAgentNode
from pyagentspec.flows.nodes import ApiNode as AgentSpecApiNode
from pyagentspec.flows.nodes import BranchingNode as AgentSpecBranchingNode
from pyagentspec.flows.nodes import CatchExceptionNode as AgentSpecCatchExceptionNode
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
from pyagentspec.tracing.events import NodeExecutionEnd as AgentSpecNodeExecutionEnd
from pyagentspec.tracing.events import NodeExecutionStart as AgentSpecNodeExecutionStart
from pyagentspec.tracing.events.exception import ExceptionRaised
from pyagentspec.tracing.spans import NodeExecutionSpan as AgentSpecNodeExecutionSpan
from pyagentspec.tracing.spans.span import get_current_span

MessageLike = Union[BaseMessage, List[str], Tuple[str, str], str, Dict[str, Any]]

logger = logging.getLogger(__name__)


class NodeExecutor(ABC):
    def __init__(self, node: Node) -> None:
        self.node = node
        self.edges: List[DataFlowEdge] = []

    def __call__(self, state: FlowStateSchema) -> Any:
        inputs = self._get_inputs(state)
        span_name = f"{self.node.__class__.__name__}Execution[{self.node.name}]"
        with AgentSpecNodeExecutionSpan(name=span_name, node=self.node) as span:
            span.add_event(AgentSpecNodeExecutionStart(node=self.node, inputs=inputs))
            outputs, execution_details = self._execute(inputs, state.get("messages", []))
            updated_status = self._update_status(outputs, execution_details, state)
            span.add_event(
                AgentSpecNodeExecutionEnd(
                    node=self.node,
                    outputs=updated_status["outputs"],
                    branch_selected=updated_status["node_execution_details"]["branch"],
                )
            )
        return updated_status

    async def __acall__(self, state: FlowStateSchema) -> Any:
        inputs = self._get_inputs(state)
        span_name = f"{self.node.__class__.__name__}Execution[{self.node.name}]"
        async with AgentSpecNodeExecutionSpan(name=span_name, node=self.node) as span:
            await span.add_event_async(AgentSpecNodeExecutionStart(node=self.node, inputs=inputs))
            # Prefer native async execution when available.
            outputs, execution_details = await self._aexecute(inputs, state.get("messages", []))
            updated_status = self._update_status(outputs, execution_details, state)
            await span.add_event_async(
                AgentSpecNodeExecutionEnd(
                    node=self.node,
                    outputs=updated_status["outputs"],
                    branch_selected=updated_status["node_execution_details"]["branch"],
                )
            )
            return updated_status

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

    async def _aexecute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        """Default async implementation delegates to sync _execute in a worker thread.

        Nodes that can perform true async work should override this to avoid
        thread offloading.
        """
        return await anyio.to_thread.run_sync(lambda: self._execute(inputs, messages))

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

    def _format_tool_result(self, tool_output: Any) -> ExecuteOutput:
        """
        Best-effort formatting of raw tool outputs to the ToolNode's declared output properties.

        Cases:
        - the node declares 0 output property: we return an empty dict
        - the node declares 1 output property: we return a wrapper dict with a single key being the property's title
        - the node declares multiple output properties:
            - the tool returns a dict: we filter this dict by the property titles and return the filtered dict
            - the tool returns a tuple: we assume alignment between the order of the tuple items
            and the order of the properties in self.node.outputs and return an ordered dict keyed by property titles
        """
        node_output_properties = self.node.outputs or []
        if not node_output_properties:
            # the node does not emit any output
            mapped = {}
        if isinstance(tool_output, list) and self._is_mcp_content_blocks_list(tool_output):
            extracted_values = self._extract_values_from_content_blocks(tool_output)
            mapped = {
                property_.title: extracted_values[i]
                for i, property_ in enumerate(node_output_properties)
            }
        elif len(node_output_properties) == 1:
            # the tool returns a dict with a single key being the node's output property's title
            # so we avoid double-wrapping
            if isinstance(tool_output, dict) and set(tool_output.keys()) == {
                node_output_properties[0].title
            }:
                mapped = tool_output
            else:
                mapped = {node_output_properties[0].title: tool_output}
        elif isinstance(tool_output, dict):
            # the node emits multiple outputs, need to filter the tool_output
            mapped = {
                property_.title: tool_output[property_.title]
                for property_ in node_output_properties
                if property_.title in tool_output
            }
        elif isinstance(tool_output, tuple):
            # if it's multiple outputs, map positionally
            mapped = {
                property_.title: tool_output[i]
                for i, property_ in enumerate(node_output_properties)
            }
        else:
            raise ValueError(
                f"Unsupported multi-output mapping for tool_output: {tool_output}"
                f"(declared_outputs={len(node_output_properties)})."
            )
        return mapped, NodeExecutionDetails()

    def _is_mcp_content_blocks_list(self, items: List[Any]) -> bool:
        # Empty lists are ambiguous; treat them as non-MCP to avoid false positives
        if not items:
            return False
        for el in items:
            if not isinstance(el, dict):
                return False
            t = el.get("type")
            if t not in {"text", "image", "file"}:
                return False
            if t == "text":
                if "text" not in el or not isinstance(el["text"], str):
                    return False
            elif t in {"image", "file"}:
                # Accept any supported payload reference
                if not any(k in el for k in ["base64", "url", "file_id"]):
                    return False
        return True

    def _extract_value_from_block(
        self,
        block: Union[
            langchain_core_messages_content.FileContentBlock,
            langchain_core_messages_content.TextContentBlock,
            langchain_core_messages_content.ImageContentBlock,
        ],
    ) -> Any:
        t = block["type"]
        if t == "text":
            text_block = cast(langchain_core_messages_content.TextContentBlock, block)
            return text_block["text"]
        if t == "image":
            image_block = cast(langchain_core_messages_content.ImageContentBlock, block)
            if "base64" in image_block:
                return image_block["base64"]
            if "url" in image_block:
                return image_block["url"]
            if "file_id" in image_block:
                return image_block["file_id"]
            raise ValueError(f"No payload found in image block: {image_block}")
        if t == "file":
            file_block = cast(langchain_core_messages_content.FileContentBlock, block)
            if "base64" in file_block:
                return file_block["base64"]
            if "url" in file_block:
                return file_block["url"]
            if "file_id" in file_block:
                return file_block["file_id"]
            raise ValueError(f"No payload found in file block: {file_block}")
        else:
            raise NotImplementedError(f"Unsupported message content block type: {t}")

    def _extract_values_from_content_blocks(
        self,
        blocks: List[
            Union[
                langchain_core_messages_content.FileContentBlock,
                langchain_core_messages_content.TextContentBlock,
                langchain_core_messages_content.ImageContentBlock,
            ]
        ],
    ) -> List[Any]:
        return [self._extract_value_from_block(block) for block in blocks]

    def _invoke_tool_sync(self, inputs: Dict[str, Any]) -> Any:
        # LangGraphTool = Union[BaseTool, Callable[..., Any]]
        tool = self.tool_callable

        if isinstance(tool, BaseTool):
            if getattr(tool, "coroutine", None) is None:
                return tool.invoke(inputs)
            else:
                # Async tool (e.g., MCP tool) executed from sync context
                async def arun():  # type: ignore
                    return await tool.ainvoke(inputs)

                return _run_async_in_sync_simple(arun, method_name="arun")
        else:
            # Plain callable: call directly
            return tool(**inputs)

    async def _invoke_tool_async(self, inputs: Dict[str, Any]) -> Any:
        tool = self.tool_callable
        if isinstance(tool, BaseTool):
            if getattr(tool, "coroutine", None) is None:
                # Sync tool executed in async context via thread offloading.
                # On Python < 3.11, langgraph's interrupt/get_config relies on contextvars
                # that are not propagated to worker threads by default. This can lead to
                # a KeyError for '__pregel_scratchpad' inside langgraph.types.interrupt.
                # Our tests expect a RuntimeError("Called get_config outside of a runnable context")
                # in this scenario. Map the KeyError accordingly on Python 3.10.
                if sys.version_info < (3, 11):
                    try:
                        return await anyio.to_thread.run_sync(lambda: tool.invoke(inputs))
                    except KeyError as exc:
                        # Match both repr and args variants of the missing key
                        missing_key = getattr(exc, "args", [None])[0]
                        if missing_key == "__pregel_scratchpad":
                            raise RuntimeError("Called get_config outside of a runnable context")
                        raise
                return await anyio.to_thread.run_sync(lambda: tool.invoke(inputs))
            else:
                return await tool.ainvoke(inputs)
        else:
            return await anyio.to_thread.run_sync(lambda: tool(**inputs))

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        tool_output = self._invoke_tool_sync(inputs)
        return self._format_tool_result(tool_output)

    async def _aexecute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        # Provide native async execution (await async tools, offload sync ones)
        tool_output = await self._invoke_tool_async(inputs)
        return self._format_tool_result(tool_output)


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
                agent=agentspec_component,
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

    def _prepare_agent_and_inputs(
        self, inputs: Dict[str, Any], messages: Messages
    ) -> Tuple[CompiledStateGraph[Any, Any], Dict[str, Any]]:
        agent = self._create_react_agent_with_given_input_values(inputs)
        # LangGraph's agent expects at least one user message to drive execution.
        # When an AgentNode is used with a templated system prompt and no messages are provided
        # by the flow, the agent can crash. To avoid this, we artificially insert an empty
        # user message when the message list is empty.
        if not messages:
            messages = cast(Messages, [{"role": "user", "content": ""}])
        inputs |= {
            "remaining_steps": 20,  # Get the right number of steps left
            "messages": messages,
            "structured_response": {},
        }
        return agent, inputs

    def _format_agent_result(self, result: Dict[str, Any]) -> ExecuteOutput:
        if not self.node.outputs:
            generated_message = result["messages"][-1]
            generated_messages: List[MessageLike] = [
                {"role": "assistant", "content": generated_message.content}
            ]
            return {}, NodeExecutionDetails(generated_messages=generated_messages)

        outputs = extract_outputs_from_invoke_result(result, self.node.outputs or [])
        return outputs, NodeExecutionDetails()

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        agent, prepared_inputs = self._prepare_agent_and_inputs(inputs, messages)
        result = agent.invoke(prepared_inputs, self.config)
        return self._format_agent_result(result)

    async def _aexecute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        agent, prepared_inputs = self._prepare_agent_and_inputs(inputs, messages)
        result = await agent.ainvoke(prepared_inputs, self.config)
        return self._format_agent_result(result)


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

    def _build_invoke_inputs(self, inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        prompt_template = self.node.prompt_template
        rendered_prompt = render_template(prompt_template, inputs)
        return [{"role": "user", "content": rendered_prompt}]

    def _format_structured_output(
        self, node_outputs: List[AgentSpecProperty], generated_raw: Any
    ) -> Dict[str, Any]:
        if not isinstance(generated_raw, dict):
            raise TypeError(
                f"Expected structured LLM to return a dict, got {type(generated_raw)!r}"
            )
        generated_output: Dict[str, Any] = generated_raw
        # LangGraph sometimes flattens a 1-property nested object; rebuild if needed
        if len(node_outputs) == 1 and node_outputs[0].title != list(generated_output.keys())[0]:
            generated_output = {node_outputs[0].title: generated_output}
        return generated_output

    def _format_unstructured_output(
        self, node_outputs: List[AgentSpecProperty], generated_message: Any
    ) -> Dict[str, Any]:
        output_name = node_outputs[0].title if node_outputs else "generated_text"
        if not hasattr(generated_message, "content"):
            raise ValueError(
                "generated_message should not be a dict when not doing structured generation"
            )
        return {output_name: generated_message.content}

    def _invoke_llm_sync(self, invoke_inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        node_outputs = self.node.outputs or []
        if self.requires_structured_generation:
            if self.structured_llm is None:
                raise RuntimeError("Structured LLM was not initialized")
            generated_raw = self.structured_llm.invoke(invoke_inputs)
            return self._format_structured_output(node_outputs, generated_raw)
        else:
            generated_message = self.llm.invoke(invoke_inputs)
            return self._format_unstructured_output(node_outputs, generated_message)

    async def _invoke_llm_async(self, invoke_inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        node_outputs = self.node.outputs or []
        if self.requires_structured_generation:
            if self.structured_llm is None:
                raise RuntimeError("Structured LLM was not initialized")
            generated_raw = await self.structured_llm.ainvoke(invoke_inputs)
            return self._format_structured_output(node_outputs, generated_raw)
        else:
            generated_message = await self.llm.ainvoke(invoke_inputs)
            return self._format_unstructured_output(node_outputs, generated_message)

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        invoke_inputs = self._build_invoke_inputs(inputs)
        generated_output = self._invoke_llm_sync(invoke_inputs)
        return generated_output, NodeExecutionDetails()

    async def _aexecute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        invoke_inputs = self._build_invoke_inputs(inputs)
        generated_output = await self._invoke_llm_async(invoke_inputs)
        return generated_output, NodeExecutionDetails()


class ApiNodeExecutor(NodeExecutor):
    node: AgentSpecApiNode

    def __init__(self, node: AgentSpecApiNode) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecApiNode):
            raise TypeError("ApiNodeExecutor can only be initialized with ApiNode")

    def _build_request_kwargs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
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
        content_type_headers = api_node_headers.get("Content-Type") or api_node_headers.get(
            "content-type"
        )
        expect_urlencoded_form_data = (
            ("application/x-www-form-urlencoded" in content_type_headers)
            if content_type_headers is not None
            else False
        )

        if isinstance(api_node_data, dict) and expect_urlencoded_form_data:
            data = api_node_data
        elif isinstance(api_node_data, (str, bytes)):
            content = api_node_data
        else:
            json_data = api_node_data

        return {
            "method": api_node.http_method,
            "url": api_node_url,
            "params": api_node_query_params,
            "json": json_data,
            "content": content,
            "data": data,
            "headers": api_node_headers,
        }

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        kwargs = self._build_request_kwargs(inputs)
        response = httpx.request(**kwargs)
        return response.json(), NodeExecutionDetails()

    async def _aexecute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        kwargs = self._build_request_kwargs(inputs)
        async with httpx.AsyncClient() as client:
            response = await client.request(**kwargs)
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

    async def _aexecute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        flow_output = await self.subflow.ainvoke(
            {"messages": messages, "inputs": inputs}, self.config
        )
        return flow_output["outputs"], NodeExecutionDetails(
            branch=flow_output["node_execution_details"]["branch"]
        )


class CatchExceptionNodeExecutor(NodeExecutor):
    node: AgentSpecCatchExceptionNode

    def __init__(
        self,
        node: AgentSpecCatchExceptionNode,
        subflow: CompiledStateGraph[Any, Any],
        config: RunnableConfig,
    ) -> None:
        super().__init__(node)
        if not isinstance(self.node, AgentSpecCatchExceptionNode):
            raise TypeError("CatchExceptionNodeExecutor can only initialize CatchExceptionNode")
        self.subflow = subflow
        self.config = config

    def _execute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        try:
            flow_output = self.subflow.invoke({"messages": messages, "inputs": inputs}, self.config)
            outputs = dict(flow_output.get("outputs", {}))
            outputs["caught_exception_info"] = None
            # ^ as per the spec, when the subflow runs without error
            # `caught_exception_info` is `None`
            return outputs, NodeExecutionDetails(
                branch=flow_output["node_execution_details"].get("branch", Node.DEFAULT_NEXT_BRANCH)
            )
        except Exception as e:
            # On exception: default subflow outputs + caught_exception_info
            import traceback

            current_span = get_current_span()
            if current_span:
                current_span.add_event(
                    ExceptionRaised(
                        exception_type=type(e).__name__,
                        exception_message=str(e),
                        exception_stacktrace=traceback.format_exc(),
                    )
                )
            else:
                logger.debug(
                    "Error when emitting ExceptionRaised event: parent NodeExecutionSpan "
                    "was not found for CatchExceptionNode.",
                )
            default_outputs: Dict[str, Any] = {}
            for property_ in self.node.subflow.outputs or []:
                # Use default value for subflow outputs when exception occurs
                default_outputs[property_.title] = property_.default
            default_outputs["caught_exception_info"] = str(e)
            return default_outputs, NodeExecutionDetails(
                branch=AgentSpecCatchExceptionNode.CAUGHT_EXCEPTION_BRANCH
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
        subflow_inputs_list, outputs = self._prepare_iterations(inputs)
        for subflow_inputs in subflow_inputs_list:
            subflow_result = self.subflow.invoke({"inputs": subflow_inputs, "messages": messages})
            self._accumulate_outputs(outputs, subflow_result["outputs"])
        return outputs, NodeExecutionDetails()

    def set_inputs_to_iterate(self, inputs_to_iterate: list[str]) -> None:
        self.inputs_to_iterate = inputs_to_iterate

    async def _aexecute(self, inputs: Dict[str, Any], messages: Messages) -> ExecuteOutput:
        subflow_inputs_list, outputs = self._prepare_iterations(inputs)
        for subflow_inputs in subflow_inputs_list:
            subflow_result = await self.subflow.ainvoke(
                {"inputs": subflow_inputs, "messages": messages}
            )
            self._accumulate_outputs(outputs, subflow_result["outputs"])
        return outputs, NodeExecutionDetails()

    def _prepare_iterations(
        self, inputs: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[Any]]]:
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

        subflow_inputs_list: List[Dict[str, Any]] = []
        for i in range(num_inputs_to_iterate):
            sub_inputs = {
                input_.title.replace("iterated_", ""): (
                    inputs[input_.title][i]
                    if input_.title in self.inputs_to_iterate
                    else inputs[input_.title]
                )
                for input_ in (self.node.inputs or [])
            }
            subflow_inputs_list.append(sub_inputs)
        return subflow_inputs_list, outputs

    def _accumulate_outputs(
        self, outputs: Dict[str, List[Any]], subflow_outputs: Dict[str, Any]
    ) -> None:
        for output_name, output_value in subflow_outputs.items():
            collected_output_name = "collected_" + output_name
            # Not all outputs might be exposed, we filter those that are required by node's outputs
            if collected_output_name in outputs:
                outputs[collected_output_name].append(output_value)


def extract_outputs_from_invoke_result(
    result: Dict[str, Any], expected_outputs: List[AgentSpecProperty]
) -> Dict[str, Any]:
    # Extracts the outputs from the return value of an invoke call made on an agent
    # The outputs are typically exposed as part of the `structured_response`, or as entries in the result directly.
    # We give priority to the latter.
    return {
        # Defaults if available
        **{
            output.title: output.default
            for output in expected_outputs or []
            if output.default is not pyagentspec_empty_default
        },
        # Results in `structured_response`
        **dict(result.get("structured_response", {})),
        # Results appended to main dictionary
        **{
            output.title: result[output.title]
            for output in expected_outputs or []
            if output.title in result
        },
    }
