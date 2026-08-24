===========================================
How to Execute Agent Spec Across Frameworks
===========================================

This guide demonstrates how to:

1. Load an Agent Spec JSON representation of an agent
2. Run it with an agentic framework using one of the Agent Spec adapters
3. Build the basics of an Agent Spec adapter

This guide shows how to execute a flexible ReAct RAG agent using a tool that simulates
information retrieval based on a query.
The example uses a pre-built Agent Spec representation of the agent, shown below.

.. tabs::

    .. tab:: JSON

        .. literalinclude:: ../agentspec_config_examples/simple_agent_with_rag_tool.json
            :language: json

    .. tab:: YAML

        .. literalinclude:: ../agentspec_config_examples/simple_agent_with_rag_tool.yaml
            :language: yaml

It also assumes a common registry of tool implementations containing the tools used by this agent.

.. literalinclude:: ../code_examples/langgraph_cross_framework_agent.py
    :language: python
    :start-after: .. define-tool-registry:
    :end-before: .. end-define-tool-registry:

Adapters
========

Using adapters is the recommended way of integrating an agentic framework runtime.
Ideally, an adapter should programmatically translate the representation of the Agent Spec components
into the equivalent solution, as per each framework's definition, and return an object that developers can run.

As a reference runtime for Agent Spec, `WayFlow <https://github.com/oracle/wayflow>`_ offers an Agent Spec adapter as part of the package.
Additionally, we provide the adapter implementation for some of the most common agentic frameworks:

- `LangGraph <https://github.com/oracle/agent-spec/tree/main/pyagentspec/src/pyagentspec/adapters/langgraph>`_
- `AutoGen <https://github.com/oracle/agent-spec/tree/main/pyagentspec/src/pyagentspec/adapters/autogen>`_
- `CrewAI <https://github.com/oracle/agent-spec/tree/main/pyagentspec/src/pyagentspec/adapters/crewai>`_

.. seealso::

    Click here to :doc:`learn more about the Agent Spec ecosystem <../ecosystem/integrations>`

Each adapter contains two main public classes, ``AgentSpecExporter`` and ``AgentSpecLoader``.

The ``AgentSpecExporter`` exposes APIs to export an object of the reference agentic framework into the equivalent
Agent Spec representation in one of the following forms: YAML, JSON, or PyAgentSpec Component object.

.. code-block:: python

    class AgentSpecExporter:
        """Helper class to convert agentic framework objects to Agent Spec configurations."""

        def to_yaml(self, framework_component: FrameworkComponent) -> str:
            """Transform the given framework component into the respective Agent Spec YAML representation."""

        def to_json(self, framework_component: FrameworkComponent) -> str:
            """Transform the given framework component into the respective Agent Spec JSON representation."""

        def to_component(self, framework_component: FrameworkComponent) -> Component:
            """Transform the given framework component into the respective PyAgentSpec Component."""


The ``AgentSpecLoader`` exposes APIs to load an Agent Spec representation in one of the aforementioned forms, i.e.,
YAML, JSON, or PyAgentSpec Component object, into the corresponding agentic framework's object.
The loader requires you to specify the registry of tool implementations.
These tools will be mapped to the ServerTools used in the Agent Spec representation.

.. code-block:: python

    class AgentSpecLoader:
        """Helper class to convert Agent Spec configurations to agentic framework objects."""

        def __init__(self, tool_registry: Optional[Dict[str, Callable]] = None):
            """Provide the tool registry containing the implementations of ServerTools"""

        def load_yaml(self, serialized_assistant: str) -> FrameworkComponent:
            """Transform the given Agent Spec YAML representation into the respective framework Component"""

        def load_json(self, serialized_assistant: str) -> FrameworkComponent:
            """Transform the given Agent Spec JSON representation into the respective framework Component"""

        def load_component(self, agentspec_component: AgentSpecComponent) -> FrameworkComponent:
            """Transform the given PyAgentSpec Component into the respective framework Component"""


Basic implementation of an adapter
==================================

As an example of how to build an adapter, let's take `WayFlow <https://github.com/oracle/wayflow>`_ as agentic framework and implement the
main functions needed to perform the transformation from an Agent Spec representation to a runnable WayFlow component.

1. Load an Agent Spec JSON representation of an agent
-----------------------------------------------------

The first step is to read the Agent Spec JSON representation of the assistant and deserialize it
to obtain a PyAgentSpec :ref:`Agent <agent>` component.
This component and its internals serve as the basis for building framework-specific implementations of the agent.
We can take advantage of the PyAgentSpec deserialization functionality for that.

.. literalinclude:: ../code_examples/langgraph_cross_framework_agent.py
    :language: python
    :start-after: .. agentspec-deserialization:
    :end-before: .. end-agentspec-deserialization:


API Reference: :ref:`AgentSpecDeserializer <deserialize>`

The agent contains mainly three components that need to be created in WayFlow:

- The vLLM used by the agent
- The RAG tool that the agent could use to gather more information
- The agent itself

The following sections detail how to create these components across different frameworks.
The programmatic way to accomplish this is to build reusable methods that translate individual
Agent Spec components, which are then combined to perform the final agent translation.

2. Defining the LLM
-------------------

WayFlow provides a specialized class for vLLMs called ``VllmModel``.
Use this class to define the agent’s language model.

.. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
    :language: python
    :start-after: .. define-llm:
    :end-before: .. end-define-llm:

3. Defining the tools
---------------------

The tool types available in WayFlow align with the ones defined in Agent Spec (Client, Server, Remote).
If the Agent Spec specifies a ``ServerTool``, the corresponding class in WayFlow must be used.

.. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
    :language: python
    :start-after: .. define-tools:
    :end-before: .. end-define-tools:

4. Defining the agent
---------------------

Create a ReAct-style agent in WayFlow using the ``Agent`` class and providing the list of available tools.

.. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
    :language: python
    :start-after: .. define-agent:
    :end-before: .. end-define-agent:

5. Conversion
-------------

Define the conversion method for the required Agent Spec components and invoke it on the agent
to produce the corresponding WayFlow implementation.

.. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
    :language: python
    :start-after: .. define-conversion:
    :end-before: .. end-define-conversion:

6. Execution
------------

Finally, we can start the conversation with our new agent and execute it.

.. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
    :language: python
    :start-after: .. start-conversation
    :end-before: .. end-conversation



Using the native Agent Spec adapters
====================================

The execution of this section requires installing pyagentspec with the extension corresponding
to the framework you want to use Agent Spec with.

.. tabs::

    .. tab:: LangGraph

        .. code-block:: bash

            # To use this adapter, please install pyagentspec with the "langgraph" extension.
            pip install "pyagentspec[langgraph]"

        .. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
            :language: python
            :start-after: .. using-langgraph-agentspec-adapter:
            :end-before: .. end-using-langgraph-agentspec-adapter:

    .. tab:: CrewAI

        .. code-block:: bash

            # To use this adapter, please install pyagentspec with the "crewai" extension.
            pip install "pyagentspec[crewai]"

        .. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
            :language: python
            :start-after: .. using-crewai-agentspec-adapter:
            :end-before: .. end-using-crewai-agentspec-adapter:

    .. tab:: AutoGen

        .. code-block:: bash

            # To use this adapter, please install pyagentspec with the "autogen" extension.
            pip install "pyagentspec[autogen]"

        .. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
            :language: python
            :start-after: .. using-autogen-agentspec-adapter:
            :end-before: .. end-using-autogen-agentspec-adapter:


The transformation can be easily performed using this library by using the ``AgentSpecLoader`` object,
and calling the ``load_json`` method directly on the Agent Spec JSON representation of the agent,
or the ``load_component`` method on the PyAgentSpec component object.

You can find more information about the Agent Spec adapter in the Agent Spec :doc:`API Documentation <../api/adapters>`.


Using the WayFlow Agent Spec adapter
====================================

The execution of this section requires installing the package ``wayflowcore``.

.. code-block:: bash
    :substitutions:

    pip install "wayflowcore==|stable_release|"


The transformation can be easily performed using this library by creating an ``AgentSpecLoader`` object,
and calling the ``load_json`` method directly on the Agent Spec JSON representation of the agent,
or the ``load_component`` method on the PyAgentSpec component object.

.. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
    :language: python
    :start-after: .. using-wayflow-agentspec-adapter:
    :end-before: .. end-using-wayflow-agentspec-adapter:

You can find more information about the Agent Spec adapter in the WayFlow `API Reference <https://github.com/oracle/wayflow>`_.

Recap
=====

This guide covered how to:

1. Load an Agent Spec JSON representation of an agent
2. Run it with an agentic framework using WayFlow
3. Build the basics of an Agent Spec adapter

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/wayflow_cross_framework_agent.py
        :language: python
        :start-after: .. start-full-code
        :end-before: .. end-full-code

If you are interested in implementing an Agent Spec runtime adapter for a framework that is not currently supported,
or you would like to enhance one of the existing ones, contributions are welcome!
See the :ref:`Contributing <contributing>` section for more details.

Next steps
==========

Having seen how to implement the same agent across three different frameworks, consider experimenting with
your preferred one using your own Agent Spec configuration.
