Agent Spec Adapters
===================

Using adapters is the recommended way of integrating an agentic framework runtime.
Ideally, an adapter should programmatically translate the representation of the Agent Spec components
into the equivalent solution, as per each framework's definition, and return an object that developers can run.

This page presents all APIs and classes related to Agent Spec Adapters.

LangGraph
---------

.. _adapters_langgraph_exporter:
.. autoclass:: pyagentspec.adapters.langgraph.AgentSpecExporter

.. _adapters_langgraph_loader:
.. autoclass:: pyagentspec.adapters.langgraph.AgentSpecLoader

CrewAI
------

.. _adapters_crewai_exporter:
.. autoclass:: pyagentspec.adapters.crewai.AgentSpecExporter

.. _adapters_crewai_loader:
.. autoclass:: pyagentspec.adapters.crewai.AgentSpecLoader

AutoGen
-------

.. _adapters_autogen_exporter:
.. autoclass:: pyagentspec.adapters.autogen.AgentSpecExporter

.. _adapters_autogen_loader:
.. autoclass:: pyagentspec.adapters.autogen.AgentSpecLoader

WayFlow
-------

.. _adapters_wayflow_exporter:
.. autoclass:: pyagentspec.adapters.wayflow.AgentSpecExporter

.. _adapters_wayflow_loader:
.. autoclass:: pyagentspec.adapters.wayflow.AgentSpecLoader

Microsoft Agent Framework
-------------------------

.. _adapters_agent_framework_exporter:
.. autoclass:: pyagentspec.adapters.agent_framework.AgentSpecExporter

.. _adapters_agent_framework_loader:
.. autoclass:: pyagentspec.adapters.agent_framework.AgentSpecLoader
