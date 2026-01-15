===================================================
How to use custom components with the Plugin System
===================================================

.. admonition:: Prerequisites

    This guide assumes you are familiar with the following concepts:

    - :doc:`Flows <howto_flow_with_conditional_branches>`

    Additionally, you need to have **Python 3.10+** installed.

Overview
========

Agent Spec supports a list of core native components to build your LLM-powered assistants, for instance a list of
pre-defined Nodes (:ref:`Agent Spec Spec <agentspecnodesspec>`, :ref:`API Reference <presentnode>`).

You might however want to go beyond the list of components supported in the base specification and use additional
components **while being able to use the Agent Spec Assistant Configuration system.** The pyagentspec plugin system
is designed to address this use case. Example uses of the plugin system include:

- New Large Language Model (LLM) configurations (by extending the ``LlmConfig`` component);
- New nodes for ``Flows`` (by extending the ``Node`` component);
- New tools (by extending the ``Tool`` component);
- Extensions to the ``Agent`` and ``Flow`` components.


.. figure:: ../_static/howto/plugin.svg
   :align: center
   :scale: 90%
   :alt: How the plugin system is used

   Overview of the Agent Spec plugin system.


This guide demonstrates how to support a custom ``PluginRegexNode`` in ``Flows`` to extract information
from a raw text using a regular expression (regex). You will:

1. Create a custom ``PluginRegexNode`` Agent Spec node and (de)serialization plugins so your assistant can be correctly saved and loaded;
2. Use the custom component to create an assistant that can extract information using regex;
3. Export your assistant configuration to Agent Spec JSON/YAML.
4. Load and execute your agent in a runtime executor (WayFlow).

.. important::

    The current plugin system enables the serialization and deserialization of custom components for Agent Spec.

    To fully support custom components, you also need to:

    1. Support the feature in your Agent Spec runtime implementation.
    2. Support the conversion between the custom Agent Spec plugin component and its
       corresponding implementation in your runtime implementation.


Basic implementation
====================

Define custom Agent Spec components
-----------------------------------

First you need to create the corresponding Agent Spec components.

.. literalinclude:: ../code_examples/howto_plugin.py
   :language: python
   :start-after: # .. start-customcomponents:
   :end-before: # .. end-customcomponents

API Reference: :ref:`Node <node>` | :ref:`Property <property>`

Here, the ``PluginRegexNode`` is the custom node that we intent to use in a Flow.

Create an assistant using the custom component
----------------------------------------------

The decision mechanism of Agents is powered by a Large Language Model.
Defining the agent with Agent Spec requires to pass the configuration for the LLM.
There are several options such as using `OCI GenAI Service <https://www.oracle.com/artificial-intelligence/generative-ai/generative-ai-service/>`_
or self hosting a model with vLLM.

Start by defining the LLM configuration to be shared across all agents.
This example uses a vLLM instance running Llama3.3 70B.

.. include:: ../_components/llm_config_tabs.rst

Here, you will create a Flow that generates an answer to a query using reasoning thoughts, and
then parses the output to return the final answer.

Use the ``PluginRegexNode`` defined previously to create your assistant.

.. literalinclude:: ../code_examples/howto_plugin.py
   :language: python
   :start-after: # .. start-create-assistant:
   :end-before: # .. end-create-assistant



Register plugins and export the agent configuration
---------------------------------------------------

You need to register (de)serialization plugins so your custom node can be correctly
saved and loaded using the Agent Spec serialization format.

.. literalinclude:: ../code_examples/howto_plugin.py
   :language: python
   :start-after: # .. start-create-plugins:
   :end-before: # .. end-create-plugins

API Reference: :ref:`PydanticComponentSerializationPlugin <pydanticcomponentserializationplugin>` | :ref:`PydanticComponentDeserializationPlugin <pydanticcomponentdeserializationplugin>`.

This enables PyAgentSpec's serializer and deserializer to recognize your custom classes.
In this example, since the components are directly inheriting from the Pydantic model :ref:`Component <component>`,
you should use the already existing (de)serialization plugins.

For more advanced use, you can implement custom plugins by inheriting from
:ref:`ComponentSerializationPlugin <componentserializationplugin>` and
:ref:`ComponentDeserializationPlugin <componentdeserializationplugin>`


You can then serialize your assistant to its Agent Spec JSON/YAML configuration using the registered plugins:

.. literalinclude:: ../code_examples/howto_plugin.py
   :language: python
   :start-after: # .. start-export-config:
   :end-before: # .. end-export-config

API Reference: :ref:`AgentSpecSerializer <serialize>`

Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/plugin_assistant.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/plugin_assistant.yaml
            :language: yaml


Load and execute your assistant from a configuration file
---------------------------------------------------------

.. seealso::

    For more details, see the guide on :doc:`How to Execute an Agent Spec Configuration with WayFlow <howto_execute_agentspec_with_wayflow>`.


To actually run the assistant, load the JSON or YAML configuration using the deserialization plugins defined above.

.. literalinclude:: ../code_examples/howto_plugin.py
   :language: python
   :start-after: # .. start-load-config:
   :end-before: # .. end-load-config


Now you can run your assistant! The assistant calls an LLM with the pre-defined request, and returns the parsed output.

.. literalinclude:: ../code_examples/howto_plugin.py
   :language: python
   :start-after: # .. start-execute-assistant:
   :end-before: # .. end-execute-assistant

Recap
=====

This guide covered how to:

- Create a custom Agent Spec component and its corresponding (de)serialization plugin.
- Build and export an assistant (Flow) with a custom regex node using the custom component and plugin.
- Load and execute the assistant in a runtime executor.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_plugin.py
        :language: python
        :start-after: # .. start-customcomponents:
        :end-before: # .. end-customcomponents

    .. literalinclude:: ../code_examples/howto_plugin.py
        :language: python
        :start-after: # .. start-create-assistant:
        :end-before: # .. end-create-assistant

    .. literalinclude:: ../code_examples/howto_plugin.py
        :language: python
        :start-after: # .. start-create-plugins:
        :end-before: # .. end-create-plugins

    .. literalinclude:: ../code_examples/howto_plugin.py
        :language: python
        :start-after: # .. start-export-config:
        :end-before: # .. end-export-config

    .. literalinclude:: ../code_examples/howto_plugin.py
        :language: python
        :start-after: # .. start-load-config:
        :end-before: # .. end-load-config


    .. literalinclude:: ../code_examples/howto_plugin.py
        :language: python
        :start-after: # .. start-execute-assistant:
        :end-before: # .. end-execute-assistant


Next steps
==========

Having learned how to build assistants with custom Agent Spec components using the plugin system,
you may now proceed to :doc:`How to Build an Orchestrator-Workers Agents Pattern <howto_orchestrator_agent>`.
