# Proposal: Tool Usage Policies for Agent Spec

**Issue**: [#125](https://github.com/oracle/agent-spec/issues/125)
**Author**: Imran Siddique ([@imran-siddique](https://github.com/imran-siddique))
**Status**: Draft

## Summary

This proposal adds a `tool_policy` property to `Tool` and `ToolBox` components, enabling spec authors to declare constraints on tool invocation. This is the first step toward governance controls in Agent Spec, scoped deliberately to tool usage policies as discussed in [#125](https://github.com/oracle/agent-spec/issues/125).

Agent-level and flow-level governance declarations are out of scope for this proposal and would follow as separate work.

## Motivation

Agent Spec defines *what* an agent can do through tools, toolboxes, and flows. Today, the only control over *how* tools are used is `requires_confirmation`. Production deployments need richer constraints: rate limits, caller restrictions, conditional approval workflows, and data sensitivity annotations.

These constraints are governance concerns that belong in the spec alongside tool definitions, not as runtime-only afterthoughts. Declaring them in the spec makes governance intent portable, auditable, and visible to anyone reading the configuration.

## Design Principles

1. **Declarative**: The spec declares constraints. Runtimes decide enforcement strategy.
2. **Additive**: All new properties are optional. Existing specs are unaffected.
3. **Native to Agent Spec**: Uses existing patterns (`$component_ref`, component IDs, versioning) rather than importing external models.

## Proposed Changes

### ToolPolicy on Tool and ToolBox

A new optional `tool_policy` property on `Tool` and `ToolBox` that declares usage constraints.

**YAML example:**

```yaml
component_type: Agent
name: Customer Support Agent
# ... llm_config, system_prompt ...
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
      rate_limit:
        max_calls: 100
        window_seconds: 3600
      data_classification: confidential
      requires_justification: true
      allowed_callers:
        - $component_ref: f7e8d9c0-b1a2-3456-7890-abcdef012345

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
      approval_required_for:
        - condition: input_contains
          field: to
          value: "@gov."
```

**Schema definition:**

```yaml
ToolPolicy:
  type: object
  description: Declares constraints on how a tool may be invoked.
  properties:
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
      description: >
        Free-form label indicating the sensitivity of data this tool
        accesses or produces (e.g., "public", "confidential", "pii").
        Runtimes may use this for access control or audit decisions.

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

### Relationship to `requires_confirmation`

The existing `Tool.requires_confirmation` and `ToolBox.requires_confirmation` fields remain unchanged. `tool_policy.approval_required_for` extends the concept by adding input-aware conditions. These are complementary:

- `requires_confirmation: true` means *always* require confirmation.
- `approval_required_for` means *conditionally* require confirmation based on inputs.

There is no duplication. `tool_policy` does not re-define `requires_confirmation`.

## Compatibility

- **Backward compatible**: `tool_policy` is optional. Existing specs parse and run without changes.
- **Version gating**: `tool_policy` would be gated behind a new `agentspec_version`, following the existing pattern used for `requires_confirmation` (v25.4.2) and `transforms` (v26.2.0).
- **Runtime behavior**: Runtimes that do not implement tool policies ignore the field. No runtime is required to enforce these constraints.

## Implementation Path

1. **This PR**: Specification proposal defining `ToolPolicy` schema and semantics.
2. **Follow-up**: Pydantic model (`ToolPolicy` class) in `pyagentspec`, serialization/deserialization support.
3. **Follow-up**: Runtime enforcement hooks in adapter layer.
4. **Future proposal**: Agent-level and flow-level governance declarations.

## Prior Art

- Agent Spec's existing `requires_confirmation` on tools and toolboxes.
- [Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit): runtime governance for agentic systems (policy enforcement, caller restrictions, audit logging) across multiple languages. Experience from this project informed the schema design.

## Open Questions

1. Should `tool_policy` be inlined on each tool, or should policies be defined as standalone components and referenced via `$component_ref`? Standalone policies would enable reuse across tools.
2. Should `data_classification` be a free-form string or a constrained enum? Free-form is more flexible across organizations; an enum is more portable.
3. Should there be a dedicated event type (e.g., `PolicyViolation`) in the tracing/events system for governance-related events?
4. How should `tool_policy` on a `ToolBox` interact with policies on individual tools within that box?

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

### Caller-restricted tool

```yaml
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
  requires_justification: true
  data_classification: restricted
  allowed_callers:
    - $component_ref: a1b2c3d4-e5f6-7890-abcd-ef1234567890
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
  rate_limit:
    max_calls: 10
    window_seconds: 3600
  requires_justification: true
  approval_required_for:
    - condition: input_contains
      field: destination_account
      value: "external:"
```
