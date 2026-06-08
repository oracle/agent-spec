# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tracing event emitted when a tool policy guard is violated."""

from typing import Any, Dict, Literal, Optional

from pyagentspec.component import Component
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.tools import Tool
from pyagentspec.tools.toolpolicy import ExecutionGuard, ToolPolicy, ViolationActionT
from pyagentspec.tracing.events.event import Event

ViolationTypeT = Literal[
    "rate_limit_exceeded",
    "caller_denied",
    "justification_missing",
    "approval_required",
    "classification_breach",
]
"""Category of the policy violation."""


class PolicyViolation(Event):
    """Emitted when a tool invocation violates a policy guard.

    This event captures which guard was triggered, what action was taken,
    and the context of the attempted invocation.
    """

    tool: Tool
    """The tool whose policy was violated."""

    policy: ToolPolicy
    """The policy that was violated."""

    guard: ExecutionGuard
    """The specific guard that triggered the violation."""

    violation_type: ViolationTypeT
    """The category of violation."""

    action_taken: ViolationActionT
    """The action that was applied as a result of the violation."""

    caller: Optional[Component] = None
    """The component that attempted the invocation."""

    inputs: SensitiveField[Optional[Dict[str, Any]]] = None
    """The input values that were provided for the attempted invocation."""

    detail: Optional[str] = None
    """Human-readable explanation of the violation."""
