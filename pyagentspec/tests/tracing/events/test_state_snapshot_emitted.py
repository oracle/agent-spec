# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

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
