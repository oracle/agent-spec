.. _docs_landing_page:


Open Agent Specification (Agent Spec)
=====================================

Open Agent Specification (Agent Spec) is a portable, platform-agnostic configuration language that allows Agents and Agentic Systems to be described with high fidelity.

It defines the conceptual building blocks—called components—that make up agents in typical agent-based systems.
This includes the properties that configure each component and the semantics that govern their behavior.
Agent Spec is based on two main standalone components:

* Agents (e.g., ReAct agents), which are conversational agents or agent modules;
* Flows (e.g., business processes), which can invoke agents and perform workflow-like processes.

Runtimes implement Agent Spec components to enable execution within agentic frameworks or libraries.
Agent Spec is designed to be supported by SDKs in various programming languages (such as Python),
allowing agents to be serialized/deserialized to common formats like JSON or YAML,
or instantiated from object representations—with guarantees of conformance to the Agent Spec specification.
More information, including the motivation and complete specification, is available in the
:doc:`dedicated section <agentspec/index>` of Agent Spec documentation.

PyAgentSpec
-----------

To facilitate the process of building framework-agnostic agents programmatically, Agent Spec SDKs can be
implemented in various programming languages. These SDKs are expected to provide two core capabilities:

* Building Agent Spec component abstractions by implementing the relevant interfaces, in full compliance with the
  Agent Spec specification;
* Importing and exporting these abstraction from and to their serialized representations (e.g., JSON).

As part of the Agent Spec project, we provide a Python SDK called PyAgentSpec.
It enables users to build Agent Spec-compliant agents in Python.
Using PyAgentSpec, you can define assistants by composing components that mirror the interfaces and behavior specified
by Agent Spec, and export them to different formats.

Quick Start
-----------

To install PyAgentSpec:

.. only:: stable

   Use the following command to install `pyagentspec` (compatible with Python 3.10+):

   .. code-block:: bash
      :substitutions:

      pip install "|package_name|==|stable_release|"

.. only:: dev

   To install the development version of `pyagentspec` (on Python 3.10+) from source, run:

   .. code-block:: bash
      :substitutions:

      bash install-dev.sh


For a complete list of supported Python versions and platforms, see the :doc:`installation guide<installation>`.

Once PyAgentSpec is installed, you can try it out with the following example:

.. literalinclude:: code_examples/pyagentspec_quickstart.py
   :language: python
   :start-after: .. full-code:
   :end-before: .. end-full-code

Next Steps
----------

- **Familiarize yourself with the basics – How-to Guides**

   * Begin with :doc:`How to Build a Simple Agent <howtoguides/howto_agent_with_remote_tools>`.
   * Then explore :doc:`How to Build a Simple Flow <howtoguides/howto_flow_with_conditional_branches>`.

- **Explore the API documentation**

   Review the :doc:`API documentation <api/index>` to learn about the available classes, methods, and functions in the library.


Security Considerations
-----------------------

LLM-based assistants and flows require careful security assessment before deployment.
See the :doc:`Security Considerations <security>` page for guidelines and best practices.

Need Help?
----------

Reach out to the :doc:`Agent Spec team <contributing>` to ask questions, request features, or share suggestions.

Browse the :doc:`Frequently Asked Questions <faqs>` for find answers to common questions.

Agent Spec is developed jointly between Oracle Cloud Infrastructure and Oracle Labs teams.

.. toctree::
   :maxdepth: 2
   :caption: Agent Spec
   :hidden:

   Agent Spec Specification <agentspec/index>

.. toctree::
   :maxdepth: 2
   :caption: Essentials
   :hidden:

   Installation <installation>
   How-to guides <howtoguides/index>
   API Reference <api/index>


.. toctree::
   :maxdepth: 2
   :caption: Adapters
   :hidden:

   LangGraph <adapters/langgraph/index>
   WayFlow <adapters/wayflow/index>
   AutoGen <adapters/autogen/index>
   Agent Framework <adapters/agent-framework/index>
   OpenAI Agents <adapters/openai/index>


.. toctree::
   :maxdepth: 1
   :caption: Ecosystem
   :hidden:

   Integrations <ecosystem/integrations>
   Collaborations <ecosystem/collaborations>


.. toctree::
   :maxdepth: 1
   :caption: Resources
   :hidden:

   Glossary <misc/glossary>
   Reference Sheet <misc/reference_sheet>
   Security Considerations <security>
   Frequently Asked Questions <faqs>
   Contributing <contributing>
   Release Notes <changelog>
