# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


def test_valid_configuration_message_summarization_transform_can_be_loaded(
    runnable_agent_with_message_summarization_transform_from_agentspec,
) -> None:
    assert (
        runnable_agent_with_message_summarization_transform_from_agentspec is not None
    ), "valid file, should be loaded"


def test_valid_configuration_conversation_summarization_transform_can_be_loaded(
    runnable_agent_with_conversation_summarization_transform_from_agentspec,
) -> None:
    assert (
        runnable_agent_with_conversation_summarization_transform_from_agentspec is not None
    ), "valid file, should be loaded"
