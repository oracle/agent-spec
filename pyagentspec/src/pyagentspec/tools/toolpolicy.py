# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tool usage policy configuration for governance and compliance controls.

A ``ToolPolicy`` defines governance constraints on tool usage including data
classification, access control, execution guards, and violation handling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from pyagentspec.component import Component
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum

DataClassificationT = Literal["public", "internal", "confidential", "restricted"]
"""Sensitivity classification for data handled by a tool.

- ``public``: Data that is freely available and has no access restrictions.
- ``internal``: Data intended for internal use only.
- ``confidential``: Sensitive data requiring controlled access.
- ``restricted``: Highly sensitive data with strict access and audit requirements.
"""

ViolationActionT = Literal["block", "flag", "log", "escalate"]
"""Action to take when a policy guard condition is violated.

- ``block``: Prevent the tool execution entirely.
- ``flag``: Allow execution but flag it for review.
- ``log``: Allow execution and log the event.
- ``escalate``: Escalate to a human or supervisory agent for a decision.
"""

GuardConditionT = Literal["always", "input_equals", "input_contains", "input_not_equals"]
"""Condition that determines when a guard is triggered.

- ``always``: Guard applies unconditionally on every invocation.
- ``input_equals``: Guard applies when a specific input field equals a value.
- ``input_contains``: Guard applies when a specific input field contains a value.
- ``input_not_equals``: Guard applies when a specific input field does not equal a value.
"""


class RateLimitGuard(Component):
    """Limits how frequently a tool may be invoked within a sliding time window."""

    max_calls: int = Field(ge=1)
    """Maximum number of allowed invocations within the time window."""

    window_seconds: int = Field(ge=1)
    """Duration of the sliding window in seconds."""

    on_violation: ViolationActionT = "block"
    """Action to take when the rate limit is exceeded."""


class ApprovalGuard(Component):
    """Requires explicit approval before tool execution proceeds."""

    condition: GuardConditionT = "always"
    """When approval is required. ``always`` requires it unconditionally;
    input-conditional values evaluate against a specific input field."""

    field: Optional[str] = None
    """Input field name to inspect when condition is input-conditional."""

    value: Optional[str] = None
    """Value to match against the input field when condition is input-conditional."""

    on_violation: Literal["block", "escalate"] = "escalate"
    """Action to take when approval is not granted."""

    @model_validator_with_error_accumulation
    def _validate_conditional_fields(self) -> "ApprovalGuard":
        """Ensure field and value are provided for input-conditional conditions."""
        if self.condition in ("input_equals", "input_contains", "input_not_equals"):
            if not self.field:
                raise ValueError(
                    f"`field` is required when condition is '{self.condition}'"
                )
            if self.value is None:
                raise ValueError(
                    f"`value` is required when condition is '{self.condition}'"
                )
        return self


class JustificationGuard(Component):
    """Requires the caller to supply a textual justification before execution."""

    condition: GuardConditionT = "always"
    """When justification is required. ``always`` requires it unconditionally;
    input-conditional values evaluate against a specific input field."""

    field: Optional[str] = None
    """Input field name to inspect when condition is input-conditional."""

    value: Optional[str] = None
    """Value to match against the input field when condition is input-conditional."""

    on_violation: Literal["block", "flag"] = "block"
    """Action to take when justification is not provided."""

    @model_validator_with_error_accumulation
    def _validate_conditional_fields(self) -> "JustificationGuard":
        """Ensure field and value are provided for input-conditional conditions."""
        if self.condition in ("input_equals", "input_contains", "input_not_equals"):
            if not self.field:
                raise ValueError(
                    f"`field` is required when condition is '{self.condition}'"
                )
            if self.value is None:
                raise ValueError(
                    f"`value` is required when condition is '{self.condition}'"
                )
        return self


ExecutionGuard = Union[RateLimitGuard, ApprovalGuard, JustificationGuard]
"""Discriminated union of all supported execution guard types.

Guards are evaluated in declaration order. The first violation triggers
the corresponding ``on_violation`` action.
"""


class ToolPolicy(Component):
    """Governance policy controlling how a tool may be invoked.

    A ``ToolPolicy`` can be attached directly to a ``Tool`` or ``ToolBox`` via
    the ``tool_policy`` field. When attached to a ToolBox, it applies to all
    tools within that box unless overridden at the individual tool level.

    As a ``Component``, ``ToolPolicy`` supports the reference system: define
    a policy once with an ``id`` and ``name``, then reference it from multiple
    tools via ``$component_ref``.

    Composition rules (ToolBox + Tool):
    - ``data_classification``: stricter (higher sensitivity) wins.
    - ``guards``: union of both guard lists, evaluated in declaration order.
    - ``allowed_callers``: intersection (caller must appear in both lists).
    - ``denied_callers``: union (denied at either level means denied).
    - ``requires_justification``: logical OR (either requiring it is sufficient).
    """

    data_classification: DataClassificationT = "public"
    """Sensitivity classification of data this tool handles."""

    requires_justification: bool = False
    """Whether a textual justification must be provided before invocation."""

    allowed_callers: Optional[List[Component]] = None
    """Component references of agents or flows permitted to invoke the tool.

    When ``None``, no caller restriction is applied. An empty list means
    no caller is allowed (effectively disabling the tool).
    """

    denied_callers: Optional[List[Component]] = None
    """Component references explicitly denied from invoking the tool.

    Takes precedence over ``allowed_callers``. When ``None``, no explicit
    denials are applied.
    """

    guards: List[ExecutionGuard] = Field(default_factory=list)
    """Ordered list of execution guards evaluated before tool invocation.

    Guards are checked in declaration order. The first guard whose condition
    is met triggers its ``on_violation`` action.
    """

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: "AgentSpecVersionEnum"
    ) -> set[str]:
        return set()
