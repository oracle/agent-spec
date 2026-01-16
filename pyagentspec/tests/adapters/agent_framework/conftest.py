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
from typing import Any

import pytest
import uvicorn

from ..conftest import skip_tests_if_dependency_not_installed


def pytest_collection_modifyitems(config: Any, items: Any):
    # We skip all the tests in this folder if agent_framework is not installed
    skip_tests_if_dependency_not_installed(
        module_name="agent_framework",
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


CONFIGS = Path(__file__).parent / "configs"


def _replace_config_placeholders(yaml_config: str) -> str:
    llama_api_url = os.environ.get("LLAMA_API_URL")
    llama70bv33_api_url = os.environ.get("LLAMA70BV33_API_URL")
    oss_120b_url = os.environ.get("OSS_API_URL")

    assert llama_api_url, "Please set LLAMA_API_URL"
    assert llama70bv33_api_url, "Please set LLAMA70BV33_API_URL"
    assert oss_120b_url, "Please set OSS_API_URL"

    return (
        yaml_config.replace("[[LLAMA_API_URL]]", llama_api_url)
        .replace("[[LLAMA70BV33_API_URL]]", llama70bv33_api_url)
        .replace("[[OSS_API_URL]]", oss_120b_url)
    )


@pytest.fixture()
def weather_agent_server_tool() -> str:
    return _replace_config_placeholders((CONFIGS / "weather_agent_server_tool.yaml").read_text())


@pytest.fixture()
def weather_agent_remote_tool() -> str:
    return _replace_config_placeholders((CONFIGS / "weather_agent_remote_tool.yaml").read_text())


@pytest.fixture()
def weather_agent_client_tool() -> str:
    return _replace_config_placeholders((CONFIGS / "weather_agent_client_tool.yaml").read_text())


def _get_free_tcp_port(host: str = "127.0.0.1") -> int | None:
    """Ask the OS for a free TCP port safely."""
    try:
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind((host, 0))  # kernel chooses free port
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]
    except OSError:
        return None


def _wait_until_hostport_is_alive(host: str, port: int, timeout: float = 5.0) -> None:
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


def _start_app_server_in_thread(
    app, host: str, port: int
) -> tuple[uvicorn.Server, threading.Thread]:
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config=config)

    thread = threading.Thread(target=server.run, name="json-test-server", daemon=True)
    thread.start()

    _wait_until_hostport_is_alive(host, port)
    return server, thread


JSON_SERVER_PORT: int | None = _get_free_tcp_port()
IS_JSON_SERVER_RUNNING: bool = False

_json_server_thread: threading.Thread | None = None
_json_server_instance: uvicorn.Server | None = None


@pytest.fixture(scope="session")
def json_server():
    """Session fixture starting/stopping FastAPI JSON server."""
    global IS_JSON_SERVER_RUNNING, _json_server_thread, _json_server_instance

    if JSON_SERVER_PORT is not None:
        IS_JSON_SERVER_RUNNING = True
        host = "127.0.0.1"
        _json_server_instance, _json_server_thread = _start_app_server_in_thread(
            _import_api_app(), host, JSON_SERVER_PORT
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
