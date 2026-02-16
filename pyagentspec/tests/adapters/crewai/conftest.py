# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pytest
import requests

from ..conftest import (
    should_skip_llm_test,
    skip_tests_if_dependency_not_installed,
)


def pytest_collection_modifyitems(config: Any, items: Any):
    # We skip all the tests in this folder if crewai is not installed
    skip_tests_if_dependency_not_installed(
        module_name="crewai",
        directory=Path(__file__).parent,
        items=items,
    )


@pytest.fixture(scope="package", autouse=True)
def _disable_tracing():
    """Disable the automatic tracing of crewai"""
    old_value = os.environ.get("CREWAI_DISABLE_TELEMETRY", None)
    os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
    try:
        yield
    finally:
        if old_value is not None:
            os.environ["CREWAI_DISABLE_TELEMETRY"] = old_value


@pytest.fixture(autouse=True)
def no_network_plusapi(monkeypatch):
    try:
        from crewai.cli.plus_api import PlusAPI

        def fake_response(self, method: str, endpoint: str, **kwargs) -> requests.Response:
            resp = requests.Response()
            resp.status_code = 200
            resp.url = urljoin(self.base_url, endpoint)
            resp.headers["Content-Type"] = "application/json"
            resp._content = json.dumps({"ok": True}).encode("utf-8")
            resp.encoding = "utf-8"
            return resp

        monkeypatch.setattr(PlusAPI, "_make_request", fake_response, raising=True)
    except ImportError:
        pass


@pytest.fixture
def mute_crewai_console_prints():
    try:
        from crewai.events.event_listener import event_listener as default_listener
        from crewai.events.utils.console_formatter import ConsoleFormatter
    except Exception:
        return

    default_listener.formatter = ConsoleFormatter(verbose=False)


@pytest.fixture
def crewai_llama():
    from crewai import LLM

    llama_endpoint = os.environ.get("LLAMA_API_URL")
    if not llama_endpoint:
        if should_skip_llm_test():
            pytest.skip(
                "Skipping LLM-dependent test: LLAMA_API_URL is not set and SKIP_LLM_TESTS is enabled"
            )
        pytest.fail("LLAMA_API_URL is not set in the environment")

    return LLM(
        model="hosted_vllm/meta-llama/Meta-Llama-3.1-8B-Instruct",
        api_base=llama_endpoint,
    )
