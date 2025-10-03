.. _securityconsiderations:

Security Considerations
=======================

**Scope**: This document covers security considerations related to Agent Spec, a portable and platform-agnostic configuration language for agents, tools, and workflows.
It applies to anyone authoring or consuming Agent Spec specifications, regardless of deployment type or execution engine used.

**Why it matters**: Agent Spec defines agents, tools, and workflows that are executed in environments integrating components like LLMs, Python, APIs, and external tools.
While Agent Spec itself is purely declarative, its specifications influence runtime behavior.
Risks can arise from configurations that include sensitive information, lack proper isolation, or rely on untrusted components.
This document helps reduce misconfiguration risks and supports the secure execution of the resulting agent.

Considerations regarding tools
------------------------------

Agent Spec lets you define tools that interact with the agent's environment.
The representation is only aware of the tool’s description, e.g. tool ID, attributes, inputs, outputs, and tool description (i.e. explaining what the tools does in natural language) and does not store any executable code.

Key Principles for Tool Security:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Mandatory Input Validation**: Always validate the tool inputs in your tool's code. \
  For all tools, use ``inputs`` to define/enforce schemas (types and descriptions) as a primary defense. \
  Note that ``inputs`` do not support constraints like ranges or max lengths, so you must implement additional validation in your tool’s code. \
  You should also validate the semantic correctness of inputs, especially when they may originate from untrusted sources like LLM completions or end-user input. \
  For remote tools, which constructs HTTP requests, validation is critical for all parameters that can be templated (e.g., url, method, json_body, data, params, headers, cookies). \
  While ``inputs`` can define the schema for arguments passed to the remote tool, the core security lies in controlling how these arguments are used to form the request.
* **Output Scrutiny**: For all tools, you should define the expected type of a tool’s output using ``outputs`` in the representation. \
  Currently, the representation does not support output constraints like maximum length or detailed validation logic. \
  The output of well-contained tools which you fully control can often be trusted, but tool outputs should be treated with caution when they:

  - are not under your direct control,
  - use an LLM to generate output,
  - are based on end-user input, or
  - pull data from untrusted or dynamic sources (e.g. a remote API or a retrieval tool searching data in a database, where the contents may change over time).

  In these cases, an attacker could inject harmful content via tools and downstream components should treat tool outputs as untrusted input and perform appropriate validation and sanitization before use.
* **Tool Reference Integrity**: In Agent Spec, tools are referenced by their unique IDs, which are resolved by the execution environment. \
  When the representation is exported and later imported in a different environment (or in the same environment under different conditions), the same tool ID may resolve to a different implementation than originally intended. \
  This can lead to unexpected or insecure behavior. \
  Always verify that referenced tool IDs map to the correct and trusted tool definitions in the target environment, especially when moving the representation between systems or teams.

Considerations regarding network communication
----------------------------------------------

The ``RemoteTool``, ``MCPTool`` and the ``ApiNode`` define HTTP-based interactions with external services.

.. important::

  Never embed API keys, passwords, or other secrets directly in Agent Spec.

Always use secure injection mechanisms and follow the principle of least privilege for credential access.

Following security considerations is important when working with remote/mcp tools or API nodes:

* **Templated Request Arguments**: Since most request fields support templating, they can be influenced by dynamic inputs, such as LLM completions or user-provided values. \
  As a result, these fields must be handled with extra caution in the specification to avoid misuse at runtime. \
  Maliciously crafted inputs could lead to information leakage (e.g., exposing sensitive data in URLs or headers) or enable attacks like SSRF (Server-Side Request Forgery) or automated DDoS. \
  Developers must validate all templated inputs, including URLs, headers, and request bodies before executing the request.
* **Secure Connections**: Use HTTPS for all remote calls.
* **HTTP Method**: When possible, use fixed and explicit HTTP methods for the ``http_method`` parameter in the ``RemoteTool`` or ``ApiNode`` (e.g., ``"GET"``, ``"POST"``) rather than dynamic templates.
* **Timeouts**: Remote/MCP tools or API nodes may block indefinitely if the external service is unresponsive. \
  Currently, Agent Spec does not support specifying request timeouts. \
  Timeout behavior should be enforced by the execution environment or tool implementation to avoid resource exhaustion.

While Agent Spec does not manage infrastructure, authors should still be aware of how their configurations interact with secure deployment environments.
We recommend to make sure that the deployment enforces strict network communication rules to make sure that only the desired and required network services are allowed (communication with external public IPs).
Consider the following security considerations:

* **Model Integrity**: For third-party models; Download via HTTPS, pin SHA-256 digests and verify integrity before loading into the execution engine.
* **Egress Restrictions**: Remote calls defined in representation (e.g., via RemoteTool or ApiNode) must align with outbound allow-lists and network policies.
* **Subnet Isolation**: Isolate Agent Spec components to limit blast radius:

  - LLM hosts (OCI Gen AI, vLLM) in dedicated subnets.
  - Remote tools and ApiNodes targets in isolated subnets.
  - Control-flow logic (e.g., Agents, Flows, BranchingSteps) separate from data processing (e.g., database mutations, data analytics)

* **TLS**: Use mTLS for service-to-service communications such as connecting to MCP servers, Monitoring/Telemetry services, File Storage Services, Databases, and so on.
* **Strict Egress Rules**: Default-deny outbound traffic. Allow only Allow-Listed domains/IPs for Agent Spec components (such as when using remote tools or API Nodes).
* **Centralized Allow-Lists**: Use a central allow-list to restrict access to LLM endpoints, logging/telemetry sinks, and external APIs called by components like remote tools or API Nodes. \
  Set up alerts for policy violations.


Considerations regarding API keys and secrets management
--------------------------------------------------------

.. important::

  Never embed API keys, passwords, or other secrets directly in Agent Spec.

Agent Spec is a declarative language for agents, tools, and flows.
It may be stored, versioned, or inspected; it is **not a secure medium for sensitive data**.
Hardcoding secrets in the representation increases the risk of accidental exposure and must be avoided.

Instead of embedding secrets in the representation, ensure that secrets are injected securely at runtime via:

* Integration with a secrets manager (e.g., OCI Vault)
* Use instance principal when working on OCI Computes
* Use Kubernetes/Docker secrets if the deployments supports it

Furthermore, follow these general best practices around credential management

* Rotate credentials regularly.
* Use organization-specific API keys with usage limits.
* Use dedicated credentials per environment or agent, rather than sharing keys across flows or services.
* Follow the principle of least privilege for credential access.
* Avoid exposing secrets to LLMs, logs, or error messages.
* Monitor credential usage for anomalies (e.g., unexpected volume or access patterns).
* Restrict network access and egress for components that hold credentials, especially tools calling external services.


Considerations regarding Resource-exhaustion vectors
----------------------------------------------------

Agent Spec allows for flexible flow and agent logic, however, certain configurations could result in infinite loops, repeated LLM calls, or unbounded parallelism which can lead to resource exhaustion.

The following example shows how to avoid resource exhaustion from repeated tool executions in an infinite loop.
The idea is to add a branching node that exits the loop once a counter hits the specified number of iterations.

.. collapse:: Python Flow example

   .. code-block:: python

    from typing import cast

    from pyagentspec.flows.nodes import StartNode, EndNode, ToolNode, BranchingNode
    from pyagentspec.tools import ClientTool, ServerTool
    from pyagentspec.flows.flow import Flow
    from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    from pyagentspec.property import IntegerProperty, StringProperty
    from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer

    # We run the tool_to_execute tool 5 times. After that, we exit

    # Start and end nodes of the flow
    start_node = StartNode(name="start")
    end_node = EndNode(name="end")

    # We are using a helper tool to count the number tool executions
    # It will increment the value of counter by 1 in each iteration
    tool_counter = ServerTool(
        name="counter",
        inputs=[IntegerProperty(title="counter", default=0)],
        outputs=[IntegerProperty(title="counter")],
    )
    tool_counter_node = ToolNode(name="counter", tool=tool_counter)

    # The tool node for the tool that we're interested in executing in a loop
    # (for the purpose of this example, the tool does nothing)
    tool_to_execute = ServerTool(
        name="do nothing",
        inputs=[],
        outputs=[],
    )
    tool_to_execute_node = ToolNode(name="counter", tool=tool_to_execute)

    # The branching node will be able to exit the loop after limit_reached iterations
    # It will compare the counter value - counting the number iterations in the loop - to
    # the constant limit_reached value
    branching_node = BranchingNode(
        name="branching",
        mapping={"5": "limit_reached"},
        inputs=[StringProperty(title="counter")],
    )

    # The control flow graph looks like this
    # start_node -> tool_node -> tool_counter_node -> branching_node -> end_node
    #                  ^                                  |
    #                  L _________________________________|
    control_flow_edges = [
        ControlFlowEdge(
            name="cf1",
            from_node=start_node,
            to_node=tool_to_execute_node,
        ),
        ControlFlowEdge(
            name="cf2",
            from_node=tool_to_execute_node,
            to_node=tool_counter_node,
        ),
        ControlFlowEdge(
            name="cf3",
            from_node=tool_counter_node,
            to_node=branching_node,
        ),
        ControlFlowEdge(
            name="cf4",
            from_node=branching_node,
            from_branch="default",
            to_node=tool_to_execute_node,
        ),
        ControlFlowEdge(
            name="cf5",
            from_node=branching_node,
            from_branch="limit_reached",
            to_node=end_node,
        ),
    ]

    # df1 creates a self-loop on the counter node s.t. the value can be incremented in each iteration
    # df2 feeds the counter into the branching step s.t. it can decide whether to continue the
    # loop or move to the end_node
    data_flow_edges = [
        DataFlowEdge(
            name="df1",
            source_node=tool_counter_node,
            source_output="counter",
            destination_node=tool_counter_node,
            destination_input="counter",
        ),
        DataFlowEdge(
            name="df2",
            source_node=tool_counter_node,
            source_output="counter",
            destination_node=branching_node,
            destination_input="counter",
        ),
    ]

    flow_with_loop = Flow(
        name="flow_with_loop",
        start_node=start_node,
        nodes=[start_node, end_node, tool_counter_node, tool_to_execute_node, branching_node],
        data_flow_connections=data_flow_edges,
        control_flow_connections=control_flow_edges,
    )

    serializer = AgentSpecSerializer()
    serialized_flow = serializer.to_json(flow_with_loop)


Gaps in coverage (what is not provided)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following controls are currently not configurable in the Agent Spec.
Some of these concerns, particularly those related to infrastructure and deployment, are the responsibility of the execution engine.
However, it's important to be aware of these gaps when designing or deploying agents.

* Memory limits – no built-in interrupt for resident-set or GPU VRAM.
* CPU / thread quotas – Python loops can still hog a core until the Step returns.
* **Soft timeouts and token limits** – the spec does not support soft timeouts or soft token limits. \
  These controls - available in some execution engines - can stop long-running agents or limit LLM token usage, but only between steps. \
* Hard timeouts inside a Tool – a Tool that calls a REST API may block indefinitely.
* Concurrent-request ceilings – there is no built-in limit on how many tool calls or sub-flows can run in parallel. Without external throttling, excessive fan-out may exhaust system resources.
* LLM generation cancellation – once a prompt is sent, the agent will block until the generation is done.
* Conversation isolation – the Agent Spec does not support isolation between sub-flows or sub-agents; conversations are shared and may be forwarded externally if an external endpoint is involved.

Considerations regarding assistant and flow serialization
---------------------------------------------------------

Deserializing data from untrusted sources is inherently risky.
Always treat Agent Spec configuration files from external or unverified origins as potentially malicious.

**Verify Data Integrity and Authenticity**:
Before attempting to import an Agent Spec configuration file to instantiate an agent or flow, ensure:

* The data comes from a trusted source and has not been tampered with. \
  Implement mechanisms such as digital signatures to verify the origin and integrity of the serialized data.
* Its contents align with your expectations; do not assume the representation defines what you think it does. \
  Review the structure, tool references, and key behaviors to ensure the deserialized agent behaves as intended.

.. important::

  Use secure built-in serialization and deserialization utilities whenever possible.
  For example, to deserialize YAML files, use ``yaml.safe_load()`` from the PyYAML package (do not use ``yaml.load()``).

When working with Agent Spec SDKs like PyAgentSpec, always use the provided serialization and deserialization
utilities to avoid unsafe behavior.

.. code-block:: python

  from pyagentspec.serialization import AgentSpecDeserializer

  # Assume verify_signature_and_integrity is a custom function you've implemented
  # to check the signature and integrity of the raw_yaml_string against a trusted key.
  # This step is conceptual and depends on your specific trust model.

  raw_yaml_string = get_potentially_untrusted_yaml_data()
  is_trusted_source = verify_signature_and_integrity(raw_yaml_string)

  if is_trusted_source:
    # from_yaml will use safe_load under the hood
    assistant_or_flow = AgentSpecDeserializer.from_yaml(raw_yaml_string)

When deploying serialized representation to an execution engine, use the engine's secure loading mechanism for the import.

Other Security Concerns
-----------------------

For any other security concerns, please submit a `GitHub issue <https://github.com/oracle/agent-spec/issues>`_.
