# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import contextlib
import os
import socket
import threading
import time
from pathlib import Path
from typing import Optional

import pytest
import uvicorn

SKIP_LLM_TESTS_ENV_VAR = "SKIP_LLM_TESTS"


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
    llama_api_url = os.environ.get("LLAMA_API_URL")
    llama70bv33_api_url = os.environ.get("LLAMA70BV33_API_URL")
    assert llama_api_url, "Please set LLAMA_API_URL"
    assert llama70bv33_api_url, "Please set LLAMA70BV33_API_URL"
    return yaml_config.replace("[[LLAMA_API_URL]]", llama_api_url).replace(
        "[[LLAMA70BV33_API_URL]]", llama70bv33_api_url
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


JSON_SERVER_PORT: int | None = None
IS_JSON_SERVER_RUNNING: bool = False


def _get_free_tcp_port(host: str = "127.0.0.1") -> int:
    """Ask the OS for a free TCP port safely."""
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((host, 0))  # kernel chooses free port
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 5.0) -> None:
    """Wait until host:port is ready to accept connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError(f"Server on {host}:{port} did not start within {timeout} seconds")


def _import_api_app():
    """Import FastAPI app from local api_server.py"""
    from . import api_server

    app = getattr(api_server, "app", None)
    if app is None:
        raise RuntimeError("tests/api_server.py must expose a FastAPI `app` variable.")
    return app


def _start_json_server_in_thread(host: str, port: int) -> tuple[uvicorn.Server, threading.Thread]:
    """Start uvicorn in background thread (no subprocess)."""
    app = _import_api_app()
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config=config)

    thread = threading.Thread(target=server.run, name="json-test-server", daemon=True)
    thread.start()

    _wait_for_port(host, port)
    return server, thread


# allocate port at import time
try:
    JSON_SERVER_PORT = _get_free_tcp_port()
except OSError:
    JSON_SERVER_PORT = None

_json_server_thread: threading.Thread | None = None
_json_server_instance: uvicorn.Server | None = None


@pytest.fixture(scope="session")
def json_server():
    """Session fixture starting/stopping FastAPI JSON server."""
    global IS_JSON_SERVER_RUNNING, _json_server_thread, _json_server_instance

    if JSON_SERVER_PORT is not None:
        IS_JSON_SERVER_RUNNING = True
        host = "127.0.0.1"
        _json_server_instance, _json_server_thread = _start_json_server_in_thread(
            host, JSON_SERVER_PORT
        )
        try:
            yield
        finally:
            _json_server_instance.should_exit = True
            _json_server_thread.join(timeout=5)
            IS_JSON_SERVER_RUNNING = False
    else:
        IS_JSON_SERVER_RUNNING = False
        yield


def should_skip_llm_test() -> bool:
    return SKIP_LLM_TESTS_ENV_VAR in os.environ


def _replace_config_placeholders(yaml_config: str) -> str:
    """
    Adapter tests load YAMLs with {{LLAMA_API_URL}} / {{LLAMA70BV33_API_URL}}.
    - if SKIP_LLM_TESTS=1 and env vars are missing → skip
    - otherwise → assert (fail early)
    """
    llama_api_url = os.environ.get("LLAMA_API_URL")
    llama70bv33_api_url = os.environ.get("LLAMA70BV33_API_URL")

    if (not llama_api_url or not llama70bv33_api_url) and should_skip_llm_test():
        pytest.skip(
            "Skipping LLM-dependent adapter test: LLAMA_API_URL / LLAMA70BV33_API_URL "
            "not set and SKIP_LLM_TESTS=1"
        )

    assert llama_api_url, "Please set LLAMA_API_URL"
    assert llama70bv33_api_url, "Please set LLAMA70BV33_API_URL"

    return yaml_config.replace("{{LLAMA_API_URL}}", llama_api_url).replace(
        "{{LLAMA70BV33_API_URL}}", llama70bv33_api_url
    )
