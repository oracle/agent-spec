=================================
How to Build A2A Agents
=================================

`A2A Protocol <https://a2a-protocol.org/latest/>`_ is an open standard that defines how two agents can communicate 
with each other. It covers both the serving and consumption aspects of agent interaction.

In this guide, you will learn how to build an A2A agent with the :ref:`A2AAgent <a2aagent>` class from the ``pyagentspec`` package.

Basic Usage
===========

To get started with an A2A agent, you need the URL of the remote server agent you wish to connect to. 
Once you have this information, creating your A2A agent is straightforward and can be done in just a few lines of code:

.. literalinclude:: ../code_examples/howto_a2aagent.py
    :language: python
    :start-after: .. start-##_Creating_the_agent
    :end-before: .. end-##_Creating_the_agent

Note that the ``A2AAgent`` is an extension of ``RemoteAgent`` in Agent Spec, which is considered an ``AgenticComponent``.
It follows that A2A agents can be used in ``AgentNodes`` inside Agent Spec flows.

Agent Spec Serialization
========================

You can export the agent configuration using the :ref:`AgentSpecSerializer <serialize>`.

.. literalinclude:: ../code_examples/howto_a2aagent.py
    :language: python
    :start-after: .. start-export-config-to-agentspec
    :end-before: .. end-export-config-to-agentspec


Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_a2aagent.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_a2aagent.yaml
            :language: yaml

Recap
=====

This how-to guide covered how to define an A2A Agent in Agent Spec.

.. collapse:: Below is the complete code from this guide.

  .. literalinclude:: ../code_examples/howto_a2aagent.py
    :language: python
    :linenos:
    :start-after: .. start-##_Creating_the_agent
    :end-before: .. end-##_Creating_the_agent

Next Steps
==========

Now that you have learned how to build A2A Agents, 
you can proceed to :doc:`How to Use the WayFlow Runtime to Execute Agent Spec <howto_execute_agentspec_with_wayflow>`.
