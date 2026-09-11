Frequently Asked Questions
==========================

**How does Agent Spec fit with other protocols like A2A and MCP?**

    While protocols like MCP and A2A standardize tool or resource provisioning
    as well as inter-agent communication, Agent Spec complements these efforts by
    enabling standardized configuration of underlying architecture and behavior of agents.

    Check our :ref:`positioning page <agentspecpositioning>` for more information about the role
    of Agent Spec in the agentic ecosystem.


**What types of assistants can I create using Agent Spec?**

    You can create two main types of assistants: :ref:`Agents <agent>` and :ref:`Flows <flow>`.
    Agents are conversational assistants that can perform tasks and ask follow-up questions,
    while Flows are workflow-based assistants that can be represented as a flow of steps.


**What is the main difference between Agents and Flows?**

    Agents are more capable but less reliable and harder to run in production, while Flows are cheaper to run and easier to debug.


**How do I serialize or deserialize my assistants?**

    You can use the APIs provided by :doc:`PyAgentSpec <installation>` to serialize and deserialize your assistants.
    You can use a few lines of code to serialize your assistant and load it in `pyagentspec` using a JSON file.
    See the :ref:`API reference <serialization>` for more information.
