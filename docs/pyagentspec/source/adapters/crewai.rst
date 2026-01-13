.. _crewaiadapter:

============================
Agent Spec Adapters - CrewAI
============================


.. figure:: ../_static/icons/crewai-adapter.jpg
    :align: center
    :scale: 18%
    :alt: Agent Spec adapter for CrewAI

    ↑ With the **Agent Spec adapter for CrewAI**, you can easily import agents from external frameworks using Agent Spec and run them with CrewAI.

*CrewAI enables the design of collaborative AI agents and workflows, incorporating guardrails, memory,
and observability for production-ready multi-agent systems.*


Get started
===========

To get started, set up your Python environment (Python 3.10 to 3.13 required),
and then install the PyAgentSpec package with the CrewAI extension.


.. code-block:: bash

    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install "pyagentspec[crewai]"


You are now ready to use the adapter:

- Run Agent Spec configurations with CrewAI (see more details :ref:`below <spectocrewai>`)
- Convert CrewAI agents to Agent Spec (see more details :ref:`below <crewaitospec>`)



.. _spectocrewai:

Run Agent Spec configurations with CrewAI
=========================================


.. literalinclude:: ../code_examples/adapter_crewai_quickstart.py
    :language: python
    :start-after: .. start-agentspec_to_runtime
    :end-before: .. end-agentspec_to_runtime


.. _crewaitospec:

Convert CrewAI agents to Agent Spec
===================================

.. literalinclude:: ../code_examples/adapter_crewai_quickstart.py
    :language: python
    :start-after: .. start-runtime_to_agentspec
    :end-before: .. end-runtime_to_agentspec
