# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import pytest

from ..validation.test_valid_configs_agent_with_mcptool import (  # noqa: F401
    agentspec_component_fixture,
)


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "What is the username of the current user?": {
            "tool_call": {"name": "get_user_session", "args": {}}
        },
        '{\n  "PersonId": "1",\n  "Username": "Bob.b",\n  "DisplayName": "Bob B"\n}': "The username is Bob.b",
    }


@pytest.mark.parametrize(
    "user_message, expected_llm_output",
    [
        (
            "What is the username of the current user?",
            "The username is Bob.b",
        ),
    ],
)
def test_agent_with_mcptool_can_be_executed(
    agentspec_component_fixture,
    user_message,
    expected_llm_output,
    local_deterministic_llm_server,
    local_mcptool_server,
) -> None:
    agentspec_component_fixture.start()
    agentspec_component_fixture.append_user_message(user_message=user_message)
    result = agentspec_component_fixture.run()

    # Check output result
    assert expected_llm_output in result.agent_messages[-1]
