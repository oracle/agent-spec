# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import os
import random
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

import pytest


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


def _replace_config_placeholders(yaml_config: str) -> str:
    return yaml_config.replace("[[LLAMA_API_URL]]", os.environ.get("LLAMA_API_URL")).replace(
        "[[LLAMA70BV33_API_URL]]", os.environ.get("LLAMA70BV33_API_URL")
    )


@pytest.fixture()
def weather_agent_client_tool_yaml() -> str:
    return _replace_config_placeholders((CONFIGS / "weather_agent_client_tool.yaml").read_text())


@pytest.fixture()
def weather_agent_remote_tool_yaml() -> str:
    return _replace_config_placeholders((CONFIGS / "weather_agent_remote_tool.yaml").read_text())


@pytest.fixture()
def weather_agent_server_tool_yaml() -> str:
    return _replace_config_placeholders((CONFIGS / "weather_agent_server_tool.yaml").read_text())


@pytest.fixture()
def weather_ollama_agent_yaml() -> str:
    return _replace_config_placeholders((CONFIGS / "weather_ollama_agent.yaml").read_text())


@pytest.fixture()
def weather_agent_with_outputs_yaml() -> str:
    return _replace_config_placeholders((CONFIGS / "weather_agent_with_outputs.yaml").read_text())


@pytest.fixture()
def ancestry_agent_with_client_tool_yaml() -> str:
    return _replace_config_placeholders(
        (CONFIGS / "ancestry_agent_with_client_tool.yaml").read_text()
    )


def is_port_busy(port: Optional[int]):
    if port is None:
        return True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


# We try to find an open port between 8000 and 9000 for 5 times, if we don't we skip remote tests
attempt = 0
while is_port_busy(JSON_SERVER_PORT := random.randint(8000, 9000)) and attempt < 5:
    time.sleep(1)
    attempt += 1

JSON_SERVER_PORT = JSON_SERVER_PORT if attempt < 5 else None
IS_JSON_SERVER_RUNNING = False


def _start_json_server() -> subprocess.Popen:
    api_server = Path(__file__).parent / "api_server.py"
    process = subprocess.Popen(
        [
            "fastapi",
            "run",
            str(api_server.absolute()),
            f"--port={JSON_SERVER_PORT}",
        ]
    )
    time.sleep(3)
    return process


@pytest.fixture(scope="session")
def json_server():
    global IS_JSON_SERVER_RUNNING
    if JSON_SERVER_PORT is not None:
        IS_JSON_SERVER_RUNNING = True
        process = _start_json_server()
        yield
        process.kill()
        process.wait()
    IS_JSON_SERVER_RUNNING = False
