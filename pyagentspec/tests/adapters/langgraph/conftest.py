# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path
from typing import Any

import pytest

from ..conftest import _replace_config_placeholders, skip_tests_if_dependency_not_installed


def pytest_collection_modifyitems(config: Any, items: Any):
    # We skip all the tests in this folder if langgraph is not installed
    skip_tests_if_dependency_not_installed(
        module_name="langgraph",
        directory=Path(__file__).parent,
        items=items,
    )


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


@pytest.fixture()
def disable_parallel_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    from langchain_openai.chat_models import ChatOpenAI

    original_init = ChatOpenAI.__init__

    def init_without_parallel_tool_calls(self: ChatOpenAI, *args: Any, **kwargs: Any) -> None:
        model_kwargs = kwargs.setdefault("model_kwargs", {})
        model_kwargs.setdefault("parallel_tool_calls", False)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(ChatOpenAI, "__init__", init_without_parallel_tool_calls)


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


@pytest.fixture()
def swarm_calculator_yaml(json_server: str) -> str:
    return _replace_config_placeholders(
        (CONFIGS / "swarm_calculator.yaml").read_text(), json_server
    )
