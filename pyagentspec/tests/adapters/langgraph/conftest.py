# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path
from typing import Any

import pytest

from ..conftest import _replace_config_placeholders


def pytest_collection_modifyitems(config: Any, items: Any):
    # We skip all the tests in this folder if langgraph is not installed
    try:
        import langgraph  # type: ignore

        dependency_missing = False
    except ImportError:
        dependency_missing = True

    for item in items:
        if dependency_missing:
            # If the dependency is missing we run only the test to check that the right error is raised
            if item.name != "test_import_raises_if_langgraph_not_installed":
                item.add_marker(pytest.mark.skip(reason="LangGraph is not installed"))
        else:
            # If the dependency is installed we run all the tests except the one that checks the import error
            if item.name == "test_import_raises_if_langgraph_not_installed":
                item.add_marker(pytest.mark.skip(reason="LangGraph is installed"))


def get_weather(city: str) -> str:
    """Returns the weather in a specific city.
    Args
    ----
        city: The city to check the weather for

    Returns
    -------
        weather: The weather in that city
    """
    return f"The weather in {city} is sunny."


CONFIGS = Path(__file__).parent / "configs"


@pytest.fixture()
def weather_agent_client_tool_yaml(json_server: str) -> str:
    return _replace_config_placeholders(
        (CONFIGS / "weather_agent_client_tool.yaml").read_text(), json_server
    )


@pytest.fixture()
def weather_agent_remote_tool_yaml(json_server: str) -> str:
    return _replace_config_placeholders(
        (CONFIGS / "weather_agent_remote_tool.yaml").read_text(), json_server
    )


@pytest.fixture()
def weather_agent_server_tool_yaml(json_server: str) -> str:
    return _replace_config_placeholders(
        (CONFIGS / "weather_agent_server_tool.yaml").read_text(), json_server
    )


@pytest.fixture()
def weather_ollama_agent_yaml(json_server: str) -> str:
    return _replace_config_placeholders(
        (CONFIGS / "weather_ollama_agent.yaml").read_text(), json_server
    )


@pytest.fixture()
def weather_agent_with_outputs_yaml(json_server: str) -> str:
    return _replace_config_placeholders(
        (CONFIGS / "weather_agent_with_outputs.yaml").read_text(), json_server
    )


@pytest.fixture()
def ancestry_agent_with_client_tool_yaml(json_server: str) -> str:
    return _replace_config_placeholders(
        (CONFIGS / "ancestry_agent_with_client_tool.yaml").read_text(), json_server
    )
