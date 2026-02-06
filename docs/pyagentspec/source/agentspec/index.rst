.. _agentspec:

=====================================
Open Agent Specification (Agent Spec)
=====================================

Agent Spec is intended to be a portable, platform-agnostic configuration language that allows Agents
and Agentic Systems to be described with sufficient fidelity.
It defines the conceptual objects, called components, that compose Agents in typical Agent systems,
including the properties that determine the components' configuration, and their respective semantics.
Agent Spec is based on two main runnable standalone components:

* Agents (e.g., ReAct), that are conversational agents or agent components;
* Flows (e.g., business process) that are structured, workflow-based processes.

Runtimes implement the Agent Spec components for execution with Agentic frameworks or libraries.
Agent Spec would be supported by SDKs in various languages (e.g. Python) to be able to serialize/deserialize Agents to yaml,
or create them from object representations with the assurance of conformance to the specification.

You can download the Agent Spec technical report at the following :download:`link <../_static/agentspec_technical_report.pdf>`.

.. only:: stable

    .. toctree::
        :maxdepth: 2

        Introduction, motivation & vision <intro_and_motivation>
        Language specification (v26.1.0 latest) <language_spec_26_1_0>
        Language specification (v25.4.1) <language_spec_25_4_1>
        Positioning in the agentic ecosystem <positioning>
        Tracing <tracing>
        Evaluation <evaluation>

.. only:: dev

    .. toctree::
        :maxdepth: 2

        Introduction, motivation & vision <intro_and_motivation>
        Language specification (under development) <language_spec_nightly>
        Language specification (v26.1.0 latest release) <language_spec_26_1_0>
        Language specification (v25.4.1) <language_spec_25_4_1>
        Positioning in the agentic ecosystem <positioning>
        Tracing <tracing>
        Evaluation <evaluation>
