# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING, Any, Callable, Union

from pyagentspec._lazy_loader import LazyLoader

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as crewai is an optional dependency.
    # Otherwise, importing the module when they are not installed would lead to an import error.

    import crewai
    from crewai import LLM as CrewAILlm
    from crewai import Agent as CrewAIAgent
    from crewai import Flow as CrewAIFlow
    from crewai.events.base_event_listener import BaseEventListener as CrewAIBaseEventListener
    from crewai.events.base_events import BaseEvent as CrewAIBaseEvent
    from crewai.events.event_bus import CrewAIEventsBus, crewai_event_bus
    from crewai.events.types.agent_events import (
        AgentExecutionCompletedEvent as CrewAIAgentExecutionCompletedEvent,
    )
    from crewai.events.types.agent_events import (
        AgentExecutionStartedEvent as CrewAIAgentExecutionStartedEvent,
    )
    from crewai.events.types.agent_events import (
        LiteAgentExecutionCompletedEvent as CrewAILiteAgentExecutionCompletedEvent,
    )
    from crewai.events.types.agent_events import (
        LiteAgentExecutionStartedEvent as CrewAILiteAgentExecutionStartedEvent,
    )
    from crewai.events.types.llm_events import LLMCallCompletedEvent as CrewAILLMCallCompletedEvent
    from crewai.events.types.llm_events import LLMCallStartedEvent as CrewAILLMCallStartedEvent
    from crewai.events.types.llm_events import LLMStreamChunkEvent as CrewAILLMStreamChunkEvent
    from crewai.events.types.tool_usage_events import (
        ToolUsageFinishedEvent as CrewAIToolUsageFinishedEvent,
    )
    from crewai.events.types.tool_usage_events import (
        ToolUsageStartedEvent as CrewAIToolUsageStartedEvent,
    )
    from crewai.tools import BaseTool as CrewAIBaseTool
    from crewai.tools.base_tool import Tool as CrewAITool
    from crewai.tools.structured_tool import CrewStructuredTool as CrewAIStructuredTool
else:
    crewai = LazyLoader("crewai")
    # We need to import the classes this way because it's the only one accepted by the lazy loader
    CrewAILlm = crewai.LLM
    CrewAIAgent = crewai.Agent
    CrewAIFlow = crewai.Flow
    CrewAIBaseTool = LazyLoader("crewai.tools").BaseTool
    CrewAITool = LazyLoader("crewai.tools.base_tool").Tool
    CrewAIStructuredTool = LazyLoader("crewai.tools.structured_tool").CrewStructuredTool
    CrewAIBaseEventListener = LazyLoader("crewai.events.base_event_listener").BaseEventListener
    CrewAIEventsBus = LazyLoader("crewai.events.event_bus").CrewAIEventsBus
    crewai_event_bus = LazyLoader("crewai.events.event_bus").crewai_event_bus
    crewai = LazyLoader("crewai")
    CrewAIAgentExecutionStartedEvent = LazyLoader(
        "crewai.events.types.agent_events"
    ).AgentExecutionStartedEvent
    CrewAIAgentExecutionCompletedEvent = LazyLoader(
        "crewai.events.types.agent_events"
    ).AgentExecutionCompletedEvent
    CrewAILiteAgentExecutionStartedEvent = LazyLoader(
        "crewai.events.types.agent_events"
    ).LiteAgentExecutionStartedEvent
    CrewAILiteAgentExecutionCompletedEvent = LazyLoader(
        "crewai.events.types.agent_events"
    ).LiteAgentExecutionCompletedEvent
    CrewAILLMCallCompletedEvent = LazyLoader("crewai.events.types.llm_events").LLMCallCompletedEvent
    CrewAIBaseEvent = LazyLoader("crewai.events.base_events").BaseEvent
    CrewAILLMCallStartedEvent = LazyLoader("crewai.events.types.llm_events").LLMCallStartedEvent
    CrewAILLMStreamChunkEvent = LazyLoader("crewai.events.types.llm_events").LLMStreamChunkEvent
    CrewAIToolUsageFinishedEvent = LazyLoader(
        "crewai.events.types.tool_usage_events"
    ).ToolUsageFinishedEvent
    CrewAIToolUsageStartedEvent = LazyLoader(
        "crewai.events.types.tool_usage_events"
    ).ToolUsageStartedEvent

CrewAIComponent = Union[CrewAIAgent, CrewAIFlow[Any]]
CrewAIServerToolType = Union[CrewAITool, Callable[..., Any]]

__all__ = [
    "crewai",
    "crewai_event_bus",
    "CrewAILlm",
    "CrewAIAgent",
    "CrewAIFlow",
    "CrewAIBaseTool",
    "CrewAITool",
    "CrewAIStructuredTool",
    "CrewAIComponent",
    "CrewAIServerToolType",
    "CrewAIBaseEvent",
    "CrewAIBaseEventListener",
    "CrewAILLMCallCompletedEvent",
    "CrewAILLMCallStartedEvent",
    "CrewAILLMStreamChunkEvent",
    "CrewAIToolUsageStartedEvent",
    "CrewAIToolUsageFinishedEvent",
    "CrewAIEventsBus",
    "CrewAIAgentExecutionStartedEvent",
    "CrewAIAgentExecutionCompletedEvent",
    "CrewAILiteAgentExecutionStartedEvent",
    "CrewAILiteAgentExecutionCompletedEvent",
]
