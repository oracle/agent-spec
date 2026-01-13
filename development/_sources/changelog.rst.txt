Changelog
=========

Agent Spec |release|
--------------------

New features
^^^^^^^^^^^^

* **MCP tools support in LangGraph adapter:**

  The LangGraph adapter now supports Model Context Protocol (MCP) tools.

  To use this, install the optional extra ``pyagentspec[langgraph_mcp]`` and invoke the loaded graph/agent asynchronously via ``.ainvoke`` within an async context.

* **Added LangGraph adapter to pyagentspec:**

  The LangGraph adapter is now available as part of ``pyagentspec``.
  You can access its functionality through the ``pyagentspec.adapters.langgraph`` subpackage.
  It requires the ``langgraph`` extra dependency to be installed.

  For more information read the :doc:`API Reference <api/adapters>`.

* **Added AutoGen adapter to pyagentspec:**

  The AutoGen adapter is now available as part of ``pyagentspec``.
  You can access its functionality through the ``pyagentspec.adapters.autogen`` subpackage.
  It requires the ``autogen`` extra dependency to be installed.

  For more information read the :doc:`API Reference <api/adapters>`.

* **Sensitive Fields Support:**

  New fields have been added to Agent Spec components that may carry sensitive data (e.g. the field `api_key` on :ref:`OpenAiCompatibleConfig <openaicompatibleconfig>`). To provide this functionality securely, we also introduced the annotation `SensitiveField` such that the sensitive fields are automatically excluded when exporting a Component to its JSON or yaml configuration.

  For more information read the :ref:`latest specification <agentspecsensitivefield_nightly>`.

* **OpenAI Responses API Support:**

  :ref:`OpenAiCompatibleConfig <openaicompatibleconfig>` and :ref:`OpenAIModel <openaiconfig>` now support the OpenAI Responses API, which can be configured
  using the ``api_type`` parameter, which accepts values from :ref:`OpenAIAPIType <openaiapitype>`.

  This enhancement allows recent OpenAI models to better leverage advanced reasoning capabilities, resulting in significant performance improvements in workflows.

  For more information read the :doc:`API Reference <api/llmmodels>`.

* **OCI Responses API Support:**

  :ref:`OciGenAiConfig <ocigenaiconfig>` now supports the OCI Responses API, which can be configured
  using the ``api_type`` parameter, which accepts values from :ref:`OciAPIType <ociapitype>`.

  This enhancement allows recent models to better leverage advanced reasoning capabilities, resulting in significant performance improvements in workflows.

  For more information read the :doc:`API Reference <api/llmmodels>`.

* **ParallelFlowNode and ParallelMapNode**

  Added support for parallelization in Agent Spec through :ref:`ParallelFlowNode <parallelflownode>`, which runs several
  flows in parallel, and :ref:`ParallelMapNode <parallelmapnode>`, which is a parallel version of the ``MapNode``.
  For more information, check out the corresponding :doc:`parallel flows how-to guide <howtoguides/howto_parallelflownode>`
  and :doc:`map-reduce how-to guide <howtoguides/howto_mapnode>`.

* **Tools with User Confirmation**

  Tools now have a new flag named `requires_confirmation`, which can be set to require user/operator approval before running the tool.
  For more information read the :doc:`API Reference <api/tools>`.

* **ToolBoxes**

  Toolboxes are now available in the Agent Spec Language Specification and can be
  passed to :ref:`Agents <agent>`. For more information read the :doc:`API Reference <api/tools>`.

* **BuiltinTool**

  Executor-specific built-in tools are now available in the Agent Spec Language Specification.
  For more information read the :doc:`API Reference <api/tools>`.

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

  Introduced ManagerWorkers in the Agent Spec Language Specification.
  For more information check out the corresponding :doc:`managerworkers how-to guide <howtoguides/howto_managerworkers>` or read the :ref:`API Reference <managerworkers>`.

Improvements
^^^^^^^^^^^^

* **Extended functionality for data parameter**

  Extended the data parameter in ``RemoteTool`` and ``ApiNode`` from only being a dictionary to any JSON serializable object (including nested objects).
  Also improved template rendering in the ``RemoteTool`` and ``ApiNode`` for PyAgentSpec adapters.

* **Python 3.14 support**

  Introduced support for Python version 3.14.

Breaking Changes
^^^^^^^^^^^^^^^^

* **Sensitive Fields**

The below fields have been marked as carrying sensitive information and will be excluded from newly generated configurations automatically. See :ref:`latest specification <agentspecsensitivefield_nightly>` for more information on this. This change is implemented retroactively to impact older configurations too.

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

These field will now require to be passed explicitly when loading an exported configuration, as in the example below:

.. code-block:: python

    AgentSpecDeserializer().from_yaml(
        serialized_component,
        components_registry={
            "<component_id>.key_file": "client.key",
            "<component_id>.cert_file": "client.crt",
            "<component_id>.ca_file": "trustedCA.pem",
        },
    )



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
