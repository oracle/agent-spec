====================================================
How to Execute Agent Spec Configuration with WayFlow
====================================================

.. admonition:: Prerequisites

    This guide assumes you have already defined either a Flow or an Agent using PyAgentSpec and exported its Agent Spec configuration.

    - :doc:`Flows <howto_flow_with_conditional_branches>`
    - :doc:`Agents <howto_agent_with_remote_tools>`


This guide demonstrates how to:

1. Install `WayFlow <https://github.com/oracle/wayflow>`_ to use its Agent Spec adapter
2. Define a tool execution registry
3. Load an Agent Spec configuration using the WayFlow adapter
4. Run and interact with the assistant

The example uses a minimal Agent configured with a single tool for performing multiplications.
The same approach can be applied to load and execute more complex assistants.

1. Installation
---------------

The execution of this guide requires to install the package ``wayflowcore``.

.. code-block:: bash
    :substitutions:

    pip install "wayflowcore==|stable_release|"

You can find more information about the Agent Spec adapter in the WayFlow
`API Reference <https://oracle.github.io/wayflow/core/api/index.html>`_.

2. Defining the tool registry
-----------------------------

Before loading the configuration, define a tool registry that specifies how tools are executed.
This registry is required to specify how tools are executed, because the tools implementation is not included in the Agent Spec configuration of the assistants.

The example below registers a single tool that performs multiplications.
In practice, this should be extended to register implementations for all tools that the assistant should use.

This guide focuses on the simplest tool type: ``ServerTool``.
For information on other types, such as :ref:`ClientTool <clienttool>` and :ref:`RemoteTool <remotetool>`, refer to the :doc:`Agent Spec Language Specification <../agentspec/language_spec_25_4_1>`.

.. code-block:: python

  from wayflowcore.tools import ServerTool

  multiplication_tool = ServerTool(
      name="multiplication_tool",
      description="Tool that allows to compute multiplications",
      parameters={"a": {"type": "integer"}, "b": {"type": "integer"}},
      output={"title": "product", "type": "integer"},
      func=lambda a, b: a*b,
  )

  tool_registry = {
      "multiplication_tool": multiplication_tool,
  }

3. Loading the Agent Spec configuration
---------------------------------------

The configuration of the agent is as follows.
Note that the configuration first defines two components ``multiplication_tool`` and ``vllm_config`` which are then referenced in the definition of the agent itself.

.. tabs::

    .. tab:: JSON

        .. literalinclude:: ../agentspec_config_examples/math_homework_agent.json
            :language: json

    .. tab:: YAML

        .. literalinclude:: ../agentspec_config_examples/math_homework_agent.yaml
            :language: yaml


Loading the configuration to the WayFlow executor is simple as long as the ``tool_registry`` has been defined.

.. code-block:: python

  from wayflowcore.agentspec import AgentSpecLoader

  loader = AgentSpecLoader(tool_registry=tool_registry)
  assistant = loader.load_yaml(AGENTSPEC_CONFIG)

4. Running the assistant
------------------------

To start the interaction, first create a conversation.
The assistant then prompts the user for input, and responses from the agent are printed continuously until the process is interrupted (e.g., via Ctrl+C).
Messages of type ``TOOL_REQUEST`` and ``TOOL_RESULT`` are also displayed.
These indicate when the agent invokes one of the available tools to respond to the user.

For more information on message types, refer to the `WayFlow API documentation <https://oracle.github.io/wayflow/core/api/index.html>`_.

.. code-block:: python

  from wayflowcore import MessageType

  if __name__ == "__main__":
      conversation = assistant.start_conversation()
      message_idx = 0
      while True:
          user_input = input("\nUSER >>> ")
          conversation.append_user_message(user_input)
          assistant.execute(conversation)
          messages = conversation.get_messages()
          for message in messages[message_idx+1:]:
              if message.message_type == MessageType.TOOL_REQUEST:
                  print(f"\n{message.message_type.value} >>> {message.tool_requests}")
              else:
                  print(f"\n{message.message_type.value} >>> {message.content}")
          message_idx = len(messages)

You may also want to execute a non-conversational flow.
In this case the execution loop could be implemented as shown below:

.. code-block:: python

  if __name__ == "__main__":
      conversation = assistant.start_conversation({ "some_input_name": "some_input_value", ... })
      status = assistant.execute(conversation)
      for output_name, output_value in conversation.state.input_output_key_values.items():
          print(f"{output_name} >>> \n{output_value}")

Recap
=====

This guide covered how to:

1. Install the Agent Spec adapter for WayFlow.
2. Define the execution of tools in a tool registry.
3. Load an Agent Spec configuration using the WayFlow adapter.
4. Run the assistant and interact with it.

.. collapse:: Below is the complete code from this guide.

  .. literalinclude:: ../code_examples/howto_execute_agentspec_with_wayflow.py
    :language: python
    :linenos:
    :start-after: .. start-full-code
    :end-before: .. end-full-code

Next steps
==========

To discover more advanced capabilities, refer to the `WayFlow documentation <https://github.com/oracle/wayflow/>`_ and
learn what you can build with Flows and Agents.
