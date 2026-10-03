# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import pytest

from ..validation.test_valid_configs_flow_with_mcptool import (  # noqa: F401
    agentspec_component_fixture,
)


@pytest.mark.parametrize(
    "inputs, expected_flow_output",
    [
        (
            {},
            (
                "user_info",
                '{\n  "PersonId": "1",\n  "Username": "Bob.b",\n  "DisplayName": "Bob B"\n}',
            ),
        ),
    ],
)
def test_flow_with_mcptool_can_be_executed(
    agentspec_component_fixture, inputs, expected_flow_output, local_mcptool_server
) -> None:
    expected_key, expected_value = expected_flow_output
    agentspec_component_fixture.start(inputs)
    result = agentspec_component_fixture.run()
    outputs = result.outputs

    # Check output result
    assert (
        expected_key in outputs and outputs[expected_key] == expected_value
    ), f"Expected output {expected_key} with value {expected_value}"
