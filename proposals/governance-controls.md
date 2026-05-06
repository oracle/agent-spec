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
rate_limit:
  max_calls: 100
  window_seconds: 3600
data_classification: pii
requires_justification: true
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
      approval_required_for:
        - condition: input_contains
          field: to
          value: "@gov."
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

    rate_limit:
      type: object
      description: Limits on invocation frequency.
      properties:
        max_calls:
          type: integer
          minimum: 1
          description: Maximum number of calls permitted within the time window.
        window_seconds:
          type: integer
          minimum: 1
          description: Rolling time window in seconds.
      required: [max_calls, window_seconds]

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

    allowed_callers:
      type: array
      items:
        $ref: "#/$component_ref"
      description: >
        Component references (by ID) of agents or flows permitted to
        invoke this tool. If omitted, any component with the tool in
        scope may invoke it.

    denied_callers:
      type: array
      items:
        $ref: "#/$component_ref"
      description: >
        Component references (by ID) explicitly denied from invoking
        this tool. Takes precedence over allowed_callers.

    approval_required_for:
      type: array
      items:
        $ref: "#/ConditionalApproval"
      description: >
        Conditions under which human approval is required before
        the tool executes. Extends the existing requires_confirmation
        concept with input-aware conditions.

  additionalProperties: false

ConditionalApproval:
  type: object
  description: >
    A condition on tool inputs that, when matched, requires human
    approval before execution.
  properties:
    condition:
      type: string
      enum: [input_equals, input_contains, input_not_equals]
      description: The type of condition to evaluate.
    field:
      type: string
      description: Name of the input field to evaluate.
    value:
      type: string
      description: Value to compare against using the specified condition.
  required: [condition, field, value]
```

### Policy Composition: ToolBox + Tool

When a `ToolBox` has a `tool_policy` and individual tools within that box also have their own `tool_policy`, the effective policy for a tool is the **union** of both:

- **rate_limit**: The more restrictive limit applies (lower `max_calls` or shorter `window_seconds`).
- **data_classification**: The higher sensitivity level wins (`restricted` > `confidential` > `internal` > `public`).
- **requires_justification**: `true` at either level means justification is required.
- **allowed_callers**: Intersection of both lists (caller must be allowed at both levels).
- **denied_callers**: Union of both lists (denied at either level means denied).
- **approval_required_for**: Union of both condition lists (all conditions from both levels apply).

**Example:**

```yaml
component_type: MCPToolBox
id: d4e5f6a7-b8c9-0123-4567-890abcdef012
name: customer_data_tools
description: Tools for accessing customer records
tool_policy:
  data_classification: confidential
  requires_justification: true
tools:
  - component_type: ServerTool
    name: query_customer
    description: Look up customer records
    inputs:
      - title: customer_id
        type: string
    outputs:
      - title: record
        type: object
    tool_policy:
      rate_limit:
        max_calls: 100
        window_seconds: 3600
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
      allowed_callers:
        - $component_ref: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

In this example:
- `query_customer` inherits `confidential` classification and `requires_justification: true` from the toolbox, and adds its own rate limit.
- `delete_customer` escalates to `restricted` (higher than the toolbox's `confidential`) and restricts callers.

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
      enum: [blocked, flagged, logged]
      description: >
        What the runtime did in response.
        - blocked: Invocation was prevented.
        - flagged: Invocation proceeded but was flagged for review.
        - logged: Invocation proceeded, violation recorded only.
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

The existing `Tool.requires_confirmation` and `ToolBox.requires_confirmation` fields remain unchanged. `tool_policy.approval_required_for` extends the concept by adding input-aware conditions. These are complementary:

- `requires_confirmation: true` means *always* require confirmation.
- `approval_required_for` means *conditionally* require confirmation based on inputs.

There is no duplication. `tool_policy` does not re-define `requires_confirmation`.

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
4. **ToolBox + Tool policy interaction**: Effective policy is the union of both levels, with specifics defined per field (see [Policy Composition](#policy-composition-toolbox--tool) above).

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
  rate_limit:
    max_calls: 50
    window_seconds: 3600
```

### Reusable policy across multiple tools

```yaml
# Standalone policy component
component_type: ToolPolicy
id: e1f2a3b4-c5d6-7890-1234-567890abcdef
name: high_security_policy
rate_limit:
  max_calls: 10
  window_seconds: 3600
data_classification: restricted
requires_justification: true

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
requires_confirmation: true
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
requires_confirmation: true
tool_policy:
  $component_ref: e1f2a3b4-c5d6-7890-1234-567890abcdef
```

### Conditional approval

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
  rate_limit:
    max_calls: 10
    window_seconds: 3600
  requires_justification: true
  approval_required_for:
    - condition: input_contains
      field: destination_account
      value: "external:"
```
