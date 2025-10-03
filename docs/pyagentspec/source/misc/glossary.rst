.. _core_glossary:

===================
Agent Spec Glossary
===================

This page provides an overview of the key concepts and terms used throughout the Agent Spec library.


Agent
=====

An :ref:`Agent <agent>` is an LLM-powered assistant that can interact with users, leverage external tools, and coordinate with other assistants to complete tasks through a conversational interface.

Simple agentic systems may consist of a single agent engaging with a user.
More complex systems can involve multiple agents collaborating to achieve broader goals.
Agents can also be integrated in Flows with the :ref:`AgentNode <agentnode>`.

To learn more about agents, see :doc:`How to Develop an Agent with Remote Tools <../howtoguides/howto_agent_with_remote_tools>` and the :ref:`API Reference <agent>`.

Branching
=========

Branching is the ability of a :ref:`Flow <flow>` to conditionally transition between different nodes based on specific input values or conditions.
Developers can then create more dynamic and adaptive workflows that respond to varying scenarios.
It is implemented using the :ref:`BranchingNode <branchingnode>`, which defines multiple possible branches and maps input values to specific nodes.

For details on configuration and usage, see the :ref:`API Reference <branchingnode>`.


Control Flow Edge
=================

A :ref:`Control Flow Edge <controlflowedge>` is a connector that represents a directional link between two nodes in a :ref:`Flow <flow>`.
It specifies a possible transition between a specific branch of a source node and a destination node.
This concept enables assistant developers to explicitly define the expected transitions that can occur within a Flow.

For more information, see the :ref:`API Reference <controlflowedge>`.

Composability
=============

Composability refers to the ability of assistants to be decomposed into smaller components, combined with other components,
and rearranged to form new assistants that can solve a wide range of tasks.
This capability enables you to create complex agentic systems from modular, reusable building blocks.

Agent Spec supports two types of agentic patterns:

* Calling :ref:`Agents in Flows <agentnode>`: Integrate conversational capabilities into structured workflows.
* Calling :ref:`Flows in Flows <flownode>`: Create nested workflows to model complex business processes.

Data Flow Edge
==============

A :ref:`Data Flow Edge <dataflowedge>` is a connector that represents a logical link between nodes or context providers within a :ref:`Flow <flow>`.
It defines how data is propagated from the output of one node, or context provider, to the input of another node.
This concept enables assistant developers to explicitly define the expected orchestration of data flows within Flows.

For more information, see the :ref:`API Reference <dataflowedge>`.

Flow
====

A :ref:`Flow <flow>` is a type of structured assistant composed of individual :ref:`nodes <presentnode>` that are connected to form a coherent sequence of actions.
Each node in a Flow is designed to perform a specific function, similar to functions in programming.

Flows can have loops, :ref:`conditional transitions <branchingnode>`, and multiple end points.
Flows can also :ref:`integrate sub-flows <flownode>` and :ref:`agents <agentnode>` to enable more complex capabilities.

Flow can be used to tackle a wide range of business processes and other tasks in a controllable and efficient way.

To learn more about flows, see the :doc:`How-to Guides <../howtoguides/index>` and the :ref:`API Reference <flow>`.

Generation Config
=================

The :ref:`LLM Generation Config <llmgenerationconfig>` defines the parameters that control the output behavior of a :ref:`Large Language Model (LLM) <llmconfig>` in Agent Spec.
Key parameters include the maximum number of tokens to generate (``max_tokens``), the sampling ``temperature``, and the probability threshold for nucleus sampling (``top_p``).

For a complete list of parameters, see the :ref:`API Reference <llmgenerationconfig>`.

Large Language Model (LLM)
==========================

A :ref:`Large Language Model <llmconfig>` is a type deep neural network trained on vast amounts of text data that can understand, generate, and manipulate human language through pattern recognition and statistical relationships.
It processes input text through multiple layers of neural networks, using specific mechanisms to understand context and relationships between words.

Modern LLMs contain billions of parameters and often require dedicated hardware for both training and inference.
As such, they are typically hosted through APIs by their respective providers, allowing for ease of integration and access.

See the :ref:`API Reference <llmconfig>` for the list of supported models.

Node
====

A :ref:`Node <presentnode>` is an atomic element of a :ref:`Flow <flow>` that encapsulates a specific piece of logic or functionality.
Agent Spec offers a variety of nodes with functionalities ranging from :ref:`LLM generation <llmnode>` to :ref:`branching <branchingnode>`.
By composing the nodes together, Agent Spec enables the creation of powerful structured assistants to solve diverse use-cases efficiently and reliably.

See the list of available nodes in the :ref:`API Reference <presentnode>`.

Prompt Engineering and Optimization
===================================

Prompt engineering and optimization is the systematic process of designing, refining, and improving prompts to achieve more accurate, reliable, and desired outputs from language models.
It involves iterative testing and refinement of prompt structures, careful consideration of context windows, and strategic use of examples and formatting.

Methods such as Automated Prompt Engineering can help improve prompts by using algorithms to optimize the prompt performance on a specific metric.

Prompt Template
===============

A prompt template is a standardized prompt structure with placeholders for variable inputs, designed to maintain consistency across similar queries while allowing for customization.
Agent Spec uses the `Jinja <https://jinja.palletsprojects.com/en/stable/>`_ templating placeholders syntax to specify the input variables to the prompt.

For more information, see the :doc:`Agent Spec Specification Reference <../agentspec/language_spec_25_4_1>`.

Properties
==========

A :ref:`Property <property>` is a metadata descriptor that defines an input or output value for a component—such as :doc:`Tools <../api/tools>`, :ref:`Nodes <presentnode>`, :ref:`Flows <flow>` and :ref:`Agents <agent>`—within an Agent Spec assistant.
Properties include attributes such as title, description, and default value, which help to clarify the purpose and behavior of the component, making it easier to understand and interact with the component.

For more details, see the :ref:`API Reference <property>`.

Retrieval Augmented Generation (RAG)
====================================

Retrieval Augmented Generation is a technique to enhance LLM outputs by first retrieving relevant information from a knowledge base and then incorporating it into the generation process.
This approach enhances the model's ability to access and utilize specific information beyond its training data.

RAG systems typically involves a retrieval component that searches for relevant information and a generation component that incorporates this information into the final output.

Serialization
=============

In Agent Spec, serialization refers to the ability of capturing an assistant’s configuration and representing it in a compact, human-readable format.
This enables assistants to be shared, stored, or deployed across environments while preserving their structure and behavior.

For more details, see the  :ref:`API Reference <serialization>`.

.. _defstructuredgeneration:

Structured Generation
=====================

Structured generation is the process of controlling LLM outputs to conform to specific formats, schemas, or patterns, ensuring consistency and machine-readability of generated content.
It involves techniques for guiding the model to produce outputs that follow predetermined structures while maintaining natural language fluency.

This approach is particularly valuable for generating data in formats like JSON, XML, or other structured representations.

Tool
====

Agent Spec supports three types of tools:

* :ref:`Server Tools <servertool>` are the simplest types of function tools, executed in the same environment as the agent.
* :ref:`Client Tools <clienttool>` are meant to be executed on the client side.
* :ref:`Remote Tools <remotetool>` to call remote APIs.

.. _defservertool:

Server Tool
-----------

A :ref:`ServerTool <servertool>` is the type of tool that runs in the same environment where the assistant is being executed.

For more information, see the :ref:`API Reference <servertool>`.

.. _defclienttool:

Client Tool
-----------

A :ref:`Client Tool <clienttool>` is one of the three tool types supported in Agent Spec.
Unlike a :ref:`Server Tool <servertool>`, which executes directly on the server, the client tool, upon execution, returns a tool request to be executed in the client side.
The client then returns the result to the assistant.

For implementation details, see the :ref:`API Reference <clienttool>`.

Remote Tool
-----------

A :ref:`Remote Tool <remotetool>` is a tool type in Agent Spec that enables integration with external web services or APIs via HTTP requests.
A remote tool enables developers to make HTTP requests to external web services or APIs, providing a way to integrate external functionality into their assistants.
It provides a flexible way to define and execute requests, including support for templated URLs, headers, and data, as well as error handling and retries.

For implementation details, see the :ref:`API Reference <remotetool>`.

Tokens
======

Tokens are the fundamental units of text processing in LLMs, representing words, parts of words, or characters that the model uses to understand and generate the language.
They form the basis for the model's context window size and directly impact processing costs and performance.

There are two types of tokens relevant to LLMs: input tokens and output tokens.
Input tokens refer to the tokens that are fed into the model as input, whereas output tokens are the tokens generated by the model as output.
In general, output tokens are more expensive than input tokens.
An example of pricing can be $3 per 1M input tokens, and $10 per 1M output tokens.
