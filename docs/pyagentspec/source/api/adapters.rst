Agent Spec Adapters
===================

Using adapters is the recommended way of integrating an agentic framework runtime.
Ideally, an adapter should programmatically translate the representation of the Agent Spec components
into the equivalent solution, as per each framework's definition, and return an object that developers can run.

This page presents all APIs and classes related to Agent Spec Adapters.


CrewAI
------

.. _adapters_crewai_exporter:
.. autoclass:: pyagentspec.adapters.crewai.AgentSpecExporter

.. _adapters_crewai_loader:
.. autoclass:: pyagentspec.adapters.crewai.AgentSpecLoader


LangGraph
---------

The LangGraph adapter is available at `langgraphagentspecadapter <https://github.com/oracle/agent-spec/tree/main/adapters/langgraphagentspecadapter>`_.

AutoGen
-------

The AutoGen adapter is available at `autogenagentspecadapter <https://github.com/oracle/agent-spec/tree/main/adapters/autogenagentspecadapter>`_.
