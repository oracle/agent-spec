# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Type, cast

from pydantic import PrivateAttr

from pyagentspec import Agent as AgentSpecAgent
from pyagentspec import Component as AgentSpecComponent
from pyagentspec.adapters.crewai._types import (
    CrewAIAgent,
    CrewAIAgentExecutionCompletedEvent,
    CrewAIAgentExecutionStartedEvent,
    CrewAIBaseEvent,
    CrewAIBaseEventListener,
    CrewAIEventsBus,
    CrewAILiteAgentExecutionCompletedEvent,
    CrewAILiteAgentExecutionStartedEvent,
    CrewAILLMCallCompletedEvent,
    CrewAILLMCallStartedEvent,
    CrewAILLMStreamChunkEvent,
    CrewAIToolUsageFinishedEvent,
    CrewAIToolUsageStartedEvent,
)
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms import OpenAiCompatibleConfig as AgentSpecOpenAiCompatibleConfig
from pyagentspec.llms import OpenAiConfig as AgentSpecOpenAiConfig
from pyagentspec.tools import Tool as AgentSpecTool
from pyagentspec.tracing.events import (
    AgentExecutionEnd,
    AgentExecutionStart,
    LlmGenerationChunkReceived,
    LlmGenerationRequest,
    LlmGenerationResponse,
    ToolExecutionRequest,
    ToolExecutionResponse,
)
from pyagentspec.tracing.messages.message import Message as AgentSpecMessage
from pyagentspec.tracing.spans import AgentExecutionSpan, LlmGenerationSpan, Span, ToolExecutionSpan
from pyagentspec.tracing.spans.span import (
    _ACTIVE_SPAN_STACK,
    get_active_span_stack,
    get_current_span,
)


def _get_closest_span_of_given_type(agentspec_span_type: Type[Span]) -> Optional[Span]:
    return next(
        (span for span in get_active_span_stack()[::-1] if isinstance(span, agentspec_span_type)),
        None,
    )


def _ensure_dict(obj: Any) -> Dict[str, Any]:
    """Ensure that an object is a dict, if it is not, transform it into one."""
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        stripped = obj.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return {"value": parsed}
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {"value": obj}
        return {"value": obj}
    return {"value": str(obj)}


class AgentSpecEventListener:

    def __init__(self, agentspec_components: Dict[int, AgentSpecComponent]) -> None:
        super().__init__()
        self.agentspec_components = agentspec_components
        self._event_listener: Optional[_CrewAiEventListener] = None
        self.scoped_handlers_context_generator: Optional[Generator[None, Any, None]] = None
        self._events_flush_timeout: float = 2.0

    @contextmanager
    def record_listener(self) -> Generator[None, Any, None]:
        from crewai.events import crewai_event_bus

        with crewai_event_bus.scoped_handlers():
            self._event_listener = _CrewAiEventListener(self.agentspec_components)
            yield
            # Before getting out, we ensure that the events have all been handled
            # We first wait a little to make the handlers start before we continue with this code
            time.sleep(0.1)
            start_time = time.time()
            while (
                len(self._event_listener._events_list) > 0
                and start_time + self._events_flush_timeout > time.time()
            ):
                time.sleep(0.1)
            self._event_listener = None


class _CrewAiEventListener(CrewAIBaseEventListener):  # type: ignore[misc]
    """Bridges CrewAI streaming and tool events to Agent Spec Tracing"""

    def __init__(self, agentspec_components: Dict[int, AgentSpecComponent]) -> None:
        super().__init__()
        self.agentspec_components = agentspec_components
        self.llm_configs_map: Dict[str, AgentSpecLlmConfig] = {
            llm.model_id: llm
            for llm in agentspec_components.values()
            if isinstance(llm, (AgentSpecOpenAiConfig, AgentSpecOpenAiCompatibleConfig))
        }
        self.tools_map: Dict[str, AgentSpecTool] = {
            tool.name: tool
            for tool in agentspec_components.values()
            if isinstance(tool, AgentSpecTool)
        }
        self.agents_map: Dict[str, AgentSpecAgent] = {
            (agent.metadata or {}).get("__crewai_agent_id__", str(agent_obj_id)): agent
            for agent_obj_id, agent in agentspec_components.items()
            if isinstance(agent, AgentSpecAgent)
        }
        # We keep a registry of conversions, so that we do not repeat the conversion for the same object twice
        self.agentspec_spans_registry: Dict[str, Span] = {}
        # Correlation helpers
        self._agent_fingerprint_to_last_msg: Dict[str, str] = {}
        # Track active tool execution spans by CrewAI agent_key
        self._tool_span_by_agent_key: Dict[str, ToolExecutionSpan] = {}
        # Track active agent execution spans by CrewAI agent_key
        self._agent_span_by_agent_key: Dict[str, AgentExecutionSpan] = {}
        # Per-agent_key tool_call_id and parent message id for correlation
        self._tool_call_id_by_agent_key: Dict[str, str] = {}
        self._parent_msg_by_agent_key: Dict[str, Optional[str]] = {}
        # This is a reference to the parent span stack, it is needed because it must be shared
        # when dealing with events, otherwise the changes to the stack performed in there,
        # like span start or end, are not persisted
        self._parent_context = _ACTIVE_SPAN_STACK.get()
        # Events are raised and handled sometimes concurrently (especially end of previous span and start of new one),
        # which makes it hard to handle the nested structure of spans
        # See the `_add_event_and_handle_events_list` method for more information.
        # This lock is used to manage the event list with a single thread at a time
        self._lock = threading.Lock()
        # This list contains all the pending events that could not be handled properly yet
        self._events_list: List[CrewAIBaseEvent] = []

    def _get_agentspec_component_from_crewai_object(self, crewai_obj: Any) -> AgentSpecComponent:
        return self.agentspec_components[id(crewai_obj)]

    @contextmanager
    def _parent_span_stack(self) -> Generator[None, Any, None]:
        """
        Context manager that sets the span stack of the root context in the current context.
        It is used because events are handled in async "threads" that have a different context,
        so changes to the span stack performed in there would not be persisted and propagated to the parent context.
        This way we centralize the context in this object and propagate/persist the changes across all the event handlers.
        """
        _ACTIVE_SPAN_STACK.set(self._parent_context)
        yield
        self._parent_context = _ACTIVE_SPAN_STACK.get()

    def _handle_event(self, event: CrewAIBaseEvent) -> bool:
        """
        Deal with the occurrence of the given event.
        Returns True if the event is properly handled, False if the event cannot be handled.
        """
        span: Span
        match event:
            case CrewAILiteAgentExecutionStartedEvent() | CrewAIAgentExecutionStartedEvent():
                if isinstance(event, CrewAILiteAgentExecutionStartedEvent):
                    agent_key = str(event.agent_info.get("id"))
                else:
                    agent_key = str(event.agent.id)
                agent = self.agents_map.get(agent_key)
                if agent is None:
                    return False
                span = AgentExecutionSpan(agent=agent)
                span.start()
                span.add_event(AgentExecutionStart(agent=agent, inputs={}))
                self._agent_span_by_agent_key[agent_key] = span
                return True
            case CrewAILiteAgentExecutionCompletedEvent() | CrewAIAgentExecutionCompletedEvent():
                if not isinstance(get_current_span(), AgentExecutionSpan):
                    return False
                if isinstance(event, CrewAILiteAgentExecutionCompletedEvent):
                    agent_key = str(event.agent_info.get("id"))
                else:
                    agent_key = str(event.agent.id)
                agent = self.agents_map.get(agent_key)
                if agent is None:
                    return False
                span = self._agent_span_by_agent_key[agent_key]
                span.add_event(
                    AgentExecutionEnd(
                        agent=agent,
                        outputs={"output": event.output} if hasattr(event, "output") else {},
                    )
                )
                span.end()
                self._agent_span_by_agent_key.pop(agent_key, None)
                return True
            case CrewAILLMCallStartedEvent():
                if not isinstance(get_current_span(), AgentExecutionSpan):
                    return False
                messages = event.messages or []
                if isinstance(messages, str):
                    messages = [{"content": messages}]
                run_id = self._compute_chat_history_hash(messages)
                model_id = self._sanitize_model_id(event.model or "")
                # model_id should match an entry in the config map
                llm_cfg = self.llm_configs_map.get(model_id)
                if llm_cfg is None and "/" in model_id:
                    # Try last token as a fallback (provider differences)
                    llm_cfg = self.llm_configs_map.get(model_id.split("/")[-1])
                if llm_cfg is None:
                    raise RuntimeError(
                        f"Unable to find the Agent Spec LlmConfig during tracing: `{model_id}`"
                    )
                span = LlmGenerationSpan(id=run_id, llm_config=llm_cfg)
                span.start()
                span.add_event(
                    LlmGenerationRequest(
                        llm_config=span.llm_config,
                        llm_generation_config=span.llm_config.default_generation_parameters,
                        prompt=[
                            AgentSpecMessage(
                                content=m["content"],
                                role=m["role"],
                            )
                            for m in messages
                        ],
                        tools=list(self.tools_map.values()),
                        request_id=run_id,
                    )
                )
                self.agentspec_spans_registry[run_id] = span
                return True
            case CrewAILLMCallCompletedEvent():
                if not isinstance(get_current_span(), LlmGenerationSpan):
                    return False
                messages = event.messages or []
                if isinstance(messages, str):
                    messages = [{"content": messages}]
                run_id = self._compute_chat_history_hash(messages)
                span = cast(LlmGenerationSpan, self.agentspec_spans_registry[run_id])
                span.add_event(
                    LlmGenerationResponse(
                        llm_config=span.llm_config,
                        completion_id=run_id,
                        content=event.response,
                        tool_calls=[],
                        request_id=run_id,
                    )
                )
                span.end()
                self.agentspec_spans_registry.pop(run_id, None)
                return True
            case CrewAILLMStreamChunkEvent():
                current_span = _get_closest_span_of_given_type(LlmGenerationSpan)
                if isinstance(current_span, LlmGenerationSpan):
                    current_span.add_event(
                        LlmGenerationChunkReceived(
                            llm_config=current_span.llm_config,
                            completion_id=current_span.id,
                            content=event.chunk,
                            tool_calls=[],
                            request_id=current_span.id,
                        )
                    )
                return True
            case CrewAIToolUsageStartedEvent():
                tool_name = event.tool_name
                tool_args = event.tool_args
                agent_key = event.agent_key or ""
                # Correlate to current assistant message via agent fingerprint
                parent_msg_id = None
                if event.source_fingerprint:
                    parent_msg_id = self._agent_fingerprint_to_last_msg.get(
                        event.source_fingerprint
                    )

                # Resolve tool object and create a ToolExecutionSpan
                tool = self.tools_map.get(tool_name)
                if tool is None:
                    return False
                tool_span = ToolExecutionSpan(name=f"ToolExecution - {tool_name}", tool=tool)
                tool_span.start()
                self._tool_span_by_agent_key[agent_key] = tool_span

                # Ensure a tool_call_id for later correlation (no streaming support → always synthesize)
                tool_call_id = str(uuid.uuid4())
                self._tool_call_id_by_agent_key[agent_key] = tool_call_id
                self._parent_msg_by_agent_key[agent_key] = parent_msg_id

                inputs = _ensure_dict(tool_args)
                tool_span.add_event(
                    ToolExecutionRequest(
                        tool=tool,
                        inputs=inputs,
                        request_id=tool_call_id,
                    )
                )
                return True
            case CrewAIToolUsageFinishedEvent():
                if not isinstance(get_current_span(), ToolExecutionSpan):
                    return False

                outputs = event.output
                agent_key = event.agent_key or ""

                tool_span = self._tool_span_by_agent_key[agent_key]
                tool_call_id = self._tool_call_id_by_agent_key[agent_key]
                if tool_span is None:
                    return False

                tool_span.add_event(
                    ToolExecutionResponse(
                        request_id=tool_call_id,
                        tool=tool_span.tool,
                        outputs=_ensure_dict(outputs),
                    )
                )
                tool_span.end()

                # Cleanup
                self._tool_span_by_agent_key.pop(agent_key, None)
                self._tool_call_id_by_agent_key.pop(agent_key, None)
                self._parent_msg_by_agent_key.pop(agent_key, None)

                return True
        return False

    def _add_event_and_handle_events_list(self, new_event: CrewAIBaseEvent) -> None:
        """
        The goal of this method is to add the given event to the events list, and then try to handle
        all the events in the _events_list. The reason why we need this is that the order in which some
        events are emitted/handled in CrewAI is arbitrary. For example, the llm generation end and the consequent
        agent execution end events are emitted at the same time, and since event handlers are executed concurrently,
        there's no guarantee on the order in which those events are handled. From an Agent Spec Tracing perspective,
        instead, we need to have a precise order in order to open and close spans properly, according to the span stack.

        In order to recreate this order manually, we adopt the following solution.
        When an event is emitted by CrewAI, we simply add it to the list of events that should be handled.
        Then we try to handle all the events in the list. The idea is that:
        - If an event cannot be handled (e.g., because it's not in the correct span), it stays in the events list.
          This means that another event has to happen in order to unlock this event to be handled. When that event will happen,
          it will unlock this event from being handled, and that will happen.
        - If the event can be handled, it is handled and popped from the list. This event being handled might unlock another event,
          that will be handled as well, and so on until no event can be handled anymore, or the events list is empty.
        """
        with self._lock:
            # We first add the new event to the list of events to be handled.
            # We use the lock to avoid changing the list that is already being modified by some other event handling
            self._events_list.append(new_event)
        with self._lock:
            # We now take the lock again and try to handle all the events we can
            events_correctly_handled = 1
            while events_correctly_handled > 0 and len(self._events_list) > 0:
                event_indices_to_remove = []
                # We go over the list of events that are waiting for being handled
                for i, event in enumerate(self._events_list):
                    # We need to ensure that we are using the right span stack contextvar
                    with self._parent_span_stack():
                        # The events that get correctly handled, will be removed from the list, the others stay
                        if self._handle_event(event):
                            event_indices_to_remove.append(i)
                events_correctly_handled = len(event_indices_to_remove)
                # Remove the handled events from the list
                for offset, event_index in enumerate(sorted(event_indices_to_remove)):
                    self._events_list.pop(event_index - offset)

    def setup_listeners(self, crewai_event_bus: CrewAIEventsBus) -> None:
        """Register handlers on the global CrewAI event bus."""

        @crewai_event_bus.on(CrewAILiteAgentExecutionStartedEvent)  # type: ignore[misc]
        def on_lite_agent_execution_started(
            source: Any, event: CrewAILiteAgentExecutionStartedEvent
        ) -> None:
            self._add_event_and_handle_events_list(event)

        @crewai_event_bus.on(CrewAILiteAgentExecutionCompletedEvent)  # type: ignore[misc]
        def on_lite_agent_execution_finished(
            source: Any, event: CrewAILiteAgentExecutionCompletedEvent
        ) -> None:
            self._add_event_and_handle_events_list(event)

        @crewai_event_bus.on(CrewAIAgentExecutionStartedEvent)  # type: ignore[misc]
        def on_agent_execution_started(
            source: Any, event: CrewAIAgentExecutionStartedEvent
        ) -> None:
            self._add_event_and_handle_events_list(event)

        @crewai_event_bus.on(CrewAIAgentExecutionCompletedEvent)  # type: ignore[misc]
        def on_agent_execution_finished(
            source: Any, event: CrewAIAgentExecutionCompletedEvent
        ) -> None:
            self._add_event_and_handle_events_list(event)

        @crewai_event_bus.on(CrewAILLMCallStartedEvent)  # type: ignore[misc]
        def on_llm_call_started(source: Any, event: CrewAILLMCallStartedEvent) -> None:
            self._add_event_and_handle_events_list(event)

        @crewai_event_bus.on(CrewAILLMCallCompletedEvent)  # type: ignore[misc]
        def on_llm_call_completed(source: Any, event: CrewAILLMCallCompletedEvent) -> None:
            self._add_event_and_handle_events_list(event)

        @crewai_event_bus.on(CrewAILLMStreamChunkEvent)  # type: ignore[misc]
        def on_llm_call_chunk(source: Any, event: CrewAILLMStreamChunkEvent) -> None:
            self._add_event_and_handle_events_list(event)

        @crewai_event_bus.on(CrewAIToolUsageStartedEvent)  # type: ignore[misc]
        def on_tool_usage_started(source: Any, event: CrewAIToolUsageStartedEvent) -> None:
            self._add_event_and_handle_events_list(event)

        @crewai_event_bus.on(CrewAIToolUsageFinishedEvent)  # type: ignore[misc]
        def on_tool_usage_finished(source: Any, event: CrewAIToolUsageFinishedEvent) -> None:
            self._add_event_and_handle_events_list(event)

    @staticmethod
    def _sanitize_model_id(model_id: str) -> str:
        model_parts = model_id.split("/") if model_id else []
        if len(model_parts) > 1:
            # Since CrewAI relies on LiteLLM, it contains the model provider at the start of the model id
            # That is removed in Agent Spec conversion, so we must remove it from here too
            return "/".join(model_parts[1:])
        return model_id

    @staticmethod
    def _compute_chat_history_hash(messages: List[Dict[str, Any]]) -> str:
        """Compute a stable UUID based on the list of messages.

        We only allow messages with role/content fields and roles in
        {system,user,assistant} to mirror the frontend inputs.
        """
        normalized = [
            {
                "role": m["role"],
                "content": str(m["content"]).replace("\r\n", "\n").replace("\r", "\n"),
            }
            for m in messages
        ]
        payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return str(uuid.uuid5(uuid.NAMESPACE_URL, payload))


class CrewAIAgentWithTracing(CrewAIAgent):  # type: ignore[misc]
    """Extension of the CrewAI agent that contains the event handler for Agent Spec Tracing"""

    _agentspec_event_listener: Optional[AgentSpecEventListener] = PrivateAttr(default=None)

    @contextmanager
    def agentspec_event_listener(self) -> Generator[None, Any, None]:
        """
        Context manager that yields the agent spec event listener.

        Example of usage:

        from pyagentspec.agent import Agent

        system_prompt = '''You are an expert in computer science. Please help the users with their requests.'''
        agent = Agent(
            name="Adaptive expert agent",
            system_prompt=system_prompt,
            llm_config=llm_config,
        )

        from pyagentspec.adapters.crewai import AgentSpecLoader
        from pyagentspec.tracing.trace import Trace

        crewai_agent = AgentSpecLoader().load_component(agent)
        with Trace(name="crewai_tracing_test"):
            with crewai_agent.agentspec_event_listener():
                response = crewai_agent.kickoff(messages="Talk about the Dijkstra's algorithm")

        """
        if self._agentspec_event_listener is None:
            raise RuntimeError(
                "Called Agent Spec event listener context manager, but no instance was provided. "
                "Please set the _agentspec_event_listener attribute first."
            )
        with self._agentspec_event_listener.record_listener():
            yield
