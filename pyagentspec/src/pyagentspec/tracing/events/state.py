# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""State snapshot tracing events for UI and observability consumers."""

from typing import Any, Dict, Optional

from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.tracing.events.event import Event


class StateSnapshotEmitted(Event):
    """A runtime emits a state snapshot for downstream consumers.

    This event carries a lightweight, JSON-serializable snapshot of the current
    conversation or thread state. The exact schema of ``state_snapshot`` is
    intentionally runtime-defined.
    """

    conversation_id: str
    """Identifier of the conversation or thread this snapshot refers to."""

    state_snapshot: SensitiveField[Optional[Dict[str, Any]]] = None
    """Runtime-defined snapshot content for the current state."""

    extra_state: SensitiveField[Optional[Dict[str, Any]]] = None
    """Optional developer-defined UI or application state."""
