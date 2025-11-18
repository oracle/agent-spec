# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
import random
import socket
import subprocess  # nosec, test-only code, args are trusted
import time
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

SKIP_LLM_TESTS_ENV_VAR = "SKIP_LLM_TESTS"


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
while (
    is_port_busy(JSON_SERVER_PORT := random.randint(8000, 9000))  # nosec, not for security/crypto
    and attempt < 5
):
    time.sleep(1)
    attempt += 1

JSON_SERVER_PORT = JSON_SERVER_PORT if attempt < 5 else None
IS_JSON_SERVER_RUNNING = False


def _start_json_server() -> subprocess.Popen:
    api_server = Path(__file__).parent / "api_server.py"
    process = subprocess.Popen(  # nosec, test context and trusted env
        [
            "fastapi",
            "run",
            str(api_server.absolute()),
            f"--port={JSON_SERVER_PORT}",
        ]
    )
    time.sleep(3)
    return process


def should_skip_llm_test() -> bool:
    """Return True if LLM-related tests should be skipped."""
    return os.environ.get(SKIP_LLM_TESTS_ENV_VAR) == "1"


@pytest.fixture(scope="session", autouse=True)
def _seed_llm_env_for_skip():
    """
    When SKIP_LLM_TESTS=1, seed harmless dummy endpoints so imports/deserialization
    never crash on missing env vars.
    """
    if should_skip_llm_test():
        os.environ.setdefault("LLAMA_API_URL", "http://dummy-llm.local")
        os.environ.setdefault("LLAMA70BV33_API_URL", "http://dummy-llm70.local")
    yield


LLM_MOCKED_METHODS = [
    "pyagentspec.llms.vllmconfig.VllmConfig.__init__",
    "pyagentspec.llms.ocigenaiconfig.OciGenAiConfig.__init__",
    "pyagentspec.llms.openaicompatibleconfig.OpenAiCompatibleConfig.__init__",
]


@pytest.fixture(scope="session", autouse=True)
def skip_llm_construction():
    """
    When SKIP_LLM_TESTS=1, any attempt to construct an LLM config triggers a skip.
    """

    def _skip(*_args, **_kwargs):
        pytest.skip("LLM called, skipping test (SKIP_LLM_TESTS=1)")

    patches = []
    if should_skip_llm_test():
        for dotted in LLM_MOCKED_METHODS:
            p = patch(dotted, side_effect=_skip)
            p.start()
            patches.append(p)

    try:
        yield
    finally:
        for p in patches:
            p.stop()


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
