# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict

from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.tracing.events.event import Event


class HumanInTheLoopRequest(Event):
    """A human-in-the-loop (HITL) intervention is required. Emitted when the execution is interrupted due to HITL request"""

    request_id: str
    "Identifier of the human-in-the-loop request"

    content: SensitiveField[Dict[str, Any]]
    "The content of the request forwarded to the user"


class HumanInTheLoopResponse(Event):
    """A human-in-the-loop response is provided. Emitted when the execution restarts after HITL response."""

    request_id: str
    "Identifier of the human-in-the-loop request"

    content: SensitiveField[Dict[str, Any]]
    "The content of the response received from the user"
