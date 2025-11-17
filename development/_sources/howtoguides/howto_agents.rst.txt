=================================
How to build a simple ReAct Agent
=================================

Agents can be configured to tackle many scenarios.
Proper configuration of their instructions is essential.

In this how to guide, we will learn how to:

- Configure the instructions of an :ref:`Agent <Agent>`.
- Set up instructions that vary based on some inputs.
- Add tools to create a ReAct Agent.

Basic implementation
====================

In this scenario built for this guide, you need an agent to assist a user in writing articles.
In the simplest implementation of your agent, you just have to specify some basic elements that compose your agent.
The first is the LLM, that can be defined as any of the ``LlmConfig`` implementations offered by Agent Spec.
This LLM is going to be prompted by the Agent to accomplish the tasks that you (in the prompt), or the user
(during the conversation), assign to it.

.. literalinclude:: ../code_examples/howto_agents.py
    :language: python
    :start-after: .. start-llm
    :end-before: .. end-llm

Now that you have defined your LLM, you can directly create your Agent by specifying a name and giving it
a system prompt to instruct the agent on what to do.

.. literalinclude:: ../code_examples/howto_agents.py
    :language: python
    :start-after: .. start-agent
    :end-before: .. end-agent

Sometimes, there is contextual information relevant to the conversation.
Assume a user is interacting with the assistant, and you know some relevant information about this user.
In such a scenario, you might want to make the agent aware of this information by injecting it in its system prompt.
To make the assistant more context-aware, Agent Spec allows defining input properties through placeholders in
the ``system_prompt``. To do this, you can just specify the name of the property between double curly brackets.
In the following example we inject the username in the system prompt of the agent.

.. literalinclude:: ../code_examples/howto_agents.py
    :language: python
    :start-after: .. start-custom-prompt-agent
    :end-before: .. end-custom-prompt-agent

Lastly, you can add tools that the Agent can use as part of its ReAct implementation to accomplish the assigned tasks.
It's not required to update the system prompt to make the agent aware of the existence of these tools.
You can simply define them, and add them to the Agent's instantiation.

.. literalinclude:: ../code_examples/howto_agents.py
    :language: python
    :start-after: .. start-tools
    :end-before: .. end-tools

.. note::
    To require user confirmation for a tool, set ``requires_confirmation=True`` (see :ref:`Tool <tool>`).
    This signals that execution environments should require user approval before running the tool, which is useful
    for tools performing sensitive actions.

Agent Spec Serialization
========================

You can export the assistant configuration using the :ref:`AgentSpecSerializer <serialize>`.

.. literalinclude:: ../code_examples/howto_agents.py
    :language: python
    :start-after: .. start-export-config-to-agentspec
    :end-before: .. end-export-config-to-agentspec


Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_agents.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_agents.yaml
            :language: yaml

Recap
=====

In this guide, you learned how to configure :ref:`Agent <Agent>` instructions with:

- Pure text instructions;
- Specific context-dependent variables;
- Tools.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_agents.py
        :language: python
        :start-after: .. start-full-code
        :end-before: .. end-full-code


Next steps
==========

Having learned how to configure agent instructions, you may now proceed to:

- :doc:`Specify the Generation Configuration when Using LLMs <howto_generation_config>`
- :doc:`How to Develop an Agent with Remote Tools <howto_agent_with_remote_tools>`
- :doc:`How to Execute Agent Spec Configuration with WayFlow <howto_execute_agentspec_with_wayflow>`
