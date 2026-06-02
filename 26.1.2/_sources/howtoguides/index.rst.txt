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
   Use OCI Generative AI Agents <howto_ociagent>
   Use an A2A Agent <howto_a2aagent>
   Build a Swarm of Agents <howto_swarm>
   Build a Manager-Worker Multi-Agent System <howto_managerworkers>
   Build Flows with Structured LLM Generation <howto_structured_generation>
   Run Multiple Flows in Parallel <howto_parallelflownode>
   Build Flows with the Flow Builder <howto_flowbuilder>
   Catch Exceptions in Flows <howto_catchexception>

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

Configuration and State Management
----------------------------------

These guides demonstrate how to configure components in Agent Spec.

.. toctree::
   :maxdepth: 1

   Use LLM from Different LLM Sources and Providers <howto_llm_from_different_providers>
   Specify the Generation Configuration when Using LLMs <howto_generation_config>
   How to Use Disaggregated Config <howto_disaggregated_config>
   How to Use Datastores <howto_datastores>
   How to Use Summarization Transforms <howto_summarization_transforms>


Ecosystem
---------

With expanding integrations and community partnerships, Agent Spec streamlines building, running, and monitoring agents across heterogeneous environments.

For more information about the Agent Spec ecosystem, see :ref:`integrations <integrations>` and :ref:`collaborations <collaborations>`.

.. toctree::
   :maxdepth: 1

   How to Use AG-UI with Agent Spec <howto_ag_ui>


External Features
-----------------

``pyagentspec`` enables the use of :ref:`custom components in Agent Spec <plugin-ecosystem>`
configuration with the :ref:`Plugin System <componentserializationplugin>`. These how-to guides
provide examples of features that can be implemented with the plugin system.

.. toctree::
   :maxdepth: 1

   How to use custom components with the Plugin System <howto_plugin>


Evaluation
----------

Agent Spec Eval standardizes how to evaluate agentic systems in a framework-agnostic way.

.. toctree::
   :maxdepth: 1

   How to evaluate with Agent Spec Eval <howto_evaluation>
