==============================
How to Build a Swarm of Agents
==============================

The Swarm pattern is a type of agentic pattern that takes inspiration from `Swarm intelligence <https://en.wikipedia.org/wiki/Swarm_intelligence>`_.
It is often observed in biological systems such as ant colonies, bee hives, and bird flocks.
In this agentic pattern, each agent is assigned a specific responsibility and can delegate tasks to other specialized agents to improve overall performance.

**When to use the Swarm pattern?**

Compared to the **hierarchical pattern**, the communication in :ref:`Swarm <swarm>` pattern reduces the number of LLM calls
as showcased in the diagram below.

.. image:: ../_static/howto/hierarchical_vs_swarm.svg
   :align: center
   :scale: 70%
   :alt: How the Swarm pattern compares to hierarchical multi-agent pattern

In the **hierarchical pattern**, a route User → Agent K → User will require:

1. All intermediate agents to call the correct sub-agent to go down to the Agent K.
2. The Agent K to generate its answer.
3. All intermediate agents to relay the answer back to the user.

In the **swarm pattern**, a route User → Agent K → User will require:

1. The first agent to call or handoff the conversation the Agent K (provided that the developer allows the connection between the two agents).
2. The Agent K to generate its answer.
3. The first agent to relay the answer (only when NOT using handoff; with handoff the Agent K **replaces** the first agent and is thus directly communicating with the human user)

-------

This guide presents an example of a simple Swarm of agents applied to a medical use case.

.. image:: ../_static/howto/swarm_example.svg
   :align: center
   :scale: 90%
   :alt: Example of a Swarm agent pattern for medical application

This guide will walk you through the following steps:

1. Define the configuration for an LLM model
2. Define tools for the agents
3. Define agents equipped with tools
4. Define a Swarm using the defined agents

It also covers how to enable ``handoff`` when building the ``Swarm``.

Basic implementation
====================

1. Define the LLM model
-----------------------

The decision mechanism of Agents is powered by a Large Language Model.
Defining the agent with Agent Spec requires to pass the configuration for the LLM.
There are several options such as using OCI GenAI Service or self hosting a model with vLLM.

Start by defining the LLM configuration to be shared across all agents.

.. include:: ../_components/llm_config_tabs.rst

2. Define tools
---------------

.. literalinclude:: ../code_examples/howto_swarm.py
    :language: python
    :start-after: .. start-tools
    :end-before: .. end-tools

API Reference: :ref:`ServerTool <servertool>`

.. note::
    To require user confirmation for a tool, set ``requires_confirmation=True`` (see :ref:`Tool <tool>`).
    This signals that execution environments should require user approval before running the tool, which is useful
    for tools performing sensitive actions.

3. Define agents equipped with tools
------------------------------------

General Practitioner Agent
^^^^^^^^^^^^^^^^^^^^^^^^^^

The first agent the user interacts with is the General Practitioner Agent.

This agent is equipped with the symptoms checker tool, and can interact with the **Pharmacist Agent**
as well as the **Dermatologist Agent**.


.. literalinclude:: ../code_examples/howto_swarm.py
    :language: python
    :start-after: .. start-first-agent
    :end-before: .. end-first-agent

API Reference: :ref:`Agent <agent>`

Pharmacist Agent
^^^^^^^^^^^^^^^^

The Pharmacist Agent is equipped with the tool to obtain medication information.
This agent cannot initiate a discussion with the other agents in the Swarm.

.. literalinclude:: ../code_examples/howto_swarm.py
    :language: python
    :start-after: .. start-second-agent
    :end-before: .. end-second-agent

Dermatologist Agent
^^^^^^^^^^^^^^^^^^^

The final agent in the Swarm is the Dermatologist agent which is equipped with a tool to query a skin condition knowledge base.
This agent can initiate a discussion with the **Pharmacist Agent**.

.. literalinclude:: ../code_examples/howto_swarm.py
    :language: python
    :start-after: .. start-third-agent
    :end-before: .. end-third-agent

4. Define a Swarm
-----------------

The Swarm has two main parameters:

- The ``first_agent`` — the initial agent the user interacts with (in this example, the General Practitioner Agent).
- A list of relationships between agents.

Additionally, the list of "relationships" between the agents must be defined.

Each relationship is defined as a tuple of Caller Agent and Recipient Agent.

In this example, the General Practitioner Doctor Agent can initiate discussions with both the Pharmacist and the Dermatologist.
The Dermatologist can also initiate discussions with the Pharmacist.

When invoked, each agent can either respond to its caller (a human user or another agent) or choose to initiate a discussion with
another agent if they are given the capability to do so.

.. literalinclude:: ../code_examples/howto_swarm.py
    :language: python
    :start-after: .. start-swarm
    :end-before: .. end-swarm

API Reference: :ref:`Swarm <swarm>`

5. Export the Agent Spec configuration
--------------------------------------

The Agent Spec configuration is generated in JSON format.
These configurations can be loaded and executed in Agent Spec-compatible systems such as the WayFlow runtime.
See, for example, :doc:`How to Execute Agent Spec Configurations with WayFlow <howto_execute_agentspec_with_wayflow>`.

.. literalinclude:: ../code_examples/howto_swarm.py
    :language: python
    :start-after: .. start-serialization
    :end-before: .. end-serialization

API Reference: :ref:`AgentSpecSerializer <serialize>`

Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_swarm.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_swarm.yaml
            :language: yaml


Enabling handoff in the Swarm
=============================

By default, communication in the ``Swarm`` pattern is done with agent sending blocking messages/requests to each other.

The ``handoff`` mechanism provides an alternative: when enabled, agents can handoff the conversation — that is, transfer the message history between
the user and one agent to another agent within the Swarm.
Agents can still communicate with each other as they do when ``handoff=False``.

A key benefit of using ``handoff`` is reduced response latency.
Talking to other agents increases the "distance" between the human user and the current agent.
Transferring a conversation to another agent keeps this distance unchanged (in other words, the agent interacting with the user is different, but the user is still the same).

To enable ``handoff`` in a Swarm, set the ``handoff`` parameter to ``True``.

.. literalinclude:: ../code_examples/howto_swarm.py
    :language: python
    :start-after: .. start-swarm-with-handoff
    :end-before: .. end-swarm-with-handoff

Recap
=====

This guide covered how to define a swarm of agents with and without handoff in Agent Spec.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_swarm.py
        :language: python
        :linenos:
        :start-after: .. define-llm
        :end-before: .. end-serialization

Next steps
==========

Having learned how to define a swarm, you may now proceed to :doc:`how to use the WayFlow runtime to execute it <howto_execute_agentspec_with_wayflow>`.
