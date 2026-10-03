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

# TO DO: Test not passing because of following error in WayFlow: "ValueError: Unknown output descriptor specified: StringProperty(name='country', description='', default_value=<class 'wayflowcore.property._empty_default'>). Make sure there is no misspelling.
# Possible output descriptors are: [StringProperty(name='http_response', description='raw http response', default_value=<class 'wayflowcore.property._empty_default'>)]"
# Problem: RemoteTool used inside a ToolNode uses name 'http_response' for output descriptor instead of the specified "country" output property name in this test.

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "remotetool_in_cascade_with_clienttool_and_servertool_flow.yaml"


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


city_by_country = {"Morocco": "Agadir", "Canada": "Nunavut"}
weather_by_city = {"Agadir": "Sunny", "Nunavut": "Cold", "Unknown": "Unknown"}

# Track if weather_tool was called
weather_tool_called = False


def weather_tool(city):
    global weather_tool_called
    weather_tool_called = True
    return weather_by_city[city]


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


def test_valid_configs_remotetool_in_cascade_with_clienttool_and_servertool_flow_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Test that the configuration can be loaded successfully."""
    assert agentspec_component_fixture is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_input, expected_weather",
    [
        ("Africa", "Sunny"),
        ("America", "Cold"),
    ],
)
def test_valid_configs_remotetool_in_cascade_with_clienttool_and_servertool_flow_can_be_executed(
    agentspec_component_fixture, user_input, expected_weather
) -> None:
    """Test execution, assuming loading already works."""
    # Ensure weather_tool_called is reset for each test
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

    # Provide input
    agentspec_component.append_tool_results(
        ToolResult(
            content=city_by_country[user_input],
            tool_request_id=result.tool_requests[0].tool_request_id,
        )
    )
    result = agentspec_component.run()

    assert weather_tool_called is True, f"The tool weather_tool was not called as expected."

    assert (
        result.outputs["weather"] == expected_weather
    ), f"Expected {expected_weather} for {user_input}"
