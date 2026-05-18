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

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from pyagentspec.validation_helpers import model_validator_with_error_accumulation

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


class RateLimitGuard(BaseModel):
    """Limits how frequently a tool may be invoked within a sliding time window."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["rate_limit"] = "rate_limit"
    """Discriminator value for guard type."""

    max_calls: int = Field(ge=1)
    """Maximum number of allowed invocations within the time window."""

    window_seconds: int = Field(ge=1)
    """Duration of the sliding window in seconds."""

    on_violation: ViolationActionT = "block"
    """Action to take when the rate limit is exceeded."""


class ApprovalGuard(BaseModel):
    """Requires explicit approval before tool execution proceeds."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["require_approval"] = "require_approval"
    """Discriminator value for guard type."""

    condition: Literal["always", "input_contains"] = "always"
    """When approval is required. ``always`` requires it unconditionally;
    ``input_contains`` triggers only when a specific input field matches a value."""

    field: Optional[str] = None
    """Input field name to inspect when ``condition`` is ``input_contains``."""

    value: Optional[str] = None
    """Value to match against the input field when ``condition`` is ``input_contains``."""

    on_violation: ViolationActionT = "escalate"
    """Action to take when approval is not granted."""

    @model_validator_with_error_accumulation
    def _validate_conditional_fields(self) -> "ApprovalGuard":
        """Ensure field and value are provided when condition is input_contains."""
        if self.condition == "input_contains":
            if not self.field:
                raise ValueError("`field` is required when condition is 'input_contains'")
            if self.value is None:
                raise ValueError("`value` is required when condition is 'input_contains'")
        return self


class JustificationGuard(BaseModel):
    """Requires the caller to supply a textual justification before execution."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["require_justification"] = "require_justification"
    """Discriminator value for guard type."""

    on_violation: ViolationActionT = "block"
    """Action to take when justification is not provided."""


ExecutionGuard = Union[RateLimitGuard, ApprovalGuard, JustificationGuard]
"""Discriminated union of all supported execution guard types.

Guards are evaluated in declaration order. The first violation triggers
the corresponding ``on_violation`` action.
"""


class ToolPolicy(BaseModel):
    """Governance policy controlling how a tool may be invoked.

    A ``ToolPolicy`` can be attached directly to a ``Tool`` or ``ToolBox`` via
    the ``tool_policy`` field. When attached to a ToolBox, it applies to all
    tools within that box unless overridden at the individual tool level.

    Composition rules (ToolBox + Tool):
    - ``data_classification``: stricter (higher sensitivity) wins.
    - ``guards``: union of both guard lists, evaluated in declaration order.
    - ``allowed_callers``: intersection (caller must appear in both lists).
    - ``requires_justification``: logical OR (either requiring it is sufficient).
    """

    model_config = ConfigDict(extra="forbid")

    data_classification: Optional[DataClassificationT] = None
    """Sensitivity classification of data this tool handles."""

    requires_justification: bool = False
    """Whether a textual justification must be provided before invocation."""

    allowed_callers: Optional[List[str]] = None
    """If set, only agent components with IDs in this list may invoke the tool.

    When ``None``, no caller restriction is applied.
    """

    guards: List[ExecutionGuard] = Field(default_factory=list)
    """Ordered list of execution guards evaluated before tool invocation.

    Guards are checked in declaration order. The first guard whose condition
    is met triggers its ``on_violation`` action.
    """
