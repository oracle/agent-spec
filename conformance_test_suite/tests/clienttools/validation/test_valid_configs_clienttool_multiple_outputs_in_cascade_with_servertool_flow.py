# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from ...conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "clienttool_multiple_outputs_in_cascade_with_servertool_flow.yaml"


# Provide the mapping for this test (only needed for the local deterministic llm server)
@pytest.fixture
def prompt_to_result_mappings():
    return {
        "Return this user input exactly as it is provided: US\n    Your answer should be a single string, without modification.\n    Do not include any units, reasoning, or extra text.": "US",
        "Return this user input exactly as it is provided: France\n    Your answer should be a single string, without modification.\n    Do not include any units, reasoning, or extra text.": "France",
    }


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


city_by_country = {"Morocco": "Agadir", "Canada": "Nunavut", "France": "Grenoble", "US": "Grenoble"}
weather_by_city = {
    "Agadir, Africa": "Sunny",
    "Nunavut, North America": "Cold",
    "Grenoble, Europe": "Rainy",
    "Grenoble, North America": "Warm",
}

# Track if weather_tool was called
weather_tool_called = False


def weather_tool(city, continent):
    global weather_tool_called
    weather_tool_called = True
    return weather_by_city[f"{city}, {continent}"]


@pytest.fixture
def agentspec_component_fixture(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:

    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    tool_registry = {"weather_tool": weather_tool}
    agentspec_component = load_agentspec_config(
        agentspec_config=agentspec_configuration, tool_registry=tool_registry
    )
    return agentspec_component


def test_valid_configs_clienttool_multiple_outputs_in_cascade_with_servertool_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Test that the configuration can be loaded successfully."""
    assert agentspec_component_fixture is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_input, expected_weather, continent",
    [
        ("Morocco", "Sunny", "Africa"),
        ("Canada", "Cold", "North America"),
        ("France", "Rainy", "Europe"),
        ("US", "Warm", "North America"),
    ],
)
def test_valid_configs_clienttool_multiple_outputs_in_cascade_with_servertool_can_be_executed(
    agentspec_component_fixture, user_input, expected_weather, continent
) -> None:
    """Test execution, assuming loading already works."""
    global weather_tool_called
    weather_tool_called = False

    agentspec_component = agentspec_component_fixture
    agentspec_component.start({"user_input": user_input})
    result = agentspec_component.run()

    assert hasattr(
        result, "tool_requests"
    ), "Returned result does not have the expected 'tool_requests' attribute"
    assert result.tool_requests[0].name == "city_tool"
    assert result.tool_requests[0].args == {"country": user_input}

    # Provide inputs and run
    agentspec_component.append_tool_results(
        ToolResult(
            content={"city": city_by_country[user_input], "continent": continent},
            tool_request_id=result.tool_requests[0].tool_request_id,
        )
    )
    result = agentspec_component.run()

    assert weather_tool_called is True, f"The tool weather_tool was not called as expected."

    assert (
        result.outputs["weather"] == expected_weather
    ), f"Expected {expected_weather} for {user_input}"
