.. _core_ref_sheet:

==========================
Agent Spec Reference Sheet
==========================

This reference sheet provides a single-page overview of basic code snippets covering the core concepts used in Agent Spec.

Each section includes links to additional guides for deeper learning.

LLMs
====

Agent Spec uses LLMs in Agents, as well as fixed-flow nodes that require them.
This section shows how to specify the configuration details needed for LLMs.


Specifying LLM configuration
----------------------------

To use an LLM in Agent Spec, you must provide configuration details that include connection information and generation parameters.

Agent Spec defines a Component called ``LlmConfig`` that contains all necessary configuration details:

.. code-block:: python

   class LlmConfig(Component):
     default_generation_parameters: Optional[Dict[str, Any]]

By default, you only need to specify the generation parameters that should be used when prompting the LLM.

Specific extensions of ``LlmConfig`` are provided for common models. For example:

.. code-block:: python

   class VLlmConfig(LlmConfig):
     model_id: str
     url: str

For more details, see the :ref:`Agent Spec Language Specification <agentspecspec>`.


Tools
=====

Tools are procedural functions or Flows that can be made available to an Agent to execute.
This section shows how to specify different types of tools in Agent Spec.

Agent Spec supports three types of tools based on where they are executed:

- **ServerTools** - Executed in the same runtime environment as the Agent
- **ClientTools** - Executed by the client, with results provided back to the executor
- **RemoteTools** - Run in an external environment, triggered by RPC or REST calls


Specifying a ServerTool
-----------------------

ServerTools are executed in the same runtime environment as the Agent. The tool definitions must be available in the Agent's environment.

.. code-block:: python

   class ServerTool(Tool):
     pass

Tools can specify multiple outputs by returning a dictionary where each entry corresponds to an output property.

.. note::

   Agent Spec does not store arbitrary code in the agent’s configuration. Instead, it contains only the tool’s metadata—such as attributes, inputs, and outputs—without the actual function implementation.


Specifying a ClientTool
-----------------------

``ClientTools`` are not executed by the executor. The client must execute the tool and provide the results back to the executor, similar to OpenAI's function calling model.

.. code-block:: python

   class ClientTool(Tool):
     pass


Specifying a RemoteTool
-----------------------

``RemoteTools`` are executed in an external environment via RPC or REST calls, triggered by the agent executor.

.. code-block:: python

   class RemoteTool(Tool):
     # Basic parameters needed for a remote API call
     url: str
     http_method: str
     api_spec_uri: Optional[str]
     data: Dict[str, Any]
     query_params: Dict[str, Any]
     headers: Dict[str, Any]
     sensitive_headers: SensitiveField[Dict[str, Any]]

For more details on tools, see the :ref:`Agent Spec Language Specification <agentspecspec>`.


Agents
======

Agent Spec Agents are the top-level constructs that hold shared resources such as conversation memory and tools.
They represent the entry point for interactions with the agentic system.


Specifying a simple Agent
-------------------------

Creating an Agent requires specifying an LLM configuration and a prompt template to guide the agent's behavior.

.. code-block:: python

   class Agent(ComponentWithIO):
     system_prompt: str
     llm_config: LlmConfig
     tools: List[Tool]

The Agent's main goal is to fill the values for all properties defined in its ``outputs`` attribute, with or without user interaction.

Example configuration:

.. code-block:: json

    {
      "id": "expert_agent_id",
      "name": "Adaptive expert agent",
      "description": null,
      "metadata": {},
      "inputs": [
        {
          "title": "domain_of_expertise",
          "type": "string"
        }
      ],
      "outputs": [],
      "llm_config": {
        "id": "llama_model_id",
        "name": "Llama 3.1 8B instruct",
        "description": null,
        "metadata": {},
        "default_generation_parameters": {},
        "url": "url.of.my.llm.deployment:12345",
        "model_id": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "component_type": "VllmConfig"
      },
      "system_prompt": "You are an expert in {{domain_of_expertise}}. Please help the users with their requests.",
      "tools": [],
      "human_in_the_loop": true,
      "component_type": "Agent",
      "agentspec_version": "26.2.0"
    }

.. note::

   Agents can be reused several times in a flow or as part of a more complex agent without replicating their definition.


Specifying an Agent with tools
------------------------------

You can equip Agents with tools by adding them to the ``tools`` attribute.

Example with a ServerTool:

.. code-block:: json

    {
      "id": "get_weather_tool",
      "name": "get_weather",
      "description": "Gets the weather in specified city",
      "metadata": {},
      "inputs": [
        {
          "title": "city_name",
          "type": "string"
        }
      ],
      "outputs": [
        {
          "title": "forecast",
          "type": "string"
        }
      ],
      "requires_confirmation": true,
      "component_type": "ServerTool",
      "agentspec_version": "26.2.0"
    }

.. note::
    Flows and agents contained in an Agent are executed in isolation. Sub-agents and sub-flows use separate conversations, independent from the top-level Agent's conversation.
.. note::
    Setting ``requires_confirmation=True`` in the :ref:`ServerTool<servertool>` signals that execution environments should require user approval before running the tool.

For more details on Agents, see the :ref:`Agent Spec Language Specification <agentspecspec>`.


Flows
=====

Flows are execution graphs with a fixed structure, which may include branches and loops.
They can be thought of as "subroutines" that encapsulate consistently-repeatable processes.


Specifying a simple Flow
------------------------

A Flow consists of nodes connected by control flow and data flow edges.

.. code-block:: python

   class Flow(ComponentWithIO):
     start_node: Node
     nodes: List[Node]
     control_flow_connections: List[ControlFlowEdge]
     data_flow_connections: Optional[List[DataFlowEdge]]

Example of a simple prompting flow:

.. code-block:: python

   from pyagentspec.property import Property
   from pyagentspec.flows.flow import Flow
   from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
   from pyagentspec.flows.nodes import LlmNode, StartNode, EndNode

   prompt_property = Property(
       json_schema={"title": "prompt", "type": "string"}
   )
   llm_output_property = Property(
       json_schema={"title": "llm_output", "type": "string"}
   )

   start_node = StartNode(name="start", inputs=[prompt_property])
   end_node = EndNode(name="end", outputs=[llm_output_property])
   llm_node = LlmNode(
       name="simple llm node",
       llm_config=llm_config,
       prompt_template="{{prompt}}",
       inputs=[prompt_property],
       outputs=[llm_output_property],
   )

   flow = Flow(
       name="Simple prompting flow",
       start_node=start_node,
       nodes=[start_node, llm_node, end_node],
       control_flow_connections=[
           ControlFlowEdge(name="start_to_llm", from_node=start_node, to_node=llm_node),
           ControlFlowEdge(name="llm_to_end", from_node=llm_node, to_node=end_node),
       ],
       data_flow_connections=[
           DataFlowEdge(
               name="prompt_edge",
               source_node=start_node,
               source_output="prompt",
               destination_node=llm_node,
               destination_input="prompt",
           ),
           DataFlowEdge(
               name="llm_output_edge",
               source_node=llm_node,
               source_output="llm_output",
               destination_node=end_node,
               destination_input="llm_output"
           ),
        ],
    )


Executing a sub-flow to an iterable with ``MapNode``
----------------------------------------------------

The ``MapNode`` is used to map a sequence of nodes to each value in a list, applying the same flow to all elements and collecting outputs.

.. code-block:: python

   square_numbers_map_node = MapNode(
       name="square number map node",
       subflow=square_number_flow,
   )

When using ``MapNode``:

- Input names are prefixed with ``iterated_``
- Output names are prefixed with ``collected_``
- The node supports reducer methods: ``append``, ``sum``, ``average``, ``max``, ``min``

Example data flow edge for ``MapNode``:

.. code-block:: python

   DataFlowEdge(
       name="list_of_x_edge",
       source_node=start_node,
       source_output="x_list",
       destination_node=square_numbers_map_node,
       destination_input="iterated_x",
   )


Adding conditional branching to Flows with ``BranchingNode``
------------------------------------------------------------

``BranchingNode`` allows conditional transitions based on input values through a key-value mapping.

.. code-block:: python

   from pyagentspec.flows.nodes import BranchingNode

   CORRECT_PASSWORD_BRANCH = "PASSWORD_OK"

   branching_node = BranchingNode(
       name="password check",
       mapping={"123456": CORRECT_PASSWORD_BRANCH},
       inputs=[password_property]
   )

Control flow edges with branching:

.. code-block:: python

   # Success branch
   ControlFlowEdge(
       name="branching_to_access_granted",
       from_node=branching_node,
       from_branch=CORRECT_PASSWORD_BRANCH,
       to_node=access_granted_end_node,
   )

   # Default branch (when mapping fails)
   ControlFlowEdge(
       name="branching_to_access_denied",
       from_node=branching_node,
       from_branch=BranchingNode.DEFAULT_BRANCH,
       to_node=access_denied_end_node,
   )

.. note::

    ``BranchingNode`` includes a ``default`` branch that is taken when the input does not match any key in the mapping.


Adding tools to Flows
---------------------

To use tools in Flows, use the ``ToolNode`` which executes a specified tool.

.. code-block:: python

   from pyagentspec.flows.nodes import ToolNode
   from pyagentspec.tools import ServerTool

   # Define the tool
   square_tool = ServerTool(
       name="compute_square_tool",
       description="Computes the square of a number",
       inputs=[x_property],
       outputs=[x_square_property],
   )

   # Create a ToolNode
   square_tool_node = ToolNode(name="square tool node", tool=square_tool)

The ``ToolNode`` automatically infers its inputs and outputs from the tool definition.

For more details on Flows and nodes, see the :ref:`Agent Spec Language Specification <agentspecspec>`.


Agentic composition patterns
============================

Agent Spec supports several composition patterns for building complex agentic systems by combining Agents and Flows.


Using an Agent in a Flow
------------------------

To use Agents in Flows, use the ``AgentNode`` which runs a potentially multi-round conversation with an Agent.

.. code-block:: python

   from pyagentspec.flows.nodes import AgentNode
   from pyagentspec.agent import Agent

   # Define an Agent
   agent = Agent(
       name="User input agent",
       llm_config=llm_config,
       prompt_template=(
           "Your task is to ask the password to the user. "
           "Once you get it, submit it and end."
       ),
       outputs=[password_property],
   )

   # Use the Agent in a Flow through AgentNode
   agent_node = AgentNode(
       name="User input agent node",
       agent=agent,
   )

The ``AgentNode``:

- Runs a conversation with the specified Agent
- Takes the inputs defined by the Agent
- Provides the outputs defined by the Agent
- Allows the same Agent to be executed in several places of a flow

.. note::

   By separating the Agent definition from the node executing it, you can reuse the same Agent in multiple locations without duplicating its definition.


Using sub-flows within Flows
----------------------------

To use sub-flows in Flows, use the FlowNode which executes another Flow as part of the current Flow.

According to the Agent Spec specification:

.. code-block:: python

   # FlowNode configuration from Agent Spec spec
   class FlowNode:
       subflow: Flow  # The flow to be executed

The ``FlowNode``:

- Runs a Flow within another Flow
- Helps structure agents and easily reuse flows across them
- Takes inputs from the ``StartNode`` of the inner flow
- Provides outputs from the ``EndNodes`` of the inner flow
- Creates one outgoing branch per ``EndNode`` in the sub-flow

Example usage pattern:

.. code-block:: python

   from pyagentspec.flows.nodes import FlowNode

   # Assuming you have a pre-defined Flow
   my_subflow = Flow(...)

   # Use it in another Flow
   flow_node = FlowNode(
       name="Execute subflow",
       subflow=my_subflow
   )

.. note::

   Sub-flows and sub-agents contained in a Flow (i.e., as part of AgentNode and FlowNode,
   see the Node section for more information) share the same conversation of the Flow they belong to.

For more details on composition patterns, see the :ref:`Agent Spec Language Specification <agentspecspec>`.

Saving and loading Agent Spec assistants
========================================

Agent Spec's primary purpose is to enable portability of agent configurations across platforms and languages through serialization.


Saving and loading assistants
-----------------------------

Use the ``AgentSpecSerializer`` and ``AgentSpecDeserializer`` to save and load Agent Spec components to and from JSON format.

Saving an assistant:

.. code-block:: python

   from pyagentspec.serialization import AgentSpecSerializer

   # Create your Agent or Flow
   agent = Agent(
       name="My Assistant",
       llm_config=llm_config,
       prompt_template="You are a helpful assistant.",
       tools=[],
       inputs=[],
       outputs=[]
   )

   # Serialize to JSON
   serializer = AgentSpecSerializer()
   json_content = serializer.to_json(agent)

Loading an assistant:

.. code-block:: python

   from pyagentspec.serialization import AgentSpecDeserializer

   # Load from JSON
   deserializer = AgentSpecDeserializer()
   loaded_agent = deserializer.from_json(json_content)

The serialization process:

- Converts all components and sub-components to JSON format
- Preserves the complete structure including tools, flows, and agents
- Uses component references to avoid duplication
- Maintains all configuration details for cross-platform compatibility

.. note::

   Every component is serialized with a ``component_type`` field that identifies the specific component class, ensuring proper deserialization.

For more details on serialization, see the :ref:`Agent Spec Language Specification <agentspecspec>` and the PyAgentSpec serialization documentation.

.. _flowbuilder_ref_sheet:

Flow Builder quick snippets
---------------------------

Build a linear flow in one line:

.. code-block:: python

    from pyagentspec.flows.flowbuilder import FlowBuilder
    from pyagentspec.flows.nodes import LlmNode
    from pyagentspec.llms import VllmConfig

    llm_config = VllmConfig(name="Llama 3.1 8B instruct", url="http://localhost:8000", model_id="meta-llama/Meta-Llama-3.1-8B-Instruct")
    n1 = LlmNode(name="n1", llm_config=llm_config, prompt_template="Hello")
    n2 = LlmNode(name="n2", llm_config=llm_config, prompt_template="World")
    flow = FlowBuilder.build_linear_flow([n1, n2])

API Reference: :ref:`FlowBuilder <flowbuilder>`

Add a sequence, then entry/finish:

.. code-block:: python

    from pyagentspec.flows.flowbuilder import FlowBuilder
    from pyagentspec.flows.nodes import LlmNode
    from pyagentspec.llms import VllmConfig

    llm_config = VllmConfig(name="Llama 3.1 8B instruct", url="http://localhost:8000", model_id="meta-llama/Meta-Llama-3.1-8B-Instruct")
    n1 = LlmNode(name="n1", llm_config=llm_config, prompt_template="Hello")
    n2 = LlmNode(name="n2", llm_config=llm_config, prompt_template="World")

    flow = (
        FlowBuilder()
        .add_sequence([n1, n2])
        .set_entry_point(n1)
        .set_finish_points(n2)
        .build()
    )

Add a conditional using a node output as key, with a default branch:

.. code-block:: python

    from pyagentspec.flows.flowbuilder import FlowBuilder
    from pyagentspec.flows.nodes import LlmNode
    from pyagentspec.llms import VllmConfig

    llm_config = VllmConfig(name="Llama 3.1 8B instruct", url="http://localhost:8000", model_id="meta-llama/Meta-Llama-3.1-8B-Instruct")
    src = LlmNode(name="src", llm_config=llm_config, prompt_template="...")
    ok = LlmNode(name="ok", llm_config=llm_config, prompt_template="OK")
    ko = LlmNode(name="ko", llm_config=llm_config, prompt_template="KO")

    flow = (
        FlowBuilder()
        .add_sequence([src])
        .add_node(ok)
        .add_node(ko)
        .add_conditional(
            source_node=src,
            source_value=LlmNode.DEFAULT_OUTPUT,
            destination_map={"success": ok, "fail": ko},
            default_destination=ko,
        )
        .set_entry_point(src)
        .set_finish_points([ok, ko])
        .build()
    )


Go beyond linear flows using control and data edges:

.. code-block:: python

    producer = LlmNode(name="producer", llm_config=llm_config, prompt_template="Say Hello")
    consumer1 = LlmNode(name="consumer1", llm_config=llm_config, prompt_template="{{generated_text}}")
    consumer2 = LlmNode(name="consumer2", llm_config=llm_config, prompt_template="{{also_value}}")

    flow_with_connections = (
        FlowBuilder()
        .add_node(producer)
        .add_node(consumer1)
        .add_node(consumer2)
        .add_edge("producer", "consumer1")
        .add_edge("producer", "consumer2")
        # Using the default output name for LlmNode.DEFAULT_OUTPUT
        .add_data_edge("producer", "consumer1", LlmNode.DEFAULT_OUTPUT)
        .add_data_edge("producer", "consumer2", (LlmNode.DEFAULT_OUTPUT, "also_value"))
        .set_entry_point("producer")
        .set_finish_points(["consumer1", "consumer2"])
        .build()
    )
