# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import logging

from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig

logging.basicConfig(level=logging.DEBUG)
import os
import subprocess  # nosec B404
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import pytest
import requests
from agentspec_cts_sdk import AgentSpecRunnableComponent

logger = logging.getLogger(__name__)
AgentSpecConfigLoaderType = Callable[[str, Optional[Dict[str, Any]]], AgentSpecRunnableComponent]

DETERMINISTIC_LLM_CONF = OpenAiCompatibleConfig(
    name="llm",
    model_id="Llama-4-Maverick",
    url="http://localhost:5006",
)

llama_api_url = os.environ.get("LLAMA_API_URL")
if not llama_api_url:
    raise Exception("LLAMA_API_URL is not set in the environment")

llama70bv33_api_url = os.environ.get("LLAMA70BV33_API_URL")
if not llama70bv33_api_url:
    raise Exception("LLAMA70BV33_API_URL is not set in the environment")

oss_api_url = os.environ.get("OSS_API_URL")
if not oss_api_url:
    raise Exception("OSS_API_URL is not set in the environment")


def _replace_config_placeholders(yaml_config: str) -> str:
    return (
        yaml_config.replace("[[LLAMA_API_URL]]", llama_api_url)
        .replace("[[LLAMA70BV33_API_URL]]", llama70bv33_api_url)
        .replace("[[OSS_API_URL]]", oss_api_url)
    )


@pytest.fixture
def load_agentspec_config() -> AgentSpecConfigLoaderType:
    runtime_class_import_path = os.environ["RUNTIME_CLASS_IMPORT_PATH"]
    runtime_module_import_path, runtime_classname = runtime_class_import_path.rsplit(".", 1)
    runtime_module = __import__(runtime_module_import_path)
    agentspec_runtime_loader_cls = getattr(runtime_module, runtime_classname)

    def load_agentspec_config_wrapper(
        agentspec_config: str,
        tool_registry: Optional[Dict[str, Any]] = None,
        components_registry: Optional[Dict[str, Any]] = None,
    ) -> AgentSpecRunnableComponent:
        return agentspec_runtime_loader_cls.load(
            agentspec_config=_replace_config_placeholders(agentspec_config),
            tool_registry=tool_registry,
            components_registry=components_registry,
        )

    return load_agentspec_config_wrapper


def _start_server_subprocess(
    server_dir: Path, app_import: str, port: int
) -> Tuple[subprocess.Popen, str]:
    process = subprocess.Popen(  # nosec B603
        [
            sys.executable,  # Calls the Python executable
            "-m",
            "uvicorn",
            app_import,  # e.g., "main:app" where main.py file should contain app = FastAPI(...)
            "--port",
            str(port),
            # "--host", "127.0.0.1",
        ],
        cwd=str(server_dir),  # Ensure we run uvicorn in the correct directory
        stdout=subprocess.DEVNULL,  # discard output to avoid PIPE buffer hangs
        stderr=subprocess.STDOUT,
        text=False,
        start_new_session=True,
    )
    return process, f"http://127.0.0.1:{port}"


def _terminate_process_tree(process: subprocess.Popen, timeout: float = 5.0) -> None:
    """Best-effort, cross-platform termination with escalation and stdout close."""
    try:
        if process.poll() is not None:
            return  # already exited
        try:
            process.terminate()
        except Exception:
            logger.warning("Error terminating process")

        # Give it a moment to exit cleanly
        try:
            process.wait(timeout=timeout)
            return
        except Exception:
            logger.warning("Error waiting for process termination")

        try:
            process.kill()
        except Exception:
            logger.warning("Error hard-terminating process")

        # Ensure it is gone
        try:
            process.wait(timeout=timeout)
        except Exception:
            logger.warning("Error waiting for hard-termination of process")

    finally:
        # Close stdout to avoid ResourceWarning if we used a PIPE
        try:
            if getattr(process, "stdout", None) and not process.stdout.closed:
                process.stdout.close()
        except Exception:
            logger.warning("Error closing stdout of process")


def _start_deterministic_llm_fastapi_server() -> Tuple[subprocess.Popen, str]:
    # Build path to local_deterministic_llm_server/main.py
    server_dir = Path(__file__).parent.parent / "local_deterministic_llm_server"
    return _start_server_subprocess(server_dir=server_dir, app_import="main:app", port=5006)


def _make_server_fixture(start_process_func, scope: str = "session"):
    @pytest.fixture(scope=scope)
    def _fixture():
        process, url = start_process_func()
        # Wait a moment for the server to be ready
        time.sleep(5)
        try:
            yield url
        finally:
            _terminate_process_tree(process)

    return _fixture


# Fixture that starts the FastAPI server as a subprocess for the local deterministic LLM server
local_deterministic_llm_server = _make_server_fixture(
    start_process_func=_start_deterministic_llm_fastapi_server, scope="session"
)


# Default (empty) mapping
# Used to provide mappings to the local deterministic llm server
@pytest.fixture
def prompt_to_result_mappings() -> Dict[str, Any]:
    """
    Default implementation – returns an empty mapping.
    A test file can override this fixture to provide its own data.
    """
    return {}


@pytest.fixture
def prompt_regex_to_result_mappings() -> Dict[str, Any]:
    """
    Default implementation – returns an empty regex mapping.
    A test file can override this fixture to provide its own regex data.
    """
    return {}


# Generic setup fixture to set your test-specific prompt-response mappings.
@pytest.fixture(autouse=True)
def setup_llm_server(
    local_deterministic_llm_server,
    prompt_to_result_mappings: Dict[str, Any],
    prompt_regex_to_result_mappings: Dict[str, Any],
):
    """
    1. Make sure the deterministic LLM server is running
       (provided by local_deterministic_llm_server – session scope).
    2. Reset its state.
    3. Push the per-test dictionary mapping.
    """
    reset_url = "http://localhost:5006/v1/chat/reset_output_mappings"
    set_url = "http://localhost:5006/v1/chat/set_output_mappings"
    reset_regex_url = "http://localhost:5006/v1/chat/reset_output_regex_mappings"
    set_regex_url = "http://localhost:5006/v1/chat/set_output_regex_mappings"

    # Always start with a clean slate
    requests.post(reset_url, timeout=5)
    requests.post(reset_regex_url, timeout=5)

    # If this test provided mappings – upload them
    if prompt_to_result_mappings:
        requests.post(set_url, json=prompt_to_result_mappings, timeout=5)
    if prompt_regex_to_result_mappings:
        requests.post(set_regex_url, json=prompt_regex_to_result_mappings, timeout=5)

    # Nothing to return, but pytest expects a yield for autouse teardown symmetry
    yield


# Server for common endpoints (Remote tools and ApiNode calls)
def _start_common_fastapi_server():
    server_dir = Path(__file__).parent
    process = _start_server_subprocess(
        server_dir=server_dir, app_import="common_server:app", port=5008
    )
    return process


# Fixture that starts the FastAPI server as a subprocess for common endpoints (Remote tools and ApiNodes)
local_common_server = _make_server_fixture(
    start_process_func=_start_common_fastapi_server, scope="session"
)


# Server for MCP tools
def _start_remotetool_mcp_server():
    server_dir = Path(__file__).parent / "mcp/"
    process = _start_server_subprocess(
        server_dir=server_dir, app_import="mcp_server:app", port=5007
    )
    return process


# Fixture that starts the FastAPI server as a subprocess for MCP tools
local_mcptool_server = _make_server_fixture(
    start_process_func=_start_remotetool_mcp_server, scope="session"
)
