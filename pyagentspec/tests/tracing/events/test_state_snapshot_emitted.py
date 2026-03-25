# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest
from pydantic import ValidationError

from pyagentspec.tracing._basemodel import _PII_MASK
from pyagentspec.tracing.events import StateSnapshotEmitted


def test_state_snapshot_emitted_creation_and_masking() -> None:
    event = StateSnapshotEmitted(
        conversation_id="conversation-123",
        state_snapshot={"conversation": {"messages": []}},
        extra_state={"ui": {"active_tab": "plan"}},
        name="snapshot",
    )

    assert event.name == "snapshot"
    assert event.conversation_id == "conversation-123"
    assert event.state_snapshot == {"conversation": {"messages": []}}
    assert event.extra_state == {"ui": {"active_tab": "plan"}}

    masked = event.model_dump(mask_sensitive_information=True)
    unmasked = event.model_dump(mask_sensitive_information=False)

    assert masked["state_snapshot"] == _PII_MASK
    assert masked["extra_state"] == _PII_MASK
    assert masked["conversation_id"] == "conversation-123"
    assert masked["type"] == "StateSnapshotEmitted"

    assert unmasked["state_snapshot"] == {"conversation": {"messages": []}}
    assert unmasked["extra_state"] == {"ui": {"active_tab": "plan"}}


@pytest.mark.parametrize(
    ("state_snapshot", "extra_state"),
    [
        ({"conversation": {"messages": []}}, None),
        (None, {"ui": {"active_tab": "plan"}}),
    ],
)
def test_state_snapshot_emitted_allows_either_payload(
    state_snapshot: dict[str, object] | None, extra_state: dict[str, object] | None
) -> None:
    event = StateSnapshotEmitted(
        conversation_id="conversation-123",
        state_snapshot=state_snapshot,
        extra_state=extra_state,
    )

    assert event.state_snapshot == state_snapshot
    assert event.extra_state == extra_state


def test_state_snapshot_emitted_requires_payload() -> None:
    with pytest.raises(
        ValidationError, match="At least one of state_snapshot or extra_state must be provided"
    ):
        StateSnapshotEmitted(conversation_id="conversation-123")


@pytest.mark.parametrize(
    ("kwargs", "expected_message"),
    [
        (
            {"state_snapshot": {"conversation": {"opaque": object()}}},
            "state_snapshot must be JSON-serializable",
        ),
        (
            {"extra_state": {"ui": {"opaque": object()}}},
            "extra_state must be JSON-serializable",
        ),
    ],
)
def test_state_snapshot_emitted_rejects_non_json_serializable_payloads(
    kwargs: dict[str, object], expected_message: str
) -> None:
    with pytest.raises(ValidationError, match=expected_message):
        StateSnapshotEmitted(conversation_id="conversation-123", **kwargs)


def test_state_snapshot_emitted_accepts_realistic_runtime_resumable_payload() -> None:
    state_snapshot = {
        "runtime": "my-agent-runtime",
        "schema_version": 1,
        "conversation_state": '{"type":"FlowConversation","version":1}',
        "conversation": {
            "id": "runtime-conversation-123",
            "messages": [],
        },
        "execution": {
            "status": None,
            "status_handled": False,
        },
    }
    event = StateSnapshotEmitted(
        conversation_id="conversation-123",
        state_snapshot=state_snapshot,
        extra_state={"ui": {"active_tab": "plan"}},
    )

    assert event.conversation_id == "conversation-123"
    assert event.state_snapshot == state_snapshot
    assert event.state_snapshot["conversation_state"] == '{"type":"FlowConversation","version":1}'
    assert event.extra_state == {"ui": {"active_tab": "plan"}}
