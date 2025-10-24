=================================================
How to Build a Manager-Worker Multi-Agent System
=================================================

With the advent of increasingly powerful Large Language Models (LLMs), multi-agent systems are becoming more relevant
and are expected to be particularly valuable in scenarios requiring high-levels of autonomy and/or processing
of diverse sources of information.

There are various types of multi-agent systems, each serving different purposes and applications.
Some notable examples include hierarchical structures, agent swarms, and mixtures of agents.

A **hierarchical multi-agent** system (also known as **manager-worker** or **orchestrator-worker** pattern) is a multi-agent pattern
in which a central manager coordinates one or more worker agents by assigning tasks, and aggregating results.

**When to use the Manager-Worker pattern?**

Manager-Worker pattern is particularly suitable when tasks can be decomposed into specialized subtasks that benefit from dedicated agents with distinct expertise or tools.
Compared to the Swarm pattern, the manager-worker pattern provides centralized coordination and explicit control flow between agents,
making it more effective for workflows that require maintaining global context and aggregated results.

In the hierarchical pattern, a route User → Manager → Worker → Manager → User will require:

- The manager to analyze the user request and decide which worker agent should handle it.
- The selected worker agent to process the assigned subtask.
- The worker to return its output to the manager.
- The manager to consolidate and deliver the final response back to the user.

-------

This guide demonstrates an example of a hierarchical multi-agent system for customer service automation, where a Customer Service Manager agent manages a team
of two specialized agents — the Refund Specialist for processing refunds and the Satisfaction Surveyor for collecting feedback.

It will walk you through the following steps:

1. Define the configuration of an LLM model
2. Define expert agents equipped with tools
3. Define a manager agent
4. Define a ``ManagerWorkers`` of the defined agents

Basic implementation
====================

1. Define the LLM model
-----------------------

The decision mechanism of Agents is powered by a Large Language Model.
Defining the agent with Agent Spec requires to pass the configuration for the LLM.
There are several options such as using OCI GenAI Service or self hosting a model with vLLM.

Start by defining the LLM configuration to be shared across all agents.

.. include:: ../_components/llm_config_tabs.rst

2. Define expert agents
-----------------------

Refund specialist agent
^^^^^^^^^^^^^^^^^^^^^^^

The refund specialist agent is equipped with two tools.

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Specialist_tools
    :end-before: .. end-##_Specialist_tools

API Reference: :ref:`ServerTool <servertool>`

The first tool is used to check whether a given order is eligible for a refund,
while the second is used to process the specific refund.

The system prompt is defined as follows:

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Specialist_prompt
    :end-before: .. end-##_Specialist_prompt

Building the agent:

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Specialist_agent
    :end-before: .. end-##_Specialist_agent

API Reference: :ref:`Agent <agent>`

Statisfaction surveyor agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The statisfaction surveyor agent is equipped with one tool.

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Surveyor_tools
    :end-before: .. end-##_Surveyor_tools

The ``record_survey_response`` tool is simulating the recording of
user feedback data.

System prompt:

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Surveyor_prompt
    :end-before: .. end-##_Surveyor_prompt

Building the agent:

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Surveyor_agent
    :end-before: .. end-##_Surveyor_agent

3. Define the manager agent
---------------------------

In the built-in ManagerWorkers component, we allow passing an Agent
as the group manager. Therefore, we just need to define an agent as usual.

In this example, our manager agent will be a Customer Service Manager.

System prompt:

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Manager_prompt
    :end-before: .. end-##_Manager_prompt

Building the agent:

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Manager_agent
    :end-before: .. end-##_Manager_agent

4. Define the ManagerWorkers of Agents
---------------------------------------

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Managerworkers_pattern
    :end-before: .. end-##_Managerworkers_pattern

API Reference: :ref:`ManagerWorkers <managerworkers>`

The ManagerWorkers has two main parameters:

- ``group_manager``
  The agent that is used as the group manager, responsible for coordinating and assigning tasks to the workers.

- ``workers`` - List of agents
  These agents serve as the workers within the group and are coordinated by the manager agent.

  - Worker agents cannot interact with the end user directly.
  - When invoked, each worker can leverage its equipped tools to complete the assigned task and report the result back to the group manager.

Agent Spec Serialization
========================

You can export the assistant configuration using the :ref:`AgentSpecSerializer <serialize>`.

.. literalinclude:: ../code_examples/howto_managerworkers.py
    :language: python
    :start-after: .. start-##_Export_serialization
    :end-before: .. end-##_Export_serialization

Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_managerworkers.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_managerworkers.yaml
            :language: yaml

Recap
=====

This guide covered how to define a manager-workers of agents in Agent Spec.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_managerworkers.py
        :language: python
        :linenos:

Next steps
==========

Having learned how to define a manager-workers, you may now proceed to :doc:`how to use the WayFlow runtime to execute it <howto_execute_agentspec_with_wayflow>`.
