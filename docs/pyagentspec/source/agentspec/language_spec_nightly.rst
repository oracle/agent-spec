:orphan:

.. _agentspecspec:
.. _agentspecspec_nightly:

====================================================
Agent Spec specification (nightly version |release|)
====================================================

.. warning::
    This is the nightly version of Agent Spec, and it is currently under development.
    It is not an official release, and it might be subject to major changes before official release.
    Use this version only for testing purposes.

Language specification
======================

This document outlines the language specification for the Open Agent Specification, abbreviated as Agent Spec.

This specification defines the foundational parts that compose the language, including the expected format
and the respective semantic.

The class definition in the following sections is outlined via Python below for ease of comprehension.
This structure can be serialized into JSON, YAML, or other formats.
The respective serialization is also called Agent Spec configuration (or representation).

.. warning::
    Agent Spec serialized specifications are not supposed to contain executable code.
    Users should adopt security measures in their serialization and deserialization code when using formats
    that support such a functionality (e.g., using safe loading and dumping with YAML).


Base ``Component``
------------------

The base of Agent Spec is a ``Component``, which by itself can be used to
describe any instance of any type, guaranteeing flexibility to adapt to future changes.

Note that Agent Spec does not need to encapsulate the implementation for code it describes;
it simply needs to be able to express enough information to instantiate a uniquely-identifiable
object of a specific type with a specific set of property values.

.. code-block:: python

    class Component:
      # All components have a set of fixed common properties
      id: str  # Unique identifier for the component. Typically generated from component type plus a unique token.
      type: str  # Concrete type specifier for this component. Can be (but is not required to be) a class name.
      name: str  # Name of the component, if applicable
      description: Optional[str]  # Description of the component, if applicable
      metadata: Optional[Dictionary[str, Any]]  # Additional metadata that could be used for extra information


The ``metadata``  field contains all the additional information that
could be useful in different usages of the component. For example, GUIs will
require to include some information about the components (e.g., position
coordinates, size, color, notes, ...), so that they will be able to
visualise them properly even after an export-import process. Metadata is
optional, and empty by default.

Not all the building blocks of Agent Spec are necessarily ``Components``.
Some other convenient classes can be defined in order to more easily
describe the configurations of the agents (e.g., ``JSONSchemaValue``, ``LlmGenerationConfig``).
Those classes do not have to align to the interface of a Component.

.. _symbolic_reference_nightly:

Symbolic references (configuration components)
----------------------------------------------

When a component wishes to reference another component entity (e.g., as a property value),
there is a simple symbolic syntax to accomplish this: an object with a single property
"$component_ref" whose value is the id of the referenced component.
This type of relationship is applicable to any component.

.. code-block:: JSON

   {"$component_ref": "{COMPONENT_ID}"}

Note that a subcomponent reused in multiple parts of a complex nested component
(for example, a ClientTool used in both an AgentNode and a ToolNode as part of
a flow) must be defined using a component reference. If two components in an
Agent Spec configuration use the same `id`, the configuration will be considered
invalid.


Input/output schemas
--------------------

Components might need some input data in order to perform their task,
and expose some output as a result of their work.

These inputs and outputs must be declared and described in the exported configuration, so
that users, developers, and other components of the Agent as well, are
aware of what is exposed by component that require inputs, or provide
outputs. We call these input and output descriptions as input/output
schemas, and we add a subclass of Component called ComponentWithIO that
adds them to the base Component class.

.. code-block:: python

   class ComponentWithIO(Component):
     inputs: List[JSONSchemaValue]
     outputs: List[JSONSchemaValue]

Note that we do not add input/output schemas directly to the base
Component class, as there are a few cases where they do not really apply
(e.g., LlmConfig, edges, see their definition in the next sections).

Input and output properties
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Input and output schemas are used to define which values the different
components accept as input, or provide as output. We call these values
"properties".

The term "properties" comes from `JSON
schema <https://json-schema.org>`__: indeed, in order to specify all the
inputs and outputs, we rely on this widely adopted and consolidated
standard.

In particular, we ask to specify a list of JSON schemas definitions, one
for each input and output property. For more information about JSON
schema definition, please check the official website at
https://json-schema.org/understanding-json-schema.

In order for the schema to be valid, we require to specify some attributes:

- title: the name of the property
- type: the type of the property, following the type system described
  below

Additionally, users can specify:

- default: the default value of this property
- description: a textual description for the property

These are the minimal attributes (or *annotations*, in JSON Schema terminology)
that must be supported to ensure compatibility with Agent Spec.

Type system
~~~~~~~~~~~

We rely on the typing system defined by the JSON schema standard
(see https://json-schema.org/understanding-json-schema/reference/type).

At its core, JSON Schema defines the following basic types:

- `string <https://json-schema.org/understanding-json-schema/reference/string>`__
- `number <https://json-schema.org/understanding-json-schema/reference/numeric#number>`__
- `integer <https://json-schema.org/understanding-json-schema/reference/numeric#integer>`__
- `object <https://json-schema.org/understanding-json-schema/reference/object>`__
- `array <https://json-schema.org/understanding-json-schema/reference/array>`__
- `boolean <https://json-schema.org/understanding-json-schema/reference/boolean>`__
- `null <https://json-schema.org/understanding-json-schema/reference/null>`__

These types have analogs in most programming languages, though they may
go by different names.

Note that some types (array, object) require additional annotations with
respect to the ones listed in the previous section. Please refer to
their JSON schema definition for more information.

Type compatibility rules
~~~~~~~~~~~~~~~~~~~~~~~~

To connect a component's output to another component's input, the output type must be compatible with the input type.
Specifically, the output type should be a subtype of the input type.
For instance, an output of type ``number`` can connect to an input of type ``[number, null]``,
but an output of type ``string`` cannot connect to an input of type ``number``.

In order to further simplify input-output connections, we define some simple type compatibility rules that are accepted by Agent Spec.

- Every type can be converted to string.
- Numeric types (i.e., ``integer`` and ``number``) can be converted to each other.
  Note that this conversion could cause the loss of decimals.
- The Boolean type can be converted to numeric ones and vice-versa.
  The convention for the conversion is the one adopted by most programming languages:
  0 refers to ``false``, while any other number refers to ``true``.

These rules apply recursively in complex types:

- To the types of the elements of an ``array``;
- To the types of the ``properties`` of an ``object``.


Inputs and outputs of nested components
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In case of nested components (e.g., using an agent inside a flow, or a
flow inside another flow, or even just a step in a flow), the wrapping
component is supposed to expose a (sub)set of the inputs/outputs
provided by the inner components, united to, potentially, additional
inputs/outputs it generates itself.

We require to replicate the JSON schema of each value in the
inputs/outputs lists of every component that exposes it, i.e., if a
wrapper component exposes some inputs and outputs of some of its
internal components, it will have to include them in its inputs/outputs
lists as well.

This makes the representation of the components a bit more verbose, but
more clear and readable. Parsers of the representation are required to
ensure the consistency of the input/output schemas defined in it.

|image6|

In the example above we have that the wrapper Flow Component (see
sections below for more details about flows) requires two inputs that
coincide with two of the inputs exposed by the Node components in it (see
sections below for more details about nodes), and exposes one output among
those exposed by the inner nodes, plus an additional one it computes
itself. This corresponds to the following code definition.

**Input output schema example**

.. code-block:: python

   # String with "input_1_default" as default value
   input_1 = StringType(title="Input_1", default="input_1_default")

   # Dictionary with string keys and integers as values, default set to empty dictionary
   input_2 = ObjectType(title="Input_2", properties={}, additional_properties=NumberType(), default={})

   # Nullable string, default value set to null
   input_3 = StringType(title="Input_3", nullable=True, default=None)

   output_1 = StringType(title="Output_1")
   output_2 = BooleanType(title="Output_2", default=True)
   output_3 = ArrayType(title="Output_3", items=ArrayType(items=NumberType()), default=[[1], [2], [3]])

   # Note that we envision a fluent-classes way of defining inputs and outputs
   # These classes get serialized to their respective JSON schema equivalent

   # VLlmConfig is a subclass of Component, we will define it more in detail later
   # This Component does not have input/output schemas, the default should be an empty list
   vllm = VllmConfig(name="LLama 3.1 8b", model_id="llama3.1-8b-instruct", url="url.to.my.llm.com/hostedllm:12345")

   # Node is a subclass of Component, we will define it more in detail later
   node_1 = StartNode(name="Node 1", input_values=[input_1, input_2, input_3])
   node_2 = LLMNode(name="Node 2", llm=vllm, ...)
   node_3 = EndNode(name="Node 3", output_values=[output_1, output_2, output_3])

   # Flow is a subclass of Component, we will define it more in detail later
   flow = Flow(nodes=[node_1, node_2, node_3], ..., inputs=[input_1, input_2], outputs=[output_2, output_3])

The presence of the inputs and outputs in the representation of every
component does not imply that they always have to be explicitly defined
by users.

Indeed, they could be automatically and dynamically generated by the
components (e.g., inputs and outputs inferred from a prompt of an LLMNode).

Validation of specified inputs/outputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some inputs and outputs schema are automatically generated by components
based on their configuration. However, to improve the clarity and readability
of Agent Spec, descriptions of all inputs and outputs should always be explicitly
included in the representation.

As a consequence, when a representation is read and imported by a runtime, or an
SDK, the inputs and outputs configuration of each component must be
validated against the one generated by its configuration (if any).

Note that the input/output schema could be a specialization of the one
generated automatically by the component (e.g., an additional
description is added, a more precise type is defined, ...).

For this reason, we do not enforce the generated I/O schemas to be
perfectly equal to the one reported in the configuration, but we require that:

- The set of input and output property names are equivalent
- The type of each property in the generated I/O schemas can be casted
  to the type of the corresponding property reported in the configuration.

If these two requirements are not met, the Agent Spec configuration should be considered invalid.

Specifying inputs through placeholders
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some Components might infer inputs from special parts of their
attributes. For example, some nodes (e.g., the LLMNode) extract inputs
from a property called ``prompt_template``, so that its value can be
adapted based on previous computations.

We let users define placeholders in some attributes, by simply wrapping
the name of the property among a double set of curly brackets. The node
will automatically infer the inputs by interpreting those
configurations, and the actual value of the input/output will be
replaced at execution time. Whether an attribute accepts placeholders
depends on the definition of the component itself.

For example, setting the prompt_template configuration of an LLMNode to
"You are a great assistant. Please help the user with this request:
{{request}}" will generate an input called "request" of type string.

We do not require the support for complex types and collections like
lists (array) and dictionaries (object) in placeholders: placeholders
are typically transformed in inputs of type string, unless differently
specified by the definition of the Component. In general, dictionaries
and lists should be used directly in inputs and outputs with a matching
type definition. The latter could also be used as input to the MapNode
(see definition below), which applies the same flow to all the elements
in the list and collects the output.

In the future, we will consider adding support for complex types (e.g.,
for loops over lists, dictionary access) through templating, for example
by adopting a subset of the functionalities available in a common standard like
`jinja <https://jinja.palletsprojects.com/en/stable/>`__.

Component families
------------------

The base ``Component`` type is extended by several component families
which represent groups of elements that are commonly used in agentic
systems, such as (but not limited to) LLMs and Tools.

Describing these component families with specific types achieves the
following goals :

- Type safety + Usage hints for GUIs

  - *Example: if a component's property is expecting an LLM, only allow
    LLM's to be connected to it.*

- Static analysis + validation

  - *Examples: if a component is a ``Flow``, it must have a start node.
    If a component is an Agent, it must have an LLM.*

- Ease of programmatic use

  - Component families each have corresponding class definitions in the
    Agent Spec SDK. This allows consumers (agent execution environments,
    editing GUIs) to utilise concrete classes, rather than having to
    implicitly understand which type has which properties.


.. list-table:: Component families
    :header-rows: 1

    * - Component Family
      - Notes
      - Example
    * - Agentic Component
      - A top-level, interactive entity that can **receive messages** and **produce messages**.
        ``Flow``, ``Agent``, ``RemoteAgent``, ``Swarm``, ``ManagerWorkers`` and ``SpecializedAgent``  are
        all specialisations of this family.
      - * A multi-step approval flow
        * A ReACT Agent
        * A remotely-hosted OCI Generative AI Agent
    * - Agent
      - An agent is an interactive entity that can converse and use tools.
        Generic Agents can be specialized for specific tasks and use-cases.
      - * A ReACT agent with tools
    * - Remote Agent
      - An ``AgenticComponent`` whose implementation is **defined and executed
        outside** the current runtime (e.g. via REST/RPC).  Provides an easy way
        to orchestrate SaaS or micro-service based agents.
      - * A Slackbot backed by an external service
    * - Flow
      - An execution graph with a fixed layout, potentially containing branches and loops.
      - A workflow with multiple, well known and well defined approval actions to be pursued based on some condition
    * - Node (flow)
      - A Flow consists of a series of Node instances. There is a "standard library" of nodes
        for things such as executing a prompt with a LLM, branching, etc.
      - * A step in the execution of a flow, it corresponds to a specific action
    * - Relations / edges (flow)
      - Flow of control and I/O (data) are defined by explicit relationships in Agent Spec.
      - * Define which is the sequence of nodes that should be executed
        * Define which outputs should be used to fill which inputs
    * - LLM (config)
      - The configuration needed to reach out to an LLM
      - * URL and id of a model deployed remotely through vLLM
    * - Tool
      - A procedural function that can be made available to an Agent
      - * A tool to calculate the Levenshtein distance between two strings
        * A tool to execute a remote API on OCI
    * - ToolBox
      - A component that exposes a set of Tools to Agentic Components. ToolBoxes are
        discovery/aggregation constructs, not executable tools. MCPToolBox exposes tools
        discovered from an MCP server.
      - * A ToolBox connecting to an MCP server and exposing its tools to an Agent

    * - Datastore
      - A component that provides storage capabilities for agentic systems, enabling them to store and access data.
      - * An in-memory datastore for testing
        * An Oracle Database datastore and a Postgres Database datastore for production use



Agentic Components
~~~~~~~~~~~~~~~~~~

An **Agentic Component** represents anything you can "talk" to – i.e. an entity
that consumes a conversation (or other structured context), performs some work,
and returns a result that can be rendered as messages or structured data. It also represents
the entry point for interactions with the agentic system. It extends from ``ComponentWithIO`` and can have inputs
and outputs.

Three concrete kinds are currently defined:

1. ``Flow`` – a self-contained execution graph (described later
   in the document).
2. ``Agent`` – an in-process, conversational entity that can reason, call
   tools, and maintain state.
3. ``RemoteAgent`` – a conversational entity that is defined **remotely** and
   invoked through an RPC or REST call.
4. ``Swarm`` – a multi-agent conversational component in which each agent can call to other agents based on a list of pre-defined relationships.
5. ``ManagerWorkers`` – a multi-agent conversational component in which a manager agent can assign tasks to worker agents.

Agent
~~~~~

The ``Agent`` is the top-level construct that holds shared resources such
as conversation memory and tools. It also represents the entry point
for interactions with the agentic system.

.. code-block:: python

   class Agent(ComponentWithIO):
     system_prompt: str
     llm_configuration: LlmConfig
     tools: List[Tool]
     toolboxes: List[ToolBox]
     human_in_the_loop: bool
     transforms: List[MessageTransform]

Its main goal is to accomplish any task assigned in the ``system_prompt`` and terminate,
with or without any interaction with the user.
If outputs are defined, structured generation is enabled, and the Agent should also fill the values for
all the properties defined in the outputs attribute (or at least those that do not have a default value
defined) before terminating.

It's important to have a separate definition for Agents as components,
so that the same Agent can be reused several times, e.g., in different flows,
without replicating its definition multiple times.

Note that we do not require to define any output parser for an Agent.
Outputs (including their types, descriptions, ...) are defined at representation
level, and the Agent will fill their values either directly, or through tools.
If a special output format is required, users can specify a tool to fit the requirement.

It is also not required to specify the presence of tools in the ``system_prompt``.
Agent Spec assumes that the list of available tools, including their description, parameters, etc.
is handled by the runtime implementation, that should inform the agent's LLM of their existence.

Toolboxes, when present, augment the set of tools available to the Agent at runtime through
discovery/aggregation.

When an Agent consumes multiple ToolBoxes and tools, runtimes MAY merge them into a single tool
registry for the Agent. In case of tool name collisions across different sources:

- The specification recommends optional namespacing (e.g., toolbox_name.tool_name) and leaves
  the exact behavior to the runtime. Runtimes MAY error on collisions.
- Implementations SHOULD provide clear diagnostics when collisions occur.

Transforms, when present, apply transformations to the messages before they are passed to the agent's LLM,
allowing for message summarization, conversation summarization, or other modifications to optimize the agent's context.

This Component will be expanded as more functionalities will be added to
Agent Spec (e.g., memory, planners, ...).

Human-in-the-Loop in Agents
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The concept of human-in-the-loop in agents refers to integrating user
oversight or intervention points into automated processes.
When an agent is designed with a human in the loop, it pauses at defined
moments, such as (but not limited to) before taking key actions or making
critical decisions, to allow a human user to review, approve, or modify the outcome.
There are many possible ways to implement this concept,
such as (but not limited to) introducing special
tools, intercepting large language model (LLM) outputs, or pausing
execution before certain actions. The specific implementation details
are left to the runtime; the essential requirement is
that user control is provided at the appropriate time when requested by
the agent. In contrast, agents without human-in-the-loop capability
operate fully autonomously, without waiting for user input.

Agent Specialization for Reusability and Flexibility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In complex automation and orchestration tasks, agent reusability is
vital for maintainability and scalability. The Open Agent Specification
introduces an extension mechanism where a base agent can be tailored for
specialized tasks, enhancing its core capabilities with refined
instructions and additional toolsets. This approach promotes building
simple, generic agents that can be flexibly adapted to diverse use cases
within a flow or as standalone agents.

A ``SpecializedAgent`` is created using the ``AgentSpecializationParameters``.
The base ``agent``'s instructions are refined by merging them with the
``additional_instructions`` in the specialization parameters, and its tools
can be extended with the ``additional_tools``. Specialization can optionally
override the behaviour  of the agent from human-in-the-loop to fully autonomous,
or vice versa (``human_in_the_loop=None`` in the specialization parameters
preserves the base agent's behavior).

.. code-block:: python

  class AgentSpecializationParameters(ComponentWithIO):
    additional_instructions: Optional[str] = None
    additional_tools: Optional[List[Tool]] = None
    human_in_the_loop: Optional[bool] = None

  class SpecializedAgent(AgenticComponent):
    agent: Agent
    agent_specialization_parameters: AgentSpecializationParameters


``AgentSpecializationParameters`` can use placeholders (as introduced in the previous sections)
in the ``additional_instructions``, which will define the inputs to the
``AgentSpecializationParameters`` component.
The inputs of the ``SpecializiedAgent`` will be the union of the specialization parameters' inputs
and the ones of the base agent.
If the same input or output property is defined in both the agent and the
specialization parameters, the respective instances must have the same type.
``AgentSpecializationParameters`` do not define any outputs, therefore the outptus of the
``SpecializiedAgent`` will be the same as the ones of the underlying base ``Agent``.


LLM
~~~

LLMs are used in agents, as well as flow nodes that need one.

In order to make them usable, we need to let users specify all the
details needed to configure the LLM, like the connection details, the
generation parameters, etc.

We define a new Component called LlmConfig that contains all the details:

.. code-block:: python

   class LlmConfig(Component):
     default_generation_parameters: Optional[Dict[str, Any]]

We require only to specify the default generation parameters that should be used by default when prompting the LLM.
These parameters are specified as a dictionary of parameter names and respective values.
The names are strings, while values can be of any type compatible with the JSON schema standard.

.. note::

    The extra parameters should never include sensitive information.
    Make sure the extra parameter values are validated either by the runtime if supported,
    or explicitly before importing the configuration into the runtime.

Null value is equivalent to an empty dictionary, i.e., no default generation parameter is specified.
Specific extensions of LlmConfig for the most common models are provided as well.

Structured Generation
^^^^^^^^^^^^^^^^^^^^^

Structured generation in LLMs refers to the process of producing outputs that adhere to specific,
predefined formats or structures. This approach is valuable for use cases requiring machine-readable responses,
data extraction, program synthesis, or integrating LLM outputs with downstream systems.

Structured generation in LLMs typically works by guiding the model through tailored prompts or instructions
that specify the required format.
In Agent Spec we allow users to define the expected output format by defining output properties in Components.
In other words, users must define the JSON schema of the different properties that the LLM is supposed to generate.
Each component defines if structured generation is supported, and how it is enabled.

In the current version of Agent Spec, the components that support structured generation are:

- LlmNode
- Agent

More information is provided in their respective definitions.

.. note::
    Note that values, despite well-structured, will be LLM-generated.
    Therefore users should consider them untrusted, and they should perform proper validation before usage.

Agent Spec Runtimes can implement structured generation by generating all the properties in the same request,
but they should expose them as separate outputs.
For example, assuming to have the following component that supports structured generation:

.. code-block:: json5

  {
    "component_type": "ComponentWithStructuredGeneration",
    // ...
    "llm_config": {
      // ...
    },
    "prompt": "What is the fastest italian car?",
    "outputs": [
      {"title": "brand", "type": "string", "description": "The brand of the car"},
      {"title": "model", "type": "string", "description": "The name of the car's model"},
      {"title": "hp", "type": "integer", "description": "The horsepower amount, which expresses the car's power"}
    ]
  }

Can generate an object as follows:

.. code-block:: json

  {"brand": "Pininfarina", "model": "Battista", "hp": 1400}

But it should then expose each property separately. Note that the descriptions of properties could be forwarded
to LLMs to improve the quality of the generation.
Therefore, providing a proper description might improve the quality of the final outcome.

.. note::
    The current version Agent Spec does not define how structured generation is enforced on the LLM.
    In case structured generation is requested to an LLM that does not natively support it, it's up to
    the Agent Spec Runtime implementation to raise an exception, or to implement it in a different form.

.. _openaicompatiblellms:

OpenAI Compatible LLMs
^^^^^^^^^^^^^^^^^^^^^^

This class of LLMs groups all the LLMs that are compatible with either the
`OpenAI chat completions APIs <https://platform.openai.com/docs/api-reference/chat>`_ or the `OpenAI Responses APIs <https://platform.openai.com/docs/api-reference/responses>`_.
The API type can be configured by using the ``api_type`` parameter, which takes one of 2 string values, namely
``chat_completions`` or ``responses``. By default, the API type is set to chat completions. Additionally, an optional
``api_key`` can be set for the remote LLM model.

.. code-block:: python

   class OpenAiCompatibleConfig(LlmConfig):
     model_id: str
     url: str
     api_type: Literal["chat_completions", "responses"] = "chat_completions"
     api_key: SensitiveField[Optional[str]] = None

Based on this class of LLMs, we provide two main implementations.

vLLM
''''

Used to indicate all the LLMs deployed through `vLLM <https://docs.vllm.ai/en/latest/>`_.

.. code-block:: python

   class VllmConfig(OpenAiCompatibleConfig):
     pass

Ollama
''''''

Used to indicate all the LLMs deployed through `Ollama <https://ollama.com/>`_.
Note that as of November 2025, Ollama does not support the `OpenAI Responses APIs <https://platform.openai.com/docs/api-reference/responses>`_,
so using this API type may lead to unexpected behavior.

.. code-block:: python

   class OllamaConfig(OpenAiCompatibleConfig):
     pass


OpenAI
^^^^^^

This class of LLMs refers to the models offered by `OpenAI <https://openai.com>`_.
Similar to :ref:`OpenAI Compatible LLMs <openaicompatiblellms>`, you can also configure the ``api_type`` parameter,
which takes one of 2 string values, namely ``chat_completions`` or ``responses``.
By default, the API type is set to chat completions. Additionally, an optional
``api_key`` can be set for the remote LLM model.

.. code-block:: python

   class OpenAiConfig(LlmConfig):
     model_id: str
     api_type: Literal["chat_completions", "responses"] = "chat_completions"
     api_key: SensitiveField[Optional[str]] = None

OCI GenAI
^^^^^^^^^

This class of LLMs refers to the models offered by
`Oracle GenAI <https://docs.oracle.com/en-us/iaas/Content/generative-ai/home.htm>`_.

OCI models require to specify the authentication method to be used when accessing the models.
Therefore, besides the attributes required to select the model to use, the ``OciGenAiConfig`` contains
the authentication information as part of the ``LlmConfig``.

The ``serving_mode`` parameter determines whether the model is served on-demand or in a dedicated capacity.
On-demand serving is suitable for variable workloads, while dedicated serving provides consistent performance
for high-throughput applications.

The ``provider`` parameter specifies the underlying model provider, META for Llama models or COHERE for cohere
models. When ``None``, it is automatically detected based on the ``model_id``. When the ``serving_mode`` is ``DEDICATED``
the ``model_id`` does not indicate what ``provider`` should be used so the user has to specify it manually,
knowing what model it is.

The API type can be configured by using the ``api_type`` parameter, which takes one of 3 string values, namely ``oci``,
``openai_chat_completions`` and ``openai_responses``. By default, the API type is set to ``oci``.
The ``conversation_store_id`` parameter allows to specify the conversation store OCI resource to use top persist
conversations when using the openai responses API.

.. code-block:: python

   class OciGenAiConfig(LlmConfig):
     model_id: str
     compartment_id: str
     serving_mode: Literal["ON_DEMAND", "DEDICATED"] = "ON_DEMAND"
     provider: Optional[Literal["META", "GROK", "COHERE", "OTHER"]] = None
     client_config: OciClientConfig
     api_type: Literal["chat_completions", "responses"] = "chat_completions"
     conversation_store_id: Optional[str] = None

.. note::
    The authentication components must not contain any sensitive information about the authentication,
    like secrets, API keys, passwords, etc. Users must not include this information anywhere, as exported
    Agent Spec configurations should never include sensitive data.

OCI Client Configuration
''''''''''''''''''''''''

The ``OciClientConfig`` contains all the settings needed to perform the authentication to use OCI services.
This object is used by the ``OciGenAiConfig`` in order to access the Gen AI services of OCI and perform LLM calls.
This client configuration is also used by other components that require access to the OCI services (e.g., the
``OciAgent`` presented later in this document).
More information about how to perform authentication in OCI is available on the
`Oracle website <https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdk_authentication_methods.htm>`_.

.. code-block:: python

    class OciClientConfig(Component):
        service_endpoint: str
        auth_type: Literal["SECURITY_TOKEN", "INSTANCE_PRINCIPAL", "RESOURCE_PRINCIPAL", "API_KEY"]

Based on the type of authentication the user wants to adopt, different specifications of the ``OciClientConfig``
are defined. In the following sections we show what client extensions are available and their specific parameters.


OciClientConfigWithSecurityToken
''''''''''''''''''''''''''''''''

Client configuration that should be used if users want to use authentication through security token.

.. code-block:: python

    class OciClientConfigWithSecurityToken(OciClientConfig):
        auth_profile: str
        auth_file_location: SensitiveField[str]
        auth_type: Literal["SECURITY_TOKEN"] = "SECURITY_TOKEN"

OciClientConfigWithApiKey
'''''''''''''''''''''''''

Client configuration that should be used if users want to use authentication with API key.

.. code-block:: python

    class OciClientConfigWithApiKey(OciClientConfig):
        auth_profile: str
        auth_file_location: SensitiveField[str]
        auth_type: Literal["API_KEY"] = "API_KEY"

OciClientConfigWithInstancePrincipal
''''''''''''''''''''''''''''''''''''

Client configuration that should be used if users want to use instance principal authentication.

.. code-block:: python

    class OciClientConfigWithInstancePrincipal(OciClientConfig):
        auth_type: Literal["INSTANCE_PRINCIPAL"] = "INSTANCE_PRINCIPAL"

OciClientConfigWithResourcePrincipal
''''''''''''''''''''''''''''''''''''

Client configuration that should be used if users want to use resource principal authentication.

.. code-block:: python

    class OciClientConfigWithResourcePrincipal(OciClientConfig):
        auth_type: Literal["RESOURCE_PRINCIPAL"] = "RESOURCE_PRINCIPAL"

Tools
~~~~~

A tool is a procedural function or a flow that can be made available to
an Agent to execute. In a flexible Agent context, the Agent can decide
to call a tool based on its signature and description. In a flow
context, a node would need to be configured to call a specific tool.

Where the actual tool functionality is actually executed or run depends
on the type of the tool:

- **ServerTools** are executed in the same runtime environment that the
  Agent is being executed in. The definitions of these tools therefore
  must be available to the Agent's environment. It is expected that
  this type of tool will be very limited in number, and relatively
  general in functionality (e.g., human-in-the-loop).
- **BuiltinTools** are defined and implemented by the execution engine.
  Which built-in tools are available, their semantics and how to configure
  them depends on, and should be verified by, the execution engine.
  Built-in tools are expected to be executed in the same runtime
  environment that the Agent is being executed in.
- **ClientTools** are not executed by the executor, the client must
  execute the tool and provide the results back to the executor (similar
  to OpenAI's function calling model)
- **RemoteTools** are run in an external environment, but triggered by
  an RPC or REST call from the Agent executor.
- **MCPTools** interact with Model Context Protocol (MCP) servers to
  support remote tool execution.

Agent Spec is not supposed to provide an implementation of how these types of
tools should work, but provide their representation, so that they can be
correctly interpreted and ported across platforms and languages.

That said, as previously argued, a tool is a function that is called
providing some parameters (i.e., inputs), performs some transformation,
and returns some values (i.e, outputs). Of course the function has a
name, and a description that can be used by an LLM in order to
understand when it's relevant to perform a task. Therefore, we can
define a Tool as a simple extension of ComponentWithIO.

We let tools specify **multiple outputs**. In this case, the expected return value
of the tool is a dictionary where each entry corresponds to an element
specified in the outputs. The key of the dictionary entry must match the
name of the property specified in the outputs. The runtime will parse the
dictionary in order to extract the different outputs and bind them correctly.

Tools also include a boolean ``requires_confirmation`` attribute.
When set to true, this signals that execution environments should require
user/operator approval before running the tool, which is especially relevant
for tools performing critical or sensitive actions.

While ServerTool and ClientTool do not require specific additional
parameters, the RemoteTool, MCPTool and the BuiltinTool require to include also
the details needed to perform the remote call to the tool or to identify
the correct built-in tool.

.. code-block:: python

   class Tool(ComponentWithIO):
     # Flag to make tool require user confirmation before execution.
     requires_confirmation: bool

   class ClientTool(Tool):
     pass

   class ServerTool(Tool):
     pass

   class RemoteTool(Tool):
     # Basic parameters needed for a remote API call
     url: str
     http_method: str
     api_spec_uri: Optional[str]
     data: Any
     query_params: Dict[str, Any]
     headers: Dict[str, Any]
     sensitive_headers: SensitiveField[Dict[str, Any]]

   class MCPTool(Tool):
     client_transport: ClientTransport

   class BuiltinTool(Tool):
     tool_type: str
     configuration: Optional[Dict[str, Any]]
     executor_name: Optional[Union[str, List[str]]]
     tool_version: Optional[str]

An important security aspect of Agent Spec is the exclusion of arbitrary
code from the agent representation. The representation contains a complete description
of the tool—its attributes, inputs, outputs, and related metadata—but does
not embed executable code.

.. _remotetools:

Remote Tools
^^^^^^^^^^^^

One common way to make tools available to agents, is to make them
available under the for of REST APIs that the agent can call when the
tool has to be executed.

Compared to ServerTools and ClientTools, these tools require more
information to be specified, in order to perform the actual request.

We add the same parameters as the APINode (see the Nodes library in the
Flows - Nodes section below), in order to perform a complete REST call
in the right manner.

Note that, similarly to the APINode, we allow users to use placeholders
(as described in section 5.3.4) in all the string attributes of the
RemoteTool (i.e., url, http_method, api_spec_uri, and in the dict values
of data, query_params, headers, and sensitive_headers). The ``data`` parameter in
``RemoteTool`` is what ends up in the body of the request.
If ``data`` is specified as a string, the runtime must encode and pass it as the body of the HTTP request,
otherwise the value of ``data`` should be JSON serializable and runtimes are
expected to dump it when adding it in the body of the HTTP request.
The data is passed to the request as Form Data if the header ``{"Content-Type": "application/x-www-form-urlencoded"}`` is specified.

MCP Tools
^^^^^^^^^

MCP Tools are a specialized type of tool that connects to servers implementing
the Model Context Protocol (MCP). They extend the base ``Tool`` with transport
configurations for secure, remote execution.

Like other tools, MCP Tools define inputs, outputs, and metadata but include a
``client_transport`` for managing connections (e.g., via SSE or Streamable HTTP
with mTLS) (details about the client transport can be found in
:ref:`the MCP section <agentspecmcpspec_nightly>` below).

.. code-block:: python

   class MCPTool(Tool):
     client_transport: ClientTransport

MCP Tools follow the same security principles as other tools: no arbitrary code is
embedded in the representation. Execution occurs remotely via the specified transport, with the
runtime handling session management and data relay.

For example, an MCP Tool might use an ``SSEmTLSTransport`` to securely call a remote
function for data processing.


ToolBoxes
^^^^^^^^^

A ToolBox is a component that exposes one or more tools to components. ToolBoxes are not
executable by themselves; they are discovery/aggregation mechanisms. A component can
receive tools from both:

- tools (concrete Tool instances), and
- toolboxes (ToolBox instances that expose tools discovered elsewhere).

When the set of tools is dynamic, its content should be established just before use by the
consuming component. ToolBoxes do not embed executable code or the full discovered tool list
at serialization time. Discovery happens at runtime.

A ToolBox also exposes a flag ``requires_confirmation`` (default to False); it exists to let users enforce
confirmation for the entire toolbox without having to set ``requires_confirmation=True`` on every
tool it provides. If the tool box does not require confirmation, confirmation is still required
for individual tools which explicitly specify it.

.. code-block:: python

   class ToolBox(Component):
     requires_confirmation: bool = False


MCPToolBox
''''''''''

MCPToolBox connects to an MCP server via a ClientTransport and exposes tools discovered
from that server to components.


.. code-block:: python

   class MCPToolBox(ToolBox):
     client_transport: ClientTransport
     tool_filter: Optional[List[Union[str, MCPToolSpec]]]


The ``client_transport`` specifies the MCP ClientTransport used to discover remote
MCP tools and route calls to them.

.. _mcp_toolfilter_rules:

By default the ``tool_filter`` parameter is null and the MCPToolBox exposes all tools
discovered from the MCP server. When the ``tool_filter`` is not null, the toolbox only
exposes the listed tools. For each entry in the list:

- If an entry is a ``str``, the MCP server MUST expose a tool with the exact name, or the configuration is invalid.
- If an entry is an ``MCPToolSpec``, it is treated as a strict signature to validate against the tool exposed by the MCP server:

  - The name MUST exactly match a name of an exposed tool.
  - If description is provided, it overrides the exposed tool description.
  - If inputs are provided, they MUST exactly match the exposed tool input schema by name and JSON Schema type.
    On mismatch, the configuration is invalid.
  - If outputs are provided, they MUST consist of exactly one string-typed property with the expected tool output
    name and optional description.
  - If the :ref:`tool confirmation flag <mcp_tool_spec_def>` is provided, its value is used; otherwise, it defaults to False.

The ``tool_filter`` information should be validated against the exposed MCP tools each time the tools
are provided to the consuming component (as the toolbox content may change dynamically). If any of the
constraints described above is not respected, the runtime can raise an error.

.. note::

  ToolBoxes are not valid values for ToolNode.tool;
  ToolNode requires a concrete Tool (including MCPTool).


MCPToolSpec
'''''''''''

``MCPToolSpec`` is a declarative tool signature used inside ``MCPToolBox.tool_filter`` to
pin and validate specific remote MCP tools.

.. _mcp_tool_spec_def:
.. code-block:: python

   class MCPToolSpec(ComponentWithIO):
    requires_confirmation: bool

See the :ref:`filter rules for the MCPToolBox <mcp_toolfilter_rules>` to see how the ``MCPToolSpec``
is used.

Built-in Tools
^^^^^^^^^^^^^^

Agent Spec execution engines may offer built-in tools out of the box and ready to use.
For example,

- An executor could provide a tool to search websites.
  Users do not need to provide a tool implementation, but only need to specify which website to search on.
- An executor running in a database might expose a native vector retrieval tool
  with the possibility to configure which tables to search on or how many relevant results to return.

Built-in tools in Agent Spec let users configure these types of tools.

.. code-block:: python

   class BuiltinTool(Tool):
     tool_type: str
     configuration: Optional[Dict[str, Any]]
     executor_name: Optional[Union[str, List[str]]]
     tool_version: Optional[str]

- ``tool_type`` identifies the runtime-provided built-in tool.
- ``configuration`` allows to configure the tool.
  Legal configurations should be documented by the runtime providing the tool.
  Not all built-in tools require configuration.
- ``executor_name`` optionally allows to specify the runtime name providing the tool for validation purposes
  (i.e., for the runtime to check that the tool config is intended for it).
  The correct value to put should be documented by the runtime providing the tool.
- ``tool_version``: if the runtime provides multiple versions of the tool, the built-in tool version can be specified here.

The advantage of built-in tools is that no tool implementation needs to be provided by the users.
The disadvantage is that built-in tools are specific to the Agent Spec execution runtime which provides them.
In general, which built-in tools are available differs for each execution runtime, and using them might limit cross-framework portability.


Implementing Built-in Tools as Execution Engine Developer
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''

For Agent Spec execution engine developers implementing built-in tools,
the following documentation should be provided to users.

- The semantics of tool
- The name of the tool, passed to the ``tool_type`` field
- The expected input and output properties (title and type), if any
- The expected static configuration parameters, if any
- The executor name. Users can optionally specify this field s.t.
  the execution engine can validate the tool is intended for it.
- The tool version. If there are multiple versions of the tool,
  this field can be used to select which tool to run. Furthermore, it should
  be documented what the default behavior is if multiple tool versions are
  available but no ``tool_version`` is specified.

Execution engine developers should validate that inputs, outputs and configuration
parameters of the built-in tool component provided in the configuration are as expected.

Furthermore, to prevent unintended behavior, execution engine developers should
validate the ``executor_name`` and ``tool_version`` fields, if they are provided,
and raise an error if the values are not expected.

.. collapse:: Example documentation for built-in tool...

    **Vector Search Built-in Tool**

    Retrieves the most relevant documents from a table based on cosine similarity
    between a query text and stored embeddings.

    **Tool Name:** "vector_retrieval_tool"

    **Inputs:**

    - ``StringProperty(title="query")``: user query text.

    **Outputs:**

    - ``ListProperty(title="results", item_type=StringProperty())``:
        list of retrieved document contents.

    **Configuration Parameters:**

    - ``schema`` (str): schema containing the table.
    - ``target_table`` (str): name of the table storing embeddings.
    - ``target_column`` (str): column containing embedding vectors.
    - ``top_k`` (int): number of nearest results to return.

    **Executor Name:** "my_execution_engine>=25.4.1".

    **Tool Version:**  Our vector_retrieval_tool is not versioned.


Execution flows
~~~~~~~~~~~~~~~

Execution flows (or graphs) are directed, potentially-cyclic workflows.
They can be thought of as "subroutines" that encapsulate consistently-repeatable processes.

Each execution flow requires 0 or more inputs (e.g., any input edges expressed on the
starting node of the graph) and may produce 0 or more outputs (e.g., any
output edges expressed by the terminal nodes of the graph - note that a
graph can have more than one terminal node, in the event of branching logic).

Flow
^^^^

``Flow`` objects specify the entry point to the graph, the nodes, and edges for the graph.
Inner Components of the flow are described in subsequent sections.

.. code-block:: python

   class Flow(ComponentWithIO):
     start_node: Node
     nodes: List[Node]
     control_flow_connections: List[ControlFlowEdge]
     data_flow_connections: Optional[List[DataFlowEdge]]

A flow exposes a (sub)set of the union of all the outputs exposed by all the EndNodes.
However, if an output defined in the flow does not have a corresponding output with the same name in every EndNode,
then a default value for that output in the flow definition must be specified.
The default value is used in case the EndNode executed at runtime does not expose an output with that name.
It is not possible to define two outputs with the same name and different types in two distinct EndNodes of the same flow.
It is instead possible to define different default values for outputs with the same name in distinct EndNodes.

For example, let's assume to have a flow with two EndNodes, called respectively ``end_node_a`` and ``end_node_b``.
``end_node_a`` exposes one output called ``output_a``, while ``end_node_b`` exposes another output called ``output_b``.
We want to expose both the outputs from the flow, so we will include them in the ``outputs`` definition of the flow
and, since they are not common to all the EndNodes in the flow, we must define a default value for them.
We assign ``default_value_a`` as default for ``output_a`` and ``default_value_b`` as default for ``output_b``.
Note that these default values are required to be included in the flow specification, not in the EndNodes.
Let's now assume that at runtime we execute the flow, and we complete it through the ``end_node_a`` with a value
for ``output_a`` set to ``value_a``. This means that as output values of the flow we will get ``value_a`` for
``output_a``, as it was generated by the EndNode that was executed, while we will get ``default_value_b`` for ``output_b``,
as no value was generated for ``output_b`` by the EndNode being executed.

As inputs, a flow must expose all the inputs that are defined in its StartNode.
Note that flows must have a unique StartNode, which is defined by the ``start_node`` parameter,
and it should appear in the list of ``nodes``.

Conversation
^^^^^^^^^^^^

At the core of the execution of a conversational agent there's the
conversation itself. The conversation is implicitly passed to all the
components throughout the flow. It contains the messages being produced
by the different nodes: each node in a flow and each agent can append
messages to the conversation if needed. Messages should have, at least,
a type (e.g., system, agent, user), content, the sender, and the recipient.

Sub-flows and sub-agents contained in a Flow (i.e., as part of AgentNode and FlowNode,
see the Node section for more information) share the same conversation of the Flow they belong to.
Sub-agents and sub-flows should have access to all the messages in the conversation,
and they should append in the same conversation all the messages that are generated during
their execution. At the end of the execution of a sub-flow/sub-agent, the Flow that
contains them should have access to all the messages generated before and during the execution
of the sub-flow/sub-agent.

.. warning::
    The conversation of the parent Flow is shared with sub-flows and sub-agents and vice-versa.
    Do not use sub-flows or sub-agents for information isolation purposes.
    For example, if a sub-agent calls a remote model, it may forward the entire conversation to that model.

I/O Data Space
^^^^^^^^^^^^^^

Alongside the conversation, flows have another data space composed of inputs and outputs generated by nodes.

Depending to their definition, nodes can require inputs and generate outputs.
When a node generates an output, this is exposed by the node itself, so that other nodes can consume it if needed.
In order to use an output's value as a component's input, there are two options:

- A data flow edge between the output and the input is created (see :ref:`Data relationships <dataflow>`);
- In case the data flow is not defined (see :ref:`Optionality of data relationships <dataflow_optionality>`),
  the input and output property names match.

An output must be generated before it can be used to fulfil an input.
In other words, the node generating an output must be executed before the node consuming it as input.
An exception is made if the input property has a default value defined.
In that case, if the respective output was not generated, the default value is used instead.

.. note::
    The Conversation and the I/O Data Space concepts are disjoint and independent from each other.
    Agent Spec Runtimes are free to implement them separately or not (e.g., with the conversation
    as a special entry in the I/O space), as long as the Agent Spec language semantic is respected.

Node
^^^^

A ``Node`` is a vertex in an execution flow.

.. code-block:: python

   class Node(ComponentWithIO):
       branches: List[str]

Being an extension of ComponentWithIO, the Node already has the
attributes of Component (id, name, ...) and ComponentWithIO (inputs and
outputs).

Additionally, the each Node class has an attribute called branches used
to define the names of the branches that can follow the current node.
This is used to support cases where branching in control flow is needed
(see the respective section in this page). For example:

- In a flow, at some point we need to take different paths based on the
  value of an input, or the result of a condition (e.g., the equivalent
  of an in-else statement)
- A flow used in a subflow has multiple end nodes, that can be reached
  as a result of an earlier branching, and that might result in
  different follow-up operations, so the different outgoing branches
  have to be exposed

Most nodes that are part of the flow have at least one default branch,
used to define which is the following node to be executed, that we
define with the name ``next`` . Note that the branches attribute of the
Node is typically managed (i.e., automatically inferred) by the
implementation of the Node, but it will appear in the representation.

Each type of node can also have other specific attributes that define
its configuration. They are defined in the table in this section
containing the list of node types available in Agent Spec.

The list of inputs and outputs exposed by a Node is supposed to be
automatically (and dynamically) generated by the Node instance itself in
one of the SDKs. The user is still allowed to explicitly define them
when generating the representation from an SDK, but the set of inputs and/or outputs
manually specified must match with the expected one as per node's
generation (i.e., all the expected inputs and/or outputs must be present
in the list specified by the user). This allows user specifying better
the type of an input/output with respect to the one inferred
automatically by the node (e.g., specify that a value in a prompt
template is supposed to be an integer instead of a generic string). The
lists of inputs and outputs will always appear in the representation of every node.

The standard library of available nodes is described in a separate
section later.

Some nodes infer inputs from special parts of their configurations. For
example, some nodes (e.g., the LLMNode) extract inputs from a property
called ``prompt_template``. We let users define placeholders in the
configuration parts that allow that, by simply wrapping the name of the
property among a double set of curly brackets. The node will
automatically infer the inputs by interpreting those configurations, and
the actual value of the input/output will be replaced at execution time.

For example, setting the prompt_template configuration of an LLMNode to
"You are a great assistant. Please help the user with this request:
{{request}}" will generate an input called "request" of type string.

Relationships / Edges
^^^^^^^^^^^^^^^^^^^^^

For flows, Agent Spec defines separate relationships (edges) for both
properties and control flow. This allows Agent Spec to unambiguously handle
patterns such as conditional branches and loops, which are very
challenging to support with data-only flow control.

Relations are only applicable for flows. All relations express a
transition from some source node to some target node.

Control edges
'''''''''''''

A control relationship defines a *potential* transition from a branch of
some node to another. The actual transition to be taken during a given
execution is defined by the implementation of a specific node.

.. code-block:: python

   class ControlFlowEdge(Component):
     from_node: Node
     from_branch: Optional[str]
     to_node: Node

The from_branch attribute of a ControlFlowEdge is set to null by
default, which means that it will connect the default branch (i.e.,
``next`` ) of the source node.

Data relationships (I/O system components)
''''''''''''''''''''''''''''''''''''''''''

Considering the I/O system, a component id alone is not sufficient to
identify a data relationship. A component may take multiple input
parameters and/or produce multiple output values. We must be able to
determine what value or reference is mapped to each input, and where
each output is used.

Sources (inputs) can be connected to outputs of another node, or to
static values.

Destination (outputs) can be connected to inputs of another node, or
left unconnected.

.. code-block:: python

   class DataFlowEdge(Component):
     source_node: Node
     source_output: str
     destination_node: Node
     destination_input: str

Connecting multiple data edges
''''''''''''''''''''''''''''''

In the case of control flow, multi-connections from the same outgoing branch
of a node are not allowed (note that we do not enable parallelism through edges).
Edges define which are the allowed "next step"  transitions,
so that it's clear that it's possible to execute one node after the execution of another.
For more information about scenarios with multiple outgoing branches (e.g., based on the value
of a condition), please refer to the section about Conditional branching.

For what concerns the data flow, instead, it is sometimes necessary to connect two
different data outputs to the same input. Two simple examples follow:

|image7|

Therefore, we let users connect multiple data outputs to the same input.
If multiple outputs are connected to the same input, the last node that
was executed and that has an output connected to the input will have the priority.
In other words, the behavior is similar to having the input exposed as a public
variable, and every node that has an output connected to that input updates its value.

Optionality of data relationships
'''''''''''''''''''''''''''''''''

Some frameworks do not require to specify the data flow, as they assume
that all the properties are publicly exposed in a shared "variable
space" that any component can access, and the read/write system is
simply name-based.

In practice, this means that:

- when a component has an input with a specific name, it will look into
  the public variable space to read the value of the variable with that
  name
- when a component has an output with a specific name, it will write (or
  overwrite if it already exists) into the public variable space the
  variable with that name

The main advantage of this approach is that users do not have to define
any data flow, making the building experience faster.

We let users adopt this type of I/O system by setting the
``data_flow_connections`` parameter of the Flow to None.

In this case, a name-based approach explained above will be adopted, which means that
if a component writes an output whose name matches a variable space entry,
the respective value in the variable space is overwritten.

Note that this name-based approach can be expressed defining explicitly
Data Flow connections (but the opposite is not possible) by connecting
all the outputs to the inputs with the same name, following the control
flow connections in the flow in order to account for overwrites.

.. collapse:: How to translate public values into data flow edges...

    As just affirmed, it's possible to transform the name-based approach to
    the data flow one, by creating automatically the right set of
    DataFlowEdges.

    As a basic approach, this translation can be done by simply connecting
    all the outputs to all the inputs with the same name. The priority-based
    solution for value updates explained in previous section 5.4.4.4.3 will
    ensure the correct behavior of the data flow.

    In order to minimize the amount of connections created, it's possible to
    also adopt different solutions that do a simulation of an execution by
    following the control flow connections. SDKs are allowed to implement
    one version of this smarter solution.

Conditional branching
^^^^^^^^^^^^^^^^^^^^^

Being able to follow different paths (or branches) based on some
conditions is an important feature required to represent processes as
flows (e.g., flowcharts).

Conditional branching in Agent Spec is supported through a special step called
BranchingNode (detailed later), a node that maps input values to
different branches through a key-value mapping.

Nodes can have multiple outgoing branches, as previously mentioned in this page.
The ``branches`` attribute of the Node is automatically filled and managed
by the implementation of the Node, but it will appear in the representation. Both
``Node.branches`` and ``ControlFlowEdge.from_branch`` are set to null by
default, and that is the default behavior in case one single branch is
going out of a node (this is compatible with the definition of Node and
ControlFlowEdge in this page). If a value is specified for the branches
of the from_node of a ControlFlowEdge, then also from_branch must be set
to one of the values in branches. GUIs will show the different branches
as output flows of the node, so that each of them can be connected in a
1-to-1 manner with another node's flow input.

.. _parallelization:

Parallelization
^^^^^^^^^^^^^^^

Support for parallelism in Agent Spec is limited to specific nodes that explicitly claim to support it.
The boundaries of parallelism (i.e., fork and join) are well defined, and coincide with those of the node where
parallelism is allowed.

.. note::

  Agent Spec does not enforce a specific way to implement parallelism. Runtimes can implement parallelism with different
  techniques (including, but not limited to, multi-processing and multi-threading), as long as they respect
  Agent Spec language directives and :ref:`security guidelines <securityconsiderations>`.
  Developers creating Agent Spec configurations should not make any assumption on how parallelism is implemented.

During parallel execution, the execution order among parallel flows is not guaranteed.
Therefore, no assumptions should be made about the order or timing of operations, nor their atomicity.

Consequently, take special precautions in flows and nodes that are supposed to be executed in parallel:

- Avoid placing interrupts or user input/output operations (including, but not limited to, message nodes,
  agent invocations, client tools) within parallel branches, as this can result in unpredictable behavior.
- Do not perform write operations on shared stateful objects in parallel nodes to prevent race conditions or inconsistent states.
- Parallel blocks should ideally be limited to independent, stateless tasks.
  Carefully review flows with parallelism to ensure they remain safe and predictable.


Standard library of nodes to use in flows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here's the list of nodes supported in Agent Spec:

- LLMNode: uses a LLM to generate some text from a prompt
- APINode: performs an API call with the given configuration and inputs
- AgentNode: runs a multi-round conversation with an Agentic Component, used to
  better structure agentic components and easily reuse them.
- FlowNode: runs a flow inline, used to better structure and easily
  reuse Flows
- CatchExceptionNode: Used to catch exceptions that may be raised during the
  execution of a given subflow.
- MapNode: performs a map-reduce operation on a given input collection,
  applying a specified Flow to each element in the collection
- StartNode:  entry point of a flow
- EndNode: exit point of a flow
- BranchingNode: allows conditional branching based on the value of an input
- ToolNode: executes a tool
- InputMessageNode: interrupts temporarily the execution to retrieve user input
- OutputMessageNode: appends an agent message to the conversation
- ParallelMapNode: performs a parallel map-reduce operation on a given input collection
- ParallelFlowNode: execute a list of subflows in parallel


A more detailed description of each node follows.

.. list-table::
    :widths: 5 20 15 15 15 15
    :class: wideoutertable
    :header-rows: 1

    * - Name
      - Description
      - Parameters
      - Input
      - Output
      - Outgoing branches
    * - LlmNode
      - * Uses a LLM to generate some text or a structured output from a prompt
        * Configured with a prompt template, a LLM and optionally generation parameters (number of tokens, etc)
        * Single round
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - prompt_template
              - Defines the prompt sent to the model. Allows placeholders, which can define inputs
              - string
              - Yes
              - -
            * - llm_configuration
              - The LLM to use for this generation
              - LlmConfig
              - Yes
              - -

      - One per variable in the prompt template
      - Two alternatives are available:

        * A single string property, that represents the raw text generated by the LLM
        * A non-string property, or multiple properties. In this case, structured generation is triggered, following the property schemas provided as outputs

      - One, the default next
    * - ApiNode
      - * Performs an API call with the given settings and inputs
        * Provides the parts of the API call response as outputs
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - url
              - The URL to send the request. Allows placeholders, which can define inputs
              - string
              - Yes
              - -
            * - http_method
              - The HTTP method. Allows placeholders, which can define inputs
              - string
              - Yes
              - -
            * - api_spec_uri
              - The path to get the specification json. Allows placeholders, which can define inputs
              - string | null
              - No
              - null
            * - data
              - The data to send to this API call. Behaves the same way as the ``data`` parameter in :ref:`RemoteTool <remotetools>`.
              - any
              - No
              - {}
            * - query_params
              - Query parameters for the API call. Allows placeholders in dict values, which can define inputs
              - object[str, any]
              - No
              - {}
            * - headers
              - Additional headers for the API call. Allows placeholders in dict values, which can define inputs
              - object[str, any]
              - No
              - {}
            * - sensitive_headers
              - Additional headers for the API call. These additional headers are merged with the headers provided
                as `headers` when executing the request, but these headers are excluded from exported configuration
                thus they are better suited to contain sensitive information not intended to be shared as widely as
                the exported configuration.
              - object[str, any]
              - No
              - {}

      - Inferred from the json spec retrieved from API Spec URI, if available and reachable.
        Empty otherwise (users will have to manually specify them)
      - Inferred from the json spec retrieved from API Spec URI, if available and reachable.
        Empty otherwise (users will have to manually specify them)
      - One, the default next
    * - AgentNode
      - * Runs a conversation with an Agentic Component (potentially multi-round)
        * The component is started giving the specified inputs
        * The component provides the specified outputs
        * By separating the component definition from the node executing it (this node),
          we can handle cases where the same component (defined once) is executed in several places of a flow,
          or by different flows (future versions)
        * If the agentic component is a flow, the flow is ran in a different conversation (isolated)
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - agent
              - The agent to be executed
              - Agent
              - Yes
              - -

      - The ones defined by the Agent
      - The ones defined by the Agent
      - One, the default next
    * - FlowNode
      - * Runs a Flow
        * Used to better structure agents and easily reuse flows across them
        * The flow is started giving the specified inputs
        * The flow provides the specified outputs
        * The flow is run as it was inlined with the overall flow
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - subflow
              - The flow to be executed
              - Flow
              - Yes
              - -

      - Inferred from the inner structure.
        It's the sets of inputs required by the StartNode of the inner flow
      - Inferred from the inner structure.
        It's the set of outputs defined in the ``subflow``'s specification
      - Inferred from the inner flow: one per unique ``branch_name`` of the ``subflow``'s EndNodes
    * - MapNode
      - The MapNode is used when we need to map a sequence of nodes to each of the values
        defined in a list (from output of a previous node). This node is responsible to
        asynchronically map each value of a collection (defined in input_schema) to the first node
        of the 'subflow' and reduce the outputs of the last node of the 'subflow' to
        defined variables (defined in output_schema)
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - subflow
              - The flow that should be applied to all the input values
              - Flow
              - Yes
              - -
            * - reducers
              - The way the outputs of the different executions (map) should be collected together (reduce).
                It's a dictionary mapping the name of an output to the respective reduction method.
                Currently supported reduction methods are: ``append``, ``sum``, ``average``, ``max``, ``min``.
                Allowed methods depend on the type of the output:

                - ``sum``, ``average``, ``max``, ``min`` are applicable only to ``integer`` and ``number`` types
                - ``append`` is applicable to all the types

              - object[str, str] | null
              - No
              - null, each output is aggregated through value concatenation (append)

      - Inferred from the inner structure (as defined in FlowNode).
        The names of the inputs will be the ones of the inner flow,
        complemented with the ``iterated_`` prefix. Their type is
        ``Union[inner_type, List[inner_type]]``, where ``inner_type``
        is the type of the respective input in the inner flow.

        - If an input of type ``inner_type`` is connected, the same value will used in
          all the executions of the inner flow
        - If an input of type ``List[inner_type]`` is connected, the input values will be iterated over

        Note that all the input lists must have the same length, otherwise a runtime error will be thrown.

      - Inferred from the inner structure (as defined in FlowNode),
        combined with the reducer method of each output.
        The names of the outputs will be the ones of the inner flow,
        complemented with the ``collected_`` prefix. Their type depends
        on the ``reduce`` method specified for that output:

        - ``List`` of the respective output type in case of ``append``
        - same type of the respective output type in case of ``sum``, ``avg``

      - One, the default next
    * - CatchExceptionNode
      - * Used to catch exceptions that may be raised during the execution of a given subflow.
        * If an exception is caught during the subflow execution, branches out to an exception branch.
          Otherwise, uses the transitions/branches specified for the subflow.
        * Exposes the inputs of the subflow and outputs the subflow outputs with additional information
          about a potentially caught exception (for more information read the :ref:`security guidelines <securitycatchexceptionnode>`).
        * When the subflow runs to completion without failure, this node returns the subflow outputs.
          Otherwise, it returns the default values for the subflow outputs, along with the exception
          information.
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - subflow
              - Flow to execute and catch errors from
              - Flow
              - Yes
              - -

      - Same as the inputs from the ``sub_flow``.

      - Composed of:

        * The outputs of the ``sub_flow``. If an exception is raised, will output the default values
          of each output property of the subflow. As a consequence, all outputs of the node must have
          default values. If they are not already specified at the subflow level, the developer must
          specify them in the output properties of the CatchExceptionNode node.
        * The caught exception information, named ``caught_exception_info``: (optional string,
          default to null when no exception is raised).

      - Composed of:

        * The branches of the ``sub_flow``;
        * A branch ``caught_exception_branch`` for when an exception is caught.
    * - ParallelMapNode
      - The ParallelMapNode is used when we need to map a sequence of nodes to each of the values
        defined in a list (from output of a previous node). Its functionality is equivalent to the MapNode,
        the only difference is that in this node the map operation is supposed to be performed in parallel.
        Please check the concerns regarding parallel execution depicted in the :ref:`parallelization section <parallelization>`.
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - subflow
              - The flow that should be applied to all the input values
              - Flow
              - Yes
              - -
            * - reducers
              - The way the outputs of the different executions (map) should be collected together (reduce).
                It's a dictionary mapping the name of an output to the respective reduction method.
                Currently supported reduction methods are: ``append``, ``sum``, ``average``, ``max``, ``min``.
                Allowed methods depend on the type of the output:

                - ``sum``, ``average``, ``max``, ``min`` are applicable only to ``integer`` and ``number`` types
                - ``append`` is applicable to all the types

              - object[str, str] | null
              - No
              - null, each output is aggregated through value concatenation (append)

      - Inferred from the inner structure (as defined in FlowNode).
        The names of the inputs will be the ones of the inner flow,
        complemented with the ``iterated_`` prefix. Their type is
        ``Union[inner_type, List[inner_type]]``, where ``inner_type``
        is the type of the respective input in the inner flow.

        - If an input of type ``inner_type`` is connected, the same value will used in
          all the executions of the inner flow
        - If an input of type ``List[inner_type]`` is connected, the input values will be iterated over

        Note that all the input lists must have the same length, otherwise a runtime error will be thrown.

      - Inferred from the inner structure (as defined in FlowNode),
        combined with the reducer method of each output.
        The names of the outputs will be the ones of the inner flow,
        complemented with the ``collected_`` prefix. Their type depends
        on the ``reduce`` method specified for that output:

        - ``List`` of the respective output type in case of ``append``
        - same type of the respective output type in case of ``sum``, ``avg``

      - One, the default next
    * - ParallelFlowNode
      - Execute a list of subflows in parallel.
        Please check the concerns regarding parallel execution depicted in the :ref:`parallelization section <parallelization>`.
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - subflows
              - The flows that should be executed in parallel
              - List[Flow]
              - Yes
              - -

      - Inferred from the inner structure. It's the union of the sets of inputs of the inner flows.
        Inputs of different inner flows that have the same name are merged if they have the same type.
        Inputs of different inner flows with the same name but different types are not allowed.

      - Inferred from the inner structure. It's the union of the outputs of the inner flows.
        Outputs of different inner flows with the same name are not allowed.

      - One, the default next
    * - StartNode
      - * Entry point of a flow
        * Defines the flow inputs
      - None
      - The list of inputs that should be exposed by the flow
      - Inferred form the inputs. If a value is given, it must match exactly the list of properties defined in inputs
      - One, the default next
    * - EndNode
      - * End point of a flow
        * Defines exported outputs of the flow
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - branch_name
              - The name of the branch that corresponds to the branch that gets closed by this node,
                which will be exposed by the Flow
              - string | null
              - No
              - null (the default ``next`` branch value is used)

      - Inferred form the outputs. If a value is given, it must match exactly the list of properties defined in outputs
      - The list of outputs that should be exposed by the flow
      - None (note that the branch_name is used by the Flow, not by this node)
    * - BranchingNode
      - * Control flow branching point
        * Defines which branch to follow based on the value of a given input
        * Each input value is mapped to a different outgoing branch
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - mapping
              - Mapping between the value of the input and the name of the outgoing branch that will
                be taken when that input value is given
              - object[str, str]
              - Yes
              - -

      - The input value that should be used as key for the mapping
      - None
      - One for each value in the mapping, plus a branch called default, which is the branch taken by the flow
        when mapping fails (i.e., the input does not match any key in the mapping)
    * - ToolNode
      - Executes the given tool
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - tool
              - The tool to be executed
              - Tool
              - Yes
              - -

      - Inferred from the definition of the tool to execute
      - Inferred from the definition of the tool to execute
      - One, the default next
    * - InputMessageNode
      - * Appends an agent message to the conversation, if given
        * Interrupts the execution of the flow in order to wait for a user input and restarts after getting it
        * User input is appended to the conversation as a user message
        * User input is also returned as a string property from the node.
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - message
              - Content of the agent message to append to the conversation before waiting for user input.
                Allows placeholders, which can define inputs
              - str
              - No
              - null (no agent message is appended)

      - One per variable in the message
      - One string property that represents the content of the input user message
      - One, the default next
    * - OutputMessageNode
      - Appends an agent message to the ongoing flow conversation
      - .. list-table::
            :header-rows: 1
            :widths: 20 35 15 15 15
            :class: mywideinnertable

            * - Name
              - Description
              - Type
              - Mandatory
              - Default
            * - message
              - Content of the agent message to append. Allows placeholders, which can define inputs
              - str
              - Yes
              - -

      - One per variable in the message
      - No outputs
      - One, the default next

A2AAgent
~~~~~~~~

``A2AAgent`` is an implementation of ``AgenticComponent`` which uses the A2A protocol to communicate with a remote server agent. It handles all necessary data transformation and communication logic to and from the server agent.
For more details on the A2A protocol, refer to the :ref:`A2A (Agent to Agent Protocol) section <agentspeca2aspec_nightly>`.

.. code-block:: python

  class A2AAgent(AgenticComponent):
    agent_url: str
    connection_config: A2AConnectionConfig # Parameters for HTTP connection settings, including timeouts and SSL/TLS security
    session_parameters: Optional[Dict[str, Any]] # Parameters controlling session behavior such as polling timeouts and retry logic

- `agent_url`: Specifies the URL of the remote server agent for establishing a connection, serving as the endpoint for communications.
- `connection_config`: Contains HTTP connection details, including timeouts and SSL/TLS security settings, ensuring a secure and optimized connection with necessary certificates.
- `session_parameters`: Defines session behavior settings such as polling timeouts and retry mechanisms, enabling precise control over interactions with the remote server to manage interruptions or delays.
                        These settings include `timeout`, specifying the maximum wait time in seconds before deeming a session unresponsive;
                        `poll_interval`, defining the interval in seconds between polling attempts to check for server responses;
                        and `max_retries`, indicating the maximum number of retry attempts to establish a connection or obtain a response before aborting.

RemoteAgent
~~~~~~~~~~~

A ``RemoteAgent`` is an ``AgenticComponent`` whose logic executes outside the
current process, typically behind a remote endpoint. The representation must therefore
capture enough information for an executor to perform the remote invocation and
to relay messages back and forth.


OciAgent
~~~~~~~~

``OciAgent`` is a concrete implementation of ``RemoteAgent`` running on
Oracle Cloud Infrastructure. It adds OCI-specific authentication and connection details.

.. code-block:: python

   class OciAgent(ComponentWithIO):
      agent_endpoint_id: str
      client_config: OciClientConfig  # contains all OCI authentication related configurations

Swarm
~~~~~

A ``Swarm`` is an ``AgenticComponent`` that enables multi-agent collaboration.
Unlike a single agent, a Swarm defines a group of agents that can communicate
and delegate tasks among each other based on a set of predefined relationships.
Agents in Swarm can be any ``AgenticComponent``.
Swarm preserves the standard messaging and execution semantics of ``AgenticComponent``.

.. code-block:: python

  class Swarm(AgenticComponent):
    first_agent: AgenticComponent
    relationships: List[Tuple[AgenticComponent, AgenticComponent]]
    handoff: Literal["never", "optional", "always"]

When a Swarm is initialized, the conversation always begins with the ``first_agent``— this is the agent that interacts directly with the human user.

From there, the ``first_agent`` may:

1. Response directly to the user's query, or
2. Call another agent (that it has a defined relationship with) to handle a specialized subtask.

The human user remains in conversation with the ``first agent`` during this time.
The called agent can, in turn, call other agents it has relationships with to further handle a subtask.

If ``handoff="optional"``, the first_agent also gains a third option:
it may hand off the entire conversation to another agent.
Once the handoff occurs, the receiving agent becomes the new primary point of contact for the human user. This mechanism can significantly reduce latency by avoiding unnecessary back-and-forth message passing between agents.

When ``handoff="always"`` is enabled, an agent cannot call another agent and wait for a reply (i.e. it does not have the second option mentioned above).
Delegation is only possible through a full handoff of the conversation.
Handing off the conversation establishes a strict chain-of-ownership: each agent must transfer the entire dialogue context when involving another agent.

Each relationship is defined as a tuple ``(caller_agent, recipient_agent)``
which represents a one-way communication link from ``caller_agent`` to ``recipient_agent``.

ManagerWorkers
~~~~~~~~~~~~~~

A ``ManagerWorkers`` is an ``AgenticComponent`` designed for manager-worker style collaboration among multiple agents.
It consists of a manager agent that coordinates and assigns tasks to a group of worker agents.
Agents in ManagerWorkers can be any ``AgenticComponent``.
The ManagerWorkers component maintains the standard messaging and execution semantics of an ``AgenticComponent``.

.. code-block:: python

  class ManagerWorkers(AgenticComponent):
    group_manager: AgenticComponent
    workers: List[AgenticComponent]

The ManagerWorkers has two main parameters:

- ``group_manager``
  An agentic component (e.g. Agent) that is used as the group manager,
  responsible for coordinating and assigning tasks to the workers.

- ``workers`` - List of agentic components
  These agentic components serve as the workers within the group and are coordinated by the group manager.

  - Workers cannot interact with the end user directly.
  - When invoked, each worker can leverage its equipped tools to complete the assigned task and report the result back to the group manager.


Datastores
~~~~~~~~~~

Datastores are the AgentSpec abstraction that enables agentic systems to store and access data.

.. code-block:: python

    class Datastore(Component, abstract=True):
        pass

All datastores currently defined represent collections of objects defined by their type as an ``Entity``, however the Datastore parent type is left without constraint to enable future extension or the development of plugins with different Datastore structure (e.g. key-value stores, or graph database, or unstructured data storage)

An ``Entity`` is a property that has a JSON schema equivalent to an object property; an object property would work.

Relational datastores & In-Memory datastore
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Relational datastores (``OracleDatabaseDatastore``, ``PostgresDatabaseDatastore``) should support SQL queries. For development use, we have a drop-in replacement for them  (``InMemoryCollectionDatastore``).
Both of these contain many collections (tables) where each collection is a set entities. They need to have a predefined fixed schema. A schema is a mapping from a collection name to an Entity object defining the entity(row).

.. code-block:: python

    class InMemoryCollectionDatastore(Datastore):
        datastore_schema: Dict[str, Entity]

    class RelationalDatastore(Datastore, is_abstract=True):
        datastore_schema: Dict[str, Entity]

OracleDatabaseDatastore
^^^^^^^^^^^^^^^^^^^^^^^

The ``OracleDatabaseDatastore`` is a relational datastore that requires an ``OracleDatabaseConnectionConfig`` object for configuration. Sensitive information (e.g., wallets, keys) is excluded from exported configurations and should be loaded at deserialization time.

.. code-block:: python

    class OracleDatabaseDatastore(RelationalDatastore):
        connection_config: OracleDatabaseConnectionConfig

``OracleDatabaseConnectionConfig`` is the abstraction we use for configuring connections to Oracle Database.

.. code-block:: python

    class OracleDatabaseConnectionConfig(Component, is_abstract=True):
        pass

``TlsOracleDatabaseConnectionConfig`` For standard TLS Oracle Database connections.

.. code-block:: python

    class TlsOracleDatabaseConnectionConfig(OracleDatabaseConnectionConfig):
        user: SensitiveField[str]
        password: SensitiveField[str]
        dsn: SensitiveField[str]
        protocol: Literal["tcp", "tcps"]
        config_dir: Optional[str]

- ``user``: User used to connect to the database
- ``password``: Password for the provided user
- ``dsn``: Connection string for the database
- ``protocol``: 'tcp' or 'tcps' indicating whether to use unencrypted network traffic or encrypted network traffic (TLS)
- ``config_dir``: Configuration directory for the database connection. Set this if you are using an alias from your tnsnames.ora files as a DSN. Make sure that the specified DSN is appropriate for TLS connections.

``MTlsOracleDatabaseConnectionConfig`` For Oracle DB connections using mutual TLS (wallet authentication).

.. code-block:: python

    class MTlsOracleDatabaseConnectionConfig(TlsOracleDatabaseConnectionConfig):

        wallet_location: SensitiveField[str]
        wallet_password: SensitiveField[str]

- ``wallet_location``: Location where the Oracle Database wallet is stored.
- ``wallet_password``: Password for the provided wallet.

PostgresDatastore
^^^^^^^^^^^^^^^^^

The ``PostgresDatabaseDatastore`` is a relational datastore intended to store entities in PostgreSQL databases. It requires a ``PostgresDatabaseConnectionConfig`` object for connection and authentication details. Sensitive information (e.g., user, password, SSL keys) is excluded from exported configurations and should be loaded at deserialization time.

.. code-block:: python

    class PostgresDatabaseDatastore(RelationalDatastore):
        connection_config: PostgresDatabaseConnectionConfig

    class PostgresDatabaseConnectionConfig(Component, is_abstract=True):
        pass

    class TlsPostgresDatabaseConnectionConfig(PostgresDatabaseConnectionConfig):
        user: SensitiveField[str]
        password: SensitiveField[str]
        url: str
        sslmode: Literal["disable","allow", "prefer","require","verify-ca","verify-full"]
        sslcert: Optional[str]
        sslkey: Optional[SensitiveField[str]]
        sslrootcert: Optional[str]
        sslcrl: Optional[str]

- ``user``: User of the postgres database
- ``password``: Password of the postgres database
- ``url``: URL to access the postgres database
- ``sslmode``: SSL mode for the PostgreSQL connection.
- ``sslcert``: Path of the client SSL certificate, replacing the default ``~/.postgresql/postgresql.crt``. Ignored if an SSL connection is not made.
- ``sslkey``: Path of the file containing the secret key used for the client certificate, replacing the default ``~/.postgresql/postgresql.key``. Ignored if an SSL connection is not made.
- ``sslrootcert``: Path of the file containing SSL certificate authority (CA) certificate(s). Used to verify server identity.
- ``sslcrl``: Path of the SSL server certificate revocation list (CRL). Certificates listed will be rejected while attempting to authenticate the server's certificate.


Transforms
^^^^^^^^^^

Transforms extend the base ``MessageTransform`` component that can be used in agents. They apply a transformation to the messages before they are passed to the agent's LLM.

.. code-block:: python

    class MessageTransform(Component, abstract=True):
        pass

MessageSummarizationTransform
'''''''''''''''''''''''''''''

Summarizes messages exceeding a given number of characters using an LLM and caches the summaries in a ``Datastore``. This is useful for conversations with long messages where the context can become too large for the agent LLM to handle.

.. code-block:: python

    class MessageSummarizationTransform(MessageTransform):
        llm: LlmConfig  # LLM to use for the summarization.
        max_message_size: int  # The maximum size in number of characters for the content of a message.
        summarization_instructions: str  # Instruction for the LLM on how to summarize the messages.
        summarized_message_template: str  # Jinja2 template on how to present the summary (with variable `summary`) to the agent using the transform.
        datastore: Optional[Datastore]  # Datastore on which to store the cache. If None, no caching happens.
        max_cache_size: Optional[int]  # The number of cache entries (messages) kept in the cache. If None, there is no limit on cache size and no eviction occurs.
        max_cache_lifetime: Optional[int]  # max lifetime of a message in the cache in seconds. If None, cached data persists indefinitely.
        cache_collection_name: str  # Name of the collection in the cache for storing summarized messages.

ConversationSummarizationTransform
''''''''''''''''''''''''''''''''''

Summarizes conversations exceeding a given number of messages using an LLM and caches conversation summaries in a ``Datastore``. This is useful to reduce long conversation history into a concise context for downstream LLM calls.

.. code-block:: python

    class ConversationSummarizationTransform(MessageTransform):
        llm: LlmConfig  # LLM to use for the summarization.
        max_num_messages: int  # Number of message after which we trigger summarization.
        min_num_messages: int  # Number of recent messages to keep from summarizing.
        summarization_instructions: str  # Instruction for the LLM on how to summarize the conversation.
        summarized_conversation_template: str  # Jinja2 template on how to present the summary (with variable ``summary``) to the agent using the transform.
        datastore: Optional[Datastore]  # Datastore on which to store the cache. If None, no caching happens.
        max_cache_size: Optional[int]  # The maximum number of entries kept in the cache
        max_cache_lifetime: Optional[int]  # max lifetime of an element in the cache in seconds
        cache_collection_name: str  # Name of the collection in the cache datastore where summarized conversations will be stored

Versioning
----------

Every Agent Spec configuration should include a property called ``agentspec_version`` at the top level.
The value of ``agentspec_version`` specifies the Agent Spec specification version the configuration is
written for. When this field is missing from the configuration, the latest (current) Agent Spec version
is used instead.

For example, the JSON serialized version of an Agent should look like the following:

.. code-block:: json

  {
    "component_type": "Agent",
    "name": "my agent",
    "id": "my_agent_id",
    "description": "",
    "human_in_the_loop": true,
    "llm_config": {
       "component_type": "VllmConfig",
       "name": "my llm",
       "id": "my_llm_id",
       "description": "",
       "default_generation_parameters": {},
       "model_id": "my/llm",
       "url": "my.llm.url"
    }
    "tools": [],
    "agentspec_version": "26.2.0"
  }

For release versioning, Agent Spec follows the format YEAR.QUARTER.PATCH. Agent Spec follows a
quarterly release cadence, and it aligns versioning to that cadence such that YEAR corresponds
to the last two digits of the year, and QUARTER refers to the quarter of the release (from 1 to 4).
The first release is 25.4.1.

Updates in the PATCH version must not introduce new features or behavioral changes,
they should only cover security concerns and clarifications if needed.
However, any version update, including PATCH ones, could contain breaking changes.

Breaking changes include all the modifications that would make a configuration written in
the previous version invalid or semantically different, for example:

- Removing/modifying components
- Removing/renaming an attribute
- Supporting new, or changing existing behavior of components,
  even when the existing signature is unchanged

Non-breaking changes include:

- Adding new components
- Adding new attributes
- Disambiguation or clarification of underspecified components' structure or behavior that do not
  contradict previous versions

It's the responsibility of the maintainers of Agent Spec Runtimes, SDKs, and Adapters to keep up
to date with the latest changes in the Agent Spec language specification, and to report
the compatibility of their artifacts with the different Agent Spec specification versions.

Due to backward compatibility reasons, we recommend to create Agent Spec configurations with the
minimum version supported by all the Components in the configuration with the desired behavior.

Backward compatibility
~~~~~~~~~~~~~~~~~~~~~~

All breaking changes must go through a deprecation cycle of one year.

Whenever a breaking change is introduced, a deprecation notice must be provided
in the language specification.

Deprecated features can be removed in any quarter release after 1 year from the deprecation notice,
but it should not be done in patch releases, unless required for security reasons.

In any case, removed features must be announced in the release notes.

.. _agentspecmcpspec_nightly:

MCP (Model Context Protocol)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Model Context Protocol (MCP) provides a standardized way for LLM-based Assistants to
interact with remote servers that expose tools and data sources. MCP enables communication
over various transports such as Streamable HTTP, Server-Sent Events (SSE), or even local
stdio for prototyping.

In Agent Spec, MCP components define configurations for establishing client sessions
and transports to MCP servers. These are used primarily for tools (via ``MCPTool``)
but can be extended to other remote interactions in future versions.

MCP Client transport
^^^^^^^^^^^^^^^^^^^^

The core abstraction is ``ClientTransport``, which manages connections and sessions.

.. code-block:: python

   class ClientTransport(Component):
     session_parameters: Optional[Dict[str, Any]]

The ``session_parameters`` should be used to specify parameters of the MCP client session,
such as the session name and version, or the session timeout.
These parameters are specified as a dictionary of parameter names and respective values.
The names are strings, while values can be of any type compatible with the JSON schema standard.

MCP transports such as ``StdioTransport`` directly extend the ``ClientTransport`` component.


Stdio Transport
'''''''''''''''

The ``StdioTransport`` component should be used for connecting to an MCP server via
subprocess with stdio. This transport must support being passed a the executable
command to run to start the servers as well as a list of command line arguments to
pass to the executable. It can also support being passed environment variables as
well as the working directory to use when spawning the process.

.. code-block:: python

   class StdioTransport(ClientTransport):
     command: str
     args: List[str]
     env: Optional[Dict[str, str]]
     cwd: Optional[str]



Remote MCP transports
^^^^^^^^^^^^^^^^^^^^^

Another category of MCP client transports rely on remote connections to MCP servers.
Those components should extend the ``RemoteTransport`` component and should support
the ``url`` and ``headers`` fields.

.. code-block:: python

   class RemoteTransport(ClientTransport):
     url: str
     headers: Dict[str, str]
     sensitive_headers: SensitiveField[Dict[str, str]]


- ``url`` is a string representing the URL to send the request.
- ``headers`` is a dictionary of additional headers to use in the client.
- ``sensitive_headers`` are additional headers that should be merged with the ``headers`` provided
  when executing the request, but these headers are excluded from exported configuration thus they
  are better suited to contain sensitive information not intended to be shared as widely as the
  exported configuration.


SSE Transport
'''''''''''''

The server-sent events (SSE) transport should be used to connect to
MCP servers via Server-Sent Events.

.. code-block:: python

   class SSETransport(RemoteTransport):
     pass


Streamable HTTP Transport
'''''''''''''''''''''''''

The Streamable HTTP transport should be used to connect to MCP servers via the
`Streamable HTTP <https://modelcontextprotocol.io/specification/2025-06-18/basic/transports#streamable-http>`_
transport.

.. code-block:: python

   class StreamableHTTPTransport(RemoteTransport):
     pass


The transports defined above can be used in components like ``MCPTool``
(see the Tools section) to connect to MCP servers.



Additions to MCP transports
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Finally, individual MCP client transports should be extended to support additional
functionalities, such as mutual Transport Layer Security (mTLS) connections.


SSE Transport with mTLS
'''''''''''''''''''''''

.. code-block:: python

   class SSEmTLSTransport(SSETransport):
     key_file: SensitiveField[str]
     cert_file: SensitiveField[str]
     ca_file: SensitiveField[str]

- ``key_file`` is the path to the client's private key file (PEM format).
- ``cert_file`` is the path to the client's certificate chain file (PEM format).
- ``ca_file`` is the path to the trusted CA certificate file (PEM format) to verify the server.


Streamable HTTP Transport with mTLS
'''''''''''''''''''''''''''''''''''

.. code-block:: python

   class StreamableHTTPmTLSTransport(StreamableHTTPTransport):
     key_file: SensitiveField[str]
     cert_file: SensitiveField[str]
     ca_file: SensitiveField[str]


- ``key_file`` is the path to the client's private key file (PEM format).
- ``cert_file`` is the path to the client's certificate chain file (PEM format).
- ``ca_file`` is the path to the trusted CA certificate file (PEM format) to verify the server.


.. warning::

    For production use, always prefer secure transports like those with mTLS to ensure
    mutual authentication.

.. _agentspeca2aspec_nightly:

A2A (Agent to Agent Protocol)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Agent to Agent Protocol (A2A) is a protocol designed to facilitate communication among agents.
This protocol enables agents to exchange messages, delegate tasks, and collaborate effectively.
It can also be used to establish a connection with a remote agent, allowing for distributed agentic systems.

The connection to a remote agent or between agents is configured using `A2AConnectionConfig`, which defines the necessary parameters for establishing a secure and reliable HTTP connection.
This includes settings such as timeouts, retry policies, and SSL/TLS security configurations to ensure encrypted and authenticated communication.

.. code-block:: python

   class A2AConnectionConfig(Component):
     timeout: float  # Connection timeout in seconds
     headers: Optional[Dict[str, str]] # A dictionary of HTTP headers to include in requests
     verify: bool  # Boolean to enable HTTPS or not
     key_file: Optional[str] # Path to the client's private key file
     cert_file: Optional[str]  # Path to the client's certificate chain file
     ssl_ca_cert: Optional[str]  # Path to private key file
     ca_path: Optional[str]  # Path to the trusted CA certificate file

Ecosystem of plugins
--------------------

In order to support a wide range of use-cases, Agent Spec allows the creation of
custom components through a plugin system. Plugins are extensions
which can include new components or variants of the built-in Agent Spec
components. For supporting reading, writing and executing plugin components,
the serialization and deserialization logic must be added in an Agent Spec SDK
and the execution logic of the plugin component must be added in an Agent Spec
Runtime of choice.

To enable the support of plugins in Agent Spec SDK and Runtime, every component
from a plugin should specify its ``component_type``. This is needed for
serialization and deserialization in order to be able to select the right
plugin serializer or deserializer. Additionally, the name and version of plugins
are needed, because this information will help track and understand the provenance
and compatibility of various components from the plugin ecosystem.

Additionally, if a plugin component is intended as a subtype of another component
(for example a ``Node``, such that the new component can be included in a Flow
which expects sub components of type ``Node``), it must then have the same
unmodified attributes as the parent type and can only add new attributes.

.. literalinclude:: ../agentspec_config_examples/example_plugin_component.json5
    :language: JSON5

Assuming an SDK in the Python programming language, as an example (see
:ref:`the sdk detailed below <sdk-agent-spec_nightly>`), the abstract interface
implemented for a plugin should be similar to this:

.. code-block:: python

    class ComponentSerializationPlugin:

        @abstractmethod
        def plugin_name(self) -> str:
            """Return the plugin name."""
            pass

        @abstractmethod
        def plugin_version(self) -> str:
            """Return the plugin version."""
            pass

        @abstractmethod
        def supported_component_types(self) -> List[str]:
            """Indicate what component types the plugin supports."""
            pass

        @abstractmethod
        def serialize(self, component: Component, serialization_provider) -> Dict[str, Any]:
            """Method to implement to serialize a component that the plugin should be able to support."""
            pass



And similarly for deserialization:

.. code-block:: python

    class ComponentDeserializationPlugin:
        def plugin_name(self) -> str: ...

        def plugin_version(self) -> str: ...

        def supported_component_types(self) -> List[str]: ...

        @abstractmethod
        def deserialize(self, serialized_component: Dict[str, Any], deserialization_provider: DeserializationProvider) -> Component:
            """Method to implement to deserialize a component that the plugin should be able to support."""
            pass


Disaggregated components
------------------------

There are scenarios where some parts of an Agent Spec configuration should not be exported
as part of the main assistant's configuration. For example when:

- Some parts of a Component configuration contain sensitive information;
- It's useful to plug different Component versions in a configuration, based on the use case
  (e.g., use different LlmConfigurations in development and production environment), but
  without duplicating the configuration for every Component's version.

.. important::
    Agent Spec exported configurations should never contain sensitive information.

For this reason, Agent Spec supports referencing **components and values** that are not serialized
in the same configuration, therefore called *disaggregated*.
A serialized configuration of disaggregated components contains only the dictionary of ``$referenced_components``,
and it does not contain any component at the top level.
These disaggregated components must be provided when the main configuration is deserialized,
otherwise the deserialization should fail.
Additional disaggregated components that are not part of any exported configuration (e.g., those containing
potentially sensitive information) can be additionally provided at deserialization time by the SDK or the Runtime
performing it.

The disaggregated components references follow the same :ref:`reference system <symbolic_reference_nightly>` described for components, based on ID matching.
The ID used for matching the disaggregated component is, by default, the key used in the ``$referenced_components`` dictionary.
Users can override this behavior at deserialization time by mapping it to a different ID to match a component reference.
A component reference and its matched disaggregated component must be type-compatible.

Note that also values (e.g., the ``prompt_template`` in an ``LlmNode``, or the ``url`` of a ``VllmConfig``)
can become referenced components. This means that in the main configuration from which they are disaggregated,
they will appear as component references in the ``$referenced_components`` dictionary,
with an ID assigned to them (i.e., the key of the dictionary entry).
The value should replace the reference in the main configuration during deserialization.

Here's an example of an Agent Spec configuration that uses disaggregated components:

.. code-block:: JSON5

    {
      "component_type": "Agent",
      "id": "powerful_agent_id",
      "name": "Powerful agent",
      "description": null,
      "human_in_the_loop": true
      "metadata": {},
      "llm_config": {
        "component_type": "VllmConfig",
        "default_generation_parameters": null,
        "description": null,
        "id": "llama_llm_id",
        "metadata": {},
        "model_id": "meta/llama-3.3-70b",
        "name": "vllm",
        "url": { "$component_ref": "llm_url_id" }
      },
      "system_prompt": "You are a powerful agent",
      "tools": [
        { "$component_ref": "powerful_tool_id" }
      ],
      "inputs": [],
      "outputs": []
    }

And here's the configuration containing the disaggregated components:

.. code-block:: JSON5

    {
      "$referenced_components": {
        "powerful_tool_id": {
          "component_type": "ClientTool",
          "name": "powerful_tool",
          "id": "powerful_tool_id",
          "description": "Does powerful things",
          "metadata": {},
          "inputs": [],
          "outputs": []
        },
        "llm_url_id": "my.url.to.llm"
      }
    }




.. _agentspecsensitivefield_nightly:

Sensitive fields
----------------

Some of the fields in the configuration of Agent Spec components may contain sensitive information
such as API keys or authentication tokens. To help developers securely support these components,
AgentSpec runtimes and SDKs must follow these three guidelines:

- **When exporting configurations**: Any sensitive field must be excluded from the configurations.
- **When loading configurations**: Runtime adapters and SDKs must allow passing the excluded sensitive information.
- **When loading configurations**: If developers have already inlined the sensitive information into their
  configurations, runtimes and SDKs should allow loading these configurations too.

See all the fields below that are considered sensitive fields:

+----------------------------------+--------------------+
| Component                        | Attribute          |
+==================================+====================+
| OpenAiCompatibleConfig           | api_key            |
+----------------------------------+--------------------+
| OpenAiConfig                     | api_key            |
+----------------------------------+--------------------+
| OciClientConfigWithSecurityToken | auth_file_location |
+----------------------------------+--------------------+
| OciClientConfigWithApiKey        | auth_file_location |
+----------------------------------+--------------------+
| RemoteTool                       | sensitive_headers  |
+----------------------------------+--------------------+
| ApiNode                          | sensitive_headers  |
+----------------------------------+--------------------+
| RemoteTransport                  | sensitive_headers  |
+----------------------------------+--------------------+
| SSEmTLSTransport                 | key_file           |
+----------------------------------+--------------------+
| SSEmTLSTransport                 | cert_file          |
+----------------------------------+--------------------+
| SSEmTLSTransport                 | ca_file            |
+----------------------------------+--------------------+
| StreamableHTTPmTLSTransport      | key_file           |
+----------------------------------+--------------------+
| StreamableHTTPmTLSTransport      | cert_file          |
+----------------------------------+--------------------+
| StreamableHTTPmTLSTransport      | ca_file            |
+----------------------------------+--------------------+


For example, the following component produced using the `pyagentspec` SDK:

.. code-block:: python

    OpenAiCompatibleConfig(
        name="llm-config",
        id="llm-config-id",
        url="https://some.api.com/v2",
        model_id="some_model_id",
        api_key="THIS_IS_SECRET",
    )

should produce the following configuration, in which the sensitive ``api_key`` is replaced by a reference

.. code-block:: JSON5

    {
      "component_type" : "OpenAiCompatibleConfig",
      "id" : "llm-config-id",
      "name" : "llm-config",
      "url" : "https://some.api.com/v2",
      "model_id" : "some_model_id",
      "api_key" : {
        "$component_ref" : "llm-config-id.api_key"
      },
    }

Such a configuration would then require to pass the referenced sensitive information when loading, as
in the example code below:

.. code-block:: python

    llm_config = AgentSpecDeserializer().from_json(
        serialized_llm,
        components_registry={"llm-config-id.api_key": "THIS_IS_SECRET"},
    )


Additional components for future versions
-----------------------------------------

In this first version we focused on the foundational elements of agents,
but some concepts are not yet covered, and should be part of further
discussions, and included in future versions.

Among them, we can highlight:

- Memory
- Data sources & search support (e.g., for easy RAG setup)
- Planning
- Multi-agent systems

These topics will be covered in future versions of Agent Spec.

Language examples
=================

Standalone agent
----------------

Agents are capable of leveraging tools in multi-turn conversation in
order to reach a specific goal.

Agents do not express flow of control: the layout for these components
simply expresses property assignments.

In the following example we provide a generic implementation of a
flexible agent that includes all the components it can take advantage of
(e.g., tools, llms). In a future extension of the language, more
components can be added to this spec (e.g., memory, planner).

|image2|

In the following example, we show the representation of an agent focused on
benefits, which has the same structure depicted above.

.. collapse:: Agent Spec representation

    .. literalinclude:: ../agentspec_config_examples/standalone_agent.json5
        :language: JSON5


Standalone flow
---------------

The following diagram illustrates a flow that could be used in an online
store's customer support system.

The flow checks if an order is eligible for a replacement, and if that
is the case, which products should be offered to the user in exchange
for their defective item.

The flow may be invoked by a conversational agent or executed upon
configuration via another user interface.

|image3|

This graph is implemented by the following Agent Spec representation:

.. collapse:: Agent Spec representation

    .. literalinclude:: ../agentspec_config_examples/standalone_flow.json5
        :language: JSON5


Agents in flow
--------------

In this example we are going to show how to use agents in a flow.

We propose a Coding Agent where different specialized agents operate in
sequence in order to generate code based on a user request.

The flow consists of a main conversational agent that talks with a user
to gather the request, then three agents that take care of the code
generation and its review.

The advantage of having this type of agent implemented as a graph is
that we have control on what is the sequence of calls and events that
should happen before approving the generated code.

In particular, we can ensure that the code gets generated by the
respective agent, and before being passed back to the main assistant
that interacts with the user, it is passed through the two reviewer
agents, and we must get both validations before going back to the main
user facing agent.

For brevity, in the diagram we omit the internal structure of the
agents, which is comparable to the one defined in example 5.1.

Put name of the agent in the diagram. Show that same agent can be
executed in different places.

|image5|

This graph is implemented by the following Agent Spec representation:

.. collapse:: Agent Spec representation

    .. literalinclude:: ../agentspec_config_examples/flow_calling_agent.json5
        :language: JSON5


(Generated) JSON Language spec
==============================

We put here the current JSON spec of the Agent Spec language.

.. collapse:: JSON Schema

    .. literalinclude:: json_spec/agentspec_json_spec_25_4_2.json
        :language: json

Note about serialization of components
--------------------------------------

Every ``Component`` is supposed to be serialized with an additional field
called ``component_type``, which defines what type of component is being described.
The value of ``component_type`` should coincide with the name of the specific component's class.

Examples of JSON serialization for a few common Components follow.


.. code-block:: JSON5

    // VllmConfig serialization
    {
      "id": "vllm",
      "name": "VLLM Model",
      "description": null,
      "metadata": {},
      "default_generation_parameters": {},
      "url": "http://url.of.my.vllm",
      "model_id": "vllm_model_id",
      "component_type": "VllmConfig",
      "agentspec_version": "25.4.1"
    }


.. code-block:: JSON5

    // ServerTool serialization
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
      "component_type": "ServerTool",
      "agentspec_version": "25.4.1"
    }


.. code-block:: JSON5

    // Agent serialization
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
      "human_in_the_loop": true
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
      "component_type": "Agent",
      "agentspec_version": "26.2.0"
    }


Note about references
---------------------

To avoid duplicating the same component serialization in a document, we use references.
For this reason, we need two types for each component in the JSON schema specification of Agent Spec.
For example, ``Agent`` becomes a union to specify that it can be replaced by a reference:

.. code-block:: json

   "Agent": {
     "anyOf": [
       { "$component_ref": "#/$defs/ComponentReference" },
       { "$component_ref": "#/$defs/RawAgent" }
     ]
   }

The ``ComponentReference`` is the same for every component, and it represents the way component references
are specified according to the Agent Spec language specification.

.. code-block:: json

   "ComponentReference": {
     "type": "object",
     "properties": {
       "$component_ref": {"type": "string"}
     }
   }

``RawAgent`` is the un-changed version with the exception that some reference like ``#/$defs/LlmConfig``
now are pointing to the type of the schema that can be potentially replaced by a ref

.. code-block:: json

   "RawAgent": {
     "description": "An agent is a component that can do se.... ",
     "properties": { }
   }

JSON Example
~~~~~~~~~~~~

Here's an example of a Flow's definition in Python, and the respective
representation generated in JSON. We use PyAgentSpec in order to define the Agent Spec's Flow.

.. collapse:: Python Flow example

    .. literalinclude:: ../code_examples/pyagentspec_example.py
        :language: python
        :start-after: .. start-code:
        :end-before: .. end-code

.. collapse:: Flow's representation

    .. literalinclude:: ../agentspec_config_examples/pyagentspec_example_config.json
        :language: json

.. _sdk-agent-spec_nightly:

SDKs for consuming/producing Agent Spec
=======================================

A SDK for Agent Spec would be developed, to guarantee adherence to the
specification, as well as providing easy to use APIs to
serialize/deserialize Agent Spec representation, or create them from code.

All SDKs should provide the following:

- classes to represent components
- APIs to help with serialization/deserialization

PyAgentSpec represents the implementation of an Agent Spec SDK in python.
The API documentation of PyAgentSpec is available at :doc:`this link <../api/index>`.


Serialization/deserialization APIs
----------------------------------

The serialization/deserialization would be served by the following APIs

.. code-block:: python

   class AgentSpecSerializer:
     def __init__(self, plugins: Optional[List[ComponentSerializationPlugin]] = None) -> None:
       ...

     def to_json(self, component: Component) -> str:
       # gets the JSON string representation for the component
       pass

   class AgentSpecDeserializer:
     def __init__(self, plugins: Optional[List[ComponentDeserializationPlugin]] = None) -> None:
       ...

     def from_json(self, json_content: str) -> Component:
       # creates a component, given its JSON string representation
       pass

So that it is possible to execute the following code:

.. code-block:: python

   # Create a Python object Agent Spec flow
   node_1 = StartNode(id="NODE_1", name="node_1")
   node_2 = LlmNode(id="NODE_2", name="node_2", prompt_template="Hi!")
   end_node = EndNode(id="end_node", name="End node")

   control_flow_edges = [
       ControlFlowEdge(id="1to2", name="1->2", from_node=node_1, to_node=node_2),
       ControlFlowEdge(id="2toend", name="2->end", from_node=node_2, to_node=end_node),
   ]

   flow = Flow(
       id="FLOW_1",
       name="My Flow",
       start_node=node_1,
       nodes=[node_1, node_2, end_node],
       control_flow_connections=control_flow_edges,
       data_flow_connections=[],
   )

   # Serialize it to JSON
   serializer = AgentSpecSerializer()
   serialized_flow = serializer.to_json(flow)

and the converse for deserialization.

The documentation of PyAgentSpec serialization is available at :doc:`this link <../api/serialization>`.


.. |image2| image:: ../_static/agentspec_spec_img/standalone_agent.png
.. |image3| image:: ../_static/agentspec_spec_img/standalone_flow.png
.. |image4| image:: ../_static/agentspec_spec_img/agent_calling_flows.png
.. |image5| image:: ../_static/agentspec_spec_img/flow_calling_agent.png
.. |image6| image:: ../_static/agentspec_spec_img/flow_io_example.png
.. |image7| image:: ../_static/agentspec_spec_img/flow_connections.png
