# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
from typing import Any, Dict, Optional

from pydantic import model_validator

from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.tracing.events.event import Event


def _validate_json_serializable_payload(
    payload_name: str, payload: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Validate that a state snapshot payload can be encoded as strict JSON."""
    if payload is None:
        return None

    try:
        # Require strict JSON here, not Python's permissive NaN/Infinity mode.
        # Snapshot payloads are forwarded through JSON-based transports and may later be stored and
        # replayed for resumability. If NaN/Infinity were accepted here, later
        # JSON encoding could silently coerce them (for example to ``null``),
        # breaking the expectation that the runtime snapshot payload is carried
        # through unchanged.
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{payload_name} must be JSON-serializable") from exc

    return payload


class StateSnapshotEmitted(Event):
    """A runtime emits a state snapshot for downstream consumers.

    This event carries a JSON-serializable snapshot of the current
    logical conversation or thread state. The exact schema of ``state_snapshot``
    is intentionally runtime-defined.
    """

    conversation_id: str
    """Stable identifier of the logical conversation or thread this snapshot refers to."""

    state_snapshot: SensitiveField[Optional[Dict[str, Any]]] = None
    """Runtime-defined JSON-serializable snapshot content for the current state.

    This payload may contain opaque runtime-owned state needed for resuming or
    reconstructing execution later.
    """

    extra_state: SensitiveField[Optional[Dict[str, Any]]] = None
    """Developer-defined JSON-serializable state such as UI or application state."""

    @model_validator(mode="after")
    def _validate_payloads(self) -> "StateSnapshotEmitted":
        """Validate that the event carries meaningful and serializable payloads."""
        if self.state_snapshot is None and self.extra_state is None:
            raise ValueError("At least one of state_snapshot or extra_state must be provided")

        _validate_json_serializable_payload("state_snapshot", self.state_snapshot)
        _validate_json_serializable_payload("extra_state", self.extra_state)
        return self
