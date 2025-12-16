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
from pyagentspec.tracing.models.message import Message as AgentSpecMessage
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

MessagesInProgressRecord = Dict[str, Optional[MessageInProgress]]  # keys are run_id


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
        # All per-run state consolidated here
        self.messages_in_process: MessagesInProgressRecord = {}
        # Track spans per run_id
        self.agentspec_spans_registry: Dict[str, AgentSpecSpan] = {}
        # Track tool-call id -> assistant message id correlation
        self.tool_call_message_ids: Dict[str, str] = {}
        # References for payloads
        self.llm_config = llm_config
        self.tools_map: Dict[str, AgentSpecTool] = {t.name: t for t in (tools or [])}

    def get_message_in_progress(self, run_id: str) -> Optional[MessageInProgress]:
        run_id = str(run_id)
        return self.messages_in_process.get(run_id)

    def set_message_in_progress(self, run_id: str, data: MessageInProgress) -> None:
        current_message_in_progress = self.messages_in_process.get(run_id)
        if current_message_in_progress:
            self.messages_in_process[run_id] = {
                **(current_message_in_progress),
                **data,
            }
        else:
            self.messages_in_process[run_id] = data

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

        tool_call_chunks = chunk_message.tool_call_chunks or []  # type: ignore
        if tool_call_chunks:
            if len(tool_call_chunks) != 1:
                raise ValueError(
                    "[on_llm_new_token] Expected exactly one tool call chunk "
                    f"if streaming tool calls, but got: {tool_call_chunks}"
                )
            self._add_tool_call_event_if_not_streamed(
                tool_call_chunks[0], message_id, run_id_str, span, streaming=True
            )
            return

        delta_text = chunk_message.content
        if delta_text:
            span.add_event(
                AgentSpecLlmGenerationChunkReceived(
                    request_id=run_id_str,
                    completion_id=message_id,
                    content=_ensure_string(delta_text),
                    llm_config=self.llm_config,
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
        # use _extract_message_content_and_tool_calls to parse the response
        # expected behavior: this should emit LlmGenerationResponse
        run_id_str = str(run_id)
        span = self._get_or_start_llm_span(run_id_str)

        message_id, content, tool_calls = _extract_message_content_and_tool_calls(response)

        for tc in tool_calls:
            self._add_tool_call_event_if_not_streamed(
                tc, message_id, run_id_str, span, streaming=False
            )

        span.add_event(
            AgentSpecLlmGenerationResponse(
                llm_config=self.llm_config,
                request_id=run_id_str,
                completion_id=message_id,
                content=content,
            )
        )

        span.end()
        self.agentspec_spans_registry.pop(run_id_str, None)
        self.messages_in_process[run_id_str] = None

    def _add_tool_call_event_if_not_streamed(
        self,
        tool_call: Dict[str, Any],
        message_id: str,
        run_id_str: str,
        span: AgentSpecSpan,
        streaming: bool = False,
    ) -> None:
        tc_id = tool_call["id"]
        if "function" in tool_call:
            tool_call: Dict[str, Any] = tool_call.get("function")  # type: ignore
            args_key = "arguments"
        else:
            args_key = "args"
        tc_name = tool_call.get("name")
        tc_args = tool_call.get(args_key)

        if not isinstance(tc_args, str):
            raise ValueError(f"Expected tool call args to be a string but got: {tc_args=}")

        tc_id, tc_name = _fill_tool_call_identifiers(
            run_id_str, streaming, self.get_message_in_progress(run_id_str), tc_id, tc_name
        )

        streamed_tool_call_ids = set(self.tool_call_message_ids.keys())

        if streaming or (tc_id not in streamed_tool_call_ids):
            span.add_event(
                AgentSpecLlmGenerationChunkReceived(
                    request_id=run_id_str,
                    llm_config=self.llm_config,
                    completion_id=message_id,
                    content="",
                    tool_calls=[
                        AgentSpecToolCall(
                            call_id=tc_id, tool_name=tc_name, arguments=_ensure_string(tc_args)
                        )
                    ],
                )
            )
        # Remember assistant message id for this tool_call to correlate to ToolMessage later
        self.tool_call_message_ids[tc_id] = message_id

        if streaming:
            self.set_message_in_progress(
                run_id_str,
                MessageInProgress(
                    id=message_id,
                    tool_call_id=tc_id,
                    tool_call_name=tc_name,
                ),
            )

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


def _fill_tool_call_identifiers(
    run_id_str: str,
    streaming: bool,
    current_stream: Optional[MessageInProgress],
    tc_id: Optional[str],
    tc_name: Optional[str],
) -> Tuple[str, str]:
    """
    Ensure tool call id/name are present. If streaming and a value is missing,
    backfill from the in-flight tool call. Only require current_stream when a
    corresponding value is missing.
    """
    if streaming and (tc_id is None or tc_name is None):
        if current_stream is None:
            # Only error if we actually needed to backfill something
            missing = []
            if tc_id is None:
                missing.append("id")
            if tc_name is None:
                missing.append("name")
            raise ValueError(
                f"Missing tool call {' and '.join(missing)} and no in-flight tool call found. Current stream: {current_stream}"
            )

        if tc_id is None:
            tc_id = current_stream["tool_call_id"]
        if tc_name is None:
            tc_name = current_stream["tool_call_name"]

    if not tc_id:
        raise ValueError("Expected non-empty tool call id")
    if not tc_name:
        raise ValueError("Expected non-empty tool call name")

    return tc_id, tc_name


@typing.no_type_check
def _extract_message_content_and_tool_calls(
    response: LLMResult,
) -> Tuple[str, str, List[Dict[str, Any]]]:
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
    # if streaming, response_id is not provided, must rely on run_id
    run_id = chat_generation.message.id
    completion_id = chat_generation.message.response_metadata.get("id")
    message_id = run_id or completion_id
    return message_id, content, tool_calls
