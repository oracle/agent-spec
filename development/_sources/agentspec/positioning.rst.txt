.. _agentspecpositioning:

==================================================
Positioning of Agent Spec in the agentic ecosystem
==================================================

Agent Spec aims to streamline the architecture and design of agentic assistants
and workflows, serving as an intermediate representation that abstracts away
implementation details of specific agentic frameworks.
It is a portable configuration language that describes agentic design patterns,
components and expected behavior.
However, Agent Spec is not the only effort aimed at unifying the different parts
that compose a common agentic ecosystem.

- The `Model Context Protocol (MCP) <https://modelcontextprotocol.io/docs/getting-started/intro>`_,
  introduced by Anthropic, standardizes resource and data provision to agents.
  Resources are made available with a client/server based Restful API.
- Google's `Agent2Agent Protocol <https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/>`_
  and BeeAi’s `Agent Communication Protocol <https://agentcommunicationprotocol.dev/introduction/welcome>`_
  propose standardized APIs for distributed agent communication.
- In March 2025 Nvidia announced `NeMo Agent toolkit <https://github.com/NVIDIA/NeMo-Agent-Toolkit>`_
  which is a framework independent library that treats "every agent, tool, and agentic workflow
  as a function call - enabling composability between these agents, tools, and workflows".
  The idea is to compose existing agentic solutions and resources, potentially written
  using different frameworks, into new systems.

While protocols like MCP and A2A standardize tool or resource provisioning
as well as inter-agent communication, Agent Spec complements these efforts by
enabling standardized configuration of underlying architecture and behavior of agents.
Hence, Agent Spec provides strong synergies with other standardization efforts
through its abstract definition of agentic system design.
In the context of ongoing unification efforts within the agentic system landscape,
Agent Spec aims to serve as the "common foundation" that connects these initiatives,
enhancing their effectiveness and fostering a more cohesive ecosystem.
Support for the aforementioned protocols may be added in future versions of
Agent Spec as new components.

.. figure:: ../_static/agentspec_spec_img/agentspec_positioning.svg
    :align: center
    :scale: 100%
    :alt: Agent Spec complements other standardizations, such as MCP or A2A

    How does Agent Spec fits the modern Agentic Ecosystem
