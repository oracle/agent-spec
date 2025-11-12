=========================================
How to Develop an Agent with Remote Tools
=========================================

This guide demonstrates how to:

1. Define properties to document the types of tool arguments and variables used in prompt templates
2. Configure remote tools that query external web APIs
3. Define the configuration for a LLM model
4. Define an agent with specific instructions and access to tools
5. Export the Agent Spec configuration for the agent

The assistant demonstrated in this guide focuses on helping users understand their benefits; however, the approach can be applied to other use-cases.
The assistant is a flexible agent based on the ReAct framework.
It has access to the tools to retrieve user-specific data and perform accurate calculations.

Basic implementation
====================

1. Define properties
--------------------

Properties help describe the inputs and outputs of assistant components, such as tools and nodes.
They serve as documentation, particularly important for tools, to guide the agent in correctly passing values to tool arguments.

.. literalinclude:: ../code_examples/howto_agent_with_remote_tools.py
    :language: python
    :start-after: .. define-properties:
    :end-before: .. end-define-properties:

API Reference: :ref:`Property <property>`

2. Define the remote tools
--------------------------

Tools are separate methods that the agent can decide to call by passing input arguments in order to fulfill user requests.
This section focuses on remote tools, which are configured to send HTTP requests to external web APIs.

.. literalinclude:: ../code_examples/howto_agent_with_remote_tools.py
    :language: python
    :start-after: .. define-tools:
    :end-before: .. end-define-tools:

API Reference: :ref:`RemoteTool <remotetool>`

.. note::

    Never commit sensitive data such as API keys or authentication tokens when using :ref:`RemoteTool <remotetool>`.
    Use secret management solutions instead.

.. note::
    To require user confirmation for a tool, set ``requires_confirmation=True`` (see :ref:`Tool <tool>`).
    This signals that execution environments should require user approval before running the tool, which is useful
    for tools performing sensitive actions.


3. Define a LLM model
----------------------

The decision mechanism of Agents is powered by a Large Language Model.
Defining the agent with Agent Spec requires to pass the configuration for the LLM.
There are several options such as using `OCI GenAI Service <https://www.oracle.com/artificial-intelligence/generative-ai/generative-ai-service/>`_ or self hosting a model with vLLM.

.. include:: ../_components/llm_config_tabs.rst

API Reference: :ref:`VllmConfig <vllmconfig>`

4. Define the agent
-------------------

The agent is defined with custom instructions that include placeholder variables and the list of accessible tools.

.. literalinclude:: ../code_examples/howto_agent_with_remote_tools.py
    :language: python
    :start-after: .. define-agent:
    :end-before: .. end-define-agent:

API Reference: :ref:`Agent <agent>`

5. Export the Agent Spec configuration
--------------------------------------

The Agent Spec configuration is generated in JSON format.
These configurations can be loaded and executed in Agent Spec-compatible systems such as the `WayFlow <https://github.com/oracle/wayflow>`_ runtime.
See, for example, :doc:`How to Execute Agent Spec Configurations with WayFlow <howto_execute_agentspec_with_wayflow>`.

.. literalinclude:: ../code_examples/howto_agent_with_remote_tools.py
    :language: python
    :start-after: .. export-serialization:
    :end-before: .. end-export-serialization:

API Reference: :ref:`AgentSpecSerializer <serialize>`.

Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_agent_with_remote_tools.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_agent_with_remote_tools.yaml
            :language: yaml

Recap
=====

This guide covered how to:

1. Define properties to document tool arguments and variables used in prompt templates
2. Define remote tools configured to query web APIs
3. Define the configuration for a LLM model
4. Define an agent with custom instructions and tool access
5. Export the Agent Spec configuration for the agent

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_agent_with_remote_tools.py
        :language: python
        :linenos:
        :start-after: .. define-properties:
        :end-before: .. end-export-serialization:

Next steps
==========

Having learned how to define an agent, you may now proceed to :doc:`how to use the WayFlow runtime to execute it <howto_execute_agentspec_with_wayflow>`.
