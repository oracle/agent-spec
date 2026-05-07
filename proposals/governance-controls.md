# Proposal: Tool Usage Policies for Agent Spec

**Issue**: [#125](https://github.com/oracle/agent-spec/issues/125)
**Author**: Imran Siddique ([@imran-siddique](https://github.com/imran-siddique))
**Status**: Draft

## Summary

This proposal introduces `ToolPolicy` as a standalone component in Agent Spec, enabling spec authors to declare reusable constraints on tool invocation. Policies can be defined once and referenced across multiple tools via `$component_ref`, or inlined on a single tool when reuse is not needed.

This is the first step toward governance controls in Agent Spec, scoped deliberately to tool usage policies as discussed in [#125](https://github.com/oracle/agent-spec/issues/125). Agent-level and flow-level governance declarations are out of scope for this proposal and would follow as separate work.

## Motivation

Agent Spec defines *what* an agent can do through tools, toolboxes, and flows. Today, the only control over *how* tools are used is `requires_confirmation`. Production deployments need richer constraints: rate limits, caller restrictions, conditional approval workflows, and data sensitivity annotations.

These constraints are governance concerns that belong in the spec alongside tool definitions, not as runtime-only afterthoughts. Declaring them in the spec makes governance intent portable, auditable, and visible to anyone reading the configuration.

## Design Principles

1. **Declarative**: The spec declares constraints. Runtimes decide enforcement strategy.
2. **Additive**: All new properties are optional. Existing specs are unaffected.
3. **Native to Agent Spec**: Uses existing patterns (`$component_ref`, component IDs, versioning) rather than importing external models.
4. **Reusable**: Policies are standalone components, referenceable across tools and toolboxes.

## Proposed Changes

### ToolPolicy as a Standalone Component

`ToolPolicy` is a first-class component with its own `component_type`, `id`, and `name`. This enables:

- **Reuse**: Define a policy once, reference it from multiple tools via `$component_ref`.
- **Inline use**: When a policy applies to only one tool, it can be defined inline (no ID required).
- **Composition**: A tool inherits policies from its parent `ToolBox` (see [Policy Composition](#policy-composition-toolbox--tool)).

**YAML example (reusable policy):**

```yaml
# Define a reusable policy as a standalone component
component_type: ToolPolicy
id: c0d1e2f3-a4b5-6789-0abc-def123456789
name: sensitive_data_policy
description: Standard policy for tools accessing customer PII
data_classification: restricted
requires_justification: true
guards:
  - type: rate_limit
    max_calls: 100
    window_seconds: 3600
    on_violation: block
```

**YAML example (referenced from tools):**

```yaml
component_type: Agent
name: Customer Support Agent
tools:
  - component_type: ServerTool
    id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
    name: query_customer_database
    description: Look up customer records by ID or email
    inputs:
      - title: customer_id
        type: string
    outputs:
      - title: customer_record
        type: object
    tool_policy:
      $component_ref: c0d1e2f3-a4b5-6789-0abc-def123456789

  - component_type: ServerTool
    id: b2c3d4e5-f6a7-8901-bcde-f12345678901
    name: send_email
    description: Send an email to a customer
    inputs:
      - title: to
        type: string
      - title: body
        type: string
    outputs:
      - title: message_id
        type: string
    tool_policy:
      data_classification: internal
      guards:
        - type: require_approval
          condition: input_contains
          field: to
          value: "@gov."
          on_violation: escalate
```

In the second tool (`send_email`), the policy is defined inline because it is specific to that tool.

**Schema definition:**

```yaml
ToolPolicy:
  component_type: ToolPolicy
  type: object
  description: >
    A standalone component declaring constraints on tool invocation.
    Can be defined once and referenced via $component_ref, or inlined
    on a tool/toolbox when the policy is single-use.
  properties:
    id:
      type: string
      format: uuid
      description: Unique identifier. Required when defining as a standalone component.

    name:
      type: string
      description: Human-readable name for the policy.

    description:
      type: string
      description: Explanation of the policy's intent.

    data_classification:
      type: string
      enum: [public, internal, confidential, restricted]
      description: >
        The sensitivity level of data this tool accesses or produces.
        Runtimes use this for access control, audit routing, and
        data-handling decisions.
        - public: No sensitivity constraints.
        - internal: Organization-internal, not for external sharing.
        - confidential: Sensitive business data, access-controlled.
        - restricted: Highest sensitivity (PII, financial, health data).

    requires_justification:
      type: boolean
      default: false
      description: >
        When true, the invoking agent must provide a reason for calling
        this tool. How justification is captured is runtime-defined.

    guards:
      type: array
      items:
        $ref: "#/ExecutionGuard"
      description: >
        Execution-time constraints on tool invocation. Each guard
        defines a type, an optional condition, and what happens when
        the constraint is not satisfied. This provides a uniform
        shape for rate limits, approvals, caller restrictions, and
        future constraint types.

    allowed_callers:
      type: array
      items:
        $ref: "#/$component_ref"
      description: >
        (MAY — optional for v1 runtimes.) Component references (by ID)
        of agents or flows permitted to invoke this tool. If omitted,
        any component with the tool in scope may invoke it. Primary
        use case: shared toolboxes in multi-agent systems where the
        same tool is exposed to agents with different trust levels.

    denied_callers:
      type: array
      items:
        $ref: "#/$component_ref"
      description: >
        (MAY — optional for v1 runtimes.) Component references (by ID)
        explicitly denied from invoking this tool. Takes precedence
        over allowed_callers.

  additionalProperties: false

ExecutionGuard:
  type: object
  description: >
    A single execution-time constraint on tool invocation. Guards
    provide a uniform abstraction for rate limits, approval
    requirements, and other controls that gate whether a tool
    call proceeds.
  properties:
    type:
      type: string
      enum: [rate_limit, require_approval, require_justification]
      description: The kind of constraint this guard enforces.
    condition:
      type: string
      enum: [always, input_equals, input_contains, input_not_equals]
      default: always
      description: >
        When this guard applies. "always" means unconditional.
        Input-conditional guards evaluate against a specific input
        field (see "field" and "value" properties).
    field:
      type: string
      description: >
        Name of the input field to evaluate. Required when condition
        is input_equals, input_contains, or input_not_equals.
    value:
      type: string
      description: >
        Value to compare against using the specified condition.
        Required when condition is input-conditional.
    max_calls:
      type: integer
      minimum: 1
      description: >
        Maximum calls within window_seconds. Only used when
        type is "rate_limit".
    window_seconds:
      type: integer
      minimum: 1
      description: >
        Rolling time window in seconds. Only used when type is
        "rate_limit".
    on_violation:
      type: string
      enum: [block, flag, log, escalate]
      default: block
      description: >
        What the runtime does when the constraint is not satisfied.
        - block: Prevent the tool call entirely.
        - flag: Allow the call but flag it for review.
        - log: Allow the call, record the violation only.
        - escalate: Route to a human or escalation workflow.
  required: [type]
```

**Note on `requires_confirmation` compatibility:** The existing `Tool.requires_confirmation: true` is equivalent to a guard of `{type: require_approval, condition: always, on_violation: block}`. Runtimes SHOULD treat them identically. `requires_confirmation` remains as the simpler form for the common unconditional case.

### Policy Composition: ToolBox + Tool

When a `ToolBox` has a `tool_policy` and individual tools within that box also have their own `tool_policy`, the ToolBox policy acts as a **base** that **combines with** (not replaces) the tool-level policy. The effective policy for a tool is determined per-field:

- **data_classification**: The higher sensitivity level wins (`restricted` > `confidential` > `internal` > `public`).
- **requires_justification**: `true` at either level means justification is required.
- **guards**: Union of both lists. All guards from both levels apply.
- **allowed_callers** (MAY): Intersection of both lists (caller must be allowed at both levels).
- **denied_callers** (MAY): Union of both lists (denied at either level means denied).

**Example (before composition):**

```yaml
# ToolBox defines base policy
component_type: MCPToolBox
id: d4e5f6a7-b8c9-0123-4567-890abcdef012
name: customer_data_tools
description: Tools for accessing customer records
tool_policy:
  data_classification: confidential
  requires_justification: true
  guards:
    - type: rate_limit
      max_calls: 200
      window_seconds: 3600
      on_violation: block

# Tool within the box adds its own policy
tools:
  - component_type: ServerTool
    name: delete_customer
    description: Permanently delete a customer record
    inputs:
      - title: customer_id
        type: string
    outputs:
      - title: success
        type: boolean
    tool_policy:
      data_classification: restricted
      guards:
        - type: rate_limit
          max_calls: 10
          window_seconds: 3600
          on_violation: block
        - type: require_approval
          condition: always
          on_violation: escalate
```

**Effective policy for `delete_customer` (after composition):**

```yaml
# Composed result:
data_classification: restricted        # tool wins (higher than confidential)
requires_justification: true           # inherited from toolbox
guards:
  - type: rate_limit                   # tool's rate limit (stricter)
    max_calls: 10
    window_seconds: 3600
    on_violation: block
  - type: require_approval             # tool's approval guard
    condition: always
    on_violation: escalate
  - type: rate_limit                   # toolbox's rate limit also applies
    max_calls: 200
    window_seconds: 3600
    on_violation: block
```

For rate limits, runtimes SHOULD apply the more restrictive limit when multiple rate_limit guards overlap on the same window. In the example above, the effective limit is 10 calls per 3600s.

### PolicyViolation Event

A new event type in the tracing/events system for governance-related violations:

```yaml
PolicyViolation:
  extends: Event
  description: >
    Emitted when a tool invocation is blocked or flagged due to a
    policy constraint. Runtimes emit this event for audit and
    observability purposes.
  properties:
    tool:
      $ref: "#/Tool"
      description: The tool whose policy was violated.
    policy:
      $ref: "#/ToolPolicy"
      description: The policy that was violated.
    violation_type:
      type: string
      enum: [rate_limit_exceeded, caller_denied, justification_missing, approval_required, classification_breach]
      description: The category of violation.
    caller:
      $ref: "#/$component_ref"
      description: The component that attempted the invocation.
    action_taken:
      type: string
      enum: [blocked, flagged, logged, escalated]
      description: >
        What the runtime did in response. Maps to the guard's
        on_violation setting.
        - blocked: Invocation was prevented.
        - flagged: Invocation proceeded but was flagged for review.
        - logged: Invocation proceeded, violation recorded only.
        - escalated: Routed to a human or escalation workflow.
    detail:
      type: string
      description: Human-readable explanation of the violation.
```

**Example event (emitted by runtime):**

```yaml
name: PolicyViolation
timestamp: 1720000000000000000
tool:
  $component_ref: a1b2c3d4-e5f6-7890-abcd-ef1234567890
policy:
  $component_ref: c0d1e2f3-a4b5-6789-0abc-def123456789
violation_type: rate_limit_exceeded
caller:
  $component_ref: f7e8d9c0-b1a2-3456-7890-abcdef012345
action_taken: blocked
detail: "Tool 'query_customer_database' exceeded 100 calls in 3600s window"
```

### Relationship to `requires_confirmation`

The existing `Tool.requires_confirmation` and `ToolBox.requires_confirmation` fields remain unchanged. They are equivalent to a guard of `{type: require_approval, condition: always, on_violation: block}` and exist as the simpler form for the common unconditional case.

The `guards` array extends this concept with conditional and typed constraints. There is no duplication: `requires_confirmation` is sugar, guards are the general mechanism.

### AGT Policy Compatibility Mapping

The [Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit) uses a condition-expression policy format at runtime. The tool-level subset maps to Agent Spec's `ToolPolicy` as follows:

| Agent Spec `ToolPolicy` | AGT Policy YAML | Notes |
|---|---|---|
| `guards: [{type: rate_limit, max_calls: 50, window_seconds: 3600}]` | `condition: "tool_name == 'web_search'"` + `action: rate_limit` + `rate_limit: {max_calls: 50, window: 3600}` | AGT uses condition expressions; Agent Spec uses structured fields |
| `data_classification: restricted` | `condition: "data_classification == 'restricted'"` + `action: deny` | AGT evaluates classification as a runtime condition |
| `allowed_callers: [$ref: agent-id]` | `condition: "caller_id in ['agent-id']"` + `action: allow` | AGT uses caller_id in condition expressions |
| `guards: [{type: require_approval, condition: always}]` | `condition: "tool_name == 'delete_record'"` + `action: require_approval` | Same semantics, different serialization |

Both formats serialize to the same enforcement semantics. A compatibility layer can translate between them so policies defined in one system are loadable in the other.

## Compatibility

- **Backward compatible**: `tool_policy` is optional. Existing specs parse and run without changes.
- **Version gating**: `tool_policy` would be gated behind a new `agentspec_version`, following the existing pattern used for `requires_confirmation` (v25.4.2) and `transforms` (v26.2.0).
- **Runtime behavior**: Runtimes that do not implement tool policies ignore the field. No runtime is required to enforce these constraints. Runtimes that do not emit `PolicyViolation` events simply omit them from the trace.

## Implementation Path

1. **This PR**: Specification proposal defining `ToolPolicy` component schema, composition semantics, and `PolicyViolation` event.
2. **Follow-up**: Pydantic model (`ToolPolicy` class) in `pyagentspec`, serialization/deserialization, `$component_ref` resolution.
3. **Follow-up**: `PolicyViolation` event class in `pyagentspec.tracing.events`.
4. **Follow-up**: Runtime enforcement hooks in adapter layer.
5. **Future proposal**: Agent-level and flow-level governance declarations.

## Prior Art

- Agent Spec's existing `requires_confirmation` on tools and toolboxes.
- [Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit): runtime governance for agentic systems (policy enforcement, caller restrictions, audit logging) across multiple languages. Experience from this project informed the schema design.

## Resolved Design Decisions

These questions were raised in the initial draft and resolved through review discussion:

1. **Standalone vs. inline policies**: `ToolPolicy` is a standalone component, referenceable via `$component_ref` for reuse. Inline definition is supported for single-use cases (same pattern as other Agent Spec components).
2. **data_classification as enum**: Uses a four-level enum (`public`, `internal`, `confidential`, `restricted`) for portability and composition semantics. Organizations needing custom labels can extend via `metadata`.
3. **PolicyViolation event**: Added as a dedicated event type in the tracing system (see [PolicyViolation Event](#policyviolation-event) above).
4. **ToolBox + Tool policy interaction**: ToolBox policy acts as a base that combines with (not replaces) tool-level policies. Composition rules are defined per-field with concrete examples (see [Policy Composition](#policy-composition-toolbox--tool)).
5. **Execution guard unification**: Rate limits, approval requirements, and other execution-time constraints use a common `ExecutionGuard` shape with `{type, condition, on_violation}`. This replaces the earlier design of separate top-level fields for each constraint type, giving us a cleaner extension point for future guard types.
6. **Caller restrictions as MAY**: `allowed_callers`/`denied_callers` are marked as MAY for v1 runtimes. The primary use case (shared toolboxes in multi-agent systems) is valid but not universal enough to require for initial conformance.
7. **AGT compatibility**: Added a mapping table showing how Agent Spec `ToolPolicy` fields correspond to AGT's condition-expression policy format. Both serialize to the same enforcement semantics.

## Examples

### Minimal: Rate-limited tool

```yaml
component_type: ServerTool
name: web_search
description: Search the web
inputs:
  - title: query
    type: string
outputs:
  - title: results
    type: array
tool_policy:
  guards:
    - type: rate_limit
      max_calls: 50
      window_seconds: 3600
      on_violation: block
```

### Reusable policy across multiple tools

```yaml
# Standalone policy component
component_type: ToolPolicy
id: e1f2a3b4-c5d6-7890-1234-567890abcdef
name: high_security_policy
data_classification: restricted
requires_justification: true
guards:
  - type: rate_limit
    max_calls: 10
    window_seconds: 3600
    on_violation: block
  - type: require_approval
    condition: always
    on_violation: escalate

---
# Tool referencing the policy
component_type: ServerTool
name: delete_record
description: Permanently delete a database record
inputs:
  - title: record_id
    type: string
outputs:
  - title: success
    type: boolean
tool_policy:
  $component_ref: e1f2a3b4-c5d6-7890-1234-567890abcdef

---
# Another tool sharing the same policy
component_type: ServerTool
name: purge_logs
description: Permanently purge audit logs older than retention period
inputs:
  - title: older_than_days
    type: integer
outputs:
  - title: purged_count
    type: integer
tool_policy:
  $component_ref: e1f2a3b4-c5d6-7890-1234-567890abcdef
```

### Conditional approval (input-aware guard)

```yaml
component_type: ServerTool
name: transfer_funds
description: Transfer money between accounts
inputs:
  - title: amount
    type: number
  - title: destination_account
    type: string
outputs:
  - title: transaction_id
    type: string
tool_policy:
  data_classification: confidential
  requires_justification: true
  guards:
    - type: rate_limit
      max_calls: 10
      window_seconds: 3600
      on_violation: block
    - type: require_approval
      condition: input_contains
      field: destination_account
      value: "external:"
      on_violation: escalate
```
