# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import pytest

from ..validation.test_valid_configs_agent_with_mcptoolbox import (  # noqa: F401
    agentspec_component_fixture,
)


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "Return the last payslip amount (e.g. 'CHF 1234', or 'USD 5678') for the current user.": {
            "tool_call": {"name": "get_user_session", "args": {}}
        },
        '{\n  "PersonId": "1",\n  "Username": "Bob.b",\n  "DisplayName": "Bob B"\n}': {
            "tool_call": {"name": "get_payslips", "args": {"PersonId": "1"}}
        },
        '{\n  "Amount": 5000,\n  "Currency": "CHF",\n  "PeriodStartDate": "2024/05/01",\n  "PeriodEndDate": "2024/06/01",\n  "PaymentDate": "2024/05/15",\n  "DocumentId": 1,\n  "PersonId": 1\n}': "The amount is CHF 5000",
    }


@pytest.mark.parametrize(
    "user_message, expected_llm_output",
    [
        (
            "Return the last payslip amount (e.g. 'CHF 1234', or 'USD 5678') for the current user.",
            "The amount is CHF 5000",
        ),
    ],
)
def test_agent_with_mcptoolbox_can_be_executed(
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
