.. _howtoguidelanding:

How-to Guides
=============

Here you will find answers to "How do I..." questions.
The proposed guides are goal-oriented and concrete, as they are meant to help you complete a specific task.
Each code example in these how-to guides is self-contained and can be run with `pyagentspec`.

* For conceptual explanations about Agent Spec and its components, see :doc:`Agent Spec Specification <../agentspec/index>`.
* For installation, see the :doc:`Installation Guide <../installation>`.
* For comprehensive descriptions of every class and function, see the :doc:`API Reference <../api/index>`.

Building Assistants
-------------------

Agent Spec provides a range of features to help you build two types of assistants: ``Agents`` and ``Flows``.
These how-to guides demonstrate how to use the main Agent Spec features to create and customize your assistants.

.. toctree::
   :maxdepth: 1

   How to build a simple ReAct Agent <howto_agents>
   How to connect MCP tools to assistants <howto_mcp>
   How to Develop a Flow with Conditional Branches <howto_flow_with_conditional_branches>
   How to Develop an Agent with Remote Tools <howto_agent_with_remote_tools>
   Do Map and Reduce Operations in Flows <howto_mapnode>
   How to Build an Orchestrator-Workers Agents Pattern <howto_orchestrator_agent>
   Specify the Generation Configuration when Using LLMs <howto_generation_config>
   Use LLM from Different LLM Sources and Providers <howto_llm_from_different_providers>
   Use OCI Generative AI Agents <howto_ociagent>
   Build an A2A Agent <howto_a2aagent>
   Build a Swarm of Agents <howto_swarm>
   Build a Manager-Worker Multi-Agent System <howto_managerworkers>
   Build Flows with Structured LLM Generation <howto_structured_generation>
   Run Multiple Flows in Parallel <howto_parallelflownode>

Additionally, we link the how-to guides offered by the `WayFlow documentation <https://github.com/oracle/wayflow/>`_.
WayFlow is a reference runtime of Agent Spec, and among its how-to guides it proposes
several examples of how to create common patterns using WayFlow and export them in Agent Spec.

Executing Assistants
--------------------

Agent Spec is framework-agnostic, and the assistants built using Agent Spec can be executed using any Agent Spec runtime.
These how-to guides provide examples of how to run your Assistant using specific runtimes.

.. toctree::
   :maxdepth: 1

   How to Execute Agent Spec Configuration with WayFlow <howto_execute_agentspec_with_wayflow>
   How to Execute Agent Spec Across Frameworks <howto_execute_agentspec_across_frameworks>


External Features
-----------------

``pyagentspec`` enables the use of :ref:`custom components in Agent Spec <plugin-ecosystem>`
configuration with the :ref:`Plugin System <componentserializationplugin>`. These how-to guides
provide examples of features that can be implemented with the plugin system.

.. toctree::
   :maxdepth: 1

   How to use custom components with the Plugin System <howto_plugin>
