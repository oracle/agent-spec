.. _agentspec_tracing:

=====================================================
Open Agent Specification Tracing (Agent Spec Tracing)
=====================================================

Overview
========

Open Agent Specification Tracing (short: Agent Spec Tracing) is an extension of
Agent Spec that standardizes how agent and flow executions emit traces.
It defines a unified, implementation-agnostic semantic for:

- Events: structured, point-in-time facts.
- Spans: time-bounded execution contexts that group events.
- Traces: trees of spans that represent an end-to-end execution.
- SpanProcessors: pluggable hooks to consume spans and events (e.g., export to UIs, tracing backends, or logs).

Agent Spec Tracing enables:

- Runtime adapters to emit consistent traces across different frameworks.
- Consumers (observability backends, UIs, developer tooling) to ingest one standardized format regardless of the producer.

Agent Spec Tracing aligns with widely used observability concepts (e.g.,
OpenTelemetry), while grounding definitions in Agent Spec components and
semantics. It specifies what spans and events to emit, when to emit them, and
which attributes to include, including which attributes are sensitive.

Scope and goals
---------------

- Provide a canonical list of span and event types for Agent Spec runtimes.
- Define lifecycle and attribute schema for each span/event.
- Identify sensitive fields and how they should be handled.
- Provide a minimal API surface for producers and consumers.
- Remain neutral to storage/transport (Telemetry, UIs, files, etc.).

Core Concepts
=============

Event
-----

An Event is an atomic episode that occurs at a specific time instant. It always belongs to exactly one Span.

Events have a definition similar to the Agent Spec Components, and they have the same descriptive fields:
``id``, ``name``, ``description``, ``type``, and ``metadata``.
Additionally, they require a ``timestamp`` that defines when the event occurred, and extensions of this class can
add more attributes based on the event they represent, aimed at preserving all the relevant information
related to the event being recorded.
Events can also have Sensitive fields, that are declared and must be handled per Agent Spec guidelines.

.. code-block:: python

   class Event:
       id: str  # Unique identifier for the event. Typically generated from component type plus a unique token.
       type: str  # Concrete type specifier for this event
       name: str  # Name of the event, if applicable
       description: str  # Description of the event, if applicable
       metadata: Dictionary[str, Any]  # Additional metadata that could be used for extra information
       timestamp: int  # nanoseconds since epoch

- timestamp: time of occurrence (ns). Producers should use monotonic clocks
  where possible and/or convert to wall-clock ns as configured by the runtime.

Agent Spec Tracing defines a set of Event types with specific attributes, that you can find in the following sections.


Span
----

A Span defines a time-bounded execution context. Each Span:

- starts at start_time (ns), ends at end_time (ns), end_time can be null if not closed.
- can contain zero or more Events.
- can be nested (child span has a parent span).


Also Spans have a definition similar to the Agent Spec Components, and they share the same descriptive fields:
``id``, ``name``, ``description``, ``type``, and ``metadata``.
Extensions of this Span can add more attributes based on the Span they represent.
Attributes on a Span typically reflect configuration that applies to the whole
duration of the Span (e.g., the Agent being executed, the LLM config, etc.).
Spans can also have Sensitive fields, that are declared and must be handled per Agent Spec guidelines.

Besides these attributes, Spans MUST also implement the following interface:

.. code-block:: python

   class Span:
       id: str  # Unique identifier for the span. Typically generated from component type plus a unique token.
       type: str  # Concrete type specifier for this span.
       name: str  # Name of the span, if applicable
       description: str  # Description of the span, if applicable
       metadata: Dictionary[str, Any]  # Additional metadata that could be used for extra information
       start_time: int
       end_time: Optional[int]
       events: List[Event]

       def start(self) -> None: ...

       def end(self) -> None: ...

       def add_event(self, event: Event) -> None: ...


- ``start``: called when the span starts.
- ``shutdown``: called when the span ends.
- ``add_event``: called when an event has to be added to this Span. It MUST append the event in the ``events`` attribute.

Lifecycle rules:

- Spans MUST have start_time when started, while end_time is set on end.
- Events added to a Span MUST have timestamps within [start_time, end_time], whenever end_time is known.
- Spans MAY contain child spans. Implementations SHOULD propagate correlation context so consumers can rebuild the tree.

Agent Spec Tracing defines a set of Span types with specific attributes, that you can find in the following sections.

SpanProcessor
-------------

A SpanProcessor receives callbacks when Spans start/end and when Events are added.
Processors are meant to consume the Agent Spec traces (spans, events) emitted by the runtime adapter
during the execution. They can be used to export traces to third parties consumers (e.g., to OpenTelemetry, files, UIs).

A SpanProcessor MUST implement the following interface.

.. code-block:: python

   class SpanProcessor(ABC):

       def on_start(self, span: Span) -> None: ...

       def on_end(self, span: "Span") -> None: ...

       def on_event(self, event: Event, span: Span) -> None: ...

       def startup(self) -> None: ...

       def shutdown(self) -> None: ...

- ``startup``: called when an Agent Spec Tracing session starts.
- ``shutdown``: called when an Agent Spec Tracing session ends.
- ``on_start``: called when a Span starts.
- ``on_end``: called when a Span ends.
- ``on_event``: called when an Event is added to a Span.

Trace
-----

A Trace groups all spans and events that belong to the same top-level assistant execution.
It is the root where all the SpanProcessors that must be active during the assistant execution are declared.

- Opening a Trace SHOULD call ``SpanProcessor.startup()`` on all configured processors.
- Closing a Trace SHOULD call ``SpanProcessor.shutdown()`` on all configured processors.

Standard Span Types
===================

This first version defines the following span types.
All spans inherit the attributes of the base ``Span`` class.
The attributes listed here are additional and span-specific.
Fields marked sensitive MUST be handled as described in Security Considerations.

LlmGenerationSpan
-----------------

Covers the whole LLM generation process.

- Starts: when the LLM generation request is received and the LLM call is
  performed.
- Ends: when the LLM output has been generated and is ready to be processed.

Attributes:

.. list-table::
    :header-rows: 1
    :widths: 20 50 12 8 10

    * - Name
      - Description
      - Type
      - Default
      - Sensitive
    * - llm_config
      - The LlmConfig performing the generation
      - LlmConfig
      - -
      - no

ToolExecutionSpan
-----------------

Covers a tool execution (excluding client-side tools executed by the UI/client).

- Starts: when tool execution starts.
- Ends: when the tool execution completes and the result is ready to be processed.

Attributes:

.. list-table::
    :header-rows: 1
    :widths: 20 50 12 8 10

    * - Name
      - Description
      - Type
      - Default
      - Sensitive
    * - tool
      - The Tool being executed
      - Tool
      - -
      - no

AgentExecutionSpan
------------------

Represents the execution of an Agent. May be nested for sub-agents.

- Starts: when the agent execution starts.
- Ends: when the agent execution completes and outputs are ready to process.

Attributes:

.. list-table::
    :header-rows: 1
    :widths: 20 50 12 8 10

    * - Name
      - Description
      - Type
      - Default
      - Sensitive
    * - agent
      - The Agent being executed
      - Agent
      - -
      - no

SwarmExecutionSpan
------------------

Specialization of AgentExecutionSpan for a Swarm Component.

- Starts: when swarm execution starts.
- Ends: when swarm execution completes and outputs are ready.

Attributes:

.. list-table::
    :header-rows: 1
    :widths: 20 50 12 8 10

    * - Name
      - Description
      - Type
      - Default
      - Sensitive
    * - swarm
      - The Swarm being executed
      - Swarm
      - -
      - no

ManagerWorkersExecutionSpan
---------------------------

Specialization of AgentExecutionSpan for a Manager-Workers pattern.

- Starts: when Manager-Workers execution starts.
- Ends: when the execution completes and outputs are ready.

Attributes:

.. list-table::
    :header-rows: 1
    :widths: 20 50 12 8 10

    * - Name
      - Description
      - Type
      - Default
      - Sensitive
    * - managerworkers
      - The ManagerWorkers being executed
      - ManagerWorkers
      - -
      - no

FlowExecutionSpan
-----------------

Covers the execution of a Flow.

- Starts: when the Flow's StartNode execution starts.
- Ends: when one of the Flow's EndNode executions finishes.

Attributes:

.. list-table::
    :header-rows: 1
    :widths: 20 50 12 8 10

    * - Name
      - Description
      - Type
      - Default
      - Sensitive
    * - flow
      - The Flow being executed
      - Flow
      - -
      - no

NodeExecutionSpan
-----------------

Covers the execution of a single Node within a Flow.

- Starts: when the Node execution starts on the given inputs.
- Ends: when the Node execution ends and outputs are ready.

Attributes:

.. list-table::
    :header-rows: 1
    :widths: 20 50 12 8 10

    * - Name
      - Description
      - Type
      - Default
      - Sensitive
    * - node
      - The Node being executed
      - Node
      - -
      - no


Standard Event Types
====================

All events are inherit the attributes defined in the base ``Event`` class.
The following events define the default set for Agent Spec Tracing.
For each, we specify when it is emitted and which attributes it carries.
Fields marked sensitive MUST be handled as described in Security Considerations.

LLM events
----------

LlmGenerationRequest
^^^^^^^^^^^^^^^^^^^^

An LLM generation request was received. Emitted when an LlmGenerationSpan starts.

Attributes:

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - llm_config
      - The LlmConfig performing the generation
      - LlmConfig
      - -
      - no
    * - request_id
      - Identifier of the generation request
      - str
      - -
      - no
    * - llm_generation_config
      - The LLM generation parameters used for this call
      - Optional[LlmGenerationConfig]
      - null
      - no
    * - prompt
      - Prompt that will be sent to the LLM; a list of Message with at least content and role, optionally sender
      - List[Message]
      - -
      - yes
    * - tools
      - Tools sent as part of the generation request
      - Optional[List[Tool]]
      - null
      - no

The ``Message`` model should be implemented as

.. code-block:: python

    class Message(BaseModel):
        """Model used to specify LLM message details in events and spans"""

        id: Optional[str] = None
        "Identifier of the message"

        content: str
        "Content of the message"

        sender: Optional[str] = None
        "Sender of the message"

        role: str
        "Role of the sender of the message. Typically 'user', 'assistant', or 'system'"


LlmGenerationResponse
^^^^^^^^^^^^^^^^^^^^^

An LLM response was received. Emitted when an LlmGenerationSpan ends.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - llm_config
      - The LlmConfig performing the generation
      - LlmConfig
      - -
      - no
    * - request_id
      - Identifier of the generation request
      - str
      - -
      - no
    * - tool_calls
      - Tool calls returned by the LLM. Each tool call should contain a ``call_id`` identifier, the ``tool_name``,
        and the ``arguments`` with which the tool is being called as a string in JSON format.
      - List[ToolCall]
      - -
      - yes
    * - completion_id
      - Identifier of the completion related to this response
      - Optional[str]
      - null
      - no
    * - content
      - The content of the response (assistant message text)
      - str
      - -
      - yes

The ``ToolCall`` model should be implemented as

.. code-block:: python

    class ToolCall(BaseModel):
        """Model for an LLM tool call."""

        call_id: str
        "Identifier of the tool call"

        tool_name: str
        "The name of the tool that should be called"

        arguments: str
        "The values of the arguments that should be passed to the tool, in JSON format"


LlmGenerationStreamingChunkReceived
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A streamed chunk was received during LLM generation.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - llm_config
      - The LlmConfig performing the generation
      - LlmConfig
      - -
      - no
    * - request_id
      - Identifier of the generation request
      - str
      - -
      - no
    * - tool_calls
      - Tool calls chunked by the LLM. Each tool call should contain a ``call_id`` identifier, the ``tool_name``,
        and the ``arguments`` with which the tool is being called as a string in JSON format. The content of arguments
        should be considered as the delta compared to the last chunk received.
      - List[ToolCall]
      - -
      - yes
    * - completion_id
      - Identifier of the parent completion (message or tool call) this chunk belongs to
      - Optional[str]
      - null
      - no
    * - content
      - The chunk content. This is the delta compared to the last chunk received.
      - str
      - -
      - yes

Tool events
-----------

ToolExecutionRequest
^^^^^^^^^^^^^^^^^^^^

A tool execution request is received. Emitted when a ToolExecutionSpan starts (or a client tool is requested).

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - tool
      - The Tool being executed
      - Tool
      - -
      - no
    * - request_id
      - Identifier of the tool execution request
      - str
      - -
      - no
    * - inputs
      - Input values for the tool (one per input property)
      - dict[str, any]
      - -
      - yes

ToolExecutionResponse
^^^^^^^^^^^^^^^^^^^^^

A tool execution finishes and a result is received. Emitted when a ToolExecutionSpan ends (or a client tool result is received).

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - tool
      - The Tool being executed
      - Tool
      - -
      - no
    * - request_id
      - Identifier of the tool execution request
      - str
      - -
      - no
    * - output
      - Return value produced by the tool (one per output property)
      - dict[str, any]
      - -
      - yes

ToolConfirmationRequest
^^^^^^^^^^^^^^^^^^^^^^^

A tool confirmation is requested (e.g., human-in-the-loop approval before execution).

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - tool
      - The Tool being executed
      - Tool
      - -
      - no
    * - tool_execution_request_id
      - Identifier of the related tool execution request
      - str
      - -
      - no
    * - request_id
      - Identifier of this confirmation request
      - str
      - -
      - no

ToolConfirmationResponse
^^^^^^^^^^^^^^^^^^^^^^^^

A tool confirmation response is received.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - tool
      - The Tool being executed
      - Tool
      - -
      - no
    * - tool_execution_request_id
      - Identifier of the related tool execution request
      - str
      - -
      - no
    * - request_id
      - Identifier of the confirmation request
      - str
      - -
      - no
    * - execution_confirmed
      - Whether execution was confirmed
      - bool
      - -
      - no

AgenticComponent events
-----------------------

AgentExecutionStart
^^^^^^^^^^^^^^^^^^^

Emitted when an AgentExecutionSpan starts.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - agent
      - The Agent being executed
      - Agent
      - -
      - no
    * - inputs
      - Inputs used for the agent execution (one per input property)
      - dict[str, any]
      - -
      - yes

AgentExecutionEnd
^^^^^^^^^^^^^^^^^

Emitted when an AgentExecutionSpan ends.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - agent
      - The Agent being executed
      - Agent
      - -
      - no
    * - outputs
      - Outputs produced by the agent (one per output property)
      - dict[str, any]
      - -
      - yes

ManagerWorkersExecutionStart
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Emitted when a ManagerWorkersExecutionSpan starts.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - managerworkers
      - The ManagerWorkers being executed
      - ManagerWorkers
      - -
      - no
    * - inputs
      - Inputs used for execution (one per input property)
      - dict[str, any]
      - -
      - yes

ManagerWorkersExecutionEnd
^^^^^^^^^^^^^^^^^^^^^^^^^^

Emitted when a ManagerWorkersExecutionSpan ends.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - managerworkers
      - The ManagerWorkers being executed
      - ManagerWorkers
      - -
      - no
    * - outputs
      - Outputs produced (one per output property)
      - dict[str, any]
      - -
      - yes

SwarmExecutionStart
^^^^^^^^^^^^^^^^^^^

Emitted when a SwarmExecutionSpan starts.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - swarm
      - The Swarm being executed
      - Swarm
      - -
      - no
    * - inputs
      - Inputs used for the swarm execution (one per input property)
      - dict[str, any]
      - -
      - yes

SwarmExecutionEnd
^^^^^^^^^^^^^^^^^

Emitted when a SwarmExecutionSpan ends.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - swarm
      - The Swarm being executed
      - Swarm
      - -
      - no
    * - outputs
      - Outputs produced (one per output property)
      - dict[str, any]
      - -
      - yes

Flow events
-----------

FlowExecutionStart
^^^^^^^^^^^^^^^^^^

Emitted when a FlowExecutionSpan starts.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - flow
      - The Flow being executed
      - Flow
      - -
      - no
    * - inputs
      - Inputs used by the flow (one per StartNode input property)
      - dict[str, any]
      - -
      - yes

FlowExecutionEnd
^^^^^^^^^^^^^^^^

Emitted when a FlowExecutionSpan ends.

.. list-table::
    :header-rows: 1
    :widths: 22 38 20 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - flow
      - The Flow being executed
      - Flow
      - -
      - no
    * - outputs
      - Outputs produced by the flow (one per flow output property)
      - dict[str, any]
      - -
      - yes
    * - branch_selected
      - Exit branch selected at the end of the Flow
      - str
      - -
      - no

NodeExecutionStart
^^^^^^^^^^^^^^^^^^

Emitted when a NodeExecutionSpan starts.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - node
      - The Node being executed
      - Node
      - -
      - no
    * - inputs
      - Inputs used by the node (one per node input property)
      - dict[str, any]
      - -
      - yes

NodeExecutionEnd
^^^^^^^^^^^^^^^^

Emitted when a NodeExecutionSpan ends.

.. list-table::
    :header-rows: 1
    :widths: 22 38 20 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - node
      - The Node being executed
      - Node
      - -
      - no
    * - outputs
      - Outputs produced by the node (one per node output property)
      - dict[str, any]
      - -
      - yes
    * - branch_selected
      - Exit branch selected at the end of the Node
      - str
      - -
      - no

Conversation and control events
-------------------------------

ConversationMessageAdded
^^^^^^^^^^^^^^^^^^^^^^^^

A message was added to the conversation.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - message
      - The message added; must contain at least content and role, optionally sender
      - Message
      - -
      - yes

ExceptionRaised
^^^^^^^^^^^^^^^

An exception occurred during execution.

.. list-table::
    :header-rows: 1
    :widths: 24 50 16 10 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - exception_type
      - Type of the exception
      - str
      - -
      - no
    * - exception_message
      - Exception message
      - str
      - -
      - yes
    * - exception_stacktrace
      - Stacktrace of the exception, if available
      - Optional[str]
      - null
      - yes

HumanInTheLoopRequest
^^^^^^^^^^^^^^^^^^^^^

A human-in-the-loop intervention is required; execution is interrupted until a response.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - request_id
      - Identifier of the human-in-the-loop request
      - str
      - -
      - no
    * - content
      - Request content forwarded to the user
      - dict[str, any]
      - {} (empty object)
      - yes

HumanInTheLoopResponse
^^^^^^^^^^^^^^^^^^^^^^

A HITL response is received; execution resumes.

.. list-table::
    :header-rows: 1
    :widths: 22 48 18 12 10

    * - Name
      - Description
      - Type
      - Default/Optional
      - Sensitive
    * - request_id
      - Identifier of the HITL request
      - str
      - -
      - no
    * - content
      - Response content received from the user
      - dict[str, any]
      - {} (empty object)
      - yes


Deterministic identifiers and correlation
-----------------------------------------

Some events define correlation identifiers to allow consumers to link request/response and other events.

For example:

- request_id: unique identifier of a single LLM or Tool execution request within a Span.
- completion_id: identifier of a completion (LLM message or tool-call) which may receive streaming chunks.
- tool_execution_request_id: identifier of a tool execution for confirmation.

Runtimes SHOULD ensure uniqueness within a Span and consistency across all related events.


PyAgentSpecTracing (Python materialization)
===========================================

The ``pyagentspec.tracing`` subpackage of ``pyagentspec`` provides convenient Pydantic-based models and interfaces so that:

- Producers (adapters, runtimes) can emit spans/events according to Agent Spec Tracing standards.
- Consumers (exporters, UIs) can receive and consume them via SpanProcessors.

Emitting traces (producer example)
----------------------------------

Here's an example of how adapters can emit traces (i.e., start and close Spans, emit Events)
extracted from the AgentNode implementation of the LangGraph's adapter in ``pyagentspec==26.1.0``.

.. code-block:: python

   with AgentExecutionSpan(name=f"AgentExecution - {agentspec_agent.name}", agent=agentspec_agent) as span:
       span.add_event(AgentExecutionStart(inputs=inputs))
       result = agent.invoke(inputs, config)
       outputs = result.outputs if hasattr(result, "outputs") else {}
       span.add_event(AgentExecutionEnd(outputs=outputs))

Consuming traces (consumer example)
-----------------------------------

.. code-block:: python

   class OpenTelemetrySpanProcessor(SpanProcessor):

       def __init__(self, sdk_processor: OtelSdkSpanProcessor):
           self._sdk_processor = sdk_processor

       def on_start(self, span: "Span") -> None:
           otel_span = self._to_otel_span(span)
           otel_span.start(start_time=span.start_time)
           self._sdk_processor.on_start(span=otel_span)

       def on_end(self, span: "Span") -> None:
           otel_span = self._to_otel_span(span)
           otel_span.end(end_time=span.end_time)
           self._sdk_processor.on_end(span=otel_span)

       def on_event(self, event: Event, span: Span) -> None:
           # Other processors may use this hook to stream events
           pass

       def startup(self) -> None:
           ...

       def shutdown(self) -> None:
           self._sdk_processor.shutdown

Interoperability examples
-------------------------

Tracing with LangGraph

.. code-block:: python

   from pyagentspec.adapters.langgraph import AgentSpecLoader
   from openinference_spanprocessor import ArizePhoenixSpanProcessor
   # Assuming this package implements a SpanProcessor that takes the Agent Spec Traces and sends them to a Phoenix Arize server

   agent_json = read_json_file("my/agentspec/agent.json")
   processor = ArizePhoenixSpanProcessor(mask_sensitive_information=False, project_name="agentspec-tracing-test")

   with Trace(name="agentspec_langgraph_demo", span_processors=[processor]) as trace:
       agent = AgentSpecLoader().load_json(agent_json)
       result = agent.invoke({"inputs": {}, "messages": []})

Tracing with WayFlow

.. code-block:: python

   from wayflowcore.agentspec import AgentSpecLoader
   from wayflowcore.agentspec.tracing import AgentSpecTracingEventListener
   from wayflowcore.events.eventlistener import register_event_listeners
   from openinference_spanprocessor import ArizePhoenixSpanProcessor

   agent_json = read_json_file("my/agentspec/agent.json")
   processor = ArizePhoenixSpanProcessor(mask_sensitive_information=False, project_name="agentspec-tracing-test")

   with register_event_listeners([AgentSpecTracingEventListener()]):
       with Trace(name="agentspec_wayflow_demo", span_processors=[processor]) as trace:
           agent = AgentSpecLoader().load_json(agent_json)
           conversation = agent.start_conversation()
           status = conversation.execute()


Security Considerations
=======================

Agent Spec Tracing inherits all security requirements from Agent Spec (see :doc:`../security`).
Additionally, tracing frequently includes potentially sensitive information (PII), including, but not limited to:

- LLM prompts and generated content
- Tool inputs/outputs
- Exception messages and stacktraces
- Conversation messages

Implementing a SpanProcessor
----------------------------

Key points:

* **Async / non-blocking** - keep the span processor off the critical path to avoid impacting agent's performance.
* **Robust error handling** - never raise from span processor methods; drop or queue on failure.
* **Back-pressure** - apply rate limits, size limits, or batch Spans and Events to avoid DoS on the collector.

Sensitive fields
----------------

Each event table above flags attributes that are considered sensitive.
Producers SHOULD mark and/or emit them using Agent Spec's Sensitive Field mechanism where
applicable; consumers (SpanProcessors) SHOULD:

- Mask or omit sensitive fields by default when exporting traces.
- Provide an explicit configuration to unmask for trusted environments.
- Avoid logging or exporting sensitive data inadvertently.

Guidelines:

- Attribute-level masking: redact entire values or apply strongly irreversible
  masking (e.g., replace content with fixed placeholders or hashes as policy dictates).
- Downstream mappers (e.g., OpenTelemetry exporters) MUST NOT downgrade masking guarantees.
- When masking affects correlation (e.g., truncating request_id), preserve minimal
  non-sensitive identifiers for linkage.

Design Notes and Best Practices
===============================

- Event emission ordering: Within a span, events SHOULD be in timestamp order.
- Time units: Use nanoseconds since epoch for timestamps and start/end times
  for consistency with common tracing systems.
- Nesting: Prefer nesting spans to represent sub-operations (e.g., NodeExecutionSpan
  under FlowExecutionSpan, ToolExecutionSpan under AgentExecutionSpan).
- Exceptions: Emit ExceptionRaised with type/message/stacktrace and consider adding
  it before ending the current span or on a dedicated error span, depending on runtime design.


FAQ and Open Questions
======================

Naming alignment with observability
-----------------------------------

This specification uses tracing terminology common in OpenTelemetry (Trace,
Span, Event, SpanProcessor) to leverage community familiarity.

Environment context
-------------------

This version focuses on agentic execution tracing. Future versions may add
execution-environment spans or include environment metadata on Trace.

References and Cross-links
==========================

- Agent Spec language specification: :doc:`language_spec_nightly`
- Security guidelines: :doc:`../security`
