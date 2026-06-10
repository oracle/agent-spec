# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
Test configuration for the OpenAI Agents flows adapter.

Adds local src paths for the adapter and vendored Agents SDK so imports
like `pyagentspec.adapters.openaiagents` and `agents` resolve during tests.
"""

import os
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest

from ..conftest import skip_tests_if_dependency_not_installed


def _add_path(p: Path) -> None:
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)


# Path layout (relative to this file):
# pyagentspec/agent-spec-public/adapters/openaiagentspecadapter/tests/conftest.py
TESTS_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = TESTS_DIR.parent
AGENT_SPEC_PUBLIC_DIR = ADAPTER_DIR.parent.parent
PYAGENTSPEC_DIR = AGENT_SPEC_PUBLIC_DIR.parent

# Ensure test helpers in this directory (e.g., retry_utils.py) are importable
_add_path(TESTS_DIR)

# Require installed packages; allow explicit opt-in to local dev fallback
DEV_FALLBACK = (Path.cwd() / ".dev_fallback").exists()

if DEV_FALLBACK:
    _add_path(ADAPTER_DIR / "src")
    _add_path(PYAGENTSPEC_DIR / "openai-agents-python" / "src")


@pytest.fixture(scope="package", autouse=True)
def _disable_openai_agents_trace_export() -> Iterator[None]:
    """
    Disable OpenAI Agents SDK trace export while adapter tests run.

    The SDK exports traces to api.openai.com when tracing is enabled and an
    OPENAI_API_KEY is present. Adapter tests use a fake key, so keep SDK trace
    export disabled without leaving the environment changed for later tests.
    """
    env_name = "OPENAI_AGENTS_DISABLE_TRACING"
    old_value = os.environ.get(env_name)
    os.environ[env_name] = "1"

    try:
        from agents import set_tracing_disabled
    except ImportError:
        set_tracing_disabled = None
    else:
        set_tracing_disabled(True)

    try:
        yield
    finally:
        if old_value is not None:
            os.environ[env_name] = old_value
        else:
            os.environ.pop(env_name, None)

        if set_tracing_disabled is not None:
            tracing_disabled = os.environ.get(env_name, "false").lower() in ("1", "true")
            set_tracing_disabled(tracing_disabled)


def pytest_collection_modifyitems(config: Any, items: Any):
    # We skip all the tests in this folder if agents is not installed
    skip_tests_if_dependency_not_installed(
        module_name="agents",
        directory=Path(__file__).parent,
        items=items,
    )
