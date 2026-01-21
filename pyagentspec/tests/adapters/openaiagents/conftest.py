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

import sys
from pathlib import Path
from typing import Any

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


def pytest_collection_modifyitems(config: Any, items: Any):
    # We skip all the tests in this folder if langgraph is not installed
    skip_tests_if_dependency_not_installed(
        module_name="agents",
        directory=Path(__file__).parent,
        items=items,
    )
