Tracing
=======

This page presents all APIs and classes related to tracing in PyAgentSpec.


Trace
-----

.. _trace:
.. autoclass:: pyagentspec.tracing.trace.Trace


SpanProcessor
-------------

.. _spanprocessor:
.. autoclass:: pyagentspec.tracing.spanprocessor.SpanProcessor


Spans
-----

.. _span:
.. autoclass:: pyagentspec.tracing.spans.span.Span

.. _rootspan:
.. autoclass:: pyagentspec.tracing.spans.root.RootSpan

.. _agentexecutionspan:
.. autoclass:: pyagentspec.tracing.spans.agent.AgentExecutionSpan

.. _flowexecutionspan:
.. autoclass:: pyagentspec.tracing.spans.flow.FlowExecutionSpan

.. _nodeexecutionspan:
.. autoclass:: pyagentspec.tracing.spans.node.NodeExecutionSpan

.. _toolexecutionspan:
.. autoclass:: pyagentspec.tracing.spans.tool.ToolExecutionSpan

.. _llmgenerationspan:
.. autoclass:: pyagentspec.tracing.spans.llm.LlmGenerationSpan

.. _managerworkersexecutionspan:
.. autoclass:: pyagentspec.tracing.spans.managerworkers.ManagerWorkersExecutionSpan

.. _swarmexecutionspan:
.. autoclass:: pyagentspec.tracing.spans.swarm.SwarmExecutionSpan


Events
------

.. _event:
.. autoclass:: pyagentspec.tracing.events.event.Event

Agent Events
~~~~~~~~~~~~

.. _agentexecutionstart:
.. autoclass:: pyagentspec.tracing.events.agent.AgentExecutionStart

.. _agentexecutionend:
.. autoclass:: pyagentspec.tracing.events.agent.AgentExecutionEnd

Flow Events
~~~~~~~~~~~

.. _flowexecutionstart:
.. autoclass:: pyagentspec.tracing.events.flow.FlowExecutionStart

.. _flowexecutionend:
.. autoclass:: pyagentspec.tracing.events.flow.FlowExecutionEnd

.. _nodeexecutionstart:
.. autoclass:: pyagentspec.tracing.events.node.NodeExecutionStart

.. _nodeexecutionend:
.. autoclass:: pyagentspec.tracing.events.node.NodeExecutionEnd

Tool Events
~~~~~~~~~~~

.. _toolexecutionrequest:
.. autoclass:: pyagentspec.tracing.events.tool.ToolExecutionRequest

.. _toolexecutionresponse:
.. autoclass:: pyagentspec.tracing.events.tool.ToolExecutionResponse

.. _toolconfirmationrequest:
.. autoclass:: pyagentspec.tracing.events.tool.ToolConfirmationRequest

.. _toolconfirmationresponse:
.. autoclass:: pyagentspec.tracing.events.tool.ToolConfirmationResponse

LLM Events
~~~~~~~~~~

.. _toolcall:
.. autoclass:: pyagentspec.tracing.events.llmgeneration.ToolCall

.. _message:
.. autoclass:: pyagentspec.tracing.messages.message.Message

.. _llmgenerationrequest:
.. autoclass:: pyagentspec.tracing.events.llmgeneration.LlmGenerationRequest

.. _llmgenerationchunkreceived:
.. autoclass:: pyagentspec.tracing.events.llmgeneration.LlmGenerationChunkReceived

.. _llmgenerationresponse:
.. autoclass:: pyagentspec.tracing.events.llmgeneration.LlmGenerationResponse

Multi-agent Events
~~~~~~~~~~~~~~~~~~

.. _managerworkersexecutionstart:
.. autoclass:: pyagentspec.tracing.events.managerworkers.ManagerWorkersExecutionStart

.. _managerworkersexecutionend:
.. autoclass:: pyagentspec.tracing.events.managerworkers.ManagerWorkersExecutionEnd

.. _swarmexecutionstart:
.. autoclass:: pyagentspec.tracing.events.swarm.SwarmExecutionStart

.. _swarmexecutionend:
.. autoclass:: pyagentspec.tracing.events.swarm.SwarmExecutionEnd

Other Events
~~~~~~~~~~~~

.. _exceptionraised:
.. autoclass:: pyagentspec.tracing.events.exception.ExceptionRaised

.. _humaninthelooprequest:
.. autoclass:: pyagentspec.tracing.events.humanintheloop.HumanInTheLoopRequest

.. _humanintheloopresponse:
.. autoclass:: pyagentspec.tracing.events.humanintheloop.HumanInTheLoopResponse
