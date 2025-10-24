Changelog
=========

Agent Spec |release|
--------------------

New features
^^^^^^^^^^^^

* **ToolBoxes**

  Toolboxes are now available in the Agent Spec Language Specification and can be
  passed to :ref:`Agents <agent>`. For more information read the :doc:`API Reference <api/tools>`.


* **Structured Generation**

  Formally introduced Structured Generation in the Agent Spec Language Specification.
  Structured Generation is now supported in the LlmNode, as well as the Agent.

* **Swarm**

  Introduced Swarm in the Agent Spec Language Specification.
  For more information check out the corresponding :doc:`swarm how-to guide <howtoguides/howto_swarm>` or read the :ref:`API Reference <swarm>`.

* **AgentSpecialization**

  Introduced the concept of agent specialization in the Agent Spec Language Specification, which allows to tailor general-purpose :ref:`Agents <agent>` to specific use-cases.
  For more information read the :doc:`API Reference <api/agent_specialization>`.

* **ManagerWorkers**

  Introduced ManagerWorkers in the Agent Spec Language Specification
  For more information check out the corresponding :doc:`managerworkers how-to guide <howtoguides/howto_managerworkers>` or read the :ref:`API Reference <managerworkers>`.

Agent Spec 25.4.1 — Initial release
-----------------------------------

**Agent Spec is now available:** Quickly build portable, framework and language-agnostic agents!

This initial release establishes the foundation of the Agent Spec ecosystem with the first version of the
language specification, a Python SDK (PyAgentSpec) for simplified agent development, and a set of adapters
that enable running Agent Spec representations on several popular, publicly available agent frameworks.

Explore further:

- :doc:`Language specification <agentspec/index>`
- :doc:`How-to Guides <howtoguides/index>`
- :doc:`PyAgentSpec API Reference <api/index>`
