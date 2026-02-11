# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import ast
import json
import logging
import typing
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)
from uuid import UUID

import anyio
from typing_extensions import NotRequired

from pyagentspec.adapters.langgraph._types import (
    BaseCallbackHandler,
    BaseMessage,
    ChatGenerationChunk,
    GenerationChunk,
    LLMResult,
    ToolMessage,
)
from pyagentspec.llms.llmconfig import LlmConfig as AgentSpecLlmConfig
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.tools import ClientTool as AgentSpecClientTool
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
from pyagentspec.tracing.spans.span import _ACTIVE_SPAN_STACK, get_active_span_stack

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
}

T = TypeVar("T")

logger = logging.getLogger(__file__)

# NOTE ABOUT CONTEXTVARS AND THE ACTIVE SPAN STACK
#
# LangGraph schedules callbacks on executors and wraps them with copy_context().run(...),
# which means each callback may observe a different ContextVars snapshot. If we naively
# call span.add_event/span.end inside these callbacks, the _ACTIVE_SPAN_STACK ContextVar
# would not reflect the stack we had when we started the span, and nested push/pop
# operations would become inconsistent (e.g., popping an empty stack).
#
# To keep the span stack consistent across callbacks for the same run, we adopt the same
# approach used in crewai_tracing.py: we capture and store a copy of the active span stack
# immediately after span.start/span.start_async and then, for each callback, we:
#   - set _ACTIVE_SPAN_STACK to the stored stack,
#   - invoke the target function (sync or async),
#   - refresh our stored snapshot from the new _ACTIVE_SPAN_STACK so nested changes persist.
#
# This per-run stack management ensures that callbacks running on different threads (or
# created from different copy_context snapshots) still participate in the same logical
# span stack for that run. It avoids the pitfalls of constructing/awaiting coroutines
# via Context.run and keeps the behavior aligned with the crewai adapter.


class _SpanStack:
    """Singleton containing the full set of span stacks. Used across sync and async handlers"""

    _instance: "_SpanStack | None" = None
    _span_stacks: Dict[str, List[AgentSpecSpan]] = {}

    def __init__(self) -> None:
        if _SpanStack._instance is not None:
            raise RuntimeError("_SpanStack should not be instantiated multiple times")

    @classmethod
    def get_instance(cls) -> "_SpanStack":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def pop(self, key: str, raise_if_not_present: bool = True) -> List[AgentSpecSpan]:
        try:
            return self._span_stacks.pop(key)
        except KeyError as e:
            if raise_if_not_present:
                raise e
            return []

    def get(self, key: str) -> List[AgentSpecSpan] | None:
        return self._span_stacks.get(key)

    def insert(self, key: str, value: List[AgentSpecSpan]) -> None:
        self._span_stacks[key] = value

    def __setitem__(self, key: Any, value: Any) -> None:
        self.insert(key, value)


class AgentSpecCallbackHandler(BaseCallbackHandler):

    def __init__(self) -> None:
        # Track spans per run_id
        self.agentspec_spans_registry: Dict[str, AgentSpecSpan] = {}
        # Track the active span stack captured right after span.start()
        # so we can run subsequent callbacks against the same stack
        self._span_stacks: _SpanStack = _SpanStack.get_instance()
        self.raise_error = True
        self._events_handled: Set[str] = set()

    def _get_stack(self, run_id_str: str) -> List[AgentSpecSpan]:
        stack = self._span_stacks.get(run_id_str)
        if stack is None:
            raise RuntimeError(
                f"[AgentSpecCallbackHandler] Missing Context for run_id={run_id_str}. "
                "Span was not started (or context not captured) before this callback."
            )
        return stack

    def _run_in_ctx(self, run_id_str: str, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        stack = self._get_stack(run_id_str)
        _ACTIVE_SPAN_STACK.set(stack)
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            self._span_stacks[run_id_str] = get_active_span_stack(return_copy=True)

    def _add_event(self, run_id_str: str, span: AgentSpecSpan, event: Any) -> None:
        self._run_in_ctx(run_id_str, span.add_event, event)

    def _end_span(self, run_id_str: str, span: AgentSpecSpan) -> None:
        self._run_in_ctx(run_id_str, span.end)
        self._span_stacks.pop(run_id_str, False)

    def _start_and_copy_ctx(self, run_id_str: str, span: AgentSpecSpan) -> None:
        self._span_stacks[run_id_str] = get_active_span_stack(return_copy=True)
        self._run_in_ctx(run_id_str, span.start)

    async def _run_in_ctx_async(
        self, run_id_str: str, afunc: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        stack = self._get_stack(run_id_str)
        _ACTIVE_SPAN_STACK.set(stack)
        try:
            result = await afunc(*args, **kwargs)
            return result
        finally:
            self._span_stacks[run_id_str] = get_active_span_stack(return_copy=True)

    async def _add_event_async(self, run_id_str: str, span: AgentSpecSpan, event: Any) -> None:
        try:
            await self._run_in_ctx_async(run_id_str, span.add_event_async, event)
        except NotImplementedError:
            self._run_in_ctx(run_id_str, span.add_event, event)

    async def _end_span_async(self, run_id_str: str, span: AgentSpecSpan) -> None:
        try:
            await self._run_in_ctx_async(run_id_str, span.end_async)
        except NotImplementedError:
            self._run_in_ctx(run_id_str, span.end)
        self._span_stacks.pop(run_id_str, False)

    async def _start_and_copy_ctx_async(self, run_id_str: str, span: AgentSpecSpan) -> None:
        self._span_stacks[run_id_str] = get_active_span_stack(return_copy=True)
        try:
            await self._run_in_ctx_async(run_id_str, span.start_async)
        except NotImplementedError:
            self._run_in_ctx(run_id_str, span.start)

    def _in_async_trace(self) -> bool:
        try:
            anyio.get_running_tasks()
            return True
        except RuntimeError:
            return False

    def __getattribute__(self, name: str) -> Any:
        # Need to use super().__getattribute__ to avoid infinite recursion by calling self.
        if name in super().__getattribute__("_events_handled"):
            if super().__getattribute__("_in_async_trace")():
                return super().__getattribute__(name + "_async")
        return super().__getattribute__(name)


class AgentSpecLlmCallbackHandler(AgentSpecCallbackHandler):

    def __init__(
        self,
        llm_config: AgentSpecLlmConfig,
    ) -> None:
        super().__init__()
        self.llm_config = llm_config
        # This is only added during tool-call streaming to associate run_id with tool_call_id
        # (tool_call_id is not available mid-stream)
        self.messages_in_process: MessagesInProgressRecord = {}
        self._events_handled.update(("on_chat_model_start", "on_llm_new_token", "on_llm_end"))

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

        # Create and start the LLM span for this run, capture Context
        span = AgentSpecLlmGenerationSpan(llm_config=self.llm_config)
        self.agentspec_spans_registry[run_id_str] = span
        self._start_and_copy_ctx(run_id_str, span)

        # this is a list of lists because it can be batched, but we assume it to be a batch of size 1
        if len(messages) != 1:
            raise ValueError(
                f"[on_chat_model_start] langchain messages is a nested list of list of BaseMessage, "
                "expected the outer list to have size one but got size {len(messages)}"
            )
        prompt = [
            AgentSpecMessage(
                content=_ensure_string(message.content),
                sender="",
                role=LANGCHAIN_ROLES_TO_OPENAI_ROLES[message.type],
            )
            for message in messages[0]  # messages[0] is a list of messages
        ]

        tools: List[AgentSpecTool] = [
            AgentSpecClientTool(
                name=tool_schema["function"]["name"],
                description=tool_schema["function"]["description"],
                inputs=[
                    AgentSpecProperty(title=property_title, json_schema=property_schema)
                    for property_title, property_schema in tool_schema["function"]["parameters"][
                        "properties"
                    ].items()
                ],
            )
            for tool_schema in kwargs["invocation_params"].get("tools", [])
        ]

        event = AgentSpecLlmGenerationRequest(
            request_id=run_id_str,
            llm_config=self.llm_config,
            llm_generation_config=self.llm_config.default_generation_parameters,
            prompt=prompt,
            tools=tools,
        )
        self._add_event(run_id_str, span, event)

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
        span = self.agentspec_spans_registry.get(run_id_str)
        if not isinstance(span, AgentSpecLlmGenerationSpan):
            raise RuntimeError("LLM span not started; on_chat_model_start must run first")
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
                AgentSpecToolCall(call_id=call_id, tool_name=tool_name, arguments=tool_args or "")
            ]

        event = AgentSpecLlmGenerationChunkReceived(
            request_id=run_id_str,
            completion_id=message_id,
            content=_ensure_string(chunk_message.content or ""),
            llm_config=self.llm_config,
            tool_calls=agentspec_tool_calls,
        )
        self._add_event(run_id_str, span, event)

    @typing.no_type_check
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        span = self.agentspec_spans_registry.get(run_id_str)
        if not isinstance(span, AgentSpecLlmGenerationSpan):
            raise RuntimeError("LLM span not started; on_chat_model_start must run first")
        message_id, content, tool_calls = _extract_message_content_and_tool_calls(response)
        event = AgentSpecLlmGenerationResponse(
            llm_config=self.llm_config,
            request_id=run_id_str,
            completion_id=message_id,
            content=content,
            tool_calls=tool_calls,
        )
        self._add_event(run_id_str, span, event)
        self._end_span(run_id_str, span)
        self.agentspec_spans_registry.pop(run_id_str)
        self.messages_in_process.pop(run_id_str, None)

    async def on_chat_model_start_async(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        span = AgentSpecLlmGenerationSpan(llm_config=self.llm_config)
        self.agentspec_spans_registry[run_id_str] = span
        await self._start_and_copy_ctx_async(run_id_str, span)

        if len(messages) != 1:
            raise ValueError(
                f"[on_chat_model_start] langchain messages is a nested list of list of BaseMessage, expected the outer list to have size one but got size {len(messages)}"
            )
        prompt = [
            AgentSpecMessage(
                content=_ensure_string(message.content),
                sender="",
                role=LANGCHAIN_ROLES_TO_OPENAI_ROLES[message.type],
            )
            for message in messages[0]
        ]

        tools: List[AgentSpecTool] = [
            AgentSpecClientTool(
                name=tool_schema["function"]["name"],
                description=tool_schema["function"]["description"],
                inputs=[
                    AgentSpecProperty(title=property_title, json_schema=property_schema)
                    for property_title, property_schema in tool_schema["function"]["parameters"][
                        "properties"
                    ].items()
                ],
            )
            for tool_schema in kwargs.get("invocation_params", {}).get("tools", [])
        ]

        event = AgentSpecLlmGenerationRequest(
            request_id=run_id_str,
            llm_config=self.llm_config,
            llm_generation_config=self.llm_config.default_generation_parameters,
            prompt=prompt,
            tools=tools,
        )
        await self._add_event_async(run_id_str, span, event)

    async def on_llm_new_token_async(
        self,
        token: str,
        *,
        chunk: Optional[Union[ChatGenerationChunk, GenerationChunk]] = None,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        if chunk is None:
            raise ValueError("[on_llm_new_token] Expected chunk to not be None")
        run_id_str = str(run_id)
        span = self.agentspec_spans_registry.get(run_id_str)
        if not isinstance(span, AgentSpecLlmGenerationSpan):
            raise RuntimeError("LLM span not started; on_chat_model_start must run first")
        chunk_message = chunk.message  # type: ignore

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
                AgentSpecToolCall(call_id=call_id, tool_name=tool_name, arguments=tool_args or "")
            ]

        event = AgentSpecLlmGenerationChunkReceived(
            request_id=run_id_str,
            completion_id=message_id,
            content=_ensure_string(chunk_message.content or ""),
            llm_config=self.llm_config,
            tool_calls=agentspec_tool_calls,
        )
        await self._add_event_async(run_id_str, span, event)

    @typing.no_type_check
    async def on_llm_end_async(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        span = self.agentspec_spans_registry.get(run_id_str)
        if not isinstance(span, AgentSpecLlmGenerationSpan):
            raise RuntimeError("LLM span not started; on_chat_model_start must run first")
        message_id, content, tool_calls = _extract_message_content_and_tool_calls(response)
        event = AgentSpecLlmGenerationResponse(
            llm_config=self.llm_config,
            request_id=run_id_str,
            completion_id=message_id,
            content=content,
            tool_calls=tool_calls,
        )
        await self._add_event_async(run_id_str, span, event)
        await self._end_span_async(run_id_str, span)
        self.agentspec_spans_registry.pop(run_id_str)
        self.messages_in_process.pop(run_id_str, None)


class AgentSpecToolCallbackHandler(AgentSpecCallbackHandler):

    def __init__(self, tool: AgentSpecTool) -> None:
        super().__init__()
        self.tool = tool
        self._events_handled.update(("on_tool_start", "on_tool_error", "on_tool_end"))

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        # get run_id and tool config
        run_id_str = str(run_id)
        # instead of the real tool_call_id, we use the run_id to correlate between tool request and tool result
        request_event = AgentSpecToolExecutionRequest(
            request_id=run_id_str,
            tool=self.tool,
            inputs=ast.literal_eval(input_str) if isinstance(input_str, str) else input_str,
        )
        # starting a tool span for this tool
        span_name = f"ToolExecution[{self.tool.name}]"
        # Hack: transmit the tool_call_id as the span's description
        # so that tool results can learn of its tool_call_id
        # by correlating with tool starts using the run_id
        if "tool_call_id" in kwargs:
            tcid_string = "tcid__" + str(kwargs["tool_call_id"])
        else:
            tcid_string = ""
        tool_span = AgentSpecToolExecutionSpan(
            name=span_name, description=tcid_string, tool=self.tool
        )
        self.agentspec_spans_registry[run_id_str] = tool_span
        self._start_and_copy_ctx(run_id_str, tool_span)
        self._add_event(run_id_str, tool_span, request_event)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        tool_span = self.agentspec_spans_registry.get(run_id_str)

        if not isinstance(tool_span, AgentSpecToolExecutionSpan):
            raise ValueError(
                f"Expected tool_span to be a ToolExecutionSpan but got {type(tool_span)}"
            )

        if isinstance(output, ToolMessage):
            try:
                parsed = (
                    json.loads(output.content)
                    if isinstance(output.content, str)
                    else output.content
                )
            except json.JSONDecodeError:
                parsed = str(output.content)
            output = parsed

        if self.tool.outputs:
            # If tool outputs is a non-empty list
            if len(self.tool.outputs) == 1:
                # If it has exactly one output, we use the title of that output
                outputs = {self.tool.outputs[0].title: output}
            else:
                # Otherwise we should already have the dictionary with the right entries
                if isinstance(output, dict):
                    outputs = output
                else:
                    # If it's not a dictionary, then something went wrong, we don't report any output
                    outputs = {}
        else:
            # If tool outputs is None, or an empty list, it means that the tool has no entries
            outputs = {}

        response_event = AgentSpecToolExecutionResponse(
            request_id=run_id_str,
            tool=tool_span.tool,
            outputs=outputs,
        )
        self._add_event(run_id_str, tool_span, response_event)
        self._end_span(run_id_str, tool_span)
        self.agentspec_spans_registry.pop(run_id_str)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        try:
            self.on_tool_end(output=None, run_id=run_id, parent_run_id=parent_run_id)
        finally:
            raise error

    async def on_tool_start_async(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        request_event = AgentSpecToolExecutionRequest(
            request_id=run_id_str,
            tool=self.tool,
            inputs=ast.literal_eval(input_str) if isinstance(input_str, str) else input_str,
        )
        # starting a tool span for this tool
        span_name = f"ToolExecution[{self.tool.name}]"
        # Hack: transmit the tool_call_id as the span's description
        # so that tool results can learn of its tool_call_id
        # by correlating with tool starts using the run_id
        if "tool_call_id" in kwargs:
            tcid_string = "tcid__" + str(kwargs["tool_call_id"])
        else:
            tcid_string = ""
        tool_span = AgentSpecToolExecutionSpan(
            name=span_name, description=tcid_string, tool=self.tool
        )
        self.agentspec_spans_registry[run_id_str] = tool_span
        await self._start_and_copy_ctx_async(run_id_str, tool_span)
        await self._add_event_async(run_id_str, tool_span, request_event)

    async def on_tool_end_async(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        tool_span = self.agentspec_spans_registry.get(run_id_str)
        if not isinstance(tool_span, AgentSpecToolExecutionSpan):
            raise ValueError(
                f"Expected tool_span to be a ToolExecutionSpan but got {type(tool_span)}"
            )

        if isinstance(output, ToolMessage):
            try:
                parsed = (
                    json.loads(output.content)
                    if isinstance(output.content, str)
                    else output.content
                )
            except json.JSONDecodeError:
                parsed = str(output.content)
            outputs = parsed if isinstance(parsed, dict) else {"output": parsed}
        else:
            if (
                not isinstance(output, dict)
                and isinstance(self.tool.outputs, list)
                and len(self.tool.outputs) == 1
            ):
                outputs = {self.tool.outputs[0].title: output}
            else:
                outputs = output

        response_event = AgentSpecToolExecutionResponse(
            request_id=getattr(output, "tool_call_id", run_id_str),
            tool=tool_span.tool,
            outputs=outputs,
        )
        await self._add_event_async(run_id_str, tool_span, response_event)
        await self._end_span_async(run_id_str, tool_span)
        self.agentspec_spans_registry.pop(run_id_str)

    async def on_tool_error_async(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        try:
            await self.on_tool_end_async(output=None, run_id=run_id, parent_run_id=parent_run_id)
        finally:
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
    tool_calls = (
        chat_generation.message.tool_calls
        or chat_generation.message.additional_kwargs.get("tool_calls", [])
    )
    # NOTE: content can be empty (empty string "")
    # in that case, chat_generation.generation_info["finish_reason"] is "tool_calls"
    # and tool_calls should not be empty
    if content == "" and not tool_calls:
        raise ValueError(
            "Expected tool_calls to not be empty when content is empty. "
            "This issue is LLM-specific depending on their tool-calling capabilities; "
            "you may want to try again or switch to another LLM."
        )
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
