.. _agentspecintroduction:

=================================================
Introduction to Agent Spec: Motivation and Vision
=================================================

Oracle Agent Specification (Agent Spec) is a standardized, framework-agnostic configuration language
designed to define AI agents and their workflows with high fidelity. By providing a standardized representation,
Agent Spec enables seamless portability and interoperability of agents across diverse frameworks, ensuring consistent
behavior and integration in various enterprise environments. Agent Spec can be thought of as one abstraction level
above framework-specific specifications, acting as a unifying standard that encapsulates agent functionality
beyond the constraints of individual frameworks.

.. image:: ../_static/agentspec_spec_img/agentspec_stack.svg
    :align: center


Key Benefits
------------

* **Cross-framework Portability**
    As a definition language, Agent Spec aims to decouple agent design from runtime execution, enabling
    consistent execution across frameworks.
* **Modular & Reusable**
    Agent Spec’s component-based structure facilitates reuse and extensibility, supporting the composition and
    adaptation of complex workflows.
* **Reliable & Consistent**
    Agent Spec's specification first approach to agent design seeks to enable predictable, transparent, and consistent agent
    behavior - contributing to improved reliability and governance.
* **Evaluation-Ready by Designs**
    Built-in metadata and behavior constraints make agents (defined in Agent Spec) easier to test, compare, and
    iterate - enabling consistent benchmarking across frameworks.
* **Flexibility**
    Agent Spec lets you focus on designing the right agentic solution for your problem -  from single agents, to
    orchestrator-worker flows - without being limited by the execution constraints of any specific framework.
* **SDK Support**
    Agent Spec provides SDKs in various programming languages (starting with Python),
    supporting serialization and deserialization of agents into Agent Spec-compatible configurations.
    This simplifies development, deployment, and debugging across different environments.
* **Evaluation Harness**
    Leveraging a standardized way of building comparable agents provides a solid base for evaluating
    agent implementations across different frameworks, thereby enabling better framework choice for different agentic tasks.

Comparison: Agent Spec and ONNX
-------------------------------

`ONNX <https://onnx.ai>`_ is an open format built to represent machine learning models.
It has revolutionized deep learning by providing a standardized way to make ML models portable across
different frameworks (e.g., PyTorch, TensorFlow). Similarly, Agent Spec aims to establish a unified representation
for AI agents, enabling seamless interoperability and execution across diverse agentic frameworks.
Just as ONNX allows models to be trained in one framework and executed in another, Agent Spec allows AI agents to be
designed once and deployed across multiple platforms without reimplementation.

.. list-table::
    :header-rows: 1

    * - Feature
      - ONNX (ML Models)
      - Agent Spec (AI Agents)
    * - Scope
      - Standardizes representation of ML models, allowing portability across different deep learning frameworks.
      - Standardizes representation of AI agents and workflows, enabling them to run across diverse agentic frameworks.
    * - Portability
      - ONNX allows ML models to be trained in one framework (e.g., PyTorch, TensorFlow) and executed in another.
      - Agent Spec enables AI agents to be built with one framework (e.g., LangGraph, AutoGen) and run on another without modification.
    * - Standardization
      - Provides a common model format
      - Provides a common agent configuration format
    * - Extensibility
      - Supports various ML operations and optimizations
      - Defines modular components for scalable agent systems


Differentiation from Framework-Specific Configurations
------------------------------------------------------

In this Agent Spec configuration, the agent is defined with components like an LLM and Tools, specifying providers and
models without binding to a specific framework's implementation details. This ensures that AI agents remain portable,
reusable, and framework-agnostic, unlike framework-specific configurations that require adaptation when moving
between different environments.
