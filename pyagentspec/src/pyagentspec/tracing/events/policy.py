# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tracing event emitted when a tool policy guard is violated."""

from typing import Any, Dict, Optional

from pyagentspec.tools import Tool
from pyagentspec.tools.toolpolicy import ExecutionGuard, ViolationActionT
from pyagentspec.tracing.events.event import Event


class PolicyViolation(Event):
    """Emitted when a tool invocation violates a policy guard.

    This event captures which guard was triggered, what action was taken,
    and the context of the attempted invocation.
    """

    tool: Tool
    """The tool whose policy was violated."""

    guard: ExecutionGuard
    """The specific guard that triggered the violation."""

    action_taken: ViolationActionT
    """The action that was applied as a result of the violation."""

    caller_id: Optional[str] = None
    """Identifier of the agent or component that attempted the invocation."""

    inputs: Optional[Dict[str, Any]] = None
    """The input values that were provided for the attempted invocation."""
