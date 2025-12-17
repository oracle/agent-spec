# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import ast
import json
import typing
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler as LangchainBaseCallbackHandler
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult
from typing_extensions import NotRequired

from pyagentspec.llms.llmconfig import LlmConfig as AgentSpecLlmConfig
from pyagentspec.tools import Tool as AgentSpecTool
from pyagentspec.tracing.events import (
    LlmGenerationChunkReceived as AgentSpecLlmGenerationChunkReceived,
)
from pyagentspec.tracing.events import LlmGenerationRequest as AgentSpecLlmGenerationRequest
from pyagentspec.tracing.events import LlmGenerationResponse as AgentSpecLlmGenerationResponse
from pyagentspec.tracing.events import ToolExecutionRequest as AgentSpecToolExecutionRequest
from pyagentspec.tracing.events import ToolExecutionResponse as AgentSpecToolExecutionResponse
from pyagentspec.tracing.events.llmgeneration import ToolCall as AgentSpecToolCall
from pyagentspec.tracing.messages.message import Message as AgentSpecMessage
from pyagentspec.tracing.spans import LlmGenerationSpan as AgentSpecLlmGenerationSpan
from pyagentspec.tracing.spans import Span as AgentSpecSpan
from pyagentspec.tracing.spans import ToolExecutionSpan as AgentSpecToolExecutionSpan

MessageInProgress = TypedDict(
    "MessageInProgress",
    {
        "id": str,  # chunk.message.id
        "tool_call_id": NotRequired[str],
        "tool_call_name": NotRequired[str],
    },
)

MessagesInProgressRecord = Dict[Union[str, UUID], MessageInProgress]  # keys are run_id


LANGCHAIN_ROLES_TO_OPENAI_ROLES = {
    "human": "user",
    "ai": "assistant",
    "tool": "tool",
    "system": "system",
    # missing developer message
}


class AgentSpecCallbackHandler(LangchainBaseCallbackHandler):

    def __init__(
        self,
        llm_config: AgentSpecLlmConfig,
        tools: Optional[List[AgentSpecTool]] = None,
    ) -> None:
        # This is only added during tool-call streaming to associate run_id with tool_call_id
        # (tool_call_id is not available mid-stream)
        self.messages_in_process: MessagesInProgressRecord = {}
        # Track spans per run_id
        self.agentspec_spans_registry: Dict[str, AgentSpecSpan] = {}
        # configs for spans
        self.llm_config = llm_config
        self.tools_map: Dict[str, AgentSpecTool] = {t.name: t for t in (tools or [])}

    def _get_or_start_llm_span(self, run_id_str: str) -> AgentSpecLlmGenerationSpan:
        span = self.agentspec_spans_registry.get(run_id_str)
        if not isinstance(span, AgentSpecLlmGenerationSpan):
            span = AgentSpecLlmGenerationSpan(llm_config=self.llm_config)
            self.agentspec_spans_registry[run_id_str] = span
            span.start()
        return span

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        # Start an LLM span and emit request with prompt and tools
        span = self._get_or_start_llm_span(run_id_str)

        # not sure why it is a list of lists, assert that the outer list is size 1
        if len(messages) != 1:
            raise ValueError(
                f"[on_chat_model_start] langchain messages is a nested list of list of BaseMessage, "
                "expected the outer list to have size one but got size {len(messages)}"
            )
        list_of_messages = messages[0]

        prompt = [
            AgentSpecMessage(
                content=_ensure_string(m.content),
                sender="",
                role=LANGCHAIN_ROLES_TO_OPENAI_ROLES[m.type],
            )
            for m in list_of_messages
        ]

        tools = list(self.tools_map.values()) if self.tools_map else []

        span.add_event(
            AgentSpecLlmGenerationRequest(
                request_id=run_id_str,
                llm_config=self.llm_config,
                llm_generation_config=self.llm_config.default_generation_parameters,
                prompt=prompt,
                tools=tools,
            )
        )

    def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: Optional[Union[ChatGenerationChunk, GenerationChunk]] = None,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        # streaming: can stream text chunks and/or tool_call_chunks

        # tool call chunks explanation:
        # shape: chunk.message.tool_call_chunks (can be empty)
        # if not empty: it is a list of length 1
        # for each on_llm_new_token invocation:
        # the first chunk would contain id and name, and empty args
        # the next chunks would not contain id and name, only args (deltas)

        # text chunks explanation:
        # shape: chunk.message.content contains the deltas

        # expected behavior:
        # it should emit LlmGenerationChunkReceived and ToolCallChunkReceived
        # NOTE: on_llm_new_token seems to be called a few times at the beginning with empty everything except for the id=run--id894224...
        if chunk is None:
            raise ValueError("[on_llm_new_token] Expected chunk to not be None")
        run_id_str = str(run_id)
        span = self._get_or_start_llm_span(run_id_str)
        chunk_message = chunk.message  # type: ignore

        # Note that chunk_message.response_metadata.id is None during streaming, but it's populated when not streaming

        if not isinstance(chunk_message.id, str):
            raise ValueError(
                f"[on_llm_new_token] Expected chunk_message.id to be a string but got: {type(chunk_message.id)}"
            )
        message_id = chunk_message.id

        agentspec_tool_calls: List[AgentSpecToolCall] = []
        tool_call_chunks = chunk_message.tool_call_chunks or []  # type: ignore
        if tool_call_chunks:
            if len(tool_call_chunks) != 1:
                raise ValueError(
                    "[on_llm_new_token] Expected exactly one tool call chunk "
                    f"if streaming tool calls, but got: {tool_call_chunks}"
                )
            tool_call_chunk = tool_call_chunks[0]
            tool_name, tool_args, call_id = (
                tool_call_chunk["name"],
                tool_call_chunk["args"],
                tool_call_chunk["id"],
            )
            if call_id is None:
                current_stream = self.messages_in_process[run_id]
                tool_name, call_id = (
                    current_stream["tool_call_name"],
                    current_stream["tool_call_id"],
                )
            else:
                self.messages_in_process[run_id] = {
                    "id": message_id,
                    "tool_call_id": call_id,
                    "tool_call_name": tool_name,
                }
            agentspec_tool_calls = [
                AgentSpecToolCall(call_id=call_id, tool_name=tool_name, arguments=tool_args)
            ]

        span.add_event(
            AgentSpecLlmGenerationChunkReceived(
                request_id=run_id_str,
                completion_id=message_id,
                content=_ensure_string(chunk_message.content or ""),
                llm_config=self.llm_config,
                tool_calls=agentspec_tool_calls,
            )
        )

    @typing.no_type_check
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id = str(run_id)
        span = self._get_or_start_llm_span(run_id)
        message_id, content, tool_calls = _extract_message_content_and_tool_calls(response)
        span.add_event(
            AgentSpecLlmGenerationResponse(
                llm_config=self.llm_config,
                request_id=run_id,
                completion_id=message_id,
                content=content,
                tool_calls=tool_calls,
            )
        )
        span.end()
        self.agentspec_spans_registry.pop(run_id, None)
        self.messages_in_process.pop(run_id, None)

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        if kwargs.get("tool_call_id"):
            # note that this run_id is different from the run_id in LLM events
            # so we cannot use it to correlate with tool_call_id above
            raise NotImplementedError(
                "[on_tool_start] This is implemented starting from langchain 1.1.2, and we should support it"
            )
        # get run_id and tool config
        run_id_str = str(run_id)
        tool_name = serialized.get("name")
        if not tool_name:
            raise ValueError("[on_tool_start] Expected tool name in serialized metadata")
        tool_obj = self.tools_map.get(tool_name)
        if tool_obj is None:
            raise ValueError(f"[on_tool_start] Unknown tool: {tool_name}")

        # starting a tool span for this tool
        tool_span = AgentSpecToolExecutionSpan(tool=tool_obj)
        self.agentspec_spans_registry[run_id_str] = tool_span
        tool_span.start()

        inputs: Dict[str, Any] = (
            ast.literal_eval(input_str) if isinstance(input_str, str) else input_str
        )
        # instead of the real tool_call_id, we use the run_id to correlate between tool request and tool result
        tool_span.add_event(
            AgentSpecToolExecutionRequest(request_id=run_id_str, tool=tool_span.tool, inputs=inputs)
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        if not isinstance(output, ToolMessage):
            raise ValueError("[on_tool_end] Expected ToolMessage for tool end")
        run_id_str = str(run_id)
        tool_span = self.agentspec_spans_registry.get(run_id_str)

        try:
            parsed = (
                json.loads(output.content) if isinstance(output.content, str) else output.content
            )
        except json.JSONDecodeError as e:
            parsed = str(output.content)
        outputs = parsed if isinstance(parsed, dict) else {"output": parsed}

        if not isinstance(tool_span, AgentSpecToolExecutionSpan):
            raise ValueError(
                f"Expected tool_span to be a ToolExecutionSpan but got {type(tool_span)}"
            )

        tool_span.add_event(
            AgentSpecToolExecutionResponse(
                request_id=output.tool_call_id,
                tool=tool_span.tool,
                outputs=outputs,
            )
        )
        tool_span.end()
        self.agentspec_spans_registry.pop(run_id_str, None)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        raise error


def _ensure_string(obj: Any) -> str:
    if obj is None:
        raise ValueError("can only coerce non-string objects to string")
    if not isinstance(obj, str):
        try:
            return str(obj)
        except:
            raise ValueError(f"obj is not a valid JSON dict: {obj}")
    return obj


@typing.no_type_check
def _extract_message_content_and_tool_calls(
    response: LLMResult,
) -> Tuple[str, str, List[AgentSpecToolCall]]:
    """
    Returns content, tool_calls
    """
    if len(response.generations) != 1 or len(response.generations[0]) != 1:
        raise ValueError("Expected response to contain one generation and one chat_generation")
    chat_generation = response.generations[0][0]
    finish_reason = chat_generation.generation_info["finish_reason"]
    content = chat_generation.message.content
    tool_calls = chat_generation.message.additional_kwargs.get("tool_calls", [])
    # NOTE: content can be empty (empty string "")
    # in that case, chat_generation.generation_info["finish_reason"] is "tool_calls"
    # and tool_calls should not be empty
    if content == "" and not tool_calls:
        raise ValueError("Expected tool_calls to not be empty when content is empty")
    content = _ensure_string(content)
    agentspec_tool_calls = [_build_agentspec_tool_call(tc) for tc in tool_calls]
    # if streaming, response_id is not provided, must rely on run_id
    run_id = chat_generation.message.id
    completion_id = chat_generation.message.response_metadata.get("id")
    message_id = run_id or completion_id
    return message_id, content, agentspec_tool_calls


def _build_agentspec_tool_call(tool_call: Dict[str, Any]) -> AgentSpecToolCall:
    tc_id = tool_call["id"]
    if "function" in tool_call:
        tool_call: Dict[str, Any] = tool_call["function"]  # type: ignore[no-redef]
        args_key = "arguments"
    else:
        args_key = "args"
    tc_name = tool_call["name"]
    tc_args = _ensure_string(tool_call[args_key])
    return AgentSpecToolCall(call_id=tc_id, tool_name=tc_name, arguments=tc_args)
