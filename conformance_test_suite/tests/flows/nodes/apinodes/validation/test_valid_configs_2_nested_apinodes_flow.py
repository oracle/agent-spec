# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path
from typing import Any

import pytest

from .....conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "2_nested_apinodes_flow.yaml"


@pytest.fixture
def agentspec_component_fixture(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:

    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(agentspec_config=agentspec_configuration)
    return agentspec_component


def test_valid_configs_2_nested_apinodes_flow_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Test that the configuration can be loaded successfully."""
    assert agentspec_component_fixture is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_input, expected_weather, expected_temperature",
    [
        ("Morocco", "Sunny", 22.0),
        ("Switzerland", "Rainy", 15.0),
    ],
)
def test_valid_configs_2_nested_apinodes_flow_can_be_executed(
    agentspec_component_fixture,
    user_input,
    expected_weather,
    expected_temperature,
    local_common_server,
) -> None:
    """Test execution, assuming loading already works."""

    agentspec_component = agentspec_component_fixture
    agentspec_component.start({"user_input": user_input})
    result = agentspec_component.run()

    assert (
        result.outputs["weather"]["weather"] == expected_weather
        and result.outputs["weather"]["temperature"] == expected_temperature
    ), f"Expected {expected_weather} and {expected_temperature} for {user_input}"
