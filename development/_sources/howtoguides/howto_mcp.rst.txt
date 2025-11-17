=================================
How to Implement a Plugin for MCP
=================================

.. admonition:: Prerequisites

    This guide assumes you are familiar with the following concepts:

    - :doc:`Flows <howto_flow_with_conditional_branches>`
    - :doc:`Agents <howto_agent_with_remote_tools>`


Overview
========

`Model Context Protocol <https://modelcontextprotocol.io/introduction>`_ (MCP) is an open protocol that standardizes
how applications provide context to LLMs. MCP servers allow you to connect your assistant to external tools and services
(such as web APIs, search engines, or custom data sources) **without writing custom adapters for each integration**.

In this guide, you will learn how to:

* Create a simple MCP Server (in a separate Python file)
* Connect an Agent/Flow to an MCP Server


.. important::

    This guide will show you how to integrate with WayFlow, which supports MCP Tools.
    Note that the steps shown in this guide can be applied on any runtime executor that supports MCP.



Prerequisite: Setup a simple MCP Server
=======================================

First, let's see how to create and start a simple MCP server exposing a couple of tools.

.. note::
    You should copy the following server code and run it in a separate Python process.

.. literalinclude:: ../code_examples/howto_mcp.py
    :language: python
    :start-after: # .. start-##Create_a_MCP_Server
    :end-before: # .. end-##Create_a_MCP_Server

This MCP server exposes two example tools: ``get_user_session`` and ``get_payslips``.
Once started, it will be available at (by default): ``http://localhost:8080/sse``.


.. note::
    When choosing a transport for MCP:

    - Use :ref:`Stdio <stdiotransport>` when launching and communicating with an MCP server as a local subprocess on the same machine as the client.
    - Use :ref:`Streamable HTTP <streamablehttpmtlstransport>` when connecting to a remote MCP server.

    For more information, visit https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#stdio


.. important::

    This guide does not aim at explaining how to make secure MCP servers, but instead mainly aims at showing how to connect to one.
    You should ensure that your MCP server configurations are secure, and only connect to trusted external MCP servers.


Connecting an Agent to the MCP Server
=====================================

You can now connect an agent to this running MCP server.


Add imports and configure an LLM
--------------------------------

Start by importing the necessary packages for this guide:

.. literalinclude:: ../code_examples/howto_mcp.py
   :language: python
   :start-after: .. start-##_Imports_for_this_guide
   :end-before: .. end-##_Imports_for_this_guide

Agent Spec supports several LLM API providers.
Select an LLM from the options below:

.. include:: ../_components/llm_config_tabs.rst


Build the Agent
---------------

:ref:`Agents <agent>` can use tools exposed by MCP servers using :ref:`MCPTool <mcptool>`.

.. literalinclude:: ../code_examples/howto_mcp.py
    :language: python
    :start-after: .. start-##_Connecting_an_agent_to_the_MCP_server
    :end-before: .. end-##_Connecting_an_agent_to_the_MCP_server

Specify the :doc:`transport <../api/mcp>` to use to handle the connection to the server
as well as the name of the specific tool you want to use. Additionally, you can override the tool
description (exposed by the MCP server) by specifying the ``description`` parameter.

.. note::
    To require user confirmation for a tool, set ``requires_confirmation=True`` (see :ref:`Tool <tool>`).
    This signals that execution environments should require user approval before running the tool, which is useful
    for tools performing sensitive actions.

Agent Serialization
-------------------

You can export the agent configuration using the :ref:`AgentSpecSerializer <serialize>`.

.. literalinclude:: ../code_examples/howto_mcp.py
    :language: python
    :start-after: .. start-##_Export_Agent_to_IR
    :end-before: .. end-##_Export_Agent_to_IR


Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_mcp_agent.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_mcp_agent.yaml
            :language: yaml


Connecting a Flow to the MCP Server
===================================

You can also use MCP tools in a :ref:`Flow <flow>` by using the :ref:`MCPTool <mcptool>` in a :ref:`ToolNode <toolnode>`.

Build the Flow
--------------

Create the flow using the MCP tool:

.. literalinclude:: ../code_examples/howto_mcp.py
    :language: python
    :start-after: .. start-##_Connecting_a_flow_to_the_MCP_server
    :end-before: .. end-##_Connecting_a_flow_to_the_MCP_server


Similarly to when equipping :ref:`Agents <agent>` with MCP Tools, you should specify the
client transport as with the MCP ToolBox, as well as the name of the specific tool
you want to use.


Flow Serialization
------------------

You can export the flow configuration using the :ref:`AgentSpecSerializer <serialize>`.

.. literalinclude:: ../code_examples/howto_mcp.py
    :language: python
    :start-after: .. start-##_Export_Flow_to_IR
    :end-before: .. end-##_Export_Flow_to_IR


Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_mcp_flow.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_mcp_flow.yaml
            :language: yaml



Next steps
==========

In this guide, you learned how to connect MCP Tools to Agent Spec :ref:`Flows <flow>` and :ref:`Agents <Agent>`.

Having learned how to configure agent instructions, you may now proceed to:

- :doc:`Specify the Generation Configuration when Using LLMs <howto_generation_config>`
- :doc:`How to Develop an Agent with Remote Tools <howto_agent_with_remote_tools>`
- :doc:`How to Execute Agent Spec Configuration with WayFlow <howto_execute_agentspec_with_wayflow>`
