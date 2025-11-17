===================================================
How to Build an Orchestrator-Workers Agents Pattern
===================================================

.. admonition:: Prerequisites

    This guide assumes you have already defined either a Flow or an Agent using PyAgentSpec and exported its Agent Spec configuration.

    - :doc:`Flows <howto_flow_with_conditional_branches>`
    - :doc:`Agents <howto_agent_with_remote_tools>`

This guide demonstrates how to:

1. Define the configuration for an LLM model
2. Define a tool to retrieve additional information about a user
3. Define an orchestrator agent
4. Define a set of worker agents
5. Wrap all the components in a flow
6. Export the Agent Spec configuration of the flow

This how-to guide demonstrates how to build an **Oracle-themed IT assistant** using an orchestrator-workers pattern.
The orchestrator attempts to understand the user's problem and, based on its topic—network, device, or account—redirects the conversation to an agent which has expertise in the topic.

The assistant is implemented as a **Flow**.
This Flow takes the username of the user as input and starts by retrieving additional information about the user via a ``ServerTool`` call.
Then the orchestrator starts the conversation with the user, identifies the topic of the problem, and redirects the conversation to the appropriate expert agent.
Once the problem is solved by the expert, the conversation goes back to the orchestrator to deal with further issues, if needed.

Basic implementation
====================

1. Define the LLM model
-----------------------

The decision mechanism of Agents is powered by a Large Language Model.
Defining the agent with Agent Spec requires to pass the configuration for the LLM.
There are several options such as using OCI GenAI Service or self hosting a model with vLLM.

Start by defining the LLM configuration to be shared across all agents.
This example uses a vLLM instance running Llama3.3 70B.

.. include:: ../_components/llm_config_tabs.rst

2. Define a tool
----------------

Define a tool responsible for retrieving additional information about the user.
This is a simple ``ServerTool`` that accepts a username as input and returns a single string containing user-related information.

.. literalinclude:: ../code_examples/orchestrator_agent.py
    :language: python
    :start-after: .. start-tool:
    :end-before: .. end-tool:

3. Define an orchestrator agent
-------------------------------

The first agent to define is the orchestrator.
As anticipated in the introduction, the goal of this agent is to understand what is the
topic of the user's problem, so that it can redirect the conversation to the appropriate expert agent.

In addition to identifying the problem topic, the orchestrator is also responsible for producing a summary of the conversation.
According to the :doc:`Agent Spec specification <../agentspec/index>`, the conversations with sub-agents are isolated from one another.
Therefore, relevant parts of the conversation with the orchestrator are passed along to expert agents.
This ensures that any user-provided details remain available throughout the interaction.

.. literalinclude:: ../code_examples/orchestrator_agent.py
    :language: python
    :start-after: .. start-orchestrator-agent:
    :end-before: .. end-orchestrator-agent:

4. Define a set of worker agents
--------------------------------

Next define a set of expert agents—one for each topic: **network**, **device**, and **account**.
Each agent shares the same basic prompt structure, but provides specific information regarding the topic (e.g., through RAG tools).
This would improve the quality of the overall assistant.

.. literalinclude:: ../code_examples/orchestrator_agent.py
    :language: python
    :start-after: .. start-expert-agents:
    :end-before: .. end-expert-agents:

5. Wrap all the components in a flow
------------------------------------

With all internal components defined, the next step is to construct the flow.
This involves building the corresponding nodes and connecting them to define both the execution order and the data dependencies.

Nodes
^^^^^

Define the nodes that compose the flow.
One node is required for each previously defined component:

- A tool node for gathering user information
- An agent node for the orchestrator
- One agent node per expert worker (three in total)

Additionally, include a ``StartNode`` and an ``EndNode`` to mark the entry and exit points of the flow.
A ``BranchingNode`` is also required to route the conversation to the appropriate expert agent based on the topic identified by the orchestrator.

.. literalinclude:: ../code_examples/orchestrator_agent.py
    :language: python
    :start-after: .. start-nodes:
    :end-before: .. end-nodes:

Control flow edges
^^^^^^^^^^^^^^^^^^

Now define the control flow edges to specify the execution order of the nodes in the flow.

.. literalinclude:: ../code_examples/orchestrator_agent.py
    :language: python
    :start-after: .. start-control-edges:
    :end-before: .. end-control-edges:


Data flow edges
^^^^^^^^^^^^^^^

Next the data connections between inputs and outputs.

.. literalinclude:: ../code_examples/orchestrator_agent.py
    :language: python
    :start-after: .. start-data-edges:
    :end-before: .. end-data-edges:

Flow
^^^^

Finally, combine all components—nodes and edges—to construct the complete Flow.

.. literalinclude:: ../code_examples/orchestrator_agent.py
    :language: python
    :start-after: .. start-flow:
    :end-before: .. end-flow:

Agent Spec Serialization
========================

You can export the assistant configuration using the :ref:`AgentSpecSerializer <serialize>`.


.. literalinclude:: ../code_examples/orchestrator_agent.py
    :language: python
    :start-after: .. start-serialization:
    :end-before: .. end-serialization:


Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/agentspec_oracle_it_assistant.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/agentspec_oracle_it_assistant.yaml
            :language: yaml

Recap
=====

This how-to guide covered how to:

1. Define the configuration for an LLM model
2. Define a tool to retrieve additional information about a user
3. Define an orchestrator agent
4. Define a set of worker agents
5. Wrap all the components in a flow
6. Export the Agent Spec configuration of the flow

.. collapse:: Below is the complete code from this guide.

  .. literalinclude:: ../code_examples/orchestrator_agent.py
    :language: python
    :linenos:
    :start-after: .. start-full-code
    :end-before: .. end-full-code

Next steps
==========

Having learned how to build an orchestrator-assistant, you may now proceed to :doc:`How to Execute Agent Spec Across Frameworks <howto_execute_agentspec_across_frameworks>` and try to run this assistant yourself.
