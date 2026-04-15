==================================================
RFC: First-class sub-agent delegation on ``Agent``
==================================================

:Author: Salah Pichen
:Status: Draft
:Date: 2026-04-15
:Target spec version: ``v26_2_0`` (no bump)

Summary
-------

Add a ``sub_agents: List[AgenticComponent]`` field to ``Agent`` so that a spec
can declare hierarchical delegation from one agent to others without leaking
adapter-specific concerns (such as LLM tool-calling) into the spec.

Motivation
----------

The spec can already express two forms of multi-agent composition:

- ``Swarm`` — peer agents with conversation handoff.
- ``AgentNode`` — an agent embedded as a node inside a ``Flow``.

Neither covers the most common case: **an agent that delegates a scoped
subroutine to another agent while staying in control of the user
conversation.** Today, the only way to express this is to wrap the nested
agent as a plain Python callable and register it via ``tool_registry``. That
is a spec-level workaround with real downsides:

- The nested agent's identity, ``description``, ``inputs``, ``outputs``, and
  ``system_prompt`` are hidden inside opaque tool metadata, so no consumer of
  the spec can reason about the delegation relationship.
- Runtimes that load the spec cannot produce a faithful execution graph — the
  nested agent is indistinguishable from any other tool, which forces each
  runtime to invent its own out-of-band mechanism (or silently lose nested
  features like HITL, observability, and resumability).
- Downstream projects routinely bypass ``AgentSpecLoader`` and carry bespoke
  graph-building code just to route nested-agent calls correctly.

These aren't implementation bugs in any one runtime; they're the consequence
of hiding a nested agent behind an opaque callable. The spec needs a way to
*say* "this agent delegates to these agents" so any consumer can interpret
it correctly.

Use case
~~~~~~~~

- A *planner* agent that calls a *code-review* sub-agent on a diff.
- A *research* agent that delegates web-search or DB-query tasks to typed
  specialist agents.
- A *customer-support* agent that calls a *billing-lookup* sub-agent
  containing its own client tools.

Impact
~~~~~~

- **Users** gain a direct, declarative way to express nested-agent topologies
  without smuggling agent definitions inside tool metadata.
- **Spec consumers** (runtimes, validators, visualisers serving Agent Spec)
  can stop bypassing ``AgentSpecLoader``. With a first-class field, every
  consumer sees the same delegation relationship and can interpret it
  natively.

Proposal
--------

Spec change
~~~~~~~~~~~

A single new field on ``Agent``:

.. code-block:: python

    class Agent(AgenticComponent):
        ...
        sub_agents: List[SerializeAsAny[AgenticComponent]] = Field(default_factory=list)
        """Other agentic components this agent may delegate to.

        The mechanism of delegation (LLM tool-calling, routing node,
        rule-based dispatch, etc.) is chosen by the runtime adapter.
        The spec only asserts the delegation relationship.
        """

        # Additive field — no ``min_agentspec_version`` bump; stays at v26_2_0.

No new component types. No new hierarchies. ``sub_agents`` is an
adapter-agnostic declaration, matching the pattern already used by
``Swarm.first_agent``, ``Swarm.relationships``, and ``AgentNode.agent``, which
all embed ``AgenticComponent`` directly.

Each entry in ``sub_agents`` is a full ``AgenticComponent`` carrying its own
``name``, ``description``, ``inputs``, ``outputs``, and ``system_prompt``.
Those fields are the sub-agent's public contract; adapters use them to build
whatever invocation plumbing they need.

Validation
~~~~~~~~~~

- **No cycles.** A sub-agent cannot reach back to itself transitively.
  Validated at load time.
- **Unique names within a parent's sub-agent list.** Re-uses existing
  name-uniqueness machinery.
- **A sub-agent may be shared across multiple parents.** Disaggregation via
  ``components_registry`` already handles this.

Why adapter code stays in the adapter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Different runtimes will compile ``sub_agents`` differently — an LLM-driven
runtime may bind each sub-agent as a tool-call, a planner/router runtime may
dispatch via a semantic-router node, a rule-based runtime may dispatch by
intent label. The spec doesn't care. A ``SubAgent(Tool)`` framing would have
baked LLM tool-calling into the spec itself; keeping the field
adapter-agnostic avoids that.

Affected components
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Area
     - Change
   * - ``pyagentspec.agent``
     - Add ``sub_agents`` field
   * - ``tracing/spans``, ``tracing/events``
     - Optional ``SubAgentExecutionSpan`` / start / end events for
       observability parity with ``Swarm`` and ``Agent`` execution spans
   * - Docs + examples
     - New guide; decision doc positioning ``sub_agents`` vs. ``Swarm`` vs.
       ``Flow`` with ``AgentNode``

Comparison with ``Swarm``
~~~~~~~~~~~~~~~~~~~~~~~~~

Both ``Swarm`` and ``Agent.sub_agents`` nest ``AgenticComponent`` in the
spec, but they encode different collaboration contracts. They are
complementary, not redundant.

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * -
     - ``Swarm``
     - ``Agent.sub_agents``
   * - Topology
     - Peer-to-peer; directed relationship graph
     - Hierarchical parent → children
   * - User dialogue
     - Can be transferred between agents
     - Always stays with the parent; sub-agent never talks to the user
       directly
   * - Control flow
     - Decentralised — any agent can become the active speaker
     - Centralised — parent invokes, sub-agent returns, parent composes
   * - Context passed in
     - Full shared conversation (OPTIONAL/ALWAYS modes)
     - Scoped args from the parent's invocation — sub-agent does not see
       parent's history
   * - Return to caller
     - Implicit via shared conversation state
     - Explicit result message fed back into parent's reasoning
   * - Best for
     - Multi-specialist conversations where any specialist may continue the
       dialogue with the user
     - Parent-managed subroutine delegation where the sub-agent is a callee
       whose answer the parent composes with

An ``Agent`` can do both: participate in a ``Swarm`` and carry
``sub_agents`` of its own. They live in different parts of the component
graph and do not conflict.

Illustrative spec fragment
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    !Agent
    name: planner
    llm_config: !OpenAiConfig { ... }
    system_prompt: You plan multi-step tasks and delegate code review to the reviewer.
    tools:
      - !ServerTool { name: search, ... }
    sub_agents:
      - !Agent
        name: code_reviewer
        description: Review a diff and return findings with severity ratings.
        inputs:
          - !Property { json_schema: { title: diff, type: string } }
        llm_config: !OpenAiConfig { ... }
        system_prompt: You review code for security and correctness.
        tools:
          - !ClientTool { name: request_severity_override, ... }

The ``description`` and ``inputs`` on ``code_reviewer`` form its public
contract — the parent's invocation must satisfy ``inputs``, and consumers
surface ``description`` as the human-readable purpose of the sub-agent.

Potential risks or concerns
---------------------------

**Recursion.**
Sub-agents may themselves declare sub-agents. Mitigations: cycle detection at
load time; ``components_registry`` deduplicates a sub-agent shared across
parents. Any depth-related limits are a runtime concern, not a spec one.

**Adapter coupling of ``description`` + ``inputs``.**
Runtimes will typically rely on the sub-agent's ``description`` and
``inputs`` to build their invocation contract. Other consumers are free to
ignore or re-interpret these. Mitigation: document that these fields serve
as the sub-agent's public contract, exactly as ``description`` already does
for tools.

**Spec versioning.**
``sub_agents`` is added as an additive field under the existing ``v26_2_0``
target version — no new ``AgentSpecVersionEnum`` value and no
``min_agentspec_version`` bump. The default (empty list) is a no-op for
existing specs, so older consumers that ignore unknown fields continue to
round-trip unchanged.

**Out of scope — dynamic sub-agents.**
Sub-agents are declared statically in the spec. Use cases requiring the
parent to synthesise a new agent definition mid-run are not addressed here.
They could be layered later via a registry hook on ``AgentSpecLoader``
without revisiting this field.

Related Links
-------------

- Existing spec precedent for embedding ``AgenticComponent``:
  ``Swarm.first_agent`` / ``Swarm.relationships`` (``pyagentspec/swarm.py``);
  ``AgentNode.agent`` (``pyagentspec/flows/nodes/agentnode.py``).
- Contrast reference, hierarchical-subroutine vs. peer-collaboration
  framing — Claude Code's subagent vs. agent-team distinction:
  https://code.claude.com/docs/en/agent-teams#compare-with-subagents
